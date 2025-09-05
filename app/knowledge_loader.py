# app/knowledge_loader.py
# Loads compact runtime guidance from knowledge/runtime and builds per-request bundles.

from __future__ import annotations
import os, json, re
from pathlib import Path
from typing import Dict, List, Any

DEFAULT_KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", "knowledge/runtime")

ITEMTYPE_FALLBACK = [
    "TEXT_FIELD", "TEXT_AREA", "TEXT_FIELD_NUMERIC",
    "MENU", "MENU_MULTI_SELECT", "CHECKBOX", "PROPOSITION",
    "DATE", "NUMERIC_SCALE", "FORMULA", "FILE_UPLOAD"
]

_KEYWORDS_MAP = [
    (r"\b(select all|check all|multi-?select|multiple choices?)\b", ["MENU_MULTI_SELECT", "CHECKBOX"]),
    (r"\b(dropdown|pick one|single[- ]choice|menu)\b", ["MENU"]),
    (r"\b(yes/no|yes or no|agree|consent|accept|decline)\b", ["PROPOSITION"]),
    (r"\b(checkbox|tick box|tick this)\b", ["CHECKBOX"]),
    (r"\b(long answer|comments?|notes?)\b", ["TEXT_AREA"]),
    (r"\b(short answer|single line|name|city|address|reason)\b", ["TEXT_FIELD"]),
    (r"\b(number|numeric|quantity|age|height|weight|cm|kg|lbs)\b", ["TEXT_FIELD_NUMERIC"]),
    (r"\b(date of birth|dob|date\b|\bYYYY[-/ ]MM[-/ ]DD)\b", ["DATE"]),
    (r"\b(scale|1[-–]5|0[-–]10|rating)\b", ["NUMERIC_SCALE"]),
    (r"\b(score|total|calculated|bmi|formula|sum|average)\b", ["FORMULA"]),
    (r"\b(upload|attach|file)\b", ["FILE_UPLOAD"]),
    (r"\b(duration|how long|minutes|hours)\b", ["APPROXIMATE_DURATION"]),
    (r"\b(month/year|approximate date|about when)\b", ["APPROXIMATE_DATE"]),
]

class Knowledge:
    def __init__(self, base_dir: str = DEFAULT_KNOWLEDGE_DIR):
        self.base_path = Path(base_dir)
        if not self.base_path.exists():
            raise RuntimeError(f"Knowledge directory not found: {self.base_path.resolve()}")

        # Core packs
        self.handbook = self._load_json("handbook_small.json")
        self.section_style = self._load_json("section_style.json")
        self.scripting = self._load_json("scripting.json")
        self.macros = self._load_json("macros.json")
        self.ref_naming = self._load_json("ref_naming.json")

        # Item type shards
        self.itemtypes_dir = self.base_path / "itemtypes"
        self.itemtypes: Dict[str, Dict[str, Any]] = {}
        if self.itemtypes_dir.exists():
            for p in self.itemtypes_dir.glob("*.json"):
                try:
                    d = json.loads(p.read_text(encoding="utf-8"))
                    t = str(d.get("type") or p.stem).upper()
                    self.itemtypes[t] = d
                except Exception:
                    continue
        if not self.itemtypes:
            raise RuntimeError(f"No item type shards found in {self.itemtypes_dir}")

        # Acceptance checks (top list used in prompts)
        self.acceptance_checks: List[str] = list(self.handbook.get("acceptance_checks", []))[:24]

    def _load_json(self, rel: str) -> Dict[str, Any] | List[Any]:
        p = self.base_path / rel
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            raise RuntimeError(f"Failed to load {p}: {e}")

    def all_item_types(self) -> List[str]:
        return sorted(self.itemtypes.keys())

    def predict_item_types(self, description: str) -> List[str]:
        """Heuristic: infer likely item types from free-text description."""
        desc = (description or "").lower()
        found: List[str] = []
        for pat, types in _KEYWORDS_MAP:
            if re.search(pat, desc):
                for t in types:
                    if t not in found:
                        found.append(t)
        # Always include a practical baseline
        for t in ITEMTYPE_FALLBACK:
            if t not in found:
                found.append(t)
        # Keep only shards we actually have
        return [t for t in found if t in self.itemtypes]

    def bundle(self, include_types: List[str] | None = None, extra_acceptance: List[str] | None = None) -> Dict[str, Any]:
        """Build a compact bundle for prompts."""
        types = include_types or []
        types = [t.upper() for t in types if t.upper() in self.itemtypes]
        if not types:
            types = ITEMTYPE_FALLBACK
            types = [t for t in types if t in self.itemtypes]

        itemtype_guides = {t: self.itemtypes[t] for t in types}
        acc = list(self.acceptance_checks)
        for a in (extra_acceptance or []):
            if a not in acc:
                acc.append(a)

        return {
            "section_style": self.section_style,
            "scripting": self.scripting,
            "macros": self.macros,
            "ref_naming": self.ref_naming,
            "acceptance_checks": acc,
            "item_types": itemtype_guides,
        }
