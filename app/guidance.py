# app/guidance.py
import json, os
from pathlib import Path
from typing import Dict

KB_PATH = Path(os.getenv("KB_MIN_PATH", "handbook/kb_min.json"))
GUIDANCE_MAX_CHARS = int(os.getenv("GUIDANCE_MAX_CHARS", "16000"))

_cached_kb = None

def _kb():
    global _cached_kb
    if _cached_kb is None:
        if KB_PATH.exists():
            _cached_kb = json.loads(KB_PATH.read_text(encoding="utf-8"))
        else:
            _cached_kb = {"type_defaults":{}, "keyword_map":[], "logic_examples":[], "menu_hint_thresholds":{"searchable":7,"dropdown":3}, "snippets":[]}
    return _cached_kb

def _suggestions_from_text(text: str) -> Dict:
    text_l = (text or "").lower()
    kb = _kb()
    found = {"validators": set(), "item_types": set()}
    for m in kb.get("keyword_map", []):
        tok = m.get("token","")
        if tok and tok in text_l:
            if m.get("suggest_validator"):
                found["validators"].add(m["suggest_validator"])
            if m.get("suggest_item_type"):
                found["item_types"].add(m["suggest_item_type"])
    return {"validators": sorted(found["validators"]), "item_types": sorted(found["item_types"])}

def build_guidance_block(user_text: str, defaults: Dict, max_chars: int = GUIDANCE_MAX_CHARS) -> str:
    kb = _kb()
    sugg = _suggestions_from_text(user_text)

    # Compose compact guidance text
    lines = []
    lines.append("Guidance:")
    lines.append("- Use CIR JSON that matches the provided schema. Only allowed enums.")
    if sugg["validators"]:
        lines.append(f"- Suggested validators from description: {', '.join(sugg['validators'])}.")
    if sugg["item_types"]:
        lines.append(f"- Suggested item types from description: {', '.join(sugg['item_types'])}.")

    # Per-type defaults (top few)
    td = kb.get("type_defaults", {})
    hot_types = ["TEXT_FIELD","DATE","MENU","MENU_MULTI_SELECT","PROPOSITION","NO_YES_NOT_SURE","TEXT_AREA","FILE_UPLOAD"]
    lines.append("\nType defaults (common patterns):")
    for t in hot_types:
        if t not in td: continue
        d = td[t]
        lines.append(f"- {t}: validators={d.get('common_validator_types', [])[:2]}, hints={d.get('common_hints', [])[:3]}")

    # Logic examples
    le = kb.get("logic_examples", [])[:8]
    if le:
        lines.append("\nLogic examples:")
        for ex in le:
            lines.append(f"- {ex}")

    # A couple of snippets
    snips = kb.get("snippets", [])[:3]
    if snips:
        lines.append("\nExample items (CIR fragments):")
        for s in snips:
            lines.append(f"- {s['title']}: {json.dumps(s['item'], ensure_ascii=False)}")

    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars]
    return text
