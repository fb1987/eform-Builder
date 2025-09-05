# app/guidance.py
# Builds a compact guidance block from knowledge/runtime for CIR generation.

from __future__ import annotations
import os, json, re
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

def _lines() -> List[str]:
    return []

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
            pat = i.get("pattern","")
            ex  = i.get("example") or ""
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
            lines.append(f"- {m.get('macro','')}")

    text = "\n".join(lines)
    # Hard cap to avoid bloating the system prompt (keep ~8–10k chars)
    return text[:12000]

# -------- public API used by openai_client --------

def build_guidance_block(user_text: str, defaults: Dict) -> str:
    """
    Returns a compact, evidence-based guidance block to append to the system prompt.
    If knowledge pack isn't available, returns a short fallback so your pipeline still runs.
    """
    if not _KNOWLEDGE_OK:
        return (
            "DATA_GUIDANCE:\n"
            f"(knowledge pack unavailable: {KNOWLEDGE_DIR} — {_KNOWLEDGE_ERR})\n"
            "- Proceed with schema-compliant CIR. Ensure top-level section maps to subcategory='QUESTIONNAIRE' in XML.\n"
            "- Enforce: unique refs [A-Za-z0-9_]+, MENU/MENU_MULTI_SELECT have >= 2 choices, no '|' in choice@val, FORMULA has formula.\n"
        )

    # Predict relevant item types from the user's description.
    predicted_types = _K.predict_item_types(user_text or "")
    bundle = _K.bundle(include_types=predicted_types)

    header = [
        "DATA_GUIDANCE:",
        f"- Selected item types: {', '.join(predicted_types)}",
        "- Output must satisfy CIR_JSON_SCHEMA; fields map 1:1 to Ocean eForm XML.",
        "- Ensure first top-level section in CIR becomes subcategory='QUESTIONNAIRE' in XML.",
        "- Keep refs unique (^[A-Za-z0-9_]+$). For MENU / MENU_MULTI_SELECT include >= 2 choices; no '|' in choice@val.",
        "- Use validators where common (e.g., MANDATORY/REG_EXP/PHONE/EMAIL/POSTAL_CODE).",
        "HARD_RULES:",
        "- Put the question prompt in 'label' (maps to <c>), not 'text'. Use 'text' only for prefill/defaults.",
        "- FORMULA must be an expression (e.g., 'q1.p + q2.p + ...' or 'ScriptUtil.sum(sectionRef)'); never use SUM().",
        "- To emit a calculated value into notes, set cNote and use '$$'.",
        "- In showIf/makeNoteIf, always compare '.r' or '.p' (e.g., consentChoice.r == 'YES', q1.p >= 2).",
    ]
    body = _emit_bundle_text(bundle)
    return "\n".join(header) + "\n\n" + body
