# app/normalizers_soft.py
from __future__ import annotations
import re, json, copy, logging
from typing import Dict, List, Any, Optional, Set, Tuple  # <-- add Set, Tuple

log = logging.getLogger("uvicorn.error")

# Reserved engine/session tokens (do not dot-qualify)
RESERVED_TOKENS = {
    "true","false","null",
    "pt","firstTime","lastCompletedTag","daysSinceLastCompleted",
    "ScriptUtil","Math"
}

# Common JS keywords & builtins (never dot-qualify)
JS_KEYWORDS = {
    "function","return","var","let","const","if","else","switch","case","break","continue","new",
    "typeof","void","delete","in","instanceof","this","try","catch","finally","throw",
    "for","while","do","of","undefined","NaN","Infinity",
    # Builtins we shouldn't touch:
    "String","Number","Boolean","Array","Object","Date","RegExp","JSON"
}

def _collect_refs(sections: List[Dict]) -> Tuple[Set[str], Set[str]]:
    """Collect item refs and section refs before normalization."""
    item_refs: Set[str] = set()
    section_refs: Set[str] = set()

    def walk_section(sec: Dict):
        if not isinstance(sec, Dict): return
        # section ref
        s_ref = sec.get("ref")
        if isinstance(s_ref, str) and s_ref.strip():
            section_refs.add(s_ref.strip())
        # items
        kids = sec.get("items") or []
        for ch in kids:
            if not isinstance(ch, Dict): 
                continue
            # Consider it a nested section if it has 'items' but no explicit 'type'
            if (ch.get("kind") == "section") or ("items" in ch and not ch.get("type")):
                walk_section(ch)
            else:
                i_ref = ch.get("ref")
                if isinstance(i_ref, str) and i_ref.strip():
                    item_refs.add(i_ref.strip())

    for s in sections or []:
        if isinstance(s, Dict):
            walk_section(s)

    return item_refs, section_refs

def _fix_expression(expr: str, item_refs: Optional[Set[str]] = None, section_refs: Optional[Set[str]] = None) -> str:
    """Heuristic repairs for Ocean eForm scripting with awareness of known refs."""
    s = (expr or "").strip()
    if not s:
        return s

    item_refs = item_refs or set()
    section_refs = section_refs or set()

    # 1) trivial safe fixes
    # single '=' (not part of ==, >=, <=, !=) -> '=='
    s = re.sub(r'(?<![!<>=])=(?!=)', '==', s)

    # '{ref}' -> 'ref'
    s = re.sub(r'\{ *([A-Za-z_]\w*) *\}', r'\1', s)

    # detect function-like content; if present, be very conservative
    has_functiony = bool(re.search(r'\bfunction\b|=>', s))

    # 2) SUM(...) support
    #    - SUM(sectionRef)  -> ScriptUtil.sum(sectionRef)
    #    - SUM(a,b,...)     -> a.p + b.p + ...
    def repl_sum(m):
        inside = m.group(1)
        args = [a.strip() for a in inside.split(',') if a.strip()]
        if len(args) == 1:
            ref = re.sub(r'^\{|\}$', '', args[0])
            if ref in section_refs:
                return f"ScriptUtil.sum({ref})"
            # single item -> item.p (if known)
            return (f"{ref}.p" if ref in item_refs and not re.search(r'\.(p|r)\b', ref) else ref)
        # multiple args -> numeric sum of points for known item refs; leave others as-is
        terms = []
        for a in args:
            a_stripped = re.sub(r'^\{|\}$', '', a)
            if a_stripped in item_refs and not re.search(r'\.(p|r)\b', a_stripped):
                terms.append(f"{a_stripped}.p")
            else:
                terms.append(a_stripped)
        return "(" + " + ".join(terms) + ")"
    s = re.sub(r'\bSUM\s*\(\s*([^)]+?)s = re.sub(r'(?<!ScriptUtil\.)\bSUM\s*\(\s*([^)]+?)\s*\)', repl_sum, s, flags=re.IGNORECASE)
    s = re.sub(r'(?i)(?:ScriptUtil\.)+(sum\s*\()', r'ScriptUtil.\1', s)\s*\)', repl_sum, s, flags=re.IGNORECASE)

    # 3) Comparisons
    # strings: left == "foo" => left.r == "foo" (only if left is a known item ref)
    def _left_str_cmp(m):
        left, op, rhs = m.group(1), m.group(2), m.group(3)
        if left in item_refs and not re.search(r'\.(p|r)\b', left):
            return f"{left}.r {op} {rhs}"
        return f"{left} {op} {rhs}"
    s = re.sub(
        r'(\b[A-Za-z_]\w*\b)\s*(==|!=)\s*([\'"][^\'"]+[\'"])',
        _left_str_cmp,
        s
    )

    # numeric: left > 3 => left.p > 3 (only if left is a known item ref)
    def _left_num_cmp(m):
        left, op, rhs = m.group(1), m.group(2), m.group(3)
        if left in item_refs and not re.search(r'\.(p|r)\b', left):
            return f"{left}.p {op} {rhs}"
        return f"{left} {op} {rhs}"
    s = re.sub(
        r'(\b[A-Za-z_]\w*\b)\s*(>=|<=|>|<)\s*([0-9]+(?:\.[0-9]+)?)',
        _left_num_cmp,
        s
    )

    # 4) Arithmetic over bare refs: only when NOT function-like, and only for known item refs
    if (not has_functiony) and re.search(r'[\+\-/*]', s):
        # Replace bare occurrences of known refs not already dotted
        # Sort by length to avoid partial replacements (e.g., q1 before q10)
        for ref in sorted(item_refs, key=len, reverse=True):
            # match whole word ref, not followed by .p/.r
            s = re.sub(fr'\b{re.escape(ref)}\b(?!\s*\.(?:p|r))', f"{ref}.p", s)

    return s

