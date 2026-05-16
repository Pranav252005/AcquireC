---
name: superpowers-index
description: Auto-loading index for the Superpowers skill system. ALWAYS check this before any coding task. Routes to the correct skill based on what you're doing — brainstorming, planning, debugging, TDD, code review, or branch management.
---

# Superpowers — Skill Index & Auto-Router

This is the master index for the **Superpowers** development workflow skills, adapted from [obra/superpowers](https://github.com/obra/superpowers) for Windsurf.

## How This Works

**Before ANY coding task, check if a superpowers skill applies.** If there's even a 1% chance a skill might be relevant, read it. Skills are mandatory workflows, not suggestions.

## Skill Registry

Read the rule file in `.windsurf/rules/superpowers/<skill-name>/` when the trigger matches:

| Skill | Trigger — Use When... | Rule File |
|-------|----------------------|-----------|
| **using-superpowers** | Starting ANY conversation — establishes how to find and use skills | `superpowers/using-superpowers/rule.md` |
| **brainstorming** | Before any creative work — creating features, building components, adding functionality, modifying behavior | `superpowers/brainstorming/rule.md` |
| **writing-plans** | You have a spec or requirements for a multi-step task, before touching code | `superpowers/writing-plans/rule.md` |
| **executing-plans** | You have a written implementation plan to execute with review checkpoints | `superpowers/executing-plans/rule.md` |
| **subagent-driven-development** | Executing implementation plans with independent tasks in the current session | `superpowers/subagent-driven-development/rule.md` |
| **dispatching-parallel-agents** | Facing 2+ independent tasks that can be worked on without shared state | `superpowers/dispatching-parallel-agents/rule.md` |
| **test-driven-development** | Implementing any feature or bugfix, before writing implementation code | `superpowers/test-driven-development/rule.md` |
| **systematic-debugging** | Encountering any bug, test failure, or unexpected behavior, before proposing fixes | `superpowers/systematic-debugging/rule.md` |
| **verification-before-completion** | About to claim work is complete, fixed, or passing — requires running verification commands first | `superpowers/verification-before-completion/rule.md` |
| **requesting-code-review** | Completing tasks, implementing major features, or before merging | `superpowers/requesting-code-review/rule.md` |
| **receiving-code-review** | Receiving code review feedback, before implementing suggestions | `superpowers/receiving-code-review/rule.md` |
| **using-git-worktrees** | Starting feature work that needs isolation or before executing implementation plans | `superpowers/using-git-worktrees/rule.md` |
| **finishing-a-development-branch** | Implementation is complete, all tests pass, need to decide how to integrate | `superpowers/finishing-a-development-branch/rule.md` |
| **writing-skills** | Creating new skills, editing existing skills, or verifying skills work | `superpowers/writing-skills/rule.md` |

## The Core Workflow (Automatic Sequence)

1. **brainstorming** → Refines ideas into designs, saves spec doc
2. **using-git-worktrees** → Creates isolated workspace on new branch
3. **writing-plans** → Breaks spec into bite-sized TDD tasks
4. **subagent-driven-development** OR **executing-plans** → Implements plan
5. **test-driven-development** → Enforces RED-GREEN-REFACTOR during implementation
6. **requesting-code-review** → Reviews against plan between tasks
7. **finishing-a-development-branch** → Verifies tests, presents merge/PR options

## Skill Priority

When multiple skills could apply:
1. **Process skills first** (brainstorming, debugging) — determine HOW to approach the task
2. **Implementation skills second** (TDD, code review) — guide execution

## Quick Decision Flow

```
"Build X"         → brainstorming → writing-plans → subagent-driven-development
"Fix this bug"    → systematic-debugging → TDD → verification-before-completion
"Review my code"  → requesting-code-review
"Got review feedback" → receiving-code-review
"Done with feature"   → finishing-a-development-branch
"Multiple independent failures" → dispatching-parallel-agents
```

## Red Flags — You're Skipping Skills

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "The skill is overkill" | Simple things become complex. Use it. |
