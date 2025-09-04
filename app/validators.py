# app/validators.py
import re
from typing import Dict, List, Tuple
from jsonschema import validate, Draft202012Validator
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

def normalize_enums_and_defaults(cir: Dict) -> List[str]:
    """Normalize common enum casing, fill defaults for noteVersion, generate missing item refs."""
    issues: List[str] = []

    # form meta defaults
    meta = cir.get("meta", {})
    if "noteVersion" not in meta or not isinstance(meta.get("noteVersion"), int):
        meta["noteVersion"] = DEFAULT_NOTE_VERSION
        issues.append("meta.noteVersion defaulted to 2")
    if "dataSecurityMode" in meta:
        v, fixed = _enum_fix(meta["dataSecurityMode"], DATA_SECURITY_MODES)
        if fixed: issues.append(f"meta.dataSecurityMode→{v}")
        meta["dataSecurityMode"] = v
    if "noteType" in meta:
        v, fixed = _enum_fix(meta["noteType"], NOTE_TYPES)
        if fixed: issues.append(f"meta.noteType→{v}")
        meta["noteType"] = v

    # walk sections/items
    def walk(node, seen_refs: set):
        if node.get("kind") == "section":
            attrs = node.get("attributes", {})
            if "headerStyle" in attrs and attrs["headerStyle"]:
                v, fixed = _enum_fix(attrs["headerStyle"], NOTE_STYLES)
                if fixed: issues.append(f"section.headerStyle→{v}")
                attrs["headerStyle"] = v
            if "flag" in attrs and attrs["flag"]:
                v, fixed = _enum_fix(attrs["flag"], FLAG_COLORS)
                if fixed: issues.append(f"section.flag→{v}")
                attrs["flag"] = v
            for h in node.get("hints", []) or []:
                hv, fixed = _enum_fix(h, HINTS)
                if fixed: issues.append(f"section.hint {h}→{hv}")
            for ch in node.get("items", []):
                walk(ch, seen_refs)
        elif node.get("kind") == "item":
            if "type" in node and node["type"]:
                v, fixed = _enum_fix(node["type"], ITEM_TYPES)
                if fixed: issues.append(f"item.type {node['type']}→{v}")
                node["type"] = v
            if "flag" in node and node["flag"]:
                v, fixed = _enum_fix(node["flag"], FLAG_COLORS)
                if fixed: issues.append(f"item.flag→{v}")
                node["flag"] = v
            if "negFlag" in node and node["negFlag"]:
                v, fixed = _enum_fix(node["negFlag"], FLAG_COLORS)
                if fixed: issues.append(f"item.negFlag→{v}")
                node["negFlag"] = v
            if "emrField" in node and node["emrField"]:
                # not strictly enum enforced; warn but keep as-is
                if node["emrField"] not in EMR_FIELDS:
                    issues.append(f"item.emrField '{node['emrField']}' not in EMR_FIELDS")

            # ensure item ref
            if not node.get("ref"):
                base = re.sub(r"[^A-Za-z0-9_]+", "_", (node.get("text") or "item").strip())[:24] or "item"
                idx = 1
                while f"{base}_{idx}" in seen_refs:
                    idx += 1
                node["ref"] = f"{base}_{idx}"
                issues.append(f"item.ref generated: {node['ref']}")
            if not REF_RE.match(node["ref"]):
                fixed = re.sub(r"[^A-Za-z0-9_]+", "_", node["ref"]) or "ITEM"
                issues.append(f"item.ref '{node['ref']}'→'{fixed}'")
                node["ref"] = fixed
            seen_refs.add(node["ref"])

            # normalize choices flags
            for c in (node.get("choices") or []):
                if c.get("flag"):
                    v, fixed = _enum_fix(c["flag"], FLAG_COLORS)
                    if fixed: issues.append(f"choice.flag→{v}")
                    c["flag"] = v

            # validator type casing
            if node.get("validator") and node["validator"].get("type"):
                v, fixed = _enum_fix(node["validator"]["type"], FIELD_VALIDATOR_TYPES)
                if fixed: issues.append(f"validator.type→{v}")
                node["validator"]["type"] = v

    seen = set()
    for s in cir.get("sections", []):
        walk(s, seen)

    return issues

def validate_and_normalize_cir(cir: Dict) -> Dict:
    issues = []
    issues += normalize_enums_and_defaults(cir)
    issues += validate_against_schema(cir)
    # check duplicate refs
    def collect_refs(node, bag):
        if node.get("kind") == "item" and node.get("ref"):
            bag.append(node["ref"])
        for ch in (node.get("items") or []):
            collect_refs(ch, bag)
    refs = []
    for s in cir.get("sections", []): collect_refs(s, refs)
    dupes = {r for r in refs if refs.count(r) > 1}
    if dupes:
        issues.append(f"duplicate item refs: {sorted(list(dupes))}")
    return {"ok": len([e for e in issues if "root:" in e]) == 0 and not dupes, "issues": issues}
