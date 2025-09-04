# app/cir_schema.py
from app.enums import (
    ITEM_TYPES, FIELD_VALIDATOR_TYPES, HINTS, FLAG_COLORS, NOTE_STYLES,
    DATA_SECURITY_MODES, NOTE_TYPES, ITEM_SUBCATEGORIES, EMR_FIELDS
)

# JSON Schema dict for Structured Outputs (OpenAI Responses API)
CIR_JSON_SCHEMA = {
  "type": "object",
  "additionalProperties": False,
  "properties": {
    "meta": {
      "type": "object",
      "additionalProperties": False,
      "required": ["ref", "title", "noteVersion", "noteType", "dataSecurityMode"],
      "properties": {
        "ref": {"type": "string", "pattern": "^[A-Za-z0-9_]+$"},
        "title": {"type": "string", "minLength": 1},
        "shortForm": {"type": "string"},
        "noteVersion": {"type": "integer"},
        "noteType": {"type": "string", "enum": sorted(list(NOTE_TYPES))},
        "dataSecurityMode": {"type": "string", "enum": sorted(list(DATA_SECURITY_MODES))}
      }
    },
    "desc": {"type": "string"},
    "tagLine": {"type": "string"},
    "keywords": {"type": "string"},
    "sections": {
      "type": "array",
      "items": {"$ref": "#/$defs/section"}
    }
  },
  "required": ["meta", "sections"],
  "$defs": {
    "section": {
      "type": "object",
      "additionalProperties": False,
      "required": ["kind", "items"],
      "properties": {
        "kind": {"type": "string", "const": "section"},
        "ref": {"type": "string"},
        "header": {"type": "string"},
        "attributes": {
          "type": "object",
          "additionalProperties": False,
          "properties": {
            "subcategory": {"type": "string"},
            "headerStyle": {"type": "string", "enum": sorted(list(NOTE_STYLES))},
            "groupItems": {"type": "boolean"},
            "quoteAnswers": {"type": "boolean"},
            "expandIf": {"type": "string"},
            "showIf": {"type": "string"},
            "makeNoteIf": {"type": "string"},
            "flag": {"type": "string", "enum": sorted(list(FLAG_COLORS))},
            "noteIndex": {"type": "string"},
            "ownLine": {"type": "boolean"}
          }
        },
        "hints": {
          "type": "array",
          "items": {"type": "string", "enum": sorted(list(HINTS))}
        },
        "items": {
          "type": "array",
          "items": {"anyOf": [{"$ref": "#/$defs/section"}, {"$ref": "#/$defs/item"}]}
        }
      }
    },
    "choice": {
      "type": "object",
      "additionalProperties": False,
      "required": ["val"],
      "properties": {
        "val": {"type": "string"},
        "display": {"type": "string"},
        "points": {"type": "string"},
        "flag": {"type": "string", "enum": sorted(list(FLAG_COLORS))},
        "note": {"type": "string"}
      }
    },
    "item": {
      "type": "object",
      "additionalProperties": False,
      "required": ["kind", "type"],
      "properties": {
        "kind": {"type": "string", "const": "item"},
        "ref": {"type": "string"},
        "type": {"type": "string", "enum": sorted(list(ITEM_TYPES))},
        "text": {"type": "string"},
        "formula": {"type": "string"},
        "showIf": {"type": "string"},
        "makeNoteIf": {"type": "string"},
        "noteIndex": {"type": "string"},
        "ownLine": {"type": "boolean"},
        "quoteAnswer": {"type": "boolean"},
        "x": {"type": "string"},
        "y": {"type": "string"},
        "subcategory": {"type": "string"},
        "tooltip": {"type": "string"},
        "studyColumnHeader": {"type": "string"},
        "markableDiagramFileName": {"type": "string"},
        "dxCode": {"type": "string"},
        "flag": {"type": "string", "enum": sorted(list(FLAG_COLORS))},
        "negFlag": {"type": "string", "enum": sorted(list(FLAG_COLORS))},
        "emrField": {"type": "string"},
        "choices": { "type": "array", "items": {"$ref": "#/$defs/choice"} },
        "validator": {
          "type": "object",
          "additionalProperties": False,
          "properties": {
            "type": {"type": "string", "enum": sorted(list(FIELD_VALIDATOR_TYPES))},
            "format": {"type": "string"},
            "message": {"type": "string"},
            "allowEmpty": {"type": "boolean"},
            "validIf": {"type": "string"}
          }
        },
        "hints": {
          "type": "array",
          "items": {"type": "string", "enum": sorted(list(HINTS))}
        }
      }
    }
  }
}
