# app/normalizers.py
from __future__ import annotations
import re
from typing import Any, Dict, List

PHQ_DISPLAY_TO_POINTS = {
    "Not at all": 0.0,
    "Several days": 1.0,
    "More than half the days": 2.0,
    "Nearly every day": 3.0,
}

def _ensure_kind(obj: Dict[str, Any], k: str) -> None:
    if obj.get("kind") != k:
        obj["kind"] = k

def _strip_json_only_fields(obj: Dict[str, Any]) -> None:
    # JSON-level fields our schema doesn't accept
    if "subcategory" in obj:
        obj.pop("subcategory")

def _to_validators_list(it: Dict[str, Any]) -> None:
    # Accept either "validator": {...} or "validators": [...]
    if "validators" in it and isinstance(it["validators"], list):
        return
    v = it.get("validator")
    if isinstance(v, dict):
        if "allowEmpty" not in v:
            # default to false unless explicitly true
            v["allowEmpty"] = False
        it["validators"] = [v]
        it.pop("validator", None)

def _ensure_label(it: Dict[str, Any]) -> None:
    if "label" not in it:
        # Many LLMs put prompt into "text"
        if isinstance(it.get("text"), str) and it["text"].strip():
            it["label"] = it.pop("text")

def _fix_choice_points_and_display(it: Dict[str, Any]) -> None:
    t = (it.get("type") or "").upper()
    if t not in {"MENU", "MENU_MULTI_SELECT", "NUMERIC_SCALE"}:
        return
    ch = it.get("choices")
    if not isinstance(ch, list):
        return
    for c in ch:
        if not isinstance(c, dict):
            continue
        # default display to val
        if "display" not in c and isinstance(c.get("val"), str):
            c["display"] = c["val"]
        # If points are missing, derive them
        if "points" not in c:
            # PHQ-9 heuristics
            disp = c.get("display")
            if isinstance(disp, str) and disp in PHQ_DISPLAY_TO_POINTS:
                c["points"] = PHQ_DISPLAY_TO_POINTS[disp]
            else:
                val = c.get("val")
                if isinstance(val, (int, float)) or (isinstance(val, str) and val.isdigit()):
                    c["points"] = float(val)
                else:
                    c["points"] = 0.0

def _coerce_yes_no_menu(it: Dict[str, Any]) -> None:
    t = (it.get("type") or "").upper()
    if t in {"NO_YES_NOT_SURE", "YES_NO", "NO_YES"}:
        it["type"] = "MENU"
        if not isinstance(it.get("choices"), list) or not it["choices"]:
            it["choices"] = [
                {"val": "YES", "display": "Yes", "points": 1.0},
                {"val": "NO", "display": "No", "points": 0.0},
                {"val": "NOT_SURE", "display": "Not sure", "points": 0.0},
            ]

_BRACED = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")

def _fix_logic_expr(expr: str, numeric_default: bool = True) -> str:
    # {ref} -> ref.p (for numeric contexts) or ref.r (fallback)
    def repl(m):
        name = m.group(1)
        return f"{name}.p" if numeric_default else f"{name}.r"
    expr = _BRACED.sub(repl, expr)
    # single '=' used as comparison -> '=='
    expr = re.sub(r"(?<![<>!=])=(?!=)", "==", expr)
    # normalize literal Yes/No/Not sure comparisons to .r with canonical values
    expr = re.sub(
        r"([A-Za-z_][A-Za-z0-9_]*)\s*==\s*'?(Yes|No|Not[ _]?Sure)'?",
        lambda m: f"{m.group(1)}.r == '{m.group(2).upper().replace(' ', '_')}'",
        expr,
        flags=re.I,
    )
    return expr

def _fix_formula(it: Dict[str, Any]) -> None:
    if (it.get("type") or "").upper() != "FORMULA":
        return
    f = it.get("formula")
    if not isinstance(f, str):
        return
    # {ref} -> ref.r (string interpolation in formulas typically wants .r)
    f = _BRACED.sub(lambda m: f"{m.group(1)}.r", f)

    # SUM(a,b,c) -> a.p + b.p + c.p
    def _sum_to_plus(m):
        inner = m.group(1)
        toks = [tok.strip() for tok in inner.split(",") if tok.strip()]
        parts: List[str] = []
        for tok in toks:
            parts.append(tok if re.search(r"\.(p|r)\b", tok) else f"{tok}.p")
        return " + ".join(parts)
    f = re.sub(r"(?i)\bSUM\s*\(([^)]+)\)", _sum_to_plus, f)

    # If we detect arithmetic with refs using .r, convert them to .p
    # e.g., (q1.r + q2.r) -> (q1.p + q2.p)
    if re.search(r"[+\-*/]", f):
        f = re.sub(r"\b([A-Za-z_][A-Za-z0-9_]*)\.r\b", r"\1.p", f)

    it["formula"] = f

def _normalize_logic(it: Dict[str, Any]) -> None:
    for key in ("showIf", "makeNoteIf"):
        if isinstance(it.get(key), str):
            # numeric defaults for conditions like ({q1} > 0)
            it[key] = _fix_logic_expr(it[key], numeric_default=True)

def _fix_item(it: Dict[str, Any]) -> None:
    _ensure_kind(it, "item")
    _coerce_yes_no_menu(it)
    _ensure_label(it)
    _to_validators_list(it)
    _fix_choice_points_and_display(it)
    _normalize_logic(it)
    _fix_formula(it)

def _walk(node: Any) -> None:
    if isinstance(node, dict):
        if "sections" in node and isinstance(node["sections"], list):
            for s in node["sections"]:
                _ensure_kind(s, "section")
                _strip_json_only_fields(s)
                if isinstance(s.get("items"), list):
                    for it in s["items"]:
                        if isinstance(it, dict):
                            _fix_item(it)
        else:
            for v in node.values():
                _walk(v)
    elif isinstance(node, list):
        for x in node:
            _walk(x)

def harden_cir(cir: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_kind(cir, "form")
    _walk(cir)
    return cir
