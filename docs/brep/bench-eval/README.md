# bench-eval — evaluator validation and failure attribution (issue #81)

Parent: #78. Depends on #79/#80. This directory holds the evidence for two
questions, in order:

1. **Can the bench measure correctly?** (evaluator validation, fixtures)
2. **Where does each named case actually fail?** (first demonstrated failure,
   three levels: trusted recipes → saved model responses → live trials)

Nothing here changes the shipped bench-final numbers; it builds the case
file that tells us whether a limit is the LLM, the pipeline, or our own
checks.

## Test inputs (defined before generation)

`CASES.json` records, for each of the six named drawings (plus the recorded
substitution for the removed missing-thickness case):

* required shape, features, dimensions, relationships, tolerances;
* the **provenance of every requirement** — `ink` (transcribed from the
  source drawing), `notes` (frozen brief text), `frozen-dimension` (plan
  field), `clarification` (frozen policy answer, disclosed), or
  `reference-only` (known only to the evaluator — a **hidden requirement**
  the model never received);
* classification: fully specified / requires clarification / requires
  unsupported construction.

A reference-only thickness is flagged as such and can never be counted as a
model failure (see EV-1). Reference geometry was never sent to the model
(every `request.json` records `reference_geometry_sent: false`).

## Evaluator defect candidates

Statuses are machine-auditable: `VERIFIED` cites the exact archived JSON
field; `candidate` must be proven by a fixture (below) before any relabel.

* **EV-2 / EV-3 — VERIFIED from archived bytes (wheel).**
  The opening-count check passed `actual 8` against `expected_at_least 1`
  while the sheet explicitly notes "8 spokes"; the position check demands an
  opening at the hub centre `(0.499, 0.499)` (a correct wheel has a solid
  hub there — fidelity is 0.0 by construction); and the product's own ink
  measurement expected `X=27.8 mm` against the explicit `OD 120 mm`.
  The wheel's model-side verdicts cannot be trusted until these checks are
  fixed: unresolved checks are marked **unreliable**, and thresholds are
  never lowered to pass existing outputs.
* **EV-1 — candidate: hidden thickness.** 004/007 GT thickness 5 mm exists
  nowhere the model can see; the frozen clarification answer is 3 mm; the
  ±2% volume check then fails for *any* compliant model. A correct answer
  rejected by an unreliable check is an evaluator failure, not a model
  failure.
* **EV-4 — candidate: acceptance insensitivity.** 007 built a plate where
  the notes + GT require an L-bracket; the product still scored 100.0.
  Invalid model output and correct application rejection must stay separate
  verdicts — this is the case where neither happened.

## Three test levels (issue #81)

1. **Trusted construction** — reviewed hand-authored OpenSCAD sources and
   BRep recipes; measures the pipeline without any LLM.
2. **Saved model responses** — archived `generation.json` /
   `model.scad` / `model.recipe.json` replays; measures parsing, validation,
   coordinate handling, execution without new inference. Repeatable.
3. **Live current-model trials** — only after 1 and 2 and the check
   validation are green; fixed run count and settings; isolated results
   directory; environment.json written per #85.

## Status

* [x] Test inputs defined with provenance + classification (CASES.json)
* [x] EV-2 / EV-3 verified from archived drawing-checks/result bytes
* [x] Fixture proof for EV-1 / EV-4 — `tests/test_bench_eval_fixtures.py`
      (7 gates: known-correct passes; planted removed-opening, blind-hole,
      disconnected-body each caught by exactly its declared check; hidden
      3 mm policy build fails reference-only extents/volume — EV-1; plate
      vs reviewed bracket score IDENTICALLY through projection_scores — EV-4)
* [ ] Per-case first-failing-stage attribution (replays)
* [ ] Substitution experiments (reviewed plan → downstream build)
* [ ] Live current-model baseline (last, fixed settings)
