# Persuasion Principles for Skill Design

## Overview

LLMs respond to the same persuasion principles as humans. Understanding this helps design more effective skills.

**Research:** Meincke et al. (2025) tested 7 principles with N=28,000 AI conversations. Persuasion more than doubled compliance (33% → 72%).

## The Seven Principles

### 1. Authority
- Imperative language: "YOU MUST", "Never", "Always"
- Non-negotiable framing: "No exceptions"
- Use for: Discipline-enforcing skills, safety-critical practices

### 2. Commitment
- Require announcements: "Announce skill usage"
- Force explicit choices
- Use tracking: TodoWrite for checklists

### 3. Scarcity
- Time-bound requirements: "Before proceeding"
- Sequential dependencies: "Immediately after X"

### 4. Social Proof
- Universal patterns: "Every time", "Always"
- Failure modes: "X without Y = failure"

### 5. Unity
- Collaborative language: "our codebase", "we're colleagues"
- Shared goals: "we both want quality"

### 6. Reciprocity — Use sparingly, rarely needed
### 7. Liking — DON'T USE for compliance; creates sycophancy

## Principle Combinations by Skill Type

| Skill Type | Use | Avoid |
|------------|-----|-------|
| Discipline-enforcing | Authority + Commitment + Social Proof | Liking, Reciprocity |
| Guidance/technique | Moderate Authority + Unity | Heavy authority |
| Collaborative | Unity + Commitment | Authority, Liking |
| Reference | Clarity only | All persuasion |

## Why This Works

- **Bright-line rules** reduce rationalization: "YOU MUST" removes decision fatigue
- **Implementation intentions** create automatic behavior: "When X, do Y"
- **LLMs are parahuman:** trained on human text containing these patterns

## Ethical Use

**Legitimate:** Ensuring critical practices are followed, preventing predictable failures
**Illegitimate:** Manipulating for personal gain, creating false urgency

**The test:** Would this technique serve the user's genuine interests if they fully understood it?
