# Root Cause Tracing

## Overview

Bugs often manifest deep in the call stack. Your instinct is to fix where the error appears, but that's treating a symptom.

**Core principle:** Trace backward through the call chain until you find the original trigger, then fix at the source.

## The Tracing Process

1. **Observe the Symptom** — What error appeared?
2. **Find Immediate Cause** — What code directly causes this?
3. **Ask: What Called This?** — Trace up the call chain
4. **Keep Tracing Up** — What value was passed? Where did bad value come from?
5. **Find Original Trigger** — Where did the invalid data originate?

## Adding Stack Traces

When you can't trace manually, add instrumentation:

```typescript
async function gitInit(directory: string) {
  const stack = new Error().stack;
  console.error('DEBUG git init:', {
    directory,
    cwd: process.cwd(),
    stack,
  });
  await execFileAsync('git', ['init'], { cwd: directory });
}
```

**Critical:** Use `console.error()` in tests (not logger - may not show)

## Key Principle

**NEVER fix just where the error appears.** Trace back to find the original trigger.

After fixing at source, also add defense-in-depth validation at each layer data passes through.
