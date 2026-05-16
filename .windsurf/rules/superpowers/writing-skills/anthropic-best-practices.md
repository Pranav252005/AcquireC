# Skill Authoring Best Practices

> Learn how to write effective Skills that agents can discover and use successfully.

## Core Principles

### Concise is key
The context window is a public good. Only add context the agent doesn't already have.

**Default assumption:** The agent is already very smart. Challenge each piece of information:
- "Does the agent really need this explanation?"
- "Can I assume the agent knows this?"
- "Does this paragraph justify its token cost?"

### Set appropriate degrees of freedom

- **High freedom** (text-based instructions): Multiple approaches valid, decisions depend on context
- **Medium freedom** (pseudocode/parameters): Preferred pattern exists, some variation acceptable
- **Low freedom** (specific scripts): Operations fragile, consistency critical, specific sequence required

### Test with all models you plan to use
What works for powerful models might need more detail for faster ones.

## Writing Effective Descriptions

The `description` field enables skill discovery.

**Always write in third person.** The description is injected into the system prompt.

**Be specific and include key terms.** Include both what the Skill does and specific triggers/contexts for when to use it.

Good: "Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files."
Bad: "Helps with documents"

## Progressive Disclosure

- Keep SKILL.md body under 500 lines
- Split content into separate files when approaching this limit
- Keep references one level deep from SKILL.md
- For reference files > 100 lines, include a table of contents

## Workflows and Feedback Loops

Break complex operations into clear, sequential steps. Provide checklists.

Common pattern: Run validator → fix errors → repeat. This greatly improves output quality.

## Content Guidelines

- **Avoid time-sensitive information** — use "old patterns" sections instead
- **Use consistent terminology** — pick one term and use it throughout
- **Avoid offering too many options** — provide a default with escape hatch

## Anti-Patterns

- Avoid Windows-style paths (use forward slashes)
- Avoid offering too many options without a default
- Don't include information that will become outdated
- Don't use inconsistent terminology