def _move_section_root_attrs_to_attributes(sec: Dict[str, Any]) -> None:
    a = sec.setdefault("attributes", {})
    for key in ("subcategory","headerStyle","expandIf","showIf","makeNoteIf","flag","noteIndex"):
        if key in sec and key not in ("items","kind","ref","attributes"):
            val = sec.pop(key, None)
            if val is not None:
                a[key] = val
    for key in ("groupItems","quoteAnswers","ownLine"):
        if key in sec and key not in ("items","kind","ref","attributes"):
            val = sec.pop(key, None)
            if val is not None:
                a[key] = bool(val)

def _looks_like_prefill(text: str) -> bool:
    return bool(re.search(r'@pt|@ptCpp|@pt[A-Z]|ScriptUtil', text or ""))

def _normalize_item(x: Dict[str, Any], item_refs: Set[str], section_refs: Set[str]) -> None:
    x["kind"] = "item"
    x["type"] = (x.get("type") or "LABEL").upper()

    # Promote <text> -> label (<c>) when it's a patient-facing prompt
    label = x.get("label")
    text  = x.get("text")
    if (not label) and text and not _looks_like_prefill(text):
        x["label"] = text
        x["text"]  = None

    # FORMULA notes: prefer cNote
    if x["type"] == "FORMULA":
        if not x.get("cNote") and (x.get("tooltip") or x.get("text")):
            x["cNote"] = x.get("tooltip") or x.get("text")
        if x.get("formula"):
            x["formula"] = _fix_expression(x["formula"], item_refs, section_refs)

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
            if "points" in ch and isinstance(ch["points"], str):
                try:
                    ch["points"] = float(ch["points"])
                except Exception:
                    ch["points"] = None
            if isinstance(ch.get("val"), str) and "|" in ch["val"]:
                ch["val"] = ch["val"].replace("|", "/")

    # Fix showIf / makeNoteIf
    for cond_key in ("showIf","makeNoteIf"):
        if isinstance(x.get(cond_key), str):
            x[cond_key] = _fix_expression(x[cond_key], item_refs, section_refs)

def _walk_section(sec: Dict[str, Any], item_refs: Set[str], section_refs: Set[str]) -> None:
    sec["kind"] = "section"
    _move_section_root_attrs_to_attributes(sec)

    attrs = sec.setdefault("attributes", {})
    if "subcategory" not in attrs:
        attrs["subcategory"] = "QUESTIONNAIRE"

    # section-level conditions
    for k in ("showIf","makeNoteIf"):
        if isinstance(attrs.get(k), str):
            attrs[k] = _fix_expression(attrs[k], item_refs, section_refs)

    items = sec.get("items")
    if not isinstance(items, list):
        sec["items"] = []
        return
    for ch in items:
        if not isinstance(ch, dict):
            continue
        k = ch.get("kind")
        if k == "section" or ("items" in ch and "type" not in ch):
            ch["kind"] = "section"
            _walk_section(ch, item_refs, section_refs)
        else:
            _normalize_item(ch, item_refs, section_refs)

def soft_repair_cir(cir: Dict[str, Any]) -> Dict[str, Any]:
    """Best-effort, conservative repairs with ref-aware scripting fixes."""
    data = copy.deepcopy(cir or {})
    meta = data.setdefault("meta", {})
    meta.setdefault("noteVersion", 2)
    meta.setdefault("noteType", "progress")
    meta.setdefault("dataSecurityMode", "encrypted")

    # Ensure sections present
    secs = data.setdefault("sections", [])
    if not secs:
        secs.append({"kind":"section","ref":"__section","attributes":{"subcategory":"QUESTIONNAIRE"},"items":[]})

    # Collect refs BEFORE normalization (so we know what to dot-qualify)
    item_refs, section_refs = _collect_refs(secs)

    # Normalize with ref-aware expression fixes
    for s in secs:
        if isinstance(s, dict):
            _walk_section(s, item_refs, section_refs)

    return data
