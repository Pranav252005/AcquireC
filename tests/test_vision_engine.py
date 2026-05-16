"""Tests for vision_engine module."""

from unittest.mock import MagicMock, patch

import pytest

from src.vision_engine import VisionAction, VisionEngineError, annotate_screenshot, build_vision_prompt, capture_screenshot, parse_action


class TestVisionAction:
    """Test the VisionAction dataclass."""

    def test_fields(self) -> None:
        """VisionAction should hold thought, action, target_id, value."""
        a = VisionAction(thought="click it", action="click", target_id=3, value=None)
        assert a.thought == "click it"
        assert a.action == "click"
        assert a.target_id == 3
        assert a.value is None


class TestParseAction:
    """Test parse_action JSON extraction."""

    def test_plain_json(self) -> None:
        """Parse simple JSON string."""
        raw = '{"thought": "go", "action": "click", "target_id": 1, "value": null}'
        a = parse_action(raw)
        assert a.action == "click"
        assert a.target_id == 1
        assert a.value is None

    def test_markdown_codeblock(self) -> None:
        """Parse JSON inside markdown code block."""
        raw = '```json\n{"thought":"x","action":"done"}\n```'
        a = parse_action(raw)
        assert a.action == "done"

    def test_plain_text_no_json(self) -> None:
        """Fallback to done when no JSON found."""
        a = parse_action("I am done with this task")
        assert a.action == "done"
        assert a.thought == "I am done with this task"

    def test_malformed_json(self) -> None:
        """Handle malformed JSON gracefully."""
        raw = '{"thought": "bad", "action": "click"'  # missing closing brace
        a = parse_action(raw)
        assert a.thought == "bad"
        assert a.action == "click"


class TestBuildVisionPrompt:
    """Test prompt construction."""

    def test_includes_task_and_elements(self) -> None:
        """Prompt should contain task and element list."""
        elements = [
            {"index": 0, "tag": "input", "role": "searchbox", "text": "", "placeholder": "Search"},
            {"index": 1, "tag": "button", "role": "", "text": "Go", "placeholder": ""},
        ]
        prompt = build_vision_prompt("Find search box", elements)
        assert "TASK: Find search box" in prompt
        assert "[0] input" in prompt
        assert 'role="searchbox"' in prompt
        assert "[1] button" in prompt
        assert "text=\"Go\"" in prompt

    def test_includes_rules(self) -> None:
        """Prompt should include action format rules."""
        prompt = build_vision_prompt("test", [])
        assert "click|fill|press|wait|scroll|done" in prompt


class TestCaptureScreenshot:
    """Test screenshot capture wrapper."""

    def test_calls_page_screenshot(self, tmp_path) -> None:
        """capture_screenshot should call page.screenshot with correct path."""
        page = MagicMock()
        path = tmp_path / "shot.png"
        capture_screenshot(page, path)
        page.screenshot.assert_called_once_with(path=str(path), full_page=True)

    def test_creates_parent_dir(self, tmp_path) -> None:
        """capture_screenshot should create parent directories."""
        page = MagicMock()
        path = tmp_path / "nested" / "shot.png"
        capture_screenshot(page, path)
        assert path.parent.exists()


class TestAnnotateScreenshot:
    """Test screenshot annotation with bounding boxes."""

    def test_creates_annotated_file(self, tmp_path) -> None:
        """annotate_screenshot should create a new image file."""
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="white")
        src = tmp_path / "src.png"
        img.save(src)

        elements = [
            {"index": 0, "x": 10, "y": 10, "width": 20, "height": 20, "tag": "button", "role": "", "text": "OK", "placeholder": ""},
        ]
        out = annotate_screenshot(src, elements, tmp_path / "out.png")
        assert out.exists()
        assert out.stat().st_size > 0

    def test_ignores_zero_size_elements(self, tmp_path) -> None:
        """Elements with zero width/height should be skipped."""
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="white")
        src = tmp_path / "src.png"
        img.save(src)

        elements = [
            {"index": 0, "x": 0, "y": 0, "width": 0, "height": 0, "tag": "div", "role": "", "text": "", "placeholder": ""},
        ]
        out = annotate_screenshot(src, elements, tmp_path / "out.png")
        assert out.exists()
