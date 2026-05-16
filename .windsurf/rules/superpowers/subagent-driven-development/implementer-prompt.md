# Implementer Subagent Prompt Template

```
Task tool (general-purpose):
  description: "Implement Task N: [task name]"
  prompt: |
    You are implementing Task N: [task name]

    ## Task Description
    [FULL TEXT of task from plan - paste it here, don't make subagent read file]

    ## Context
    [Scene-setting: where this fits, dependencies, architectural context]

    ## Before You Begin
    If you have questions about requirements, approach, dependencies, or anything unclear — Ask them now.

    ## Your Job
    1. Implement exactly what the task specifies
    2. Write tests (following TDD if task says to)
    3. Verify implementation works
    4. Commit your work
    5. Self-review (see below)
    6. Report back

    ## Code Organization
    - Follow the file structure defined in the plan
    - Each file should have one clear responsibility
    - If a file is growing beyond plan's intent, report as DONE_WITH_CONCERNS
    - In existing codebases, follow established patterns

    ## When You're in Over Your Head
    STOP and escalate when:
    - Task requires architectural decisions with multiple valid approaches
    - You need to understand code beyond what was provided
    - You feel uncertain about your approach
    Report: BLOCKED or NEEDS_CONTEXT with specifics.

    ## Self-Review
    Review your work: Completeness? Quality? Discipline (YAGNI)? Testing?
    Fix issues before reporting.

    ## Report Format
    - **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
    - What you implemented (or attempted)
    - Test results
    - Files changed
    - Self-review findings
    - Issues or concerns
```
