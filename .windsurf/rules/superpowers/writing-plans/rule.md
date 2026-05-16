---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch, code, testing, how to test it. DRY. YAGNI. TDD. Frequent commits.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Save plans to:** `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`

## Scope Check

If the spec covers multiple independent subsystems, break into separate plans — one per subsystem.

## File Structure

Before defining tasks, map out which files will be created or modified. Design units with clear boundaries. Prefer smaller, focused files over large ones. Files that change together should live together.

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

Every plan MUST start with this header:

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** [One sentence]
**Architecture:** [2-3 sentences]
**Tech Stack:** [Key technologies]

---
```

## Task Structure

```markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**
```

## No Placeholders

Every step must contain actual content. Never write: "TBD", "TODO", "implement later", "Add appropriate error handling" (without actual code), "Write tests for the above" (without actual test code).

## Self-Review

After writing the complete plan:
1. **Spec coverage:** Can you point to a task that implements each requirement?
2. **Placeholder scan:** Search for red flags — fix them
3. **Type consistency:** Do method signatures match across tasks?

## Execution Handoff

Offer execution choice:
1. **Subagent-Driven (recommended)** — dispatch fresh subagent per task, review between tasks
2. **Inline Execution** — execute tasks using executing-plans with checkpoints
