# app/composer.py
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from typing import Dict, List, Optional
from app.config import DEFAULT_NOTE_VERSION
from app.enums import FLAG_COLORS, NOTE_STYLES

def _attr(el: Element, pairs: List[tuple]):
    """Set attributes in a stable order."""
    for k, v in pairs:
        if v is None: 
            continue
        vs = str(v)
        if vs == "": 
            continue
        el.set(k, vs)

def _set_bool_attr(el: Element, name: str, val: Optional[bool]):
    if val is None: return
    el.set(name, "true" if val else "false")

def _text(parent: Element, tag: str, value: Optional[str]):
    if value:
        s = SubElement(parent, tag)
        s.text = value

def _compose_item(parent_items: Element, node: Dict):
    # item / picture / video / diagram normalize to <item/> and siblings where required
    itype = node.get("type") or "LABEL"
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

    _text(el, "text", node.get("text"))
    if node.get("tooltip"): _text(el, "tooltip", node["tooltip"])
    if node.get("studyColumnHeader"): _text(el, "studyColumnHeader", node["studyColumnHeader"])
    if node.get("markableDiagramFileName"): _text(el, "markableDiagramFileName", node["markableDiagramFileName"])
    if node.get("dxCode"):
        dx = SubElement(el, "dxCode")  # content packed as "code|desc|type"
        parts = (node["dxCode"] or "").split("|")
        if len(parts) > 0: dx.set("code", parts[0])
        if len(parts) > 1: dx.set("desc", parts[1])
        if len(parts) > 2: dx.set("type", parts[2])

    # validator
    v = node.get("validator")
    if v and (v.get("type") or v.get("validIf") or v.get("format") or v.get("message")):
        vv = SubElement(el, "validator")
        _attr(vv, [("type", v.get("type")), ("format", v.get("format")), ("message", v.get("message"))])
        if v.get("allowEmpty") is not None:
            _set_bool_attr(vv, "allowEmpty", v.get("allowEmpty"))
        if v.get("validIf"):
            vv.set("validIf", v.get("validIf"))

    # hints
    if node.get("hints"):
        hints = SubElement(el, "hints")
        for h in node["hints"]:
            ht = SubElement(hints, "hint")
            ht.text = h

    # choices
    if node.get("choices"):
        chs = SubElement(el, "choices")
        for c in node["choices"]:
            ce = SubElement(chs, "choice")
            _attr(ce, [("val", c.get("val")), ("points", c.get("points")), ("flag", c.get("flag"))])
            if c.get("display"): _text(ce, "display", c["display"])
            if c.get("note"): _text(ce, "note", c["note"])

def _compose_section(parent_items: Element, node: Dict):
    sec = SubElement(parent_items, "section")
    attrs = node.get("attributes", {}) or {}
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

    # captions / notes
    if node.get("header"):
        _text(sec, "c", node["header"])

    # hints
    if node.get("hints"):
        hints = SubElement(sec, "hints")
        for h in node["hints"]:
            ht = SubElement(hints, "hint")
            ht.text = h

    items = SubElement(sec, "items")
    for ch in node.get("items", []):
        if ch.get("kind") == "section":
            _compose_section(items, ch)
        elif ch.get("kind") == "item":
            _compose_item(items, ch)

def compose_xml(cir: Dict) -> bytes:
    meta = cir["meta"]
    root = Element("eform")
    # Attribute order approximates schema order
    _attr(root, [
        ("ref", meta.get("ref")),
        ("noteVersion", str(meta.get("noteVersion", DEFAULT_NOTE_VERSION))),
        ("title", meta.get("title")),
        ("shortForm", meta.get("shortForm")),
        ("noteType", meta.get("noteType")),
        ("dataSecurityMode", meta.get("dataSecurityMode")),
    ])

    # Optional top-level info
    _text(root, "tagLine", cir.get("tagLine"))
    _text(root, "desc", cir.get("desc"))
    _text(root, "keywords", cir.get("keywords"))

    # main section
    main = SubElement(root, "mainSection")
    # Sections under a wrapper <items> to mirror schema
    ms_items = SubElement(main, "items")
    for s in cir.get("sections", []):
        _compose_section(ms_items, s)

    pretty = minidom.parseString(tostring(root, encoding="utf-8")).toprettyxml(indent="  ", encoding="utf-8")
    return pretty
