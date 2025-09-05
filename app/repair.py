from __future__ import annotations
import os, re, copy
from typing import Dict, List, Set, Tuple

AUTO_REPAIR_ENABLED = os.getenv("AUTO_REPAIR", "1") != "0"

# -------- helpers --------

_EQ_SINGLE = re.compile(r"(?<![=!<>])=(?!=)")          # lone "=" -> "=="
CURLY_REF = re.compile(r"\{([A-Za-z0-9_]+)\}")         # {q1} -> q1
TOKEN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]{0,63})\b")

def _is_number_literal(s: str) -> bool:
    try:
        float(s)
        return True
    except Exception:
        return False

def _split_csv(s: str) -> List[str]:
    return [t.strip() for t in s.split(",") if t.strip()]

def _fix_sum(formula: str, item_refs: Set[str], section_refs: Set[str]) -> str:
    if not formula:
        return formula
    f = formula.strip()
    # Replace SUM(...) (case-insensitive) with either ScriptUtil.sum(section) or a + chain of .p
    m = re.search(r"(?i)\bSUM\s*\((.+)\)", f)
    if not m:
        return f
    inside = m.group(1)
    parts = _split_csv(inside)
    if len(parts) == 1:
        ref = parts[0]
        ref = CURLY_REF.sub(r"\1", ref)
        if ref in section_refs:
            repl = f"ScriptUtil.sum({ref})"
        else:
            repl = f"{ref}.p"  # fallback
    else:
        refs = [CURLY_REF.sub(r"\1", p) for p in parts]
        repl = " + ".join([f"{r}.p" for r in refs])
    return re.sub(r"(?i)\bSUM\s*\(.+\)", repl, f)

def _decide_dot(ref: str, right: str) -> str:
    """Choose .p vs .r heuristically: numeric comparisons/arithmetic => .p else .r."""
    if right is None:
        return ".p"
    right = right.strip().strip("'").strip('"')
    if _is_number_literal(right):
        return ".p"
    # Common booleans/labels -> treat as response text
    if right.lower() in {"y","n","u","yes","no","true","false"}:
        return ".r"
    # Default heuristic
    return ".r"

def _normalize_expr(expr: str, known_refs: Set[str]) -> str:
    if not expr or not isinstance(expr, str):
        return expr
    e = CURLY_REF.sub(r"\1", expr)
    e = _EQ_SINGLE.sub("==", e)

    # Add .p or .r where obviously missing:
    # Pattern: <ref> <op> <rhs>  or wrapped in parentheses. We'll do a light pass.
    def repl(m):
        ref = m.group(1)
        if ref not in known_refs:
            return m.group(0)
        # If ref already has .p/.r in the source, skip
        after = m.string[m.end():]
        if after.startswith(".p") or after.startswith(".r"):
            return m.group(0)
        # Peek ahead to see comparator and RHS
        tail = m.string[m.end():]
        comp_m = re.match(r"\s*(==|!=|>=|<=|>|<)\s*([^)&|]+)", tail)
        if comp_m:
            rhs = comp_m.group(2)
            return f"{ref}{_decide_dot(ref, rhs)}"
        # Arithmetic usage => assume .p
        ar_m = re.match(r"\s*[\+\-\*/]", tail)
        if ar_m:
            return f"{ref}.p"
        return f"{ref}.r"

    e = TOKEN.sub(repl, e)
    return e

def _ensure_points_on_numeric_choices(item: Dict) -> None:
    if item.get("type") not in {"MENU","NUMERIC_SCALE"}:
        return
    chs = item.get("choices") or []
    any_missing = any("points" not in (c or {}) for c in chs)
    if not any_missing:
        return
    for c in chs:
        if c is None:
            continue
        if "points" in c and c["points"] not in (None,""):
            continue
        val = (c.get("val") or "").strip()
        if _is_number_literal(val):
            try:
                c["points"] = float(val)
            except Exception:
                pass

