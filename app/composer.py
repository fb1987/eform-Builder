# app/composer.py
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from typing import Dict, List, Optional
from app.config import DEFAULT_NOTE_VERSION

def _attr(el: Element, pairs: List[tuple]):
    """Set attributes in a stable order; skip empty strings/None."""
    for k, v in pairs:
        if v is None: 
            continue
        vs = str(v)
        if vs == "":
            continue
        el.set(k, vs)

def _set_bool_attr(el: Element, name: str, val: Optional[bool]):
    if val is None:
        return
    el.set(name, "true" if val else "false")

def _text(parent: Element, tag: str, value: Optional[str]):
    if value is not None and str(value).strip() != "":
        s = SubElement(parent, tag)
        s.text = str(value)

def _compose_item(parent_items: Element, node: Dict):
    itype = (node.get("type") or "LABEL").upper()

    # Picture / Video / Diagram are sibling elements (not <item type="...">)
    if itype in {"PICTURE","VIDEO","DIAGRAM"}:
        tag = "picture" if itype == "PICTURE" else ("video" if itype == "VIDEO" else "diagram")
        el = SubElement(parent_items, tag)
        _attr(el, [
            ("ref", node.get("ref")),
            ("subcategory", node.get("subcategory")),
            ("x", node.get("x")), ("y", node.get("y")),
            ("showIf", node.get("showIf")),
            ("makeNoteIf", node.get("makeNoteIf")),
            ("noteIndex", node.get("noteIndex")),
        ])
        _set_bool_attr(el, "ownLine", node.get("ownLine"))
        return

    # Regular eFormItem
    el = SubElement(parent_items, "item")
    _attr(el, [
        ("ref", node.get("ref")),
        ("type", itype),
        ("subcategory", node.get("subcategory")),
        ("x", node.get("x")), ("y", node.get("y")),
        ("formula", node.get("formula")),
        ("showIf", node.get("showIf")),
        ("makeNoteIf", node.get("makeNoteIf")),
        ("noteIndex", node.get("noteIndex")),
        ("flag", node.get("flag")),
        ("negFlag", node.get("negFlag")),
        ("emrField", node.get("emrField")),
    ])
    _set_bool_attr(el, "ownLine", node.get("ownLine"))
    _set_bool_attr(el, "quoteAnswer", node.get("quoteAnswer"))

    # === Correct element mapping for items ===
    # Patient-facing prompt:
    _text(el, "c", node.get("label"))
    # Default/pre-fill text/macros (e.g., @ptCpp.*):
    _text(el, "text", node.get("text"))
    # Tooltip (rarely used by Ocean; allowed):
    _text(el, "tooltip", node.get("tooltip"))
    # Study export column header:
    _text(el, "studyColumnHeader", node.get("studyColumnHeader"))
    # Diagram overlay file name:
    _text(el, "markableDiagramFileName", node.get("markableDiagramFileName"))
    # Note output fields:
    _text(el, "cNote", node.get("cNote"))
    _text(el, "posNote", node.get("posNote"))
    _text(el, "negNote", node.get("negNote"))

    # Dx codes (packed as "code|desc|type")
    if node.get("dxCode"):
        dx = SubElement(el, "dxCode")
        parts = (node["dxCode"] or "").split("|")
        if len(parts) > 0: dx.set("code", parts[0])
        if len(parts) > 1: dx.set("desc", parts[1])
        if len(parts) > 2: dx.set("type", parts[2])

    # Validator
    v = node.get("validator")
    if isinstance(v, dict) and (v.get("type") or v.get("validIf") or v.get("format") or v.get("message") or (v.get("allowEmpty") is not None)):
        vv = SubElement(el, "validator")
        _attr(vv, [("type", v.get("type")), ("format", v.get("format")), ("message", v.get("message"))])
        if v.get("allowEmpty") is not None:
            _set_bool_attr(vv, "allowEmpty", v.get("allowEmpty"))
        if v.get("validIf"):
            vv.set("validIf", v.get("validIf"))

    # Hints
    if node.get("hints"):
        hints = SubElement(el, "hints")
        for h in node["hints"]:
            ht = SubElement(hints, "hint")
            ht.text = str(h)

    # Choices
    if node.get("choices"):
        chs = SubElement(el, "choices")
        for c in node["choices"]:
            if not isinstance(c, dict):
                continue
            ce = SubElement(chs, "choice")
            _attr(ce, [("val", c.get("val")), ("points", c.get("points")), ("flag", c.get("flag"))])
            _text(ce, "display", c.get("display"))
            _text(ce, "note", c.get("note"))

def _compose_section(parent_items: Element, node: Dict):
    sec = SubElement(parent_items, "section")

    # Merge attributes from node["attributes"] if present
    attrs = node.get("attributes") or {}
    _attr(sec, [
        ("ref", node.get("ref")),
        ("subcategory", attrs.get("subcategory")),
        ("headerStyle", attrs.get("headerStyle")),
        ("expandIf", attrs.get("expandIf")),
        ("showIf", attrs.get("showIf")),
        ("makeNoteIf", attrs.get("makeNoteIf")),
        ("flag", attrs.get("flag")),
        ("noteIndex", attrs.get("noteIndex")),
    ])
    _set_bool_attr(sec, "groupItems", attrs.get("groupItems"))
    _set_bool_attr(sec, "quoteAnswers", attrs.get("quoteAnswers"))
    _set_bool_attr(sec, "ownLine", attrs.get("ownLine"))

    # Section header / note
    _text(sec, "c", node.get("header"))
    _text(sec, "cNote", node.get("cNote"))

    # Section hints
    if node.get("hints"):
        hints = SubElement(sec, "hints")
        for h in node["hints"]:
            ht = SubElement(hints, "hint")
            ht.text = str(h)

    # Children
    items = SubElement(sec, "items")
    for ch in node.get("items", []):
        kind = (ch or {}).get("kind")
        if kind == "section":
            _compose_section(items, ch)
        else:
            _compose_item(items, ch)

def compose_xml(cir: Dict) -> bytes:
    meta = cir.get("meta", {})
    root = Element("eform")
    _attr(root, [
        ("ref", meta.get("ref")),
        ("noteVersion", str(meta.get("noteVersion", DEFAULT_NOTE_VERSION))),
        ("title", meta.get("title")),
        ("shortForm", meta.get("shortForm")),
        ("noteType", meta.get("noteType")),
        ("dataSecurityMode", meta.get("dataSecurityMode")),
    ])

    # top-level metadata
    _text(root, "tagLine", cir.get("tagLine"))
    _text(root, "desc", cir.get("desc"))
    _text(root, "keywords", cir.get("keywords"))

    # mainSection
    main = SubElement(root, "mainSection")
    ms_items = SubElement(main, "items")
    for s in cir.get("sections", []):
        _compose_section(ms_items, s)

    pretty = minidom.parseString(tostring(root, encoding="utf-8")).toprettyxml(indent="  ", encoding="utf-8")
    return pretty
