from __future__ import annotations
import os, re, copy
from typing import Dict, List, Set

AUTO_REPAIR_ENABLED = os.getenv("AUTO_REPAIR", "1") != "0"

# -------- regex helpers --------

_EQ_SINGLE = re.compile(r"(?<![=!<>])=(?!=)")          # lone "=" -> "=="
CURLY_REF  = re.compile(r"\{([A-Za-z0-9_]+)\}")        # {q1} -> q1
TOKEN      = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]{0,63})\b", re.ASCII)
SUM_CALL   = re.compile(r"(?i)\bSUM\s*\((.+)\)")

# -------- small utils --------

def _is_number_literal(s: str) -> bool:
    try:
        float(s)
        return True
    except Exception:
        return False

def _split_csv(s: str) -> List[str]:
    return [t.strip() for t in (s or "").split(",") if t and t.strip()]

def _looks_like_default_text(s: str) -> bool:
    """Heuristic: default/macros belong in <text>, not in the patient-facing <c> label."""
    if not s:
        return False
    s = s.strip()
    if s.startswith("@"):
        return True
    # Common Ocean script/macros / session vars:
    bad_fragments = (
        "@pt", "@patient", "@ptCpp.", "ScriptUtil.", "firstTime", "daysSinceLastCompleted",
        "lastCompletedTag", "pt.", "$$",  # '$$' should only be used in the item's own c/cNote, not as a prompt
    )
    return any(frag in s for frag in bad_fragments)

def _fix_sum(formula: str, item_refs: Set[str], section_refs: Set[str]) -> str:
    if not formula:
        return formula
    f = formula.strip()
    m = SUM_CALL.search(f)
    if not m:
        return f
    inside = m.group(1)
    parts = _split_csv(inside)
    if len(parts) == 1:
        ref = CURLY_REF.sub(r"\1", parts[0])
        if ref in section_refs:
            repl = f"ScriptUtil.sum({ref})"
        else:
            repl = f"{ref}.p"
    else:
        refs = [CURLY_REF.sub(r"\1", p) for p in parts]
        repl = " + ".join([f"{r}.p" for r in refs])
    return SUM_CALL.sub(repl, f)

def _decide_dot(rhs: str) -> str:
    """Choose .p vs .r based on RHS."""
    if rhs is None:
        return ".p"
    s = rhs.strip().strip("'").strip('"')
    if _is_number_literal(s):
        return ".p"
    if s.lower() in {"y","n","u","yes","no","true","false"}:
        return ".r"
    return ".r"

def _normalize_expr(expr: str, known_refs: Set[str]) -> str:
    if not expr or not isinstance(expr, str):
        return expr
    e = CURLY_REF.sub(r"\1", expr)      # {q1} -> q1
    e = _EQ_SINGLE.sub("==", e)         # "=" -> "=="
    # Add .p/.r when missing
    def repl(m):
        ref = m.group(1)
        if ref not in known_refs:
            return m.group(0)
        # already qualified?
        tail = m.string[m.end():]
        if tail.startswith(".p") or tail.startswith(".r"):
            return m.group(0)
        # comparator
        comp_m = re.match(r"\s*(==|!=|>=|<=|>|<)\s*([^)&|]+)", tail)
        if comp_m:
            rhs = comp_m.group(2)
            return f"{ref}{_decide_dot(rhs)}"
        # arithmetic usage -> assume numeric points
        if re.match(r"\s*[\+\-\*/]", tail):
            return f"{ref}.p"
        return f"{ref}.r"
    return TOKEN.sub(repl, e)

def _ensure_points_on_numeric_choices(item: Dict) -> None:
    if item.get("type") not in {"MENU","NUMERIC_SCALE"}:
        return
    chs = item.get("choices") or []
    any_missing = any(("points" not in (c or {})) for c in chs)
    if not any_missing:
        return
    for c in chs:
        if not c:
            continue
        if "points" in c and c["points"] not in (None, ""):
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
    def pick(key): 
        return attrs.get(key) if attrs.get(key) not in (None, "") else sec.get(key)
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
    sec["attributes"] = {k: v for k, v in merged.items() if v not in (None, "")}

