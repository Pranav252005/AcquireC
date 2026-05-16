"""Vision agent: perceive-plan-act loop for browser automation.

When the fast text-based vision_mapper fails, this agent takes over,
captures screenshots, queries a local VLM, and executes actions.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from src.config import get_settings
from src.vision_engine import VisionAction, VisionEngineError, annotate_screenshot, build_vision_prompt, capture_screenshot, parse_action, _get_interactive_elements
from src.vision_executor import VisionExecutor


class VisionAgent:
    """Headed or headless browser agent driven by a vision-language model."""

    def __init__(
        self,
        page,
        max_steps: int = 5,
        retries_per_step: int = 2,
        screenshot_dir: str = "screenshots",
    ) -> None:
        self.page = page
        self.max_steps = max_steps
        self.retries_per_step = retries_per_step
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.history: list[dict[str, Any]] = []

    def _save_state(self, step: int, label: str) -> Path:
        """Save a screenshot for debugging."""
        path = self.screenshot_dir / f"step_{step:02d}_{label}.png"
        self.page.screenshot(path=str(path), full_page=True)
        return path

    def run_task(self, task: str) -> bool:
        """Run the perceive-plan-act loop until the task is done or max steps reached.

        Returns True if the VLM emitted a 'done' action, False otherwise.
        """
        settings = get_settings()
        if not settings.use_vision:
            return False

        for step in range(1, self.max_steps + 1):
            self._save_state(step, "before")

            # PERCEIVE
            screenshot_path = capture_screenshot(self.page, self.screenshot_dir / f"step_{step:02d}_full.png")
            elements = _get_interactive_elements(self.page)
            annotated_path = annotate_screenshot(
                screenshot_path, elements,
                self.screenshot_dir / f"step_{step:02d}_annotated.png",
            )

            # Build prompt with history context
            history_lines: list[str] = []
            if self.history:
                history_lines.append("Previous actions taken:")
                for h in self.history[-5:]:
                    history_lines.append(f"  - [{h['step']}] {h['action']} -> {h['result']}")
                history_lines.append("")

            prompt = build_vision_prompt(task, elements)
            if history_lines:
                prompt = "\n".join(history_lines) + "\n" + prompt

            # PLAN
            from src.vision_engine import _query_local_vlm

            try:
                raw_response = _query_local_vlm(annotated_path, prompt)
            except Exception as exc:
                self.history.append({
                    "step": step,
                    "action": "plan",
                    "result": f"VLM failed: {exc}",
                })
                continue

            action = parse_action(raw_response)

            # ACT
            executor = VisionExecutor(self.page, elements)
            result = "ok"
            for attempt in range(self.retries_per_step):
                try:
                    executor.execute(action)
                    break
                except Exception as exc:
                    logging.warning("Vision action %s failed (attempt %d/%d): %s", action.action, attempt + 1, self.retries_per_step, exc)
                    result = f"error ({exc})"
                    if attempt < self.retries_per_step - 1:
                        time.sleep(1)
                    else:
                        break

            self.history.append({
                "step": step,
                "action": f"{action.action} target={action.target_id} value={action.value}",
                "thought": action.thought,
                "result": result,
            })

            self._save_state(step, "after")

            if action.action == "done":
                return True

            # Brief pause between steps so the page can react
            self.page.wait_for_timeout(1500)

        return False


class VisionFallbackMixin:
    """Mixin to add vision-agent fallback to any Playwright-based class."""

    def _vision_fallback(self, page, task: str) -> bool:
        """Invoke the vision agent as a recovery mechanism.

        Returns True if the agent reported success.
        """
        agent = VisionAgent(page)
        return agent.run_task(task)
