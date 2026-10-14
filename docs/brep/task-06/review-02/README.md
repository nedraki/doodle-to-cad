# PR 41 sequential review

The numeric construction guard allowed changes to root evidence, the recipe
name and body identity. Those changes are outside the permitted numeric repair.
The guard now preserves all root fields except operations and parameter values.
The correction prompt states the same rule and has version
`construction-numeric-fields-3`.

Validation:

- Full suite before this fix: 120 passed.
- Focused suite after the guard fix: 22 passed, including three new rejection cases.
- Saved successful wheel and both successful original-knob corrections still pass
  the stricter guard. See `guard-revalidation.json`.
- No new live generation trial. Earlier screenshots and native geometry retain
  their original meaning; this check does not improve drawing fidelity.

The known interpretation errors and the original-wheel correction failure remain
in `../correction-01/README.md`. PR #41 remains draft pending its product review.
No merge or change to `main` is made by this review.
