"""Preset marketplace for submitting and sharing presets."""

from __future__ import annotations

from src.presets.validator import PresetValidator


class PresetMarketplace:
    """Minimal preset marketplace.

    Future: support PR-based submission to a shared GitHub repository.
    """

    def __init__(self, validator: PresetValidator) -> None:
        self.validator = validator

    def submit_preset(self, preset_json: dict, author: str) -> dict:
        """Submit a preset for validation.

        Args:
            preset_json: The preset dictionary to submit.
            author: The author name to attach to the preset.

        Returns:
            A status dictionary with "status" and "preset_id" keys.

        Raises:
            PresetError: If validation fails.
        """
        preset = dict(preset_json)
        preset["author"] = author
        self.validator.validate(preset)
        return {"status": "validated", "preset_id": preset["id"]}