def _collect_refs(section: Dict, section_refs: Set[str], item_types: Dict[str,str]) -> None:
    if not section:
        return
    if section.get("ref"):
        section_refs.add(section["ref"])
    items = section.get("items") or []
    for ch in items:
        if not ch:
            continue
        k = ch.get("kind") or ("section" if ch.get("type") == "SECTION" else "item")
        ch["kind"] = k
        if k == "section":
            _collect_refs(ch, section_refs, item_types)
        else:
            ref = ch.get("ref")
            if ref:
                item_types[ref] = ch.get("type")

def _unify_section_attrs(sec: Dict, is_first: bool) -> None:
    attrs = sec.get("attributes") or {}
    # Allow attributes either nested or top-level, prefer nested.
    def pick(key): return (attrs.get(key) if attrs.get(key) not in (None,"") else sec.get(key))
    merged = {
        "subcategory": pick("subcategory") or ("QUESTIONNAIRE" if is_first else None),
        "headerStyle": pick("headerStyle"),
        "expandIf": pick("expandIf"),
        "showIf": pick("showIf"),
        "makeNoteIf": pick("makeNoteIf"),
        "flag": pick("flag"),
        "noteIndex": pick("noteIndex"),
        "groupItems": attrs.get("groupItems") if attrs.get("groupItems") is not None else sec.get("groupItems"),
        "quoteAnswers": attrs.get("quoteAnswers") if attrs.get("quoteAnswers") is not None else sec.get("quoteAnswers"),
        "ownLine": attrs.get("ownLine") if attrs.get("ownLine") is not None else sec.get("ownLine"),
    }
    # Strip Nones/empties
    sec["attributes"] = {k:v for k,v in merged.items() if v not in (None,"")}

def _repair_section(sec: Dict, is_first: bool, known_refs: Set[str], section_refs: Set[str]) -> None:
    sec["kind"] = "section"
    _unify_section_attrs(sec, is_first)

    # Normalize conditional expressions on the section
    attrs = sec.get("attributes") or {}
    if "showIf" in attrs and isinstance(attrs["showIf"], str):
        attrs["showIf"] = _normalize_expr(attrs["showIf"], known_refs)
    if "makeNoteIf" in attrs and isinstance(attrs["makeNoteIf"], str):
        attrs["makeNoteIf"] = _normalize_expr(attrs["makeNoteIf"], known_refs)
    sec["attributes"] = attrs

    # Normalize header
    if not sec.get("header"):
        lbl = sec.get("label")
        if lbl:
            sec["header"] = lbl

    # Children
    items = sec.get("items") or []
    for ch in items:
        if not ch:
            continue
        k = ch.get("kind") or ("section" if ch.get("type") == "SECTION" else "item")
        ch["kind"] = k
        if k == "section":
            _repair_section(ch, False, known_refs, section_refs)
        else:
            _repair_item(ch, known_refs, section_refs)

def _repair_item(item: Dict, known_refs: Set[str], section_refs: Set[str]) -> None:
    item["kind"] = "item"

    # Label -> keep as is; composer will emit <c> from 'label'
    # Notes maintained if present.
    # Conditions
    for key in ("showIf","makeNoteIf"):
        if isinstance(item.get(key), str):
            item[key] = _normalize_expr(item[key], known_refs)

    # Formula: SUM(...) and braces, plus implicit .p on arithmetic
    if isinstance(item.get("formula"), str):
        f = item["formula"]
        f = _fix_sum(f, known_refs, section_refs)
        f = _normalize_expr(f, known_refs)
        item["formula"] = f

    # Choices: if numeric val and missing points, set points=val
    _ensure_points_on_numeric_choices(item)

# -------- public API --------

def auto_repair_cir(cir: Dict) -> Dict:
    """Deterministic repairs to make CIR valid & Ocean-strict."""
    c = copy.deepcopy(cir or {})
    c.setdefault("meta", {})
    sections: List[Dict] = list(c.get("sections") or [])
    c["sections"] = sections

    # Collect refs first
    section_refs: Set[str] = set()
    item_types: Dict[str,str] = {}
    for s in sections:
        _collect_refs(s, section_refs, item_types)
    known_refs = set(item_types.keys())

    # Repair sections/items recursively
    for idx, s in enumerate(sections):
        _repair_section(s, is_first=(idx == 0), known_refs=known_refs, section_refs=section_refs)

    return c
