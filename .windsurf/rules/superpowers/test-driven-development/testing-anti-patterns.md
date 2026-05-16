# Testing Anti-Patterns

**Load this reference when:** writing or changing tests, adding mocks, or tempted to add test-only methods to production code.

## The Iron Laws

```
1. NEVER test mock behavior
2. NEVER add test-only methods to production classes
3. NEVER mock without understanding dependencies
```

## Anti-Pattern 1: Testing Mock Behavior

❌ BAD: Testing that the mock exists
✅ GOOD: Test real component or don't mock it

**Gate:** BEFORE asserting on any mock element, ask: "Am I testing real component behavior or just mock existence?"

## Anti-Pattern 2: Test-Only Methods in Production

❌ BAD: Adding destroy() to Session class only for test cleanup
✅ GOOD: Test utilities handle test cleanup

**Gate:** BEFORE adding any method to production class, ask: "Is this only used by tests?" If yes → put it in test utilities.

## Anti-Pattern 3: Mocking Without Understanding

❌ BAD: Mock prevents config write that test depends on
✅ GOOD: Mock at correct level — preserve behavior test needs

**Gate:** BEFORE mocking any method, ask: "What side effects does the real method have? Does this test depend on any of those?"

## Anti-Pattern 4: Incomplete Mocks

❌ BAD: Partial mock — only fields you think you need
✅ GOOD: Mirror real API completeness — include ALL fields

**Gate:** Check: "What fields does the real API response contain?" Include all.

## Anti-Pattern 5: Integration Tests as Afterthought

❌ BAD: Implementation complete, no tests written
✅ GOOD: TDD cycle — write failing test, implement to pass, refactor, THEN claim complete

## Quick Reference

| Anti-Pattern | Fix |
|--------------|-----|
| Assert on mock elements | Test real component or unmock it |
| Test-only methods in production | Move to test utilities |
| Mock without understanding | Understand dependencies first, mock minimally |
| Incomplete mocks | Mirror real API completely |
| Tests as afterthought | TDD - tests first |
| Over-complex mocks | Consider integration tests |

## Red Flags

- Assertion checks for `*-mock` test IDs
- Methods only called in test files
- Mock setup is >50% of test
- Test fails when you remove mock
- Mocking "just to be safe"
