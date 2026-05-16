---
name: test-driven-development
description: Use when implementing any feature or bugfix, before writing implementation code
---

# Test-Driven Development (TDD)

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

**Violating the letter of the rules is violating the spirit of the rules.**

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete

## Red-Green-Refactor

### RED - Write Failing Test
- One behavior, clear name, real code (no mocks unless unavoidable)

### Verify RED - Watch It Fail (MANDATORY)
- Test fails (not errors)
- Failure message is expected
- Fails because feature missing (not typos)

### GREEN - Minimal Code
- Simplest code to pass the test
- Don't add features, refactor other code, or "improve" beyond the test

### Verify GREEN - Watch It Pass (MANDATORY)
- Test passes, other tests still pass, output pristine

### REFACTOR - Clean Up
- After green only: remove duplication, improve names, extract helpers
- Keep tests green. Don't add behavior.

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Tests after achieve same goals" | Tests-after = "what does this do?" Tests-first = "what should this do?" |
| "Already manually tested" | Ad-hoc ≠ systematic. No record, can't re-run. |
| "Deleting X hours is wasteful" | Sunk cost fallacy. Keeping unverified code is technical debt. |
| "TDD is dogmatic, I'm being pragmatic" | TDD IS pragmatic — finds bugs before commit. |

## Red Flags — STOP and Start Over

- Code before test
- Test passes immediately
- Can't explain why test failed
- Rationalizing "just this once"
- "Keep as reference" or "adapt existing code"

**All of these mean: Delete code. Start over with TDD.**

## Verification Checklist

- [ ] Every new function/method has a test
- [ ] Watched each test fail before implementing
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass
- [ ] Tests use real code (mocks only if unavoidable)

## Testing Anti-Patterns

See `testing-anti-patterns.md` in this directory for common pitfalls.
