# app/openai_client.py
import json
import re
from typing import Dict, Tuple
from openai import OpenAI, APIError
from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.cir_schema import CIR_JSON_SCHEMA

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
- Use showIf/makeNoteIf/formula appropriately, referencing items by ref.
- Keep output minimal; omit null/empty fields.
"""

def _strip_json_fences(s: str) -> str:
    if not s:
        return s
    s = s.strip()
    # Remove ```json ... ``` or ``` ... ```
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", s, flags=re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else s

def _chat_with_schema(messages, schema: Dict) -> Dict:
    """
    Primary path: Chat Completions with Structured Outputs via response_format.json_schema (strict).
    Fallback: JSON mode + local parse if the server rejects json_schema.
    """
    client = _get_client()
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "ocean_cir",
            "schema": schema,
            "strict": True
        }
    }
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            response_format=response_format,  # Structured Outputs (strict)
            temperature=1
        )
        txt = resp.choices[0].message.content
        cir = json.loads(_strip_json_fences(txt))
        return cir
    except APIError as e:
        # If the installed API/model rejects json_schema response_format, retry with JSON mode.
        if getattr(e, "status_code", None) in (400, 404) or "response_format" in str(e):
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    messages[0],  # system
                    {
                        "role": "user",
                        "content": (
                            "Return ONLY valid JSON that adheres to this JSON Schema. "
                            "Do not include any explanation or code fences.\n\n"
                            f"JSON Schema:\n{json.dumps(schema)}\n\n"
                            f"Task:\n{messages[-1]['content']}"
                        ),
                    },
                ],
                response_format={"type": "json_object"},  # JSON mode
                temperature=1
            )
            txt = resp.choices[0].message.content
            return json.loads(_strip_json_fences(txt))
        raise

def cir_from_description(description: str, defaults: Dict) -> Tuple[Dict, str]:
    """
    Create a CIR from a free-text description using structured output (chat completions).
    Returns (cir_dict, raw_json_string).
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Defaults: {json.dumps(defaults)}\n\nDescription:\n{description.strip()}"},
    ]
    cir = _chat_with_schema(messages, CIR_JSON_SCHEMA)
    raw = json.dumps(cir, ensure_ascii=False)
    return cir, raw

def cir_from_pdf_text(pdf_text: str, defaults: Dict) -> Tuple[Dict, str]:
    prompt = f"""You are converting a paper form into Ocean eForm CIR.

PDF text (may be messy; normalize headings/fields; avoid duplicates):
---
{pdf_text[:20000]}
---

Defaults: {json.dumps(defaults)}

Return ONLY CIR JSON."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    cir = _chat_with_schema(messages, CIR_JSON_SCHEMA)
    raw = json.dumps(cir, ensure_ascii=False)
    return cir, raw
