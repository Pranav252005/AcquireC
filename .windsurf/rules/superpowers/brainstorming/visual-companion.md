# Visual Companion Guide

Browser-based visual brainstorming companion for showing mockups, diagrams, and options.

## When to Use

Decide per-question, not per-session. **Would the user understand this better by seeing it than reading it?**

**Use the browser** when content IS visual: UI mockups, architecture diagrams, side-by-side comparisons, design polish, spatial relationships.

**Use the terminal** when content is text: requirements questions, conceptual choices, tradeoff lists, technical decisions, clarifying questions.

## How It Works

Write HTML content to a screen directory, the user sees it in their browser and can click to select options. Selections are recorded to a state directory.

## The Loop

1. Write HTML to a new file in screen_dir (never reuse filenames)
2. Tell user what to expect and end your turn
3. On next turn: read state_dir/events for user interactions
4. Iterate or advance based on feedback
5. When returning to terminal: push a waiting screen to clear stale content

## Writing Content Fragments

Write just the content — the server wraps it in a frame template automatically.

## CSS Classes Available

- `.options` with `.option[data-choice]` — A/B/C choices
- `.cards` with `.card[data-choice]` — Visual designs
- `.mockup` with `.mockup-header` and `.mockup-body` — Previews
- `.split` — Side-by-side
- `.pros-cons` — Pros/Cons layout
- Mock elements: `.mock-nav`, `.mock-sidebar`, `.mock-content`, `.mock-button`, `.mock-input`, `.placeholder`

## Design Tips

- Scale fidelity to the question — wireframes for layout, polish for polish questions
- 2-4 options max per screen
- Use real content when it matters
- Keep mockups simple — focus on layout and structure
