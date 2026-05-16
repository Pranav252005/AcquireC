"""Vision engine: screenshots, annotation, VLM inference, action parsing.

Provides the perceive layer for the vision-guided browser automation system.
"""

from __future__ import annotations

import io
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from src.config import get_settings
from src.vision_mapper import ElementNode, build_page_map


@dataclass
class VisionAction:
    """Structured action returned by the VLM."""

    thought: str
    action: str  # click, fill, press, wait, scroll, done
    target_id: int | None = None
    value: str | None = None


def capture_screenshot(page, path: Path | None = None) -> Path:
    """Save a full-page screenshot and return the file path."""
    if path is None:
        path = Path("screenshots") / f"vision_{int(time.time())}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path), full_page=True)
    return path


def _get_interactive_elements(page) -> list[dict[str, Any]]:
    """Query the page for interactive elements and return their metadata + bbox."""
    selectors = [
        "button",
        "a[href]",
        "input",
        "textarea",
        "select",
        '[role="button"]',
        '[role="link"]',
        '[role="textbox"]',
        '[role="searchbox"]',
        '[role="combobox"]',
        '[role="checkbox"]',
        '[role="radio"]',
        '[role="tab"]',
        '[contenteditable="true"]',
    ]
    elements: list[dict[str, Any]] = []
    seen = set()

    for sel in selectors:
        handles = page.locator(sel).all()
        for nth, handle in enumerate(handles):
            try:
                box = handle.bounding_box()
                if not box:
                    continue
                key = (round(box["x"], 1), round(box["y"], 1), round(box["width"], 1), round(box["height"], 1))
                if key in seen:
                    continue
                seen.add(key)
                text = handle.text_content(timeout=1000) or ""
                tag = handle.evaluate("el => el.tagName.toLowerCase()")
                role = handle.get_attribute("role") or ""
                placeholder = handle.get_attribute("placeholder") or ""
                elements.append({
                    "tag": tag,
                    "role": role,
                    "text": text.strip()[:100],
                    "placeholder": placeholder[:100],
                    "x": box["x"],
                    "y": box["y"],
                    "width": box["width"],
                    "height": box["height"],
                    "selector": f"({sel}) >> nth={nth}",
                    "index": len(elements),
                })
            except Exception:
                continue

    return elements


def annotate_screenshot(screenshot_path: Path, elements: list[dict[str, Any]], output_path: Path | None = None) -> Path:
    """Draw numbered bounding boxes over interactive elements on a screenshot.

    Returns the path to the annotated image.
    """
    img = Image.open(screenshot_path)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    except Exception:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 14)
        except Exception:
            font = ImageFont.load_default()

    for el in elements:
        x, y, w, h = el["x"], el["y"], el["width"], el["height"]
        if w <= 0 or h <= 0:
            continue
        draw.rectangle([x, y, x + w, y + h], outline="red", width=2)
        label = str(el["index"])
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.rectangle([x, y - th - 4, x + tw + 4, y], fill="red")
        draw.text((x + 2, y - th - 2), label, fill="white", font=font)

    if output_path is None:
        output_path = screenshot_path.parent / f"{screenshot_path.stem}_annotated{screenshot_path.suffix}"
    img.save(output_path)
    return output_path


def build_vision_prompt(task: str, elements: list[dict[str, Any]]) -> str:
    """Build the text prompt for the VLM describing the current page and task."""
    lines: list[str] = [
        "You are a browser automation agent. You see a screenshot of a web page with numbered red boxes around interactive elements.",
        "",
        f"TASK: {task}",
        "",
        "Interactive elements on the page:",
    ]
    for el in elements:
        line = f"  [{el['index']}] {el['tag']}"
        if el["role"]:
            line += f' role="{el["role"]}"'
        if el["text"]:
            line += f' text="{el["text"]}"'
        if el["placeholder"]:
            line += f' placeholder="{el["placeholder"]}"'
        lines.append(line)
    lines.extend([
        "",
        "Return ONLY valid JSON in this exact format:",
        '  {"thought": "your reasoning", "action": "click|fill|press|wait|scroll|done", "target_id": number or null, "value": "text or null"}',
        "",
        "Rules:",
        "- Use target_id to refer to the numbered element.",
        "- 'fill' requires a target_id and value.",
        "- 'press' requires a value like 'Enter', 'Tab', etc.",
        "- 'wait' uses value for milliseconds (default 2000).",
        "- 'scroll' uses value for pixels to scroll down (positive) or up (negative).",
        "- 'done' means the task is complete.",
    ])
    return "\n".join(lines)


