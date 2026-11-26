---
name: r-security
description: Asks the security questions for r-plan and runs the security checks for r-review. Use before a slice is closed and after implementation, when the change listens, stores a secret, accepts input, or runs a command.
kind: check
order: 10
---

The general rules in `CLAUDE.md` apply.

<purpose>
The checks keep secrets, listeners, inputs, and commands inside the limits that the slice and the accepted ADRs name.
</purpose>

<questions>
1. What crosses a trust boundary: a listener, a file, a secret, or a command?
2. Who can call it?
3. What happens when the check says no?
4. What is the bound on the size and on the type of each input?
</questions>

<checks>
1. A secret is not in the tree, a log, or an error.
2. A listener is the one the accepted ADR names.
3. Input has a bound on size and on type. For a function that other code calls, a type in the signature is the bound on type.
4. A command the program runs is the one the slice named.
</checks>
