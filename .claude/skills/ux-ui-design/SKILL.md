---
name: ux-ui-design
description: Asks the interaction questions for plan and runs the interaction checks for review. Use before a slice is closed and after implementation, when the change has a screen, a control, or a visual.
kind: check
order: 30
---

The general rules in `CLAUDE.md` apply.

<rules>
- The tokens, the type scale, and the component catalogue of a product stay in a project skill that `CLAUDE.md` names.
</rules>

<questions>
1. What does the person do, in one sentence?
2. What does the empty state show, and what does the error state show?
3. Can a keyboard reach every control that a pointer can reach?
</questions>

<checks>
1. The screen matches the answers, including the empty state and the error state.
2. Focus is visible, and contrast holds for the text that the person must read.
3. A token that belongs to one product was not copied into this skill.
</checks>
