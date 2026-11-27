---
name: r-api-design
description: Gives the questions that r-plan asks and the checks that r-review runs for the shape of an API. Use when the change adds or alters an HTTP route, a body, a status code, or what a module or a library exports.
kind: check
order: 40
stages: [r-plan, r-review]
---

The general rules in `CLAUDE.md` apply.

<purpose>
One part of the questions and of the checks is HTTP. The other part is what a module or a library exports.
</purpose>

<rules>
- The list of routes for one product stays in a project skill that `CLAUDE.md` names.
</rules>

<questions>
If the slice changes a route, answer questions 1 to 5. If not, answer `not HTTP`.

1. What is the resource, the verb, and the status on success? Which verb returns the record?
2. What is the status and the error body on failure?
3. Which existing contract has to change in the same change as the handler?
4. What does a mutation of a record that does not exist answer?
5. Which one error handler turns an error into a response?

If the slice changes what callers can import, answer questions 6 to 8. If not, answer `not a module`.

6. What is exported?
7. What may a caller rely on?
8. What stays internal?
</questions>

<checks>
If the answer was `not HTTP`, skip checks 1 to 8. If the answer was `not a module`, skip checks 9 to 11.

1. The route matches the answers, including the failure status and the error body.
2. The contract and the handler changed together.
3. A new failure mode has a status and a body. A success body is not an error shape.
4. A thrown error that carries a status keeps that status. A body over the size limit answers 413, not 500.
5. A 5xx body has a fixed generic message. The detail goes to the log once.
6. A mutation of a record that does not exist answers 404, not success.
7. POST answers 201 with the record. PATCH answers 200 with the record. DELETE of one record answers 204 with no body.
8. One error handler turns errors into responses. A path of the API never answers HTML, an unknown path included.
9. The export list matches the answers.
10. A caller relies only on what the answers named.
11. A name that the answers called internal is not exported.
</checks>
