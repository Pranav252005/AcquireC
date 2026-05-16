"""Vision executor: translates structured VLM actions into Playwright commands.

This is the act layer of the perceive-plan-act loop.
"""

from __future__ import annotations

from typing import Any

from src.vision_engine import VisionAction, VisionEngineError


class VisionExecutor:
    """Execute a sequence of VisionActions against a Playwright page."""

    def __init__(self, page, elements: list[dict[str, Any]]) -> None:
        self.page = page
        self.elements = elements
        self._selector_cache: dict[int, str] = {}

    def _resolve_selector(self, target_id: int | None) -> str | None:
        """Map a numeric target_id back to a Playwright selector."""
        if target_id is None:
            return None
        if target_id in self._selector_cache:
            return self._selector_cache[target_id]

        for el in self.elements:
            if el["index"] == target_id:
                sel = el.get("selector", "")
                if sel:
                    self._selector_cache[target_id] = sel
                    return sel

        # Fallback: try to find by approximate coordinates
        return None

    def execute(self, action: VisionAction) -> None:
        """Run a single action on the page."""
        a = action.action

        if a == "done":
            return

        if a == "wait":
            ms = int(action.value or 2000)
            self.page.wait_for_timeout(ms)
            return

        if a == "press":
            key = action.value or "Enter"
            self.page.keyboard.press(key)
            return

        if a == "scroll":
            delta = int(action.value or 500)
            self.page.mouse.wheel(0, delta)
            return

        # Actions that need a target element
        selector = self._resolve_selector(action.target_id)
        if selector is None and a in ("click", "fill"):
            raise VisionEngineError(
                f"Cannot {a}: target_id {action.target_id} not found in page map"
            )

        if a == "click":
            self.page.locator(selector).first.click(timeout=10000)
            return

        if a == "fill":
            if action.value is None:
                raise VisionEngineError("fill action requires a value")
            self.page.locator(selector).first.fill(action.value, timeout=10000)
            return

        raise VisionEngineError(f"Unknown action: {action.action}")

    def run_sequence(self, actions: list[VisionAction]) -> None:
        """Execute a list of actions sequentially."""
        for act in actions:
            self.execute(act)