def _promote_label_and_notes(item: Dict) -> None:
    """
    - If 'label' missing but 'text' looks like prompt (not macro/default), move text -> label.
    - LABEL always prefers 'label'; move text -> label when present.
    - FORMULA: move tooltip/text with '$$' or score-ish content into cNote.
    """
    itype = (item.get("type") or "").upper()

    # 1) Promote text -> label for visible prompts
    if (not item.get("label")) and isinstance(item.get("text"), str):
        t = item["text"].strip()
        if t and not _looks_like_default_text(t):
            # Heuristics: prompts for patient items; keep default text for macros only.
            item["label"] = t
            # Only clear text if it wasn't a macro/default
            item["text"] = None

    # LABEL items: ensure label is used
    if itype == "LABEL":
        if item.get("text") and not item.get("label"):
            item["label"] = item["text"].strip()
            item["text"] = None

    # 2) FORMULA: move tooltip/text into cNote when appropriate
    if itype == "FORMULA":
        # tooltip -> cNote if looks like an output message
        tip = item.get("tooltip")
        if isinstance(tip, str) and tip.strip():
            if "$$" in tip or "Score" in tip or "Total" in tip or "Severity" in tip:
                item["cNote"] = tip.strip()
                item["tooltip"] = None
        # text -> cNote if it contains $$ (intended to print the result)
        txt = item.get("text")
        if isinstance(txt, str) and "$$" in txt:
            item["cNote"] = txt.strip()
            item["text"] = None

def _repair_item(item: Dict, known_refs: Set[str], section_refs: Set[str]) -> None:
    item["kind"] = "item"

    # Promote patient-visible fields first
    _promote_label_and_notes(item)

    # Normalize conditions
    for key in ("showIf","makeNoteIf"):
        if isinstance(item.get(key), str):
            item[key] = _normalize_expr(item[key], known_refs)

    # Formula normalization
    if isinstance(item.get("formula"), str):
        f = item["formula"]
        f = _fix_sum(f, known_refs, section_refs)
        f = _normalize_expr(f, known_refs)
        item["formula"] = f

    # MENU / NUMERIC_SCALE points
    _ensure_points_on_numeric_choices(item)

def _repair_section(sec: Dict, is_first: bool, known_refs: Set[str], section_refs: Set[str]) -> None:
    sec["kind"] = "section"
    _unify_section_attrs(sec, is_first)

    # Section-level conditions
    attrs = sec.get("attributes") or {}
    if "showIf" in attrs and isinstance(attrs["showIf"], str):
        attrs["showIf"] = _normalize_expr(attrs["showIf"], known_refs)
    if "makeNoteIf" in attrs and isinstance(attrs["makeNoteIf"], str):
        attrs["makeNoteIf"] = _normalize_expr(attrs["makeNoteIf"], known_refs)
    sec["attributes"] = attrs

    # Prefer 'header' over legacy 'label' for sections
    if not sec.get("header"):
        lbl = sec.get("label")
        if isinstance(lbl, str) and lbl.strip():
            sec["header"] = lbl.strip()

    # Recurse children
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

# -------- public API --------

def auto_repair_cir(cir: Dict) -> Dict:
    """Deterministic repairs to make CIR valid & Ocean-strict."""
    c = copy.deepcopy(cir or {})
    c.setdefault("meta", {})
    sections: List[Dict] = list(c.get("sections") or [])
    c["sections"] = sections

    # Collect refs
    section_refs: Set[str] = set()
    item_types: Dict[str, str] = {}
    for s in sections:
        _collect_refs(s, section_refs, item_types)
    known_refs = set(item_types.keys())

    # Repair sections/items
    for idx, s in enumerate(sections):
        _repair_section(s, is_first=(idx == 0), known_refs=known_refs, section_refs=section_refs)

    return c
