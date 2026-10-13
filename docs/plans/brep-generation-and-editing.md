# Direct BRep generation and richer editing

## Goal

Generate richer parts from doodles. Let users edit the saved construction recipe.
Keep the working OpenSCAD path during evaluation.

## Architecture

Use this path for new BRep generation:

Drawing → measured evidence → AI interpretation → validated recipe → BRep worker → geometry and drawing checks → product result.

Keep OpenSCAD as an alternative backend. Do not require OpenSCAD generation before direct BRep generation.
Keep the existing conversion action for old parts.
The AI infers features and proposes operations. The application checks capability and recipe validity.
The user selects the experimental backend during this project. Automatic routing is deferred.
Do not require users to name CAD operations. Ask for missing design information only when it changes the part.

## Starting point

The prototype exists on `codex/brep-detail-editing`, at commit `3ef2adc`.
It has an isolated worker, a bounded recipe, three test parts, and parameter editing.
Its reported baseline is 71 passing tests plus browser checks. Recheck this baseline in task 01.
It does not yet provide direct drawing-to-BRep generation or general feature editing.
Do not repeat completed prototype work without a documented reason.

## Related work

- [#15](https://github.com/nedraki/doodle-to-cad/issues/15) contains the kernel evaluation and adoption decision.
- [#16](https://github.com/nedraki/doodle-to-cad/issues/16) defines user-requested repair after generation. Keep that product feature separate.
- Share revision storage and candidate controls with [#16](https://github.com/nedraki/doodle-to-cad/issues/16). Do not create two competing implementations.

## Branch policy

Keep `main` at the pre-BRep version, `2672a6d`, during this project.
Use `brep-integration` for BRep development and product tests.
Create each new task branch from `brep-integration`.
Set `brep-integration` as the base of each BRep task pull request.
Merge a task only after its checks and user review pass.
Do not merge BRep changes into `main` without a separate release review and explicit user approval.
Use a separate test server and result directory for BRep work.

PRs #35 and #36 are closed without merging. Their commits are preserved in `brep-integration`.
They remain available as review history. Issue #18 still requires user review.

## Work rules

1. Work on one task at a time, in the listed order.
2. Read its dependencies and the current product state before implementation.
3. Create each task branch from `brep-integration`. Target its pull request at `brep-integration`.
4. Keep the current OpenSCAD flow working. Make new behavior optional until its gate passes.
5. Attach test results, a product demonstration, known limits, and recovery evidence to the issue.
6. Request user review of the demonstrated result before starting the next task.
7. Close a task only after its checks and user review pass.
8. Record partial work and blockers. A successful kernel call alone does not pass the gate.

Each task has one main result. Split it before implementation if it needs several independent product changes.
No calendar estimate is assigned before task 01 confirms the baseline.

## Validation record for each task

- Code: branch, commit, and pull request.
- Inputs: drawing or recipe IDs, model version, and relevant settings.
- Checks: expected values, fixed tolerances, observed values, and failures.
- Product: steps, screenshot or recording, download checks, and recovery checks.
- Decision: pass, fail, or blocked; user review; next issue.

Use deterministic tests for geometry contracts. Use saved fixtures for model-response tests.
Use live model trials for end-to-end evidence. Record all attempts; do not select only good results.

## Terms and writing style

- Interpretation: the proposed meaning of the drawing.
- Recipe: validated data that defines construction operations and dependencies.
- Backend: software that builds geometry from supported input.
- Candidate: a result that has not yet been selected by the user.
- Revision: a saved state with its source, parameters, artifacts, and checks.
- Validation gate: the evidence and review required before the next task starts.

Use ASD-STE100 principles for approximately 80% of the writing style.
Use short sentences, active voice, direct instructions, and one term for each concept.
Keep necessary CAD and software terms. This is not a measured compliance score or formal certification.
Reference: [official ASD-STE100 guidance](https://www.asd-ste100.org/about_STE.html).

## Release stages

| Stage | Tasks | Product result required |
|---|---|---|
| A: Integrate the foundation | 01–04 | A saved recipe uses the normal product flow. |
| B: Generate from the doodle | 05–08 | A doodle produces a checked BRep part without SCAD translation. |
| C: Add richer generation | 09–12 | Drawings produce profiles, sweeps, lofts, and hollow bodies. |
| D: Add richer editing | 13–15 | Users select features and keep or discard checked changes. |
| E: Prepare and evaluate release | 16–17 | Setup and comparison evidence support a release decision. |

## Deferred work

Automatic backend routing, general sketch constraints, arbitrary freeform surfaces, and untested export formats are outside this plan.
Revolutions and further operations can become separate tasks after the selected corpus shows a need.
The plan does not require feature parity between backends.
Never remove an unsupported feature silently or hide a backend switch.

## Ordered tasks

Task 01 evidence is preserved in `brep-integration` and awaits user review.
[PR #36](https://github.com/nedraki/doodle-to-cad/pull/36) is closed and retained as review history.
See [issue #18](https://github.com/nedraki/doodle-to-cad/issues/18) for the recorded generation failure.
All later tasks remain planned.

- [ ] 01. [#18](https://github.com/nedraki/doodle-to-cad/issues/18) — Record the baseline and review the existing BRep prototype
- [ ] 02. [#19](https://github.com/nedraki/doodle-to-cad/issues/19) — Use one build result contract for both backends
- [ ] 03. [#20](https://github.com/nedraki/doodle-to-cad/issues/20) — Define a versioned executable construction recipe
- [ ] 04. [#21](https://github.com/nedraki/doodle-to-cad/issues/21) — Run a saved recipe through the existing generation job flow
- [ ] 05. [#22](https://github.com/nedraki/doodle-to-cad/issues/22) — Extract feature relationships from drawing evidence
- [ ] 06. [#23](https://github.com/nedraki/doodle-to-cad/issues/23) — Generate a BRep part directly from the interpreted doodle
- [ ] 07. [#24](https://github.com/nedraki/doodle-to-cad/issues/24) — Check BRep generation against the drawing and repair bounded failures
- [ ] 08. [#25](https://github.com/nedraki/doodle-to-cad/issues/25) — Ask for missing drawing information when it changes the part
- [ ] 09. [#26](https://github.com/nedraki/doodle-to-cad/issues/26) — Generate extrusions from bounded drawing profiles
- [ ] 10. [#27](https://github.com/nedraki/doodle-to-cad/issues/27) — Generate a curved sweep from drawing evidence
- [ ] 11. [#28](https://github.com/nedraki/doodle-to-cad/issues/28) — Generate a loft between two drawing profiles
- [ ] 12. [#29](https://github.com/nedraki/doodle-to-cad/issues/29) — Generate a hollow body with a checked wall thickness
- [ ] 13. [#30](https://github.com/nedraki/doodle-to-cad/issues/30) — Save BRep edits as recoverable product revisions
- [ ] 14. [#31](https://github.com/nedraki/doodle-to-cad/issues/31) — Select generated features and map them to solid geometry
- [ ] 15. [#32](https://github.com/nedraki/doodle-to-cad/issues/32) — Apply targeted BRep recipe changes through the existing product
- [ ] 16. [#33](https://github.com/nedraki/doodle-to-cad/issues/33) — Make worker setup and exported files ready for a limited release
- [ ] 17. [#34](https://github.com/nedraki/doodle-to-cad/issues/34) — Compare generation paths and decide the product default


Tracking issue: https://github.com/nedraki/doodle-to-cad/issues/17
