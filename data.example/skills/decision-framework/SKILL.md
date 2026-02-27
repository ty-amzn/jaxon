---
name: decision-framework
description: Structured decision analysis with weighted criteria, pros/cons, and clear recommendations. Activates for comparison and tradeoff questions.
---
# Decision Framework

When the user asks for help deciding between options — "should I use X or Y?", "help me decide", "compare X vs Y", tradeoff questions — use this structured approach.

## 1. Clarify the Decision

Before diving in, make sure you understand:
- What exactly is being decided?
- What are the options on the table? (Ask if unclear — don't assume only two.)
- What matters most? Ask the user for their top priorities/criteria if they haven't stated them.
- What's the context? (Personal project vs. production system, budget constraints, timeline, team size, etc.)

Use `memory_search` to check for relevant past decisions, preferences, or context the user has shared before.

## 2. Research the Options

Gather concrete data to inform the comparison:
- Use `web_search` for current benchmarks, comparisons, and community consensus
- Use `memory_search` for any past experience the user has mentioned with these options
- Don't rely on stale training data for fast-moving topics — verify current state

## 3. Weighted Criteria Matrix

Build a comparison matrix with the criteria that matter for this decision. Weight criteria by importance to the user.

Example format:
```
| Criteria          | Weight | Option A | Option B | Option C |
|-------------------|--------|----------|----------|----------|
| Performance       | High   | Strong   | Moderate | Strong   |
| Learning curve    | Medium | Steep    | Easy     | Moderate |
| Community support | Medium | Large    | Growing  | Large    |
| Cost              | Low    | Free     | Free     | Paid     |
```

Rate each option on each criterion. Use plain language (Strong/Moderate/Weak) rather than arbitrary numeric scores unless the user prefers numbers.

## 4. Give a Clear Recommendation

**Don't fence-sit.** After analyzing the tradeoffs, give a direct recommendation:
- State which option you'd pick and why
- Acknowledge the strongest argument for the other option(s)
- Note any dealbreakers or scenarios where your recommendation would flip

Format: "I'd go with **X** because [primary reason]. The main argument for Y is [strongest counterpoint], but [why X still wins for their context]."

## 5. Anti-Patterns — When NOT to Use This

- **Simple preferences**: "Should I use tabs or spaces?" — just answer, don't build a matrix.
- **Obvious choices**: When one option is clearly better on every axis, say so directly.
- **Missing context**: If the user hasn't given enough context to make a real recommendation, ask questions first rather than generating a vague comparison.
- **More than 4-5 options**: Narrow down first, then compare the top contenders.

## Use Cases
- "Should I use PostgreSQL or MongoDB?"
- "Help me decide between React and Vue"
- "Compare AWS vs GCP for my startup"
- "Is it worth switching from X to Y?"
- "What database should I use for [use case]?"

## Notes
- Keep the matrix readable — 3-5 criteria is ideal, more than 7 becomes noise
- If the user pushes back on your recommendation, explore their concerns rather than immediately caving
- Store the decision outcome in memory if the user makes a choice, for future reference
