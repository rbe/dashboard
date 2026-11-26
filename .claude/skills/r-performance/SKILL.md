---
name: r-performance
description: Asks the performance questions for r-plan and runs the performance checks for r-review. Use before a slice is closed and after implementation, when the change reads, parses, imports, or aggregates data, or claims a gain in speed, size, or quality.
kind: check
order: 60
stages: [r-plan, r-review]
---

The general rules in `CLAUDE.md` apply.

<purpose>
The checks limit the work that a change does for the largest input it must handle.
</purpose>

<rules>
- A claim about speed, size, or model output quality needs a baseline from the same session.
</rules>

<questions>
1. What is the largest input that the change must handle?
2. How many times does the change read each file or row?
3. Where does the data live, and where does the aggregation run?
</questions>

<checks>
1. Each file or row is read once for each request, not once for each loop step.
2. An import or a parse runs in one pass.
3. Aggregation runs where the data is, not in a client that must first fetch all of it.
4. A claim that a change is faster or slower states a measured baseline from before the change and a measurement after it. Both come from the same machine and the same session.
</checks>
