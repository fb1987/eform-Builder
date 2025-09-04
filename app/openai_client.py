# app/openai_client.py
import json
from typing import Dict, Tuple
from openai import OpenAI
from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.cir_schema import CIR_JSON_SCHEMA

# NOTE: Requires OpenAI Python SDK (Responses API).
# Structured Outputs with json_schema and strict true.
# Docs: Structured Outputs & Responses API.  # :contentReference[oaicite:1]{index=1}

_client = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client

SYSTEM_PROMPT = """You are an Ocean eForm architect. Produce ONLY a valid CIR JSON object that matches the provided JSON Schema.
Rules:
- Use ONLY allowed enums for itemType, flagColor, hints, validator types, noteType, dataSecurityMode.
- Generate safe item refs matching ^[A-Za-z0-9_]+$ (unique within the form).
- Prefer concise, clinically sensible item texts and sections.
- If user asks for complex logic, use showIf/makeNoteIf/formula accordingly (reference items by ref).
- Keep the output minimal; omit null/empty fields.
"""

def _response_format():
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "ocean_cir",
            "schema": CIR_JSON_SCHEMA,
            "strict": True
        }
    }

def cir_from_description(description: str, defaults: Dict) -> Tuple[Dict, str]:
    """
    Create a CIR from a free-text description using structured outputs.
    Returns (cir_dict, raw_json_string).
    """
    client = _get_client()
    input_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Defaults: {json.dumps(defaults)}\n\nDescription:\n{description.strip()}"}
    ]
    resp = client.responses.create(
        model=OPENAI_MODEL,
        input=input_messages,
        response_format=_response_format(),
    )
    # Robust parsing across SDK versions
    cir = getattr(resp, "output_parsed", None)
    if not cir:
        txt = getattr(resp, "output_text", None)
        if not txt and getattr(resp, "output", None):
            try:
                txt = resp.output[0].content[0].text  # older shape
            except Exception:
                txt = None
        cir = json.loads(txt) if txt else {}
    raw = json.dumps(cir, ensure_ascii=False)
    return cir, raw

def cir_from_pdf_text(pdf_text: str, defaults: Dict) -> Tuple[Dict, str]:
    client = _get_client()
    prompt = f"""You are converting a paper form into Ocean eForm CIR.

PDF text (may be messy, deduplicate & normalize headings/fields):
---
{pdf_text[:20000]}
---

Defaults: {json.dumps(defaults)}

Return ONLY CIR JSON."""
    resp = client.responses.create(
        model=OPENAI_MODEL,
        input=[{"role": "system", "content": SYSTEM_PROMPT},
               {"role": "user", "content": prompt}],
        response_format=_response_format(),
    )
    cir = getattr(resp, "output_parsed", None)
    if not cir:
        txt = getattr(resp, "output_text", None)
        if not txt and getattr(resp, "output", None):
            try:
                txt = resp.output[0].content[0].text
            except Exception:
                txt = None
        cir = json.loads(txt) if txt else {}
    raw = json.dumps(cir, ensure_ascii=False)
    return cir, raw
