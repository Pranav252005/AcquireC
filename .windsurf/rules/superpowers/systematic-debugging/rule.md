---
name: systematic-debugging
description: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
---

# Systematic Debugging

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to Use

Use for ANY technical issue: test failures, bugs, unexpected behavior, performance problems, build failures, integration issues.

**Use ESPECIALLY when:** under time pressure, "just one quick fix" seems obvious, previous fix didn't work, you don't fully understand the issue.

## The Four Phases

### Phase 1: Root Cause Investigation

1. **Read Error Messages Carefully** — Don't skip past errors. Read stack traces completely.
2. **Reproduce Consistently** — Can you trigger it reliably? What are the exact steps?
3. **Check Recent Changes** — Git diff, recent commits, new dependencies, config changes
4. **Gather Evidence in Multi-Component Systems** — Add diagnostic instrumentation at each component boundary
5. **Trace Data Flow** — Where does bad value originate? See `root-cause-tracing.md` in this directory

### Phase 2: Pattern Analysis

1. **Find Working Examples** — Locate similar working code
2. **Compare Against References** — Read reference implementation COMPLETELY
3. **Identify Differences** — List every difference, however small
4. **Understand Dependencies** — What settings, config, environment?

### Phase 3: Hypothesis and Testing

1. **Form Single Hypothesis** — "I think X is the root cause because Y"
2. **Test Minimally** — Smallest possible change, one variable at a time
3. **Verify Before Continuing** — Did it work? Yes → Phase 4. No → NEW hypothesis
4. **When You Don't Know** — Say "I don't understand X". Don't pretend.

### Phase 4: Implementation

1. **Create Failing Test Case** — Simplest possible reproduction
2. **Implement Single Fix** — ONE change at a time, no "while I'm here"
3. **Verify Fix** — Test passes? No other tests broken?
4. **If Fix Doesn't Work** — Count fixes tried. If ≥ 3: STOP and question architecture
5. **If 3+ Fixes Failed** — Question fundamentals. Discuss with your human partner.

## Red Flags — STOP and Follow Process

- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "It's probably X, let me fix that"
- "One more fix attempt" (when already tried 2+)
- Each fix reveals new problem in different place

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. |
| "Emergency, no time for process" | Systematic debugging is FASTER than thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |

## Supporting Techniques

- **`root-cause-tracing.md`** — Trace bugs backward through call stack
- **`defense-in-depth.md`** — Add validation at multiple layers after finding root cause
- **`condition-based-waiting.md`** — Replace arbitrary timeouts with condition polling

**Related skills:**
- **superpowers:test-driven-development** — For creating failing test case
- **superpowers:verification-before-completion** — Verify fix worked before claiming success
