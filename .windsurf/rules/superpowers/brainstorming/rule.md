---
name: brainstorming
description: "You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation."
---

# Brainstorming Ideas Into Designs

Help turn ideas into fully formed designs and specs through natural collaborative dialogue.

<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY project regardless of perceived simplicity.
</HARD-GATE>

## Anti-Pattern: "This Is Too Simple To Need A Design"

Every project goes through this process. A todo list, a single-function utility, a config change — all of them. The design can be short, but you MUST present it and get approval.

## Checklist

1. **Explore project context** — check files, docs, recent commits
2. **Ask clarifying questions** — one at a time, understand purpose/constraints/success criteria
3. **Propose 2-3 approaches** — with trade-offs and your recommendation
4. **Present design** — in sections scaled to their complexity, get user approval after each section
5. **Write design doc** — save to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` and commit
6. **Spec self-review** — quick inline check for placeholders, contradictions, ambiguity, scope
7. **User reviews written spec** — ask user to review the spec file before proceeding
8. **Transition to implementation** — read the writing-plans skill to create implementation plan

## The Process

**Understanding the idea:**
- Check out the current project state first
- If the project is too large for a single spec, decompose into sub-projects
- Ask questions one at a time to refine the idea
- Prefer multiple choice questions when possible
- Focus on understanding: purpose, constraints, success criteria

**Exploring approaches:**
- Propose 2-3 different approaches with trade-offs
- Lead with your recommended option and explain why

**Presenting the design:**
- Scale each section to its complexity
- Ask after each section whether it looks right
- Cover: architecture, components, data flow, error handling, testing

**Design for isolation and clarity:**
- Break the system into smaller units with one clear purpose
- Each unit should answer: what does it do, how do you use it, what does it depend on?

**Working in existing codebases:**
- Explore the current structure before proposing changes
- Follow existing patterns
- Don't propose unrelated refactoring

## After the Design

- Write the validated design to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
- Commit the design document
- **Spec Self-Review:** Check for placeholders, contradictions, scope issues, ambiguity — fix inline
- **User Review Gate:** Ask user to review the written spec before proceeding
- Invoke the writing-plans skill to create implementation plan

## Key Principles

- **One question at a time** - Don't overwhelm
- **Multiple choice preferred** - Easier to answer
- **YAGNI ruthlessly** - Remove unnecessary features
- **Explore alternatives** - Always propose 2-3 approaches
- **Incremental validation** - Present design, get approval before moving on
