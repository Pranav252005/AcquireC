"""Preset loading utilities."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.config import get_settings
from src.presets.validator import PresetError, PresetValidator

logger = logging.getLogger(__name__)


class PresetLoader:
    """Load preset JSON files from a directory."""

    def __init__(
        self,
        presets_dir: str | None = None,
        validator: PresetValidator | None = None,
    ) -> None:
        if presets_dir is not None:
            self.presets_dir = Path(presets_dir)
        else:
            self.presets_dir = Path(get_settings().presets_dir)
        self.validator = validator

    def load(self, preset_id: str) -> dict:
        """Load a single preset by ID.

        Args:
            preset_id: The identifier for the preset (filename stem).

        Returns:
            The preset as a dictionary.

        Raises:
            PresetError: If the preset file does not exist, is malformed, or
                fails validation.
        """
        path = self.presets_dir / f"{preset_id}.json"
        if not path.exists():
            raise PresetError(f"Preset not found: {preset_id}")

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise PresetError(f"Malformed JSON in preset '{preset_id}': {exc}") from exc
        except (PermissionError, OSError) as exc:
            raise PresetError(f"Cannot read preset '{preset_id}': {exc}") from exc

        if self.validator is not None:
            self.validator.validate(data)

        return data

    def list_presets(self) -> list[dict]:
        """List all available presets with injected IDs.

        Files that are malformed, unreadable, or fail validation are
        logged and skipped.

        Returns:
            A list of preset dictionaries, each with an "id" key derived
            from the filename stem.
        """
        results: list[dict] = []
        for path in sorted(self.presets_dir.glob("*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping malformed preset file '%s': %s", path.name, exc)
                continue
            except (PermissionError, OSError) as exc:
                logger.warning("Skipping unreadable preset file '%s': %s", path.name, exc)
                continue

            if self.validator is not None:
                try:
                    self.validator.validate(data)
                except Exception as exc:
                    logger.warning(
                        "Skipping invalid preset file '%s': %s", path.name, exc
                    )
                    continue

            data["id"] = path.stem
            results.append(data)
        return results

    def load_all(self) -> dict[str, dict]:
        """Load all presets into a mapping keyed by preset ID.

        Returns:
            A dictionary mapping preset ID to preset dictionary.
        """
        return {p["id"]: p for p in self.list_presets()}
