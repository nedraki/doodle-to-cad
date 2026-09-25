# Doodle to CAD benchmark

The benchmark is case-based. Supplied artifacts are immutable; generated evidence and renders live under `derived/` and may be regenerated.

Each case contains:

- `source/`: user drawing(s) and source metadata.
- `ground_truth/`: reference CAD supplied for the case.
- `derived/`: reproducible renders, mesh measurements, and perception evidence.
- `manifest.json`: labels, provenance, tolerances, and exact/inferred status.

## Benchmark rules

1. Never tune against the evaluation holdout set.
2. A case may enter the holdout only after its intended design and view labels are confirmed.
3. Keep supplied files byte-for-byte unchanged and record SHA-256 hashes.
4. Separate facts encoded in reference CAD from human/model inference.
5. Score topology, dimensions, feature presence, and registered projections independently.
6. Do not add a geometry-specific production rule unless it represents a documented CAD invariant and improves multiple unrelated benchmark families.
7. Report per-family performance; an aggregate score must not hide a failed mandatory gate.

## Dataset splits

- `development`: visible during implementation.
- `validation`: used for threshold selection, not code-specific tuning.
- `holdout`: frozen before evaluation and opened only for release decisions.

Case `001_l_bookend_multiview` is currently in `development` until the user confirms that its supplied SCAD/STL represent the intended target exactly.

## Run the descriptive baseline

```bash
uv run python benchmarks/validate.py
uv run python benchmarks/run_baseline.py
```

The baseline measures the current evaluator against supplied reference geometry. It is diagnostic only until the dataset includes enough unrelated families and a frozen validation split.

Current projection similarity uses the better of filled-profile overlap and a symmetric edge-distance score. This allows both broad silhouettes and thin/open projected profiles to be compared without using object-specific rules.
