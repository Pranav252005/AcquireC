---
name: finishing-a-development-branch
description: Use when implementation is complete, all tests pass, and you need to decide how to integrate the work - guides completion of development work by presenting structured options for merge, PR, or cleanup
---

# Finishing a Development Branch

Guide completion of development work by presenting clear options and handling chosen workflow.

**Core principle:** Verify tests → Present options → Execute choice → Clean up.

**Announce at start:** "I'm using the finishing-a-development-branch skill to complete this work."

## The Process

### Step 1: Verify Tests

Run project's test suite. If tests fail: STOP. Don't proceed to Step 2.

### Step 2: Determine Base Branch

```bash
git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null
```

### Step 3: Present Options

Present exactly these 4 options:

```
1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work
```

### Step 4: Execute Choice

**Option 1: Merge Locally** — checkout base, pull, merge, verify tests, delete branch, cleanup worktree
**Option 2: Push and Create PR** — push branch, create PR via `gh pr create`, cleanup worktree
**Option 3: Keep As-Is** — Report branch name and worktree path. Don't cleanup worktree.
**Option 4: Discard** — Confirm first with typed "discard". Then delete branch and cleanup worktree.

### Step 5: Cleanup Worktree

For Options 1, 2, 4: Remove worktree if in one. For Option 3: Keep worktree.

## Red Flags — Never

- Proceed with failing tests
- Merge without verifying tests on result
- Delete work without confirmation
- Force-push without explicit request

## Integration

**Called by:**
- subagent-driven-development (after all tasks)
- executing-plans (after all batches)

**Pairs with:**
- using-git-worktrees — cleans up worktree created by that skill
