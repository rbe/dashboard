---
name: r-privacy
description: Asks the privacy questions for r-plan and runs the privacy checks for r-review. Use before a slice is closed and after implementation, when the change stores, logs, exports, or shows personal data.
kind: check
order: 20
stages: [r-plan, r-review]
---

The general rules in `CLAUDE.md` apply.

<purpose>
The checks limit where a change stores, shows, logs, and exports personal data.
</purpose>

<questions>
1. What personal data is stored, shown, logged, or exported?
2. What remains if a log or a fixture is copied out of the machine?
3. Who asked for the export?
4. Which text in an error or a message comes from outside the code?
5. Does an import refuse a row, and how does the message name the row?
</questions>

<checks>
1. Logs and errors contain no personal data.
2. An export is one the user asked for in this slice.
3. Example data is marked as an example. Real data is not in the tree.
4. Text from outside the code goes to the log. A parser, a provider, and the network are outside the code. The error that the user sees is text that the code wrote.
5. A refused row of an import is named by its line number, never by its content.
</checks>
