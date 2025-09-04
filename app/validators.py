# app/validators.py
import re
from typing import Dict, List, Tuple
from jsonschema import Draft202012Validator
from app.cir_schema import CIR_JSON_SCHEMA
from app.enums import (
    ITEM_TYPES, FIELD_VALIDATOR_TYPES, HINTS, FLAG_COLORS, NOTE_STYLES,
    DATA_SECURITY_MODES, NOTE_TYPES, ITEM_SUBCATEGORIES, EMR_FIELDS
)
from app.config import DEFAULT_NOTE_VERSION

REF_RE = re.compile(r"^[A-Za-z0-9_]+$")

def _enum_fix(v: str, allowed: set) -> Tuple[str, bool]:
    if v in allowed: return v, False
    if v.upper() in allowed: return v.upper(), True
    if v.lower() in allowed: return v.lower(), True
    return v, False

def validate_against_schema(cir: Dict) -> List[str]:
    errors = []
    v = Draft202012Validator(CIR_JSON_SCHEMA)
    for err in v.iter_errors(cir):
        loc = " → ".join(map(str, err.path))
        errors.append(f"{loc or 'root'}: {err.message}")
    return errors

def _add_validator(node: Dict, vtype: str, issues: List[str]):
    if "validator" not in node or not node["validator"]:
        node["validator"] = {"type": vtype}
        issues.append(f"repair: added validator {vtype} to {node.get('ref') or '(no-ref)'}")
    elif not node["validator"].get("type"):
        node["validator"]["type"] = vtype
        issues.append(f"repair: set validator.type={vtype} for {node.get('ref') or '(no-ref)'}")

def _apply_heuristics(cir: Dict, issues: List[str]):
    """Small, safe repairs: add validators based on wording; menu hints based on size."""
    def walk(n):
        if n.get("kind") == "section":
            for ch in (n.get("items") or []): walk(ch)
        elif n.get("kind") == "item":
            text = (n.get("text") or "").lower()
            itype = (n.get("type") or "").upper()
            # Email/Phone/Postal validators
            if any(k in text for k in ["email","e-mail"]):
                _add_validator(n, "EMAIL", issues)
            if any(k in text for k in ["phone","telephone","cell"]):
                _add_validator(n, "PHONE", issues)
            if any(k in text for k in ["postal","zip"]):
                _add_validator(n, "POSTAL_CODE", issues)
            # Menu hints
            ch = n.get("choices") or []
            if itype in {"MENU","MENU_MULTI_SELECT"} and ch:
                L = len(ch)
                hints = set(n.get("hints") or [])
                if L >= 7 and "USE_SEARCHABLE_MENU" not in hints:
                    hints.add("USE_SEARCHABLE_MENU")
                    n["hints"] = sorted(list(hints))
                    issues.append(f"repair: added USE_SEARCHABLE_MENU to {n.get('ref')}")
                elif 3 <= L <= 6 and "USE_DROPDOWN_MENU" not in hints:
                    hints.add("USE_DROPDOWN_MENU")
                    n["hints"] = sorted(list(hints))
                    issues.append(f"repair: added USE_DROPDOWN_MENU to {n.get('ref')}")
    for s in cir.get("sections", []): walk(s)

def normalize_enums_and_defaults(cir: Dict) -> List[str]:
    issues: List[str] = []
    meta = cir.get("meta", {})
    if "noteVersion" not in meta or not isinstance(meta.get("noteVersion"), int):
        meta["noteVersion"] = DEFAULT_NOTE_VERSION
        issues.append("meta.noteVersion defaulted to 2")
    if "dataSecurityMode" in meta and meta["dataSecurityMode"]:
        v, fixed = _enum_fix(meta["dataSecurityMode"], DATA_SECURITY_MODES)
        if fixed: issues.append(f"meta.dataSecurityMode→{v}")
        meta["dataSecurityMode"] = v
    if "noteType" in meta and meta["noteType"]:
        v, fixed = _enum_fix(meta["noteType"], NOTE_TYPES)
        if fixed: issues.append(f"meta.noteType→{v}")
        meta["noteType"] = v

    # walk
    def walk(node, seen_refs: set):
        if node.get("kind") == "section":
            attrs = node.get("attributes", {}) or {}
            if "headerStyle" in attrs and attrs["headerStyle"]:
                v, fixed = _enum_fix(attrs["headerStyle"], NOTE_STYLES)
                if fixed: issues.append(f"section.headerStyle→{v}")
                attrs["headerStyle"] = v
            if "flag" in attrs and attrs["flag"]:
                v, fixed = _enum_fix(attrs["flag"], FLAG_COLORS)
                if fixed: issues.append(f"section.flag→{v}")
                attrs["flag"] = v
            for ch in node.get("items", []) or []:
                walk(ch, seen_refs)
        elif node.get("kind") == "item":
            if "type" in node and node["type"]:
                v, fixed = _enum_fix(node["type"], ITEM_TYPES)
                if fixed: issues.append(f"item.type {node['type']}→{v}")
                node["type"] = v
            for k in ("flag","negFlag"):
                if node.get(k):
                    v, fixed = _enum_fix(node[k], FLAG_COLORS)
                    if fixed: issues.append(f"item.{k}→{v}")
                    node[k] = v
            if node.get("validator") and node["validator"].get("type"):
                v, fixed = _enum_fix(node["validator"]["type"], FIELD_VALIDATOR_TYPES)
                if fixed: issues.append(f"validator.type→{v}")
                node["validator"]["type"] = v
            # ref hygiene
            if not node.get("ref"):
                base = re.sub(r"[^A-Za-z0-9_]+", "_", (node.get("text") or "item").strip())[:24] or "item"
                idx = 1
                while f"{base}_{idx}" in seen_refs: idx += 1
                node["ref"] = f"{base}_{idx}"
                issues.append(f"item.ref generated: {node['ref']}")
            if not REF_RE.match(node["ref"]):
                fixed = re.sub(r"[^A-Za-z0-9_]+", "_", node["ref"]) or "ITEM"
                issues.append(f"item.ref '{node['ref']}'→'{fixed}'")
                node["ref"] = fixed
            seen_refs.add(node["ref"])
    seen = set()
    for s in cir.get("sections", []): walk(s, seen)
    return issues

def validate_and_normalize_cir(cir: Dict) -> Dict:
    # 1) normalize enums/defaults and refs
    issues = normalize_enums_and_defaults(cir)
    # 2) gentle heuristic repairs
    _apply_heuristics(cir, issues)
    # 3) schema validation
    schema_errors = validate_against_schema(cir)
    issues.extend(schema_errors)
    # 4) duplicate refs
    def collect_refs(node, bag):
        if node.get("kind") == "item" and node.get("ref"): bag.append(node["ref"])
        for ch in (node.get("items") or []): collect_refs(ch, bag)
    refs = []
    for s in cir.get("sections", []): collect_refs(s, refs)
    dupes = {r for r in refs if refs.count(r) > 1}
    if dupes: issues.append(f"duplicate item refs: {sorted(list(dupes))}")
    ok = (len(schema_errors) == 0) and (not dupes)
    return {"ok": ok, "issues": issues, "cir": cir}
