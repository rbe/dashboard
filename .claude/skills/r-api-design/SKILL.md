---
name: r-api-design
description: Gives the questions that r-plan asks and the checks that r-review runs for the shape of an API. Use when the change adds or alters an HTTP route, a body, a status code, or what a module or a library exports.
kind: check
order: 40
---

The general rules in `CLAUDE.md` apply.

<purpose>
One part of the questions and of the checks is HTTP. The other part is what a module or a library exports.
</purpose>

<rules>
- The list of routes for one product stays in a project skill that `CLAUDE.md` names.
</rules>

<questions>
If the slice changes a route, answer questions 1 to 3. If not, answer `not HTTP`.

1. What is the resource, the verb, and the status on success?
2. What is the status and the error body on failure?
3. Which existing contract has to change in the same change as the handler?

If the slice changes what callers can import, answer questions 4 to 6. If not, answer `not a module`.

4. What is exported?
5. What may a caller rely on?
6. What stays internal?
</questions>

<checks>
If the answer was `not HTTP`, skip checks 1 to 3. If the answer was `not a module`, skip checks 4 to 6.

1. The route matches the answers, including the failure status and the error body.
2. The contract and the handler changed together.
3. A new failure mode has a status and a body. A success body is not an error shape.
4. The export list matches the answers.
5. A caller relies only on what the answers named.
6. A name that the answers called internal is not exported.
</checks>