def parse_action(raw: str) -> VisionAction:
    """Parse VLM response text into a VisionAction.

    Handles JSON extraction from markdown code blocks or plain text.
    """
    text = raw.strip()
    # Try to extract JSON from markdown code block
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    data = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                data = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        # Attempt regex extraction of thought and action for any JSON-like fragment
        if data is None:
            thought_match = re.search(r'"thought"\s*:\s*"([^"]*)"', text)
            action_match = re.search(r'"action"\s*:\s*"([^"]*)"', text)
            if thought_match or action_match:
                data = {
                    "thought": thought_match.group(1) if thought_match else raw,
                    "action": action_match.group(1) if action_match else "done",
                }
            else:
                data = {"thought": raw, "action": "done"}

    return VisionAction(
        thought=data.get("thought", "No thought provided"),
        action=data.get("action", "done").lower().strip(),
        target_id=data.get("target_id"),
        value=data.get("value"),
    )


# Lazy-loaded VLM instances
_vlm_local: Any = None
_vlm_available: bool | None = None


def _load_local_vlm() -> Any:
    """Load local Qwen VLM via llama-cpp-python with mmproj (cached)."""
    global _vlm_local, _vlm_available
    if _vlm_available is not None:
        return _vlm_local if _vlm_available else None

    settings = get_settings()
    model_path = settings.vlm_model_path
    mmproj_path = settings.vlm_mmproj_path

    if not model_path.exists() or not mmproj_path.exists():
        _vlm_available = False
        return None

    try:
        from llama_cpp import Llama
        _vlm_local = Llama(
            model_path=str(model_path),
            clip_model_path=str(mmproj_path),
            n_ctx=4096,
            verbose=False,
        )
        _vlm_available = True
        return _vlm_local
    except Exception:
        _vlm_available = False
        return None


def _query_local_vlm(image_path: Path, prompt: str) -> str:
    """Run inference on a local VLM via llama-cpp-python.

    Returns the raw text response.
    """
    llm = _load_local_vlm()
    if llm is None:
        raise VisionEngineError("Local VLM not available")

    image_url = f"file://{image_path.resolve()}"

    try:
        response = llm.create_chat_completion(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            max_tokens=512,
            temperature=0.2,
        )
        return response["choices"][0]["message"]["content"]
    except Exception as exc:
        raise VisionEngineError(f"Local VLM inference failed: {exc}") from exc


def plan_action(page, task: str, max_steps: int = 1) -> list[VisionAction]:
    """Perceive the page, query the VLM, and return a list of planned actions.

    This orchestrates: screenshot -> element detection -> annotation -> VLM prompt -> parse.
    """
    settings = get_settings()
    if not settings.use_vision:
        raise VisionEngineError("Vision is disabled in settings")

    # 1. Capture screenshot
    screenshot_path = capture_screenshot(page)

    # 2. Detect interactive elements
    elements = _get_interactive_elements(page)

    # 3. Annotate screenshot
    annotated_path = annotate_screenshot(screenshot_path, elements)

    # 4. Build prompt
    prompt = build_vision_prompt(task, elements)

    # 5. Query local VLM (hard-fail if unavailable)
    raw_response = _query_local_vlm(annotated_path, prompt)

    # 6. Parse actions
    actions: list[VisionAction] = []
    for _ in range(max_steps):
        action = parse_action(raw_response)
        actions.append(action)
        if action.action == "done":
            break
        # If VLM returned multiple actions in one response, only the first parsed is used per call.
        # For multi-step, re-query (not implemented in single-shot; agent loop handles re-query).
        break

    return actions, elements


class VisionEngineError(Exception):
    """Raised when the vision engine cannot perceive or plan."""
