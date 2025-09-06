# Builds a compact guidance block from knowledge/runtime for CIR generation.

from __future__ import annotations
import os, json
from typing import Dict, Any, List
from app.knowledge_loader import Knowledge, DEFAULT_KNOWLEDGE_DIR

# Where the compressed knowledge lives (you uploaded this under repo root)
KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", DEFAULT_KNOWLEDGE_DIR)

# Load once at import; fall back to a minimal, no-op guidance if missing.
_KNOWLEDGE_ERR = None
try:
    _K = Knowledge(KNOWLEDGE_DIR)
    _KNOWLEDGE_OK = True
except Exception as e:
    _K = None
    _KNOWLEDGE_ERR = str(e)
    _KNOWLEDGE_OK = False

# -------- helpers --------

def _take(lst: List[Any], n: int) -> List[Any]:
    return list(lst or [])[:n]

def _emit_bundle_text(bundle: Dict[str, Any], per_type_limit: int = 6) -> str:
    """
    Turn a compact bundle into a short, LLM-friendly guidance string.
    Keep this concise: it's appended to the system message.
    """
    lines: List[str] = []

    acc = _take(bundle.get("acceptance_checks"), 12)
    if acc:
        lines.append("ACCEPTANCE_CHECKS:")
        for a in acc:
            lines.append(f"- {a}")

    sec = bundle.get("section_style") or {}
    derived = _take(sec.get("derived"), 6)
    rules   = _take(sec.get("rules"), 6)
    if derived or rules:
        lines.append("\nSECTION_STYLE:")
        for r in derived: lines.append(f"- {r}")
        for r in rules:   lines.append(f"- {r}")

    scr = bundle.get("scripting") or {}
    idioms = _take(scr.get("idioms"), 8)
    if idioms:
        lines.append("\nSCRIPTING_IDIOMS:")
        for i in idioms:
            pat = (i or {}).get("pattern","")
            ex  = (i or {}).get("example") or ""
            lines.append(f"- {pat}" + (f"  (e.g., {ex})" if ex else ""))

    its: Dict[str,Any] = bundle.get("item_types") or {}
    if its:
        lines.append("\nITEM_TYPES_GUIDE:")
        for t, g in its.items():
            lines.append(f"- {t}:")
            req = _take(g.get("required"), per_type_limit)
            rec = _take(g.get("recommended"), max(2, per_type_limit//2))
            anti= _take(g.get("anti_patterns"), max(2, per_type_limit//2))
            vals= _take(g.get("validators_common"), 3)
            hints=_take(g.get("hints_common"), 3)
            ca  = _take(g.get("choice_authoring"), 3)

            for r in req:
                text = r.get("rule") if isinstance(r, dict) else str(r)
                lines.append(f"  * MUST: {text}")
            for r in rec:
                text = r.get("rule") if isinstance(r, dict) else str(r)
                lines.append(f"  * SHOULD: {text}")
            for r in anti:
                text = r.get("rule") if isinstance(r, dict) else str(r)
                lines.append(f"  * AVOID: {text}")
            if vals:
                lines.append(f"  * VALIDATORS: {', '.join(vals)}")
            if hints:
                lines.append(f"  * HINTS: {', '.join(hints)}")
            if ca:
                lines.append(f"  * CHOICE_AUTHORING: {', '.join(ca)}")

    rn = bundle.get("ref_naming") or {}
    recipes = _take(rn.get("recipes"), 2)
    if recipes:
        lines.append("\nREF_NAMING:")
        for r in recipes:
            if isinstance(r, dict) and r.get("recipe"):
                lines.append(f"- {r['recipe']}")
            elif isinstance(r, str):
                lines.append(f"- {r}")

    macros = _take(bundle.get("macros"), 8)
    if macros:
        lines.append("\nCOMMON_MACROS:")
        for m in macros:
            macro = (m or {}).get('macro','')
            if macro:
                lines.append(f"- {macro}")

    text = "\n".join(lines)
    # Hard cap to avoid bloating the system prompt (~12k chars)
    return text[:12000]

# -------- public API used by openai_client --------

_OCEAN_STRICT = """
OCEAN-STRICT RULES (do not violate):
- Put the patient-visible prompt in <c>. Reserve <text> for default values/macros only (e.g., @ptCpp.*).
- Conditions must use JavaScript with .p (numeric points) or .r (response text). Examples:
  * Show if answer is chosen:   someItem.p > 0   or   someItem.r == 'Yes'
  * PROPOSITION/NO_YES_NOT_SURE often compare .r to 'Y'/'N'/'U'.
- Never invent functions. Do NOT use SUM(). Use either q1.p+q2.p+... or ScriptUtil.sum(sectionRef).
- '$$' expands the current item's own value in its <c> or <cNote> only. To show other items' values, compose a string in a FORMULA (e.g., name.r + '...' + date.r) and output it via <cNote> using $$.
- MENUs must include a <choices> block with >= 2 <choice> entries. Avoid '|' in choice@val. Set points explicitly when scoring.
- Add validators where common (e.g., MANDATORY on required fields; EMAIL/PHONE/POSTAL_CODE/REG_EXP where applicable).
- First top-level section must map to subcategory='QUESTIONNAIRE'.
- Refs must match ^[A-Za-z0-9_]+$ and be unique within the form.
- If you add a total score FORMULA, prefer showIf="false" and report the value in <cNote> with $$.
""".strip()

def build_guidance_block(user_text: str, defaults: Dict) -> str:
    """
    Returns a compact, evidence-based guidance block to append to the system prompt.
    If knowledge pack isn't available, returns a strict fallback so your pipeline still runs.
    """
    header = [
    "DATA_GUIDANCE:",
    "- Output MUST satisfy CIR_JSON_SCHEMA; fields map 1:1 to Ocean eForm XML.",
    "- Include 'kind' for every node (section/item).",
    "- Keep refs unique; avoid '|' in choice@val."
    "- FORMULA must be a single JavaScript expression (no function/var/let/const/return). Prefer simple arithmetic using .p (e.g., q1.p + q2.p) or ScriptUtil.sum(sectionRef).",
    "- For conditionals, use boolean expressions (e.g., q1.p >= 2) or a nested ternary to produce strings. For bucketed outputs (e.g., severity bands), prefer hidden LABEL items with makeNoteIf or a ternary expression, not function bodies.",
    "- When comparing to strings, use .r (e.g., consentChoice.r == 'Yes'); for numeric arithmetic/thresholds, use .p (e.g., score.p >= 10). Never chain .p/.r (e.g., avoid '.p.p' or '.r.p').",
    ]


    if not _KNOWLEDGE_OK:
        body = "\n".join([
            f"(knowledge pack unavailable: {KNOWLEDGE_DIR} — {_KNOWLEDGE_ERR})",
            _OCEAN_STRICT
        ])
        return "\n".join(header) + "\n\n" + body

    # Predict relevant item types from the user's description, then bundle compact guidance.
    predicted_types = _K.predict_item_types(user_text or "")
    bundle = _K.bundle(include_types=predicted_types)

    header.append(f"- Selected item types (from request): {', '.join(predicted_types)}")
    body = _emit_bundle_text(bundle)

    # Always append the non-negotiable Ocean rules.
    return "\n".join(header) + "\n\n" + _OCEAN_STRICT + ("\n\n" + body if body else "")
