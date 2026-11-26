---
name: r-observability
description: Asks the observability questions for r-plan and runs the observability checks for r-review. Use before a slice is closed and after implementation, when the change starts a program, prints a message, writes a log line, or can fail.
kind: check
order: 50
stages: [r-plan, r-review]
---

The general rules in `CLAUDE.md` apply.

<purpose>
The checks make a program tell the person what it does and what failed.
</purpose>

<rules>
- `r-privacy` owns personal data in logs. `r-api-design` owns the error body.
</rules>

<questions>
1. What does the program print on start?
2. Which failure can the user cause, and where does the user see it?
3. Which unexpected failure needs its cause in the log?
4. Which code path runs for each request, and does it log?
</questions>

<checks>
1. On start, the program prints one line with the address it listens on and the data paths it uses.
2. A message is short and says what to do.
3. A hot path writes no log line for each request.
4. A failure that the user can cause reaches the user as a visible error, not as a silent empty view.
5. The program logs the cause of an unexpected failure once.
</checks>
