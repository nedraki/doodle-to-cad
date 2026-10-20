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

## Evaluator/input defects — final registry (v2 byte re-read)

Statuses are machine-auditable: `VERIFIED` cites the exact archived JSON
field or a fixture in `tests/test_bench_eval_fixtures.py`; `REFUTED` records
a withdrawn claim with the bytes that killed it. Unresolved checks are
marked **unreliable** in RECLASSIFY (never deleted); thresholds were never
lowered to pass existing outputs.

* **EV-1 VERIFIED** — hidden GT dimensions (004 thickness, 007 depth/height,
  008 depth/height, 101 x/z): extents/volume checks unachievable by any
  compliant model (policy-compliant fixture passes build+genus, fails both).
* **EV-2 VERIFIED** — wheel opening count (`expected_at_least 1` passed 8)
  and the position check demanding an opening at the solid hub centre.
* **EV-3 VERIFIED** — the 27.8 mm ink measurement vs the explicit OD 120
  note; it REJECTED both score-100.0 wheel rows (false rejection).
* **EV-4 REFUTED** — "product accepted the 007 plate at 100.0" was a row
  mix-up from session notes. The accepted cells are shape-correct brackets;
  the actual plate was caught by harness fidelity (0.35) and product
  (accepted=False). Frozen in `test_ev4_refuted_the_bench_did_catch_the_wrong_part`.
* **EV-5 VERIFIED** — wheel volume compares the reference author's
  undimensioned rim (6 mm) / spoke (8 mm) choices.
* **EV-6 VERIFIED** — the only numeric in every brief is an unlabeled bare
  number (`dimension='54'`, `dimension_text=null`).
* **EV-7 VERIFIED** — orientation-dependent fidelity: the same 004 part
  passes fid on openscad and fails fid on usd-brep (front expects 3,
  renders 0 / top expects 0, renders 3).
* **EV-8 VERIFIED** — `ask_missing_dimensions=false` + no thickness in the
  form: the frozen 3 mm policy reaches the model only if it asks; openscad
  silently guessed 10 mm. The run measures guessing, not clarification.
* **EV-9 RESOLVED** — the two contract rejections (007 usd t2
  "Unsupported clarification", 004 usd t2 "Expected canonical world frame")
  are model-side: both rules are documented verbatim in the model prompts
  (direct_brep.py:23 frames block; intent-prompt clarification kinds).
  Disclosed gap: rejected payloads not retained → proposed product issue
  to write rejected plans/kernel-crash inputs into the cell dir.

## Re-scoring (RECLASSIFY.py — frozen numbers untouched)

Marking only VERIFIED-unreliable checks: openscad 2→9 passing, usd-brep
0→2. The 007 plate stays FAIL (fidelity is reliable — EV-4 refuted), and
101/003 stay FAIL on the visible-topology checks: the reclassification
measures the bench, not the parts. ATTRIBUTION.md holds the per-row blame.

## One command that re-verifies every published claim

```
uv run python docs/brep/bench-eval/eval_status.py
```

Runs manifest seal + audit (expect 34/34), the adversarial selftest incl.
the fresh-clone leg, the evaluator fixture gate, a reclassification
regeneration, and the EV-7 probe with a published-numbers drift guard.
Exit 0 only when every gate passes AND the probe reproduces the numbers in
`EV7_PROBE.md`. Last full run: `ALL GATES GREEN` — audit 34/34, selftest
29/29 + clone, fixtures 8 passed, reclassify 92 cells stable.

## Status

* [x] Test inputs defined with provenance + classification (CASES.json v2,
      every outcome re-read from archived bytes; v1 corrections recorded)
* [x] Fixture gate: known-correct passes; planted removed-opening,
      blind-hole, disconnected-body each caught by exactly its declared
      check; hidden-requirement (EV-1) fixture; EV-7/EV-4 byte freezes
* [x] Per-case first-failing-stage attribution (ATTRIBUTION.md v2)
* [x] Re-scoring with proven-unreliable checks (RECLASSIFY)
* [x] Level-2 replay: handle usd recipe exonerates the pipeline (+0.1 % capability variant)
* [x] EV-9 blame assignment (model-side, documented contracts; retention gap disclosed)
* [ ] EV-7 fix prototype (orientation normalization) + re-score
* [ ] Live current-model baseline (last, fixed settings, environment.json per #85)
