---
name: writing-skills
description: Use when creating new skills, editing existing skills, or verifying skills work before deployment
---

# Writing Skills

**Writing skills IS Test-Driven Development applied to process documentation.**

You write test cases (pressure scenarios), watch them fail (baseline behavior), write the skill (documentation), watch tests pass (agents comply), and refactor (close loopholes).

**REQUIRED BACKGROUND:** You MUST understand superpowers:test-driven-development before using this skill.

## What is a Skill?

A **skill** is a reference guide for proven techniques, patterns, or tools.

**Skills are:** Reusable techniques, patterns, tools, reference guides
**Skills are NOT:** Narratives about how you solved a problem once

## SKILL.md Structure

```markdown
---
name: Skill-Name-With-Hyphens
description: Use when [specific triggering conditions and symptoms]
---

# Skill Name

## Overview
What is this? Core principle in 1-2 sentences.

## When to Use
Symptoms and use cases. When NOT to use.

## Core Pattern
Before/after code comparison.

## Quick Reference
Table or bullets for scanning.

## Common Mistakes
What goes wrong + fixes.
```

## Claude Search Optimization (CSO)

### Description Field
- Start with "Use when..." to focus on triggering conditions
- **NEVER summarize the skill's process or workflow** in the description
- Write in third person
- Keep under 500 characters if possible

**Why no workflow in description:** Descriptions that summarize workflow create a shortcut agents will take instead of reading the full skill.

### Keyword Coverage
- Error messages, symptoms, synonyms, tools
- Use words agents would search for

### Token Efficiency
- Getting-started skills: <150 words
- Frequently-loaded skills: <200 words
- Other skills: <500 words

## The Iron Law (Same as TDD)

```
NO SKILL WITHOUT A FAILING TEST FIRST
```

Write skill before testing? Delete it. Start over.

## Testing Skill Types

| Skill Type | Test With | Success Criteria |
|------------|-----------|------------------|
| Discipline-enforcing | Pressure scenarios (3+ combined) | Agent follows rule under max pressure |
| Technique | Application scenarios | Agent applies technique correctly |
| Pattern | Recognition + counter-examples | Agent identifies when/how to apply |
| Reference | Retrieval scenarios | Agent finds and applies info correctly |

## Bulletproofing Against Rationalization

1. **Close Every Loophole Explicitly** — Don't just state the rule, forbid specific workarounds
2. **Address "Spirit vs Letter"** — Add: "Violating the letter of the rules is violating the spirit of the rules"
3. **Build Rationalization Table** — Every excuse agents make goes in the table
4. **Create Red Flags List** — Easy self-check when rationalizing

## Supporting References

- `anthropic-best-practices.md` — Official skill authoring best practices
- `persuasion-principles.md` — Psychology of effective skill design
- `testing-skills-with-subagents.md` — Complete testing methodology
