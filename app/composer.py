# app/composer.py
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from typing import Dict, List, Optional
from app.config import DEFAULT_NOTE_VERSION
from app.enums import FLAG_COLORS, NOTE_STYLES

def _attr(el: Element, pairs: List[tuple]):
    """Set attributes in a stable order, skipping empty/None."""
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

def _write_validators(el: Element, node: Dict):
    """
    Accept either:
      - node["validator"] = {type, allowEmpty, format, message, validIf}
      - node["validators"] = [ {...}, ... ]
    """
    v_single = node.get("validator")
    v_list = node.get("validators")

    validators: List[Dict] = []
    if isinstance(v_list, list) and v_list:
        validators = [v for v in v_list if isinstance(v, dict)]
    elif isinstance(v_single, dict):
        validators = [v_single]

    for v in validators:
        if not any(v.get(k) for k in ("type", "validIf", "format", "message", "allowEmpty")):
            continue
        vv = SubElement(el, "validator")
        _attr(vv, [
            ("type", v.get("type")),
            ("format", v.get("format")),
            ("message", v.get("message")),
            ("validIf", v.get("validIf")),
        ])
        if v.get("allowEmpty") is not None:
            _set_bool_attr(vv, "allowEmpty", v.get("allowEmpty"))

def _compose_item(parent_items: Element, node: Dict):
    # PICTURE/VIDEO/DIAGRAM map to dedicated tags
    itype = (node.get("type") or "LABEL").upper()
    if itype in {"PICTURE", "VIDEO", "DIAGRAM"}:
        tag = "picture" if itype == "PICTURE" else ("video" if itype == "VIDEO" else "diagram")
        el = SubElement(parent_items, tag)
        _attr(el, [
            ("ref", node.get("ref")),
            ("x", node.get("x")), ("y", node.get("y")),
            ("showIf", node.get("showIf")),
            ("makeNoteIf", node.get("makeNoteIf")),
            ("noteIndex", node.get("noteIndex")),
        ])
        _set_bool_attr(el, "ownLine", node.get("ownLine"))
        return

    # Regular item
    el = SubElement(parent_items, "item")
    _attr(el, [
        ("ref", node.get("ref")),
        ("type", itype),
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

    # Visible prompt -> <c>
    # Prefill/default text/macros -> <text>
    # Notes template -> <cNote>
    # Backward-compat: if only "text" was provided, we keep it as <text>.
    if node.get("label"):
        _text(el, "c", node["label"])
    if node.get("text"):
        _text(el, "text", node["text"])
    if node.get("cNote"):
        _text(el, "cNote", node["cNote"])
    elif node.get("note"):
        _text(el, "cNote", node["note"])

    if node.get("tooltip"):
        _text(el, "tooltip", node["tooltip"])
    if node.get("studyColumnHeader"):
        _text(el, "studyColumnHeader", node["studyColumnHeader"])
    if node.get("markableDiagramFileName"):
        _text(el, "markableDiagramFileName", node["markableDiagramFileName"])

    # dxCode packed as "code|desc|type"
    if node.get("dxCode"):
        dx = SubElement(el, "dxCode")
        parts = (node["dxCode"] or "").split("|")
        if len(parts) > 0:
            dx.set("code", parts[0])
        if len(parts) > 1:
            dx.set("desc", parts[1])
        if len(parts) > 2:
            dx.set("type", parts[2])

    # validators (single or list)
    _write_validators(el, node)

    # hints
    if node.get("hints"):
        hints = SubElement(el, "hints")
        for h in node["hints"]:
            ht = SubElement(hints, "hint")
            ht.text = str(h)

    # choices
    if node.get("choices"):
        chs = SubElement(el, "choices")
        for c in node["choices"]:
            if not isinstance(c, dict):
                continue
            ce = SubElement(chs, "choice")
            _attr(ce, [
                ("val", c.get("val")),
                ("points", c.get("points")),
                ("flag", c.get("flag")),
            ])
            if c.get("display"):
                _text(ce, "display", c["display"])
            if c.get("note"):
                _text(ce, "note", c["note"])

def _compose_section(parent_items: Element, node: Dict):
    sec = SubElement(parent_items, "section")
    attrs = (node.get("attributes") or {}) if isinstance(node.get("attributes"), dict) else {}

    # Default to QUESTIONNAIRE and BOLD if not provided
    subcat = attrs.get("subcategory") or "QUESTIONNAIRE"
    header_style = attrs.get("headerStyle") or "BOLD"

    _attr(sec, [
        ("ref", node.get("ref")),
        ("subcategory", subcat),
        ("headerStyle", header_style),
        ("expandIf", attrs.get("expandIf")),
        ("showIf", attrs.get("showIf")),
        ("makeNoteIf", attrs.get("makeNoteIf")),
        ("flag", attrs.get("flag")),
        ("noteIndex", attrs.get("noteIndex")),
    ])
    _set_bool_attr(sec, "groupItems", attrs.get("groupItems"))
    _set_bool_attr(sec, "quoteAnswers", attrs.get("quoteAnswers"))
    _set_bool_attr(sec, "ownLine", attrs.get("ownLine"))

    # Section caption
    # Accept either node["header"] or node["title"] as the section <c>
    if node.get("header"):
        _text(sec, "c", node["header"])
    elif node.get("title"):
        _text(sec, "c", node["title"])

    # Section hints
    if node.get("hints"):
        hints = SubElement(sec, "hints")
        for h in node["hints"]:
            ht = SubElement(hints, "hint")
            ht.text = str(h)

    items = SubElement(sec, "items")
    for ch in node.get("items", []):
        kind = ch.get("kind")
        if kind == "section":
            _compose_section(items, ch)
        elif kind == "item":
            _compose_item(items, ch)

    # Optional list separator on section if supplied
    if node.get("listSep"):
        _text(sec, "listSep", node["listSep"])

def compose_xml(cir: Dict) -> bytes:
    meta = cir.get("meta", {})
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
    ms_items = SubElement(main, "items")
    for s in cir.get("sections", []):
        if isinstance(s, dict) and s.get("kind") == "section":
            _compose_section(ms_items, s)

    # Optional multiPage, actions, refs, etc. (kept minimal for MVP)
    # If you want explicit <multiPage>false</multiPage>, uncomment:
    # _text(root, "multiPage", "false")

    pretty = minidom.parseString(tostring(root, encoding="utf-8")).toprettyxml(
        indent="  ", encoding="utf-8"
    )
    return pretty
