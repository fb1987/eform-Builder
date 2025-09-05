# app/openai_client.py
import json
import re
from typing import Dict, Tuple
from openai import OpenAI, APIError
from app.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE
from app.cir_schema import CIR_JSON_SCHEMA
from app.guidance import build_guidance_block
import os

_client = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client

USE_DATA_GUIDANCE = os.getenv("USE_DATA_GUIDANCE", "0") == "1"

BASE_SYSTEM = """You are an Ocean eForm architect. Produce ONLY a valid CIR JSON object that matches the provided JSON Schema.
Rules:
- Use ONLY allowed enums for itemType, flagColor, hints, validator types, noteType, dataSecurityMode.
- Generate safe item refs matching ^[A-Za-z0-9_]+$ (unique within the form).
- Use showIf/makeNoteIf/formula appropriately, referencing items by ref.
- Keep output minimal; omit null/empty fields."""

def _strip_json_fences(s: str) -> str:
    if not s: return s
    s = s.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", s, flags=re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else s

def _chat_with_schema(messages, schema: Dict) -> Dict:
    client = _get_client()
    response_format = {
        "type": "json_schema",
        "json_schema": {"name": "ocean_cir", "schema": schema, "strict": True}
    }
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            response_format=response_format,
            temperature=OPENAI_TEMPERATURE,
        )
        txt = resp.choices[0].message.content
        return json.loads(_strip_json_fences(txt))
    except APIError as e:
        if getattr(e, "status_code", None) in (400, 404) or "response_format" in str(e):
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    messages[0],
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
                response_format={"type": "json_object"},
                temperature=OPENAI_TEMPERATURE,
            )
            return json.loads(_strip_json_fences(resp.choices[0].message.content))
        raise

def _system_with_guidance(user_text: str, defaults: Dict) -> str:
    if not USE_DATA_GUIDANCE:
        return BASE_SYSTEM
    block = build_guidance_block(user_text, defaults)
    return BASE_SYSTEM + "\n\n" + block

def cir_from_description(description: str, defaults: Dict) -> Tuple[Dict, str]:
    system = _system_with_guidance(description, defaults)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Defaults: {json.dumps(defaults)}\n\nDescription:\n{description.strip()}"},
    ]
    cir = _chat_with_schema(messages, CIR_JSON_SCHEMA)
    return cir, json.dumps(cir, ensure_ascii=False)

def cir_from_pdf_text(pdf_text: str, defaults: Dict) -> Tuple[Dict, str]:
    system = _system_with_guidance(pdf_text[:1000], defaults)
    prompt = f"""Convert this paper form text into Ocean CIR.

PDF text (normalize headings/fields; avoid duplicates):
---
{pdf_text[:20000]}
---

Defaults: {json.dumps(defaults)}

Return ONLY CIR JSON."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    cir = _chat_with_schema(messages, CIR_JSON_SCHEMA)
    return cir, json.dumps(cir, ensure_ascii=False)
