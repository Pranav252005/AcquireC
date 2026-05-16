---
name: subagent-driven-development
description: Use when executing implementation plans with independent tasks in the current session
---

# Subagent-Driven Development

Execute plan by dispatching fresh subagent per task, with two-stage review after each: spec compliance review first, then code quality review.

**Why subagents:** You delegate tasks to specialized agents with isolated context. They should never inherit your session's context or history — you construct exactly what they need.

**Core principle:** Fresh subagent per task + two-stage review (spec then quality) = high quality, fast iteration

## When to Use

- Have implementation plan? → Tasks mostly independent? → Stay in this session? → Use this skill
- For parallel sessions, use executing-plans instead

## The Process

1. **Read plan, extract all tasks with full text, note context, create todo list**
2. **Per task:**
   - Dispatch implementer subagent with full task text + context
   - Answer any questions the implementer has
   - After implementation: dispatch spec reviewer subagent
   - If spec issues: implementer fixes, re-review
   - After spec passes: dispatch code quality reviewer subagent
   - If quality issues: implementer fixes, re-review
   - Mark task complete
3. **After all tasks:** Dispatch final code reviewer for entire implementation
4. **Use superpowers:finishing-a-development-branch** to complete

## Model Selection

Use the least powerful model that can handle each role:
- **Mechanical tasks** (1-2 files, clear specs): fast, cheap model
- **Integration tasks** (multi-file, pattern matching): standard model
- **Architecture/review tasks**: most capable model

## Handling Implementer Status

- **DONE:** Proceed to spec review
- **DONE_WITH_CONCERNS:** Read concerns before proceeding
- **NEEDS_CONTEXT:** Provide missing context and re-dispatch
- **BLOCKED:** Assess blocker, provide more context or escalate

## Red Flags — Never

- Start implementation on main/master without explicit user consent
- Skip reviews (spec compliance OR code quality)
- Proceed with unfixed issues
- Dispatch multiple implementation subagents in parallel (conflicts)
- Make subagent read plan file (provide full text instead)
- Accept "close enough" on spec compliance
- Start code quality review before spec compliance is ✅

## Prompt Templates

See supporting files in this directory:
- `implementer-prompt.md` — dispatch implementer subagent
- `spec-reviewer-prompt.md` — dispatch spec compliance reviewer
- `code-quality-reviewer-prompt.md` — dispatch code quality reviewer
