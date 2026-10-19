# Issue #68 — never invent unconstrained dimensions: ask (size lottery)

**Date:** 2026-10-19 · **Branch:** brep-integration · **Case:** jeep grille
`012_vent_grille_grid` (single front view; GT plate 4 mm)

## Problem (measured)

`derive_physical_sizes()` returns `None` for every axis no registered view
constrains. The OpenSCAD pipeline then let the LLM invent that value from ink
proportions on every run: the same drawing produced visibly different plate
thicknesses trial to trial (issue #34 evidence, class "thickness lottery";
#62 calibration class `false_accepts_not_addressable_by_gate`). The
evaluator cannot judge an axis the drawing never states.

## Fix

One bounded question, asked before generation, reusing the existing
clarification channel (BRep openings already use it):

- `doodle_to_cad/sizes.py::plan_unconstrained_axes` — axes with no view
  constraint, ask priority depth → height → width.
- `doodle_to_cad/pipeline.py` — when an `ask_user` callback exists and the
  ink leaves an axis unconstrained, the pipeline publishes exactly one
  `body_dimension` question and waits. An answered value becomes the
  authoritative extent for that axis (`derived-sizes.json` gains
  `user_supplied_axes`). Unanswered runs record `unconstrained_axes` for
  audit instead of silently inventing.
- `doodle_to_cad/clarification.py` — new `body_dimension` kind in
  `ask_clarification`/`accept_answer` (validation mirrors thickness
  questions: positive, finite, ≤ 4× the authoritative max dimension,
  question-id bound) plus an optional `timeout_s`: on timeout the job
  returns to `queued`, continues without an answer, and the
  `clarifications.json` record says `timeout`.
- `doodle_to_cad/app.py` — wires `ask_user` into the OpenSCAD job with
  `timeout_s=120` and a form flag `ask_missing_dimensions` (default true)
  so unattended API clients that cannot answer opt out instead of stalling.
- `web/app.js` (v=20) — renders the number prompt and posts `value_mm`.
- Enforcement (found by the live demo itself): the first asked run reached
  `waiting_for_answer` and recorded the answer, but the generator still
  emitted a 5 mm plate — a suggestion the 0.22–2.6 sanity window happily
  swallowed. Now `derived_sizes.user_supplied_axes` flows into
  `spec.dimensions.user_supplied_axes`, `SCAD_PROMPT` marks those axes as
  user-stated absolute sizes, and `evaluate_candidate` hard-fails the
  `dimensions` gate when a user-stated axis deviates >15%, feeding the
  supervisor's retry loop "rebuild with exactly N mm for that axis".
  Unit test `test_evaluation_hard_gate_on_user_stated_axis` pins both
  directions (hard with the mark, loose window without it).

## Evidence

- `logs/full-suite.txt` — full pytest on this head (see audit).
- `logs/lottery-and-ask.json` + `logs/demo-ask.log` — live run on server
  8142: three OpenSCAD runs with the question suppressed
  (`ask_missing_dimensions=false`) guess the plate thickness from ink
  gestalt and never reach the 4 mm reference (all three: 5.0 mm); the
  fourth run reaches `waiting_for_answer` on the depth axis, is answered
  `4 mm` (the GT plate thickness), and the produced STL thickness is
  exactly 4.0 mm (score 99.3 vs 95.7 unasked).
- `scripts/demo_ask.py` — rerunnable driver (needs a server on the given
  URL, default `http://127.0.0.1:8142`).
- Manifest notes: `benchmarks/cases/012_vent_grille_grid/manifest.json`
  → `provenance.dimension_audit_issue_68` (single-view ink cannot constrain
  depth; score thickness only for answered/supplied runs), and
  `003_front_grille_multiview` → `provenance.ink_adaptation` (ink re-cut
  from the trusted STL; original drawing preserved).

## Acceptance mapping

| Issue acceptance | Where proven |
|---|---|
| Single-view run without size asks once, not silently guesses | `logs/lottery-and-ask.json`: `question_status=waiting_for_answer`, `question_kind=body_dimension` |
| Answered value lands in geometry | `ask_run.extents_xyz` thickness = 4.0 mm exactly (unasked: 5.0 mm); `size_clarification.answer.value_mm` recorded |
| No-ask clients unaffected | `ask_missing_dimensions=false` lottery runs complete without stalling; unit test asserts wiring contract |
| Frozen rows unaffected | #62 frozen calibration unchanged (registration untouched) |

## Known limits

- One question per generation (house rule "one question at a time"); a
  second unconstrained axis still falls back to LLM gestalt and is listed
  in `derived-sizes.json` → `unconstrained_axes`.
- The 120 s answer timeout is server-side; a user who walks away gets the
  old behavior after 2 minutes, with `clarifications.json` status
  `timeout` as the audit trail.
