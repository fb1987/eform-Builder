# app/normalizers.py
from __future__ import annotations
import re
from typing import Any, Dict, List

_NEED_LABEL = {
    "MENU","MENU_MULTI_SELECT","NUMERIC_SCALE","PROPOSITION","CHECKBOX",
    "LABEL","TEXT_FIELD","TEXT_FIELD_NUMERIC","TEXT_AREA","DATE","TIME",
    "APPROXIMATE_DATE","APPROXIMATE_DURATION","FILE_UPLOAD"
}

def _drop_unknowns(obj: Dict[str, Any]) -> None:
    # Remove fields our schema doesn't know about (common LLM artifacts)
    obj.pop("kind", None)

def _ensure_label(it: Dict[str, Any]) -> None:
    t = (it.get("type") or "").upper()
    if t in _NEED_LABEL:
        if not it.get("label") and isinstance(it.get("text"), str) and it["text"].strip():
            it["label"] = it.pop("text")

def _fix_formula(it: Dict[str, Any]) -> None:
    if (it.get("type") or "").upper() != "FORMULA":
        return
    f = it.get("formula")
    if not isinstance(f, str):
        return
    # {ref} -> ref.r
    f = re.sub(r"\{([A-Za-z0-9_]+)\}", r"\1.r", f)

    # SUM(a,b,c) -> a.p + b.p + c.p
    def _sum_to_plus(m: re.Match) -> str:
        inner = m.group(1)
        toks = [tok.strip() for tok in inner.split(",") if tok.strip()]
        parts: List[str] = []
        for tok in toks:
            parts.append(tok if re.search(r"\.(p|r)\b", tok) else f"{tok}.p")
        return " + ".join(parts)
    f = re.sub(r"(?i)\bSUM\s*\(([^)]+)\)", _sum_to_plus, f)
    it["formula"] = f

def _fix_logic_expr(expr: str) -> str:
    # turn single '=' used as comparison into '==', but don't touch <=, >=, !=
    expr = re.sub(r"(?<![<>!=])=(?!=)", "==", expr)

    # ConsentDecision == 'Yes' -> ConsentDecision.r == 'YES'
    expr = re.sub(
        r"([A-Za-z_][A-Za-z0-9_]*)\s*==\s*'?(Yes|No|Not[ _]?Sure)'?",
        lambda m: f"{m.group(1)}.r == '{m.group(2).upper().replace(' ','_')}'",
        expr,
        flags=re.I,
    )
    return expr

def _normalize_logic(it: Dict[str, Any]) -> None:
    for key in ("showIf", "makeNoteIf"):
        if isinstance(it.get(key), str):
            it[key] = _fix_logic_expr(it[key])

def _coerce_yes_no_menu(it: Dict[str, Any]) -> None:
    """Convert NO_YES_NOT_SURE (or similar) into a MENU with explicit choices."""
    t = (it.get("type") or "").upper()
    if t in {"NO_YES_NOT_SURE", "YES_NO", "NO_YES"}:
        it["type"] = "MENU"
        # Only build choices if none provided
        if not isinstance(it.get("choices"), list) or not it["choices"]:
            it["choices"] = [
                {"val": "YES", "points": 1.0, "display": "Yes"},
                {"val": "NO", "points": 0.0, "display": "No"},
                {"val": "NOT_SURE", "points": 0.0, "display": "Not sure"},
            ]

def _ensure_menu_choice_points(it: Dict[str, Any]) -> None:
    if (it.get("type") or "").upper() not in {"MENU", "MENU_MULTI_SELECT", "NUMERIC_SCALE"}:
        return
    ch = it.get("choices")
    if not isinstance(ch, list):
        return
    for c in ch:
        if isinstance(c, dict):
            # default display to val
            if "display" not in c and isinstance(c.get("val"), str):
                c["display"] = c["val"]
            # default points
            if "points" not in c:
                c["points"] = 0.0

def _fix_section_defaults(sec: Dict[str, Any]) -> None:
    # Ensure the first/top-level authoring section renders as a questionnaire
    if not isinstance(sec.get("subcategory"), str) or not sec["subcategory"].strip():
        sec["subcategory"] = "QUESTIONNAIRE"

def _fix_item_dict(it: Dict[str, Any]) -> None:
    _drop_unknowns(it)
    _coerce_yes_no_menu(it)
    _ensure_label(it)
    _ensure_menu_choice_points(it)
    _normalize_logic(it)
    _fix_formula(it)

def _walk(node: Any, in_section: bool = False) -> None:
    if isinstance(node, dict):
        # Section object?
        if "items" in node and isinstance(node.get("items"), list):
            # It's likely a section
            _drop_unknowns(node)
            _fix_section_defaults(node)
            for child in node["items"]:
                _walk(child)
        # Item object?
        if "type" in node and isinstance(node["type"], str):
            _fix_item_dict(node)
        # Recurse other dict values
        for v in list(node.values()):
            _walk(v)
    elif isinstance(node, list):
        for x in node:
            _walk(x)

def harden_cir(cir: Dict[str, Any]) -> Dict[str, Any]:
    """Repairs common LLM-produced CIR issues so JSON Schema validation passes."""
    _drop_unknowns(cir)
    _walk(cir)
    return cir
