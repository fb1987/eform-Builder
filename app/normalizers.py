# app/normalizers.py
from __future__ import annotations
import re
from typing import Any, Dict, List

# Item types that must render a visible prompt (<c>) rather than using <text>
_NEED_LABEL = {
    "MENU","MENU_MULTI_SELECT","NUMERIC_SCALE","PROPOSITION","CHECKBOX",
    "NO_YES_NOT_SURE","LABEL","TEXT_FIELD","TEXT_FIELD_NUMERIC","TEXT_AREA",
    "DATE","TIME","APPROXIMATE_DATE","APPROXIMATE_DURATION","FILE_UPLOAD"
}

def _fix_item_dict(it: Dict[str, Any]) -> None:
    t = (it.get("type") or "").upper()

    # 1) Move prompts from 'text' -> 'label' for items that should show a question caption.
    if t in _NEED_LABEL:
        if not it.get("label") and isinstance(it.get("text"), str) and it["text"].strip():
            # For question types, 'text' should not be the prompt. Promote to label.
            it["label"] = it.pop("text")

    # 2) Repair FORMULA expressions:
    if t == "FORMULA":
        f = it.get("formula")
        if isinstance(f, str):
            # Replace {ref} placeholders with ref.r
            f = re.sub(r"\{([A-Za-z0-9_]+)\}", r"\1.r", f)
            # Replace SUM(a,b,c) with a.p + b.p + c.p
            def _sum_to_plus(m: re.Match) -> str:
                inner = m.group(1)
                toks = [tok.strip() for tok in inner.split(",") if tok.strip()]
                parts: List[str] = []
                for tok in toks:
                    parts.append(tok if re.search(r"\.(p|r)\b", tok) else f"{tok}.p")
                return " + ".join(parts)
            f = re.sub(r"(?i)SUM\s*\(([^)]+)\)", _sum_to_plus, f)
            it["formula"] = f

    # 3) Normalize simple string comparisons in showIf/makeNoteIf:
    for key in ("showIf", "makeNoteIf"):
        expr = it.get(key)
        if isinstance(expr, str):
            # consentChoice == 'Yes'  -> consentChoice.r == 'YES'
            expr = re.sub(
                r"([A-Za-z_][A-Za-z0-9_]*)\s*==\s*'?(Yes|No|Not[ _]?Sure)'?",
                lambda m: f"{m.group(1)}.r == '{m.group(2).upper().replace(' ','_')}'",
                expr,
                flags=re.I,
            )
            it[key] = expr

def _walk(node: Any) -> None:
    if isinstance(node, dict):
        if "type" in node and isinstance(node["type"], str):
            _fix_item_dict(node)
        # Recurse all values
        for v in list(node.values()):
            _walk(v)
    elif isinstance(node, list):
        for x in node:
            _walk(x)

def harden_cir(cir: Dict[str, Any]) -> Dict[str, Any]:
    """In-place corrections for common LLM mistakes that break Ocean XML."""
    _walk(cir)
    return cir
