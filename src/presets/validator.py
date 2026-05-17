"""Preset schema validation using jsonschema."""

from __future__ import annotations

from jsonschema import ValidationError, validate


class PresetError(Exception):
    """Raised when a preset operation fails."""


PRESET_SCHEMA = {
    "type": "object",
    "required": ["id", "name", "version", "target", "pitch"],
    "properties": {
        "id": {"type": "string", "pattern": "^[a-z0-9_]+$"},
        "name": {"type": "string", "minLength": 1},
        "version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$"},
        "description": {"type": "string"},
        "author": {"type": "string"},
        "target": {
            "type": "object",
            "required": ["categories"],
            "properties": {
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
                "cities": {"type": "array", "items": {"type": "string"}},
                "countries": {
                    "type": "array",
                    "items": {"type": "string", "pattern": "^[A-Z]{2}$"},
                },
            },
        },
        "scrapers": {
            "type": "array",
            "items": {
                "enum": ["google_maps", "justdial", "yelp", "yellow_pages"]
            },
        },
        "pain_points": {
            "type": "object",
            "properties": {
                "detectors": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "weight": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                        },
                        "required": ["id", "weight"],
                    },
                },
            },
        },
        "pitch": {
            "type": "object",
            "required": ["tone", "max_length"],
            "properties": {
                "tone": {"type": "string"},
                "max_length": {"type": "integer", "minimum": 100},
                "must_include": {"type": "array", "items": {"type": "string"}},
                "system_prompt": {"type": "string"},
            },
        },
        "membership": {
            "type": "object",
            "properties": {
                "concepts": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
            },
        },
        "follow_up": {
            "type": "object",
            "properties": {
                "sequence": {
                    "type": "string",
                    "enum": ["gentle", "aggressive", "b2b_enterprise"],
                },
                "channels": {
                    "type": "array",
                    "items": {"enum": ["email", "whatsapp"]},
                },
            },
        },
    },
}


class PresetValidator:
    """Validate preset dictionaries against the PRESET_SCHEMA."""

    def validate(self, preset: dict) -> None:
        """Validate a preset dict against the schema.

        Args:
            preset: The preset dictionary to validate.

        Raises:
            ValidationError: If the preset fails schema validation.
        """
        validate(instance=preset, schema=PRESET_SCHEMA)
