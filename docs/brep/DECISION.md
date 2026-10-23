# Decision: keep manual backend selection; open a separate routing issue

Decision proposed 2026-10-19 for issue #34 (BRep 17), based on the 80-generation
matrix in [task-17-comparison](task-17-comparison/README.md). Evidence is
re-verified by [task-17-comparison/audit.py](task-17-comparison/audit.py).
The earlier prototype decision is archived at
[decision-2026-10-13-prototype.md](decision-2026-10-13-prototype.md).
This issue changes no code default; `backend` stays `openscad` in the form.

## Numbers that drive the decision

| Measure (5 trials per cell, 8 drawings, 2 backends) | OpenSCAD | USD BRep |
|---|---:|---:|
| Runs passing every frozen check | 2/40 (5%) | 5/40 (12.5%) |
| Runs building a valid single watertight solid | 32/40 | 33/40 |
| Runs passing drawing-fidelity similarity (all views ≥ 0.45) | 24/40 | 11/40 |
| Hard build failures (job ended in error) | 0 | 7 (kernel: wheel ×3, curved_handle ×3; invalid_recipe: enclosure ×1) |
| Wall time per generation (min / median / max) | 58 / 215 / 975 s | 84 / 123 / 229 s |
| Median parameter-edit round-trip | 0.52 s | 2.87 s |
| Clarifications asked (ambiguous / missing-thickness) | 0 (no mechanism) | 10/10, then correct build |
| BRep-only editable operations produced (loft/shell/arc_pipe/extrude/sweep) | n/a | 22/33 built recipes |

Note: BRep's 5 "passes" are the missing-thickness behavior cell, whose
genus/volume/extents checks are not-applicable by design. On shared checks
alone no backend passed a cell outright except profiles/openscad (2/5).

## Reading the numbers

Neither backend is ready to own the default on correctness grounds.

1. Both backends fail the same drawings for different reasons. Bookend depth
   fails 10/10 across both. Wheel fails on the BRep kernel and on OpenSCAD
   volume. Enclosure splits: OpenSCAD wins fidelity (5/5), BRep wins topology
   (genus 4/5) — a default switch trades one failure class for another.
2. Speed is not a tiebreaker either. BRep generates faster (no LLM code-repair
   loop) but edits slower, and its supervisor-equivalent (construction
   correction) recovers rarely: mean attempts 0.4–1.4 vs OpenSCAD's 3.0 on hard
   cells, where the loop usually burns all three attempts without converging.
3. The product's own acceptance gate is out of calibration for either backend:
   the OpenSCAD agent accepted 7/40 runs that fail the stricter frozen checks,
   and the 0.45 per-view floor rejects BRep solids that match the reference
   volume exactly (profiles, 0.313 top view). Choosing a default cannot be
   justified by the current gates.
4. BRep's genuinely differentiating, measured strengths are product behavior,
   not raw pass rate: it asks clarification questions (10/10 where the drawing
   was ambiguous or under-specified), and it produces editable first-class
   recipes (5/5 real lofts on transition, 5/5 shells with exposed thickness on
   the shell fixture). These are reasons to keep BRep selectable and reachable,
   not reasons to make it the silent default.

## Proposal

1. **Keep manual selection** (recommended, adopted here as the proposal):
   the app stays as shipped — user-picked backend, current `openscad` form
   default. No default change ships from this issue.
2. **Open a separate routing issue** for automatic backend selection. The
   data already suggests cheap, verifiable routing signals: uniform shell,
   rectangular-to-round loft, circular-section sweep or parametric fillet in
   the construction plan → BRep; box-cutter pocket or plain boolean part →
   OpenSCAD; ambiguous opening/missing thickness → BRep (it asks). Routing
   rules, their guardrails and their own trial gate belong there — this issue
   deliberately leaves automatic routing out.
3. **File two calibration/defect issues** surfaced by the matrix:
   (a) `usd_brep 1.0.0` `tessellate(chord_height_tolerance)` dies with
   `ModuleNotFoundError: _omni_solid` on `arc_pipe + cylinder` unions
   (deterministic, serial-rebuild evidence); (b) the 0.45 top-view similarity
   floor and the 70-score accept gate reject reference-exact BRep solids while
   accepting wrong-volume OpenSCAD ones.
4. **Release flow unchanged.** `main` stays at the pre-BRep commit; a release
   into `main` still needs separate review and explicit user approval.

## Not verified here

n=5 per cell gives coarse rates. One model, one host, one day. The top-view
similarity artifact needs a viewer-side check. Targeted edits were
not-applicable on every run (no box-cutter pockets in this corpus); that path
is covered by task-15 evidence, not by this matrix.

## Update (issue #60) — opt-in Auto routing

The default stays manual: OpenSCAD remains the form default and an explicit
manual pick is never overridden. Issue #60 added an opt-in "Auto" choice whose
rules (kernel-history exclusion, operation keywords, view density, circular-
pattern kernel risk, single-view+dimension) and its frozen-set validation
(0 disagreements over 8 drawings) are documented in
`docs/brep/issue-60-routing/README.md`. This does not reverse the decision
above; it ships the escape-hatch-preserving half of issue #60. Auto-routing
may become the default only after `routing.json` telemetry accumulates enough
real jobs to re-calibrate the thresholds (see the Telemetry section there).

## Final ruling (issue #15, user decision 2026-10-19)

User ruling: the kernel stays user-selectable at the start of the flow and
**Direct BRep is the default**. Implemented on this branch:

- Form default: "Direct BRep (default)" is the first/selected option; OpenSCAD
  and Auto remain explicit choices. A manual pick is never overridden.
- Graceful degradation: on page load the UI reads /api/health; if the BRep
  worker is not installed and the selector is untouched, the default falls
  back to OpenSCAD (the health chip shows "BRep kernel missing").
- Legacy HTTP contract unchanged: POST /api/generate without a `backend`
  field still routes to the OpenSCAD pipeline (94 existing test/script call
  sites depend on it; the app always sends the field explicitly).
  Pinned by tests/test_backend_default.py.
- Known trade-offs of the BRep default, accepted with the data on record:
  multi-view sheets with uploaded projected views return a clear 422 (Direct
  BRep accepts one drawing sheet); the two usd_brep 1.0.0 kernel defects
  (issue #61) surface as kernel_unavailable with "Retry with the OpenSCAD
  backend" advice; frozen fidelity on dense multi-view ink favors OpenSCAD.
  Auto (issue #60) is the data-driven answer for those cases.
