---
name: dispatching-parallel-agents
description: Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies
---

# Dispatching Parallel Agents

When you have multiple unrelated failures, investigating them sequentially wastes time. Each investigation is independent and can happen in parallel.

**Core principle:** Dispatch one agent per independent problem domain. Let them work concurrently.

## When to Use

**Use when:**
- 3+ test files failing with different root causes
- Multiple subsystems broken independently
- Each problem can be understood without context from others
- No shared state between investigations

**Don't use when:**
- Failures are related (fix one might fix others)
- Need to understand full system state
- Agents would interfere with each other

## The Pattern

1. **Identify Independent Domains** — Group failures by what's broken
2. **Create Focused Agent Tasks** — Each agent gets: specific scope, clear goal, constraints, expected output
3. **Dispatch in Parallel** — All agents run concurrently
4. **Review and Integrate** — Read summaries, verify no conflicts, run full test suite

## Agent Prompt Structure

Good agent prompts are:
1. **Focused** - One clear problem domain
2. **Self-contained** - All context needed
3. **Specific about output** - What should the agent return?

## Common Mistakes

- ❌ Too broad: "Fix all the tests" → ✅ Specific: "Fix agent-tool-abort.test.ts"
- ❌ No context: "Fix the race condition" → ✅ Context: Paste error messages and test names
- ❌ No constraints: Agent might refactor everything → ✅ Constraints: "Do NOT change production code"

## Verification

After agents return:
1. Review each summary
2. Check for conflicts (did agents edit same code?)
3. Run full suite
4. Spot check — agents can make systematic errors
