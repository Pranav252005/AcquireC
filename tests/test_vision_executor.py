"""Tests for vision_executor module."""

from unittest.mock import MagicMock

import pytest

from src.vision_engine import VisionAction, VisionEngineError
from src.vision_executor import VisionExecutor


class TestVisionExecutor:
    """Test suite for VisionExecutor action translation."""

    @pytest.fixture
    def page(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def elements(self) -> list[dict]:
        return [
            {"index": 0, "tag": "button", "role": "", "selector": 'button:has-text("Go")'},
            {"index": 1, "tag": "input", "role": "textbox", "selector": 'input[type="text"]'},
        ]

    @pytest.fixture
    def executor(self, page, elements) -> VisionExecutor:
        return VisionExecutor(page, elements)

    def test_done_action_no_op(self, executor, page) -> None:
        """done action should not interact with page."""
        act = VisionAction(thought="finished", action="done")
        executor.execute(act)
        page.locator.assert_not_called()

    def test_wait_action(self, executor, page) -> None:
        """wait action should call page.wait_for_timeout with default ms."""
        act = VisionAction(thought="wait", action="wait")
        executor.execute(act)
        page.wait_for_timeout.assert_called_once_with(2000)

    def test_wait_with_custom_ms(self, executor, page) -> None:
        """wait action should use provided value."""
        act = VisionAction(thought="wait", action="wait", value="500")
        executor.execute(act)
        page.wait_for_timeout.assert_called_once_with(500)

    def test_press_action(self, executor, page) -> None:
        """press action should call page.keyboard.press."""
        act = VisionAction(thought="press enter", action="press", value="Enter")
        executor.execute(act)
        page.keyboard.press.assert_called_once_with("Enter")

    def test_scroll_action(self, executor, page) -> None:
        """scroll action should call page.mouse.wheel."""
        act = VisionAction(thought="scroll", action="scroll", value="300")
        executor.execute(act)
        page.mouse.wheel.assert_called_once_with(0, 300)

    def test_click_action(self, executor, page) -> None:
        """click action should locate and click the stored element."""
        act = VisionAction(thought="click go", action="click", target_id=0)
        executor.execute(act)
        page.locator.assert_called_once_with('button:has-text("Go")')
        page.locator.return_value.first.click.assert_called_once_with(timeout=10000)

    def test_fill_action(self, executor, page) -> None:
        """fill action should locate and fill the stored element."""
        act = VisionAction(thought="type hello", action="fill", target_id=1, value="hello")
        executor.execute(act)
        page.locator.return_value.first.fill.assert_called_once_with("hello", timeout=10000)

    def test_fill_without_value_raises(self, executor) -> None:
        """fill action without value should raise VisionEngineError."""
        act = VisionAction(thought="bad fill", action="fill", target_id=1)
        with pytest.raises(VisionEngineError):
            executor.execute(act)

    def test_click_missing_target_raises(self, executor) -> None:
        """click action with unknown target_id should raise."""
        act = VisionAction(thought="bad click", action="click", target_id=99)
        with pytest.raises(VisionEngineError):
            executor.execute(act)

    def test_unknown_action_raises(self, executor) -> None:
        """Unknown action string should raise VisionEngineError."""
        act = VisionAction(thought="what", action="fly")
        with pytest.raises(VisionEngineError):
            executor.execute(act)

    def test_run_sequence(self, executor, page) -> None:
        """run_sequence should execute multiple actions in order."""
        actions = [
            VisionAction(thought="wait", action="wait", value="100"),
            VisionAction(thought="press", action="press", value="Tab"),
        ]
        executor.run_sequence(actions)
        page.wait_for_timeout.assert_called_with(100)
        page.keyboard.press.assert_called_with("Tab")
