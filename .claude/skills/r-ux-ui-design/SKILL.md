---
name: r-ux-ui-design
description: Asks the interaction questions for r-plan and runs the interaction checks for r-review. Use before a slice is closed and after implementation, when the change has a screen, a control, or a visual.
kind: check
order: 30
stages: [r-plan, r-review]
---

The general rules in `CLAUDE.md` apply.

<rules>
- WCAG is the Web Content Accessibility Guidelines.
- The tokens, the type scale, and the component catalogue of a product stay in a project skill that `CLAUDE.md` names.
</rules>

<questions>
1. What does the person do, in one sentence?
2. What does the empty state show, and what does the error state show?
3. Can a keyboard reach every control that a pointer can reach?
4. Which control returns focus to which control when a dialog closes?
5. Which state does the screen show, and what shows it besides colour?
</questions>

<checks>
1. The screen matches the answers, including the empty state and the error state.
2. Focus is visible. Text and controls meet contrast level AA of WCAG 2.2.
3. Each input has a programmatic label.
4. A validation error is text next to its field, not only a colour.
5. No state shows by colour alone.
6. A decorative icon is hidden from assistive technology. An icon-only control has an accessible name.
7. No content flashes more than three times in one second.
8. A dialog returns focus to the control that opened it.
9. A token that belongs to one product was not copied into this skill.
</checks>
