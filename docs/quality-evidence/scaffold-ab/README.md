# Parts-list scaffolding A/B (held-out categories)

Question: does forcing the designer to emit an explicit component manifest
(role/attached_to/visible_in/drawn_position per member) before writing SCAD
move generation quality? Held-out set (house/butterfly/boat/anchor), N=2
per arm, same commit cf53fc1, same one-judge, only prompt difference
(spec_prompt hash 0545422b vs 4005cb61 recorded per run fingerprint).

Machine: plain 0/8 accepted, scaffold 1/8 (butterfly t1).
Manifests materialized: scaffold boat names Mast/Sail/Flag, anchor names
shackle/stock/arms/flukes, house names chimney (plain emitted none).

Visual audit of all 16 iso renders (scaffold-sheet.png): 2-2 rows.
- scaffold better: house (only gable roof in the whole grid), boat (only
  upright-triangle sail topology)
- plain better: butterfly (only disc wings), anchor (only curved crown arc
  + paired flukes — the grid's single PASS is plain t1)
- The one judge-accepted build (scaffold butterfly t1) is a visual FAIL:
  cube + cylinder "wheels" at the drawn wing positions. Placement gates
  accept correctly-placed wrong-shape material — shape semantics are
  outside any pixel-coverage check.

Verdict: scaffolding shifts the failure mode (undeclared parts -> declared,
built, sometimes wrongly shaped/detached) but does NOT improve outcomes at
N=2: no new human-good accepts, machine/human intersection still zero.
Retired from the product path (kept behind DOODLE_PARTS_SCAFFOLD=1 flag,
default off). Bottleneck is model shape-reasoning talent, not contracts:
the trust layer now refuses the wrong-plane class everywhere it can see it.
