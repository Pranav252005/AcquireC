---
name: using-git-worktrees
description: Use when starting feature work that needs isolation from current workspace or before executing implementation plans - creates isolated git worktrees with smart directory selection and safety verification
---

# Using Git Worktrees

Git worktrees create isolated workspaces sharing the same repository, allowing work on multiple branches simultaneously.

**Core principle:** Systematic directory selection + safety verification = reliable isolation.

**Announce at start:** "I'm using the using-git-worktrees skill to set up an isolated workspace."

## Directory Selection Process

1. Check existing directories: `.worktrees` (preferred) or `worktrees`
2. Check project config for preferences
3. If neither: ask user — `.worktrees/` (hidden) or `~/.config/superpowers/worktrees/<project>/`

## Safety Verification

**MUST verify directory is ignored before creating worktree:**
```bash
git check-ignore -q .worktrees 2>/dev/null
```

If NOT ignored: Add to .gitignore, commit, then proceed.

## Creation Steps

1. **Detect project name:** `project=$(basename "$(git rev-parse --show-toplevel)")`
2. **Create worktree:** `git worktree add "$path" -b "$BRANCH_NAME"`
3. **Run project setup:** Auto-detect (npm install / cargo build / pip install / go mod download)
4. **Verify clean baseline:** Run tests to ensure worktree starts clean
5. **Report location:** "Worktree ready at <full-path>. Tests passing."

## Red Flags — Never

- Create worktree without verifying it's ignored (project-local)
- Skip baseline test verification
- Proceed with failing tests without asking
- Assume directory location when ambiguous

## Integration

**Called by:**
- brainstorming (after design approved)
- subagent-driven-development (before executing tasks)
- executing-plans (before executing tasks)

**Pairs with:**
- finishing-a-development-branch — cleans up worktree after work complete
