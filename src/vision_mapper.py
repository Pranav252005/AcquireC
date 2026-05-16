"""Vision mapper for text-only LLMs using Playwright accessibility trees.

Extracts a structured text representation of a web page so a text-only model
can reason about layout and choose elements to click / fill.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from playwright.sync_api import Page

from src.config import get_settings


@dataclass
class ElementNode:
    """Lightweight representation of an interactive page element."""

    eid: int
    role: str
    name: str
    text: str = ""
    placeholder: str = ""
    selector: str = ""
    bbox: dict[str, float] = field(default_factory=dict)


def _clean_text(text: str | None) -> str:
    """Normalize whitespace and truncate long text."""
    if not text:
        return ""
    return " ".join(text.split())[:200]


def build_page_map(page: Page) -> list[ElementNode]:
    """Return a list of interactive ElementNodes on the current page.

    Uses a JavaScript DOM walker (no screenshots needed).
    """
    INTERESTING_ROLES = {
        "textbox", "searchbox", "combobox", "button", "link",
        "menuitem", "menuitemcheckbox", "menuitemradio", "option",
        "checkbox", "radio", "tab", "treeitem", "listitem", "heading",
    }

    js = """
    () => {
        const interesting = new Set([
            "textbox", "searchbox", "combobox", "button", "link",
            "menuitem", "menuitemcheckbox", "menuitemradio", "option",
            "checkbox", "radio", "tab", "treeitem", "listitem", "heading"
        ]);
        const results = [];
        const elements = document.querySelectorAll(
            'input, button, a, select, textarea, [role], [contenteditable="true"]'
        );
        for (const el of elements) {
            const role = (el.getAttribute("role") || "").toLowerCase();
            const tag = el.tagName.toLowerCase();
            let inferredRole = role;
            if (!inferredRole) {
                if (tag === "input") {
                    const type = (el.getAttribute("type") || "").toLowerCase();
                    inferredRole = type === "search" ? "searchbox" : "textbox";
                } else if (tag === "button") {
                    inferredRole = "button";
                } else if (tag === "a") {
                    inferredRole = "link";
                } else if (tag === "select") {
                    inferredRole = "combobox";
                } else if (tag === "textarea") {
                    inferredRole = "textbox";
                } else if (el.isContentEditable) {
                    inferredRole = "textbox";
                }
            }
            if (!interesting.has(inferredRole)) continue;
            const eid = results.length + 1;
            el.setAttribute("__eid__", String(eid));
            const name = (
                el.getAttribute("aria-label") ||
                el.getAttribute("title") ||
                el.placeholder ||
                el.textContent ||
                ""
            ).trim();
            const value = (el.value || "").trim();
            const placeholder = (el.placeholder || "").trim();
            results.push({
                role: inferredRole,
                name: name.slice(0, 200),
                value: value.slice(0, 200),
                placeholder: placeholder.slice(0, 200),
            });
        }
        return results;
    }
    """

    snapshot: list[dict[str, Any]] = page.evaluate(js)
    nodes: list[ElementNode] = []
    for idx, item in enumerate(snapshot, start=1):
        nodes.append(
            ElementNode(
                eid=idx,
                role=item.get("role", ""),
                name=_clean_text(item.get("name", "")),
                text=_clean_text(item.get("value", "")),
                placeholder=_clean_text(item.get("placeholder", "")),
                selector=f"[__eid__='{idx}']",
            )
        )
    return nodes


def render_page_map(nodes: list[ElementNode]) -> str:
    """Render the page map as human-readable text for an LLM."""
    lines: list[str] = [
        "--- PAGE MAP (interactive elements) ---",
        "",
    ]
    for n in nodes:
        line = f"[{n.eid}] {n.role}: \"{n.name}\""
        if n.text:
            line += f' value="{n.text}"'
        if n.placeholder:
            line += f' placeholder="{n.placeholder}"'
        lines.append(line)
    lines.append("")
    lines.append("--- END PAGE MAP ---")
    return "\n".join(lines)


def find_element_by_role_and_text(
    page: Page,
    role: str,
    text_substring: str = "",
    placeholder_substring: str = "",
) -> str | None:
    """Return a robust Playwright selector for the first matching element.

    Falls back through accessibility attributes, then generic CSS.
    """
    text = text_substring.strip().lower()
    placeholder = placeholder_substring.strip().lower()

    # 1. aria-label / name contains
    if text:
        sel = f'[role="{role}" i][aria-label*="{text_substring}" i]'
        if page.locator(sel).count() > 0:
            return sel
        sel = f'[role="{role}" i][name*="{text_substring}" i]'
        if page.locator(sel).count() > 0:
            return sel

    # 2. placeholder contains
    if placeholder:
        sel = f'input[role="{role}" i][placeholder*="{placeholder_substring}" i]'
        if page.locator(sel).count() > 0:
            return sel

    # 3. text body contains
    if text:
        sel = f'[role="{role}" i]:has-text("{text_substring}")'
        try:
            if page.locator(sel).count() > 0:
                return sel
        except Exception:
            pass

    # 4. Generic role + nth=0
    sel = f'[role="{role}" i]'
    if page.locator(sel).count() > 0:
        return sel

    # 5. Native tag fallbacks for elements without explicit role attributes
    tag_fallbacks = {
        "textbox": ['input[type="text"]', 'input:not([type])', 'textarea', '[contenteditable="true"]'],
        "searchbox": ['input[type="search"]', 'input[type="text"]', '[role="combobox"]', '[contenteditable="true"]'],
        "button": ['button', '[type="submit"]', '[type="button"]'],
        "link": ['a[href]'],
        "combobox": ['select', '[role="combobox"]'],
    }
    for fallback_sel in tag_fallbacks.get(role, []):
        if page.locator(fallback_sel).count() > 0:
            return fallback_sel

    return None


def _try_vision_fallback(page: Page, task: str) -> bool:
    """Attempt vision-agent recovery before giving up."""
    settings = get_settings()
    if not getattr(settings, "use_vision", False):
        return False
    try:
        from src.vision_agent import VisionAgent
        agent = VisionAgent(page, max_steps=3, retries_per_step=1)
        return agent.run_task(task)
    except Exception as exc:
        logging.warning("Vision fallback failed: %s", exc)
        return False


def safe_fill(page: Page, role: str, value: str, label_hint: str = "", placeholder_hint: str = "") -> None:
    """Fill an input field discovered via accessibility tree.

    Falls back to the vision agent if the element cannot be located.
    """
    selector = find_element_by_role_and_text(
        page, role, text_substring=label_hint, placeholder_substring=placeholder_hint
    )
    if not selector:
        task = f"Find and fill the {role} field"
        if label_hint:
            task += f' labelled "{label_hint}"'
        if placeholder_hint:
            task += f' with placeholder "{placeholder_hint}"'
        task += f' with the text "{value}"'
        if _try_vision_fallback(page, task):
            return
        nodes = build_page_map(page)
        map_text = render_page_map(nodes)
        raise PageMapError(
            f"Could not find {role} element (hint={label_hint!r}).\n\n{map_text}"
        )
    page.locator(selector).first.fill(value)


def safe_click(page: Page, role: str, label_hint: str = "") -> None:
    """Click a button/link discovered via accessibility tree.

    Falls back to the vision agent if the element cannot be located.
    """
    selector = find_element_by_role_and_text(page, role, text_substring=label_hint)
    if not selector:
        task = f"Find and click the {role} element"
        if label_hint:
            task += f' labelled "{label_hint}"'
        if _try_vision_fallback(page, task):
            return
        nodes = build_page_map(page)
        map_text = render_page_map(nodes)
        raise PageMapError(
            f"Could not find {role} element to click (hint={label_hint!r}).\n\n{map_text}"
        )
    page.locator(selector).first.click()


class PageMapError(Exception):
    """Raised when vision mapper cannot locate an element."""
