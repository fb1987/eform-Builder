# app/normalizers_soft.py
from __future__ import annotations
import re, json, copy, logging
from typing import Dict, List, Any, Optional

log = logging.getLogger("uvicorn.error")

RESERVED_TOKENS = {
    "true","false","null",
    "pt","firstTime","lastCompletedTag","daysSinceLastCompleted",
    "ScriptUtil","Math"
}

def _fix_expression(expr: str) -> str:
    """Heuristic repairs for common Ocean eForm scripting mistakes from LLM output."""
    s = (expr or "").strip()
    if not s:
        return s

    # Replace single '=' (not part of >=, <=, !=, ==) with '=='
    s = re.sub(r'(?<![!<>=])=(?!=)', '==', s)

    # Replace {ref} with ref
    s = re.sub(r'\{ *([A-Za-z_]\w*) *\}', r'\1', s)

    # SUM(a,b,c) -> (a.p + b.p + c.p)
    def repl_sum(m):
        args = [a.strip() for a in m.group(1).split(',') if a.strip()]
        terms = [(a if re.search(r'\.(p|r)\b', a) else f"{a}.p") for a in args]
        return "(" + " + ".join(terms) + ")"
    s = re.sub(r'\bSUM\s*\(\s*([^)]+?)\s*\)', repl_sum, s, flags=re.IGNORECASE)

    # For comparisons to quoted strings, ensure left side uses .r when missing
    s = re.sub(
        r'(\b[A-Za-z_]\w*\b)\s*(==|!=)\s*([\'"][^\'"]+[\'"])',
        lambda m: (
            (m.group(1) if re.search(r'\.(p|r)\b', m.group(1)) else f"{m.group(1)}.r")
            + " " + m.group(2) + " " + m.group(3)
        ),
        s
    )

    # For numeric comparisons, ensure .p on the left if missing
    s = re.sub(
        r'(\b[A-Za-z_]\w*\b)\s*(>=|<=|>|<)\s*([0-9][0-9]*\.?[0-9]*)',
        lambda m: (
            (m.group(1) if re.search(r'\.(p|r)\b', m.group(1)) else f"{m.group(1)}.p")
            + " " + m.group(2) + " " + m.group(3)
        ),
        s
    )

    # If arithmetic present, add .p to bare refs (avoid reserved tokens / already-qualified)
    if re.search(r'[\+\-/*]', s):
        def add_p(tok: re.Match) -> str:
            t = tok.group(0)
            if t in RESERVED_TOKENS or t.startswith("ScriptUtil") or re.search(r'\.(p|r)\b', t):
                return t
            if re.fullmatch(r'[A-Za-z_]\w*', t):
                return t + ".p"
            return t
        s = re.sub(r'\b[A-Za-z_]\w*\b', add_p, s)

    return s

def _move_section_root_attrs_to_attributes(sec: Dict[str, Any]) -> None:
    a = sec.setdefault("attributes", {})
    for key in ("subcategory","headerStyle","expandIf","showIf","makeNoteIf","flag","noteIndex"):
        if key in sec and key not in ("items","kind","ref","attributes"):
            val = sec.pop(key, None)
            if val is not None:
                a[key] = val
    # booleans
    for key in ("groupItems","quoteAnswers","ownLine"):
        if key in sec and key not in ("items","kind","ref","attributes"):
            val = sec.pop(key, None)
            if val is not None:
                a[key] = bool(val)

def _looks_like_prefill(text: str) -> bool:
    """Heuristic: leave in <text> if it's a macro / prefill."""
    return bool(re.search(r'@pt|@ptCpp|@pt[A-Z]|ScriptUtil', text or ""))

def _normalize_item(x: Dict[str, Any]) -> None:
    x["kind"] = "item"
    x["type"] = (x.get("type") or "LABEL").upper()

    # Caption vs default text
    label = x.get("label")
    text  = x.get("text")
    if (not label) and text and not _looks_like_prefill(text):
        x["label"] = text
        x["text"]  = None

    # FORMULA notes: prefer cNote (for $$ rendering in notes)
    if x["type"] == "FORMULA":
        if not x.get("cNote") and (x.get("tooltip") or x.get("text")):
            x["cNote"] = x.get("tooltip") or x.get("text")
        # Common LLM mistake: SUM(q1,...)
        if x.get("formula"):
            x["formula"] = _fix_expression(x["formula"])

    # Normalize validator
    v = x.get("validator")
    if isinstance(v, str):
        x["validator"] = {"type": v}
    elif isinstance(v, dict):
        if "type" in v and v["type"] is None:
            v.pop("type")

    # Hints list
    if isinstance(x.get("hints"), list):
        x["hints"] = [str(h) for h in x["hints"]]

    # Choices normalization
    if isinstance(x.get("choices"), list):
        for ch in x["choices"]:
            if not isinstance(ch, dict):
                continue
            # points -> float if numeric string
            if "points" in ch and isinstance(ch["points"], str):
                try:
                    ch["points"] = float(ch["points"])
                except Exception:
                    ch["points"] = None
            # Avoid pipe in vals
            if isinstance(ch.get("val"), str) and "|" in ch["val"]:
                ch["val"] = ch["val"].replace("|", "/")

    # Fix showIf / makeNoteIf after we know the item type
    for cond_key in ("showIf","makeNoteIf"):
        if isinstance(x.get(cond_key), str):
            x[cond_key] = _fix_expression(x[cond_key])

def _walk_section(sec: Dict[str, Any]) -> None:
    sec["kind"] = "section"
    _move_section_root_attrs_to_attributes(sec)

    # default subcategory for first level sections if absent
    attrs = sec.setdefault("attributes", {})
    if "subcategory" not in attrs:
        attrs["subcategory"] = "QUESTIONNAIRE"

    items = sec.get("items")
    if not isinstance(items, list):
        sec["items"] = []
        return
    for i, ch in enumerate(items):
        if not isinstance(ch, dict):
            continue
        k = ch.get("kind")
        if k == "section" or ("items" in ch and "type" not in ch):
            ch["kind"] = "section"
            _walk_section(ch)
        else:
            _normalize_item(ch)

def soft_repair_cir(cir: Dict[str, Any]) -> Dict[str, Any]:
    """Make best-effort, conservative repairs to the model-produced CIR so it passes validation more often."""
    data = copy.deepcopy(cir or {})
    meta = data.setdefault("meta", {})
    meta.setdefault("noteVersion", 2)
    meta.setdefault("noteType", "progress")
    meta.setdefault("dataSecurityMode", "encrypted")

    # Ensure sections
    secs = data.setdefault("sections", [])
    if not secs:
        secs.append({"kind":"section","ref":"__section","attributes":{"subcategory":"QUESTIONNAIRE"},"items":[]})

    # Normalize all sections/items
    for s in secs:
        if isinstance(s, dict):
            _walk_section(s)

    # As a final sweep, fix any loose expression strings on top-level items (unlikely)
    return data
