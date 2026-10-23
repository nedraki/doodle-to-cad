# 003_front_grille_multiview — source files

Two drawings ship with this case:

- `drawing.png` — the ACTIVE benchmark input. Re-inked from the ground-truth
  `../ground_truth/model.stl` by `benchmarks/tools/gen_doodle_from_stl.py`
  (seed 3, scale 4.0 px/mm, 706x619 sheet) so the ink and the reference agree.
  The reference user drawing encoded ~20 mm thickness in its edge strip while
  the STL is 3 mm; that contradiction made the reference unreachable for any
  depth inference. See `../manifest.json` -> `provenance.ink_adaptation`.
- `drawing-as-drawn.png` — the ORIGINAL user-supplied hand drawing, preserved
  verbatim (its hash is recorded in the manifest) for future ink-ambiguity
  experiments. Not used for scoring.

`model.scad` and `model.stl` are the untouched user-supplied ground truth
(pair-verified: identical extents, zero relative volume delta).
