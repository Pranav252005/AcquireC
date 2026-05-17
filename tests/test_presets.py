"""Tests for the preset system."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from src.presets import PresetError, PresetLoader, PresetMarketplace, PresetValidator


class TestPresetLoader:
    """Test suite for PresetLoader."""

    def test_load_returns_dict_for_valid_preset(self, tmp_path: Path) -> None:
        """load() should return a dict for an existing preset file."""
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        preset_data = {"id": "test_preset", "name": "Test"}
        preset_file = presets_dir / "test_preset.json"
        preset_file.write_text(json.dumps(preset_data), encoding="utf-8")

        loader = PresetLoader(presets_dir=str(presets_dir))
        result = loader.load("test_preset")

        assert isinstance(result, dict)
        assert result["id"] == "test_preset"
        assert result["name"] == "Test"

    def test_load_raises_preset_error_for_missing_preset(self, tmp_path: Path) -> None:
        """load() should raise PresetError when the preset file is missing."""
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        loader = PresetLoader(presets_dir=str(presets_dir))

        with pytest.raises(PresetError, match="Preset not found: missing"):
            loader.load("missing")

    def test_load_raises_preset_error_for_malformed_json(self, tmp_path: Path) -> None:
        """load() should raise PresetError for malformed JSON."""
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "bad.json").write_text("not json", encoding="utf-8")
        loader = PresetLoader(presets_dir=str(presets_dir))

        with pytest.raises(PresetError, match="Malformed JSON"):
            loader.load("bad")

    def test_list_presets_skips_malformed_files(self, tmp_path: Path) -> None:
        """list_presets() should skip malformed files and return valid ones."""
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "good.json").write_text(json.dumps({"name": "Good"}), encoding="utf-8")
        (presets_dir / "bad.json").write_text("not json", encoding="utf-8")
        loader = PresetLoader(presets_dir=str(presets_dir))

        results = loader.list_presets()
        assert len(results) == 1
        assert results[0]["id"] == "good"

    def test_list_presets_returns_all_presets(self, tmp_path: Path) -> None:
        """list_presets() should return all presets with injected IDs."""
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        for i in range(5):
            data = {"name": f"Preset {i}", "version": "1.0.0"}
            (presets_dir / f"preset_{i}.json").write_text(
                json.dumps(data), encoding="utf-8"
            )

        loader = PresetLoader(presets_dir=str(presets_dir))
        results = loader.list_presets()

        assert len(results) == 5
        ids = {r["id"] for r in results}
        assert ids == {"preset_0", "preset_1", "preset_2", "preset_3", "preset_4"}

    def test_load_all_returns_mapping(self, tmp_path: Path) -> None:
        """load_all() should return a dict keyed by preset ID."""
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        for i in range(3):
            data = {"name": f"Preset {i}", "version": "1.0.0"}
            (presets_dir / f"preset_{i}.json").write_text(
                json.dumps(data), encoding="utf-8"
            )

        loader = PresetLoader(presets_dir=str(presets_dir))
        all_presets = loader.load_all()

        assert set(all_presets.keys()) == {"preset_0", "preset_1", "preset_2"}

    def test_load_with_validator_validates_preset(self, tmp_path: Path) -> None:
        """load() should validate when a validator is provided."""
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "invalid.json").write_text(
            json.dumps({"id": "invalid"}), encoding="utf-8"
        )
        loader = PresetLoader(
            presets_dir=str(presets_dir), validator=PresetValidator()
        )

        with pytest.raises(ValidationError):
            loader.load("invalid")

    def test_list_presets_with_validator_skips_invalid(self, tmp_path: Path) -> None:
        """list_presets() should skip invalid presets when validator is provided."""
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        valid = {
            "id": "valid",
            "name": "Valid",
            "version": "1.0.0",
            "target": {"categories": ["cafe"]},
            "pitch": {"tone": "friendly", "max_length": 500},
        }
        (presets_dir / "valid.json").write_text(json.dumps(valid), encoding="utf-8")
        (presets_dir / "invalid.json").write_text(
            json.dumps({"id": "invalid"}), encoding="utf-8"
        )
        loader = PresetLoader(
            presets_dir=str(presets_dir), validator=PresetValidator()
        )

        results = loader.list_presets()
        assert len(results) == 1
        assert results[0]["id"] == "valid"

    def test_default_presets_dir_uses_settings(self, monkeypatch) -> None:
        """PresetLoader should default to settings.presets_dir when no arg given."""
        from src.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "presets_dir", "./presets")
        loader = PresetLoader()
        assert loader.presets_dir == Path("./presets")


class TestPresetValidator:
    """Test suite for PresetValidator."""

    def _valid_preset(self) -> dict:
        return {
            "id": "test",
            "name": "Test Preset",
            "version": "1.0.0",
            "description": "A test preset.",
            "author": "tester",
            "target": {
                "categories": ["cafe"],
                "cities": ["Mumbai"],
                "countries": ["IN"],
            },
            "scrapers": ["google_maps"],
            "pain_points": {
                "detectors": [
                    {"id": "no_website", "weight": 1.0},
                ],
            },
            "pitch": {
                "tone": "friendly",
                "max_length": 1000,
                "must_include": ["website"],
                "system_prompt": "You are a consultant.",
            },
            "membership": {
                "concepts": {"cafe": "Coffee Club"},
            },
            "follow_up": {
                "sequence": "gentle",
                "channels": ["email"],
            },
        }

    def test_validate_passes_for_valid_preset(self) -> None:
        """validate() should not raise for a valid preset."""
        validator = PresetValidator()
        preset = self._valid_preset()
        validator.validate(preset)

    def test_validate_raises_for_missing_required_field(self) -> None:
        """validate() should raise ValidationError when a required field is missing."""
        validator = PresetValidator()
        preset = self._valid_preset()
        del preset["target"]

        with pytest.raises(ValidationError):
            validator.validate(preset)

    def test_validate_raises_for_invalid_version(self) -> None:
        """validate() should raise ValidationError for an invalid version string."""
        validator = PresetValidator()
        preset = self._valid_preset()
        preset["version"] = "1.0"

        with pytest.raises(ValidationError):
            validator.validate(preset)

    def test_validate_raises_for_invalid_country_code(self) -> None:
        """validate() should raise ValidationError for an invalid country code."""
        validator = PresetValidator()
        preset = self._valid_preset()
        preset["target"]["countries"] = ["in"]

        with pytest.raises(ValidationError):
            validator.validate(preset)


class TestPresetMarketplace:
    """Test suite for PresetMarketplace."""

    def test_submit_preset_returns_validated_status(self, tmp_path: Path) -> None:
        """submit_preset() should return a validated status dict."""
        validator = PresetValidator()
        marketplace = PresetMarketplace(validator)

        preset = {
            "id": "marketplace_test",
            "name": "Marketplace Test",
            "version": "1.0.0",
            "target": {
                "categories": ["gym"],
            },
            "pitch": {
                "tone": "professional",
                "max_length": 500,
            },
        }

        result = marketplace.submit_preset(preset, author="test_author")

        assert result["status"] == "validated"
        assert result["preset_id"] == "marketplace_test"
        assert "author" not in preset

    def test_submit_preset_raises_on_invalid_preset(self, tmp_path: Path) -> None:
        """submit_preset() should raise ValidationError for an invalid preset."""
        validator = PresetValidator()
        marketplace = PresetMarketplace(validator)

        preset = {
            "id": "bad_preset",
            "name": "Bad Preset",
            "version": "1.0.0",
        }

        with pytest.raises(ValidationError):
            marketplace.submit_preset(preset, author="test_author")


class TestDefaultPresets:
    """Test suite for the bundled default presets."""

    def test_all_default_presets_are_valid(self) -> None:
        """All bundled presets should pass validation."""
        loader = PresetLoader(presets_dir="./presets")
        validator = PresetValidator()
        presets = loader.list_presets()

        assert len(presets) == 5
        for preset in presets:
            validator.validate(preset)

    def test_default_presets_match_expected_ids(self) -> None:
        """Bundled presets should have the expected IDs."""
        loader = PresetLoader(presets_dir="./presets")
        all_presets = loader.load_all()

        expected = {
            "web_design_agency",
            "seo_freelancer",
            "social_media_manager",
            "real_estate_agent",
            "insurance_agent",
        }
        assert set(all_presets.keys()) == expected
