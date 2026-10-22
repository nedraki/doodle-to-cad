# cases-draft — pre-wired draft cells from the ABC open CAD dataset

**Status: DRAFT. No ground truth. Do not score against these yet.**

These cells are pre-wired candidates from the **ABC dataset** — *ABC: A Big
CAD Model Dataset For Geometric Deep Learning* (Koch et al. 2019) — staged so
the user can later ink **real doodles** over them. Each cell contains a
watertight candidate mesh fetched from the open dataset plus *placeholder*
ink; nothing here has been reviewed or drawn by a human.

## Layout (per cell)

```
NNN_abc_<MODELID>/
  ground_truth/model.stl        watertight candidate mesh, scaled so max
                                extent = 120 mm, xy-centred, base at z=0
  meta.yml                      ABC stats yml copied VERBATIM from the release
  derived/view-front.png        orthographic silhouette along -Y (x right, z up)
  derived/view-top.png          orthographic silhouette along -Z (x right, y up)
  source/drawing.png            PLACEHOLDER re-inked from the GT STL — see below
  manifest.json                 draft metadata, measurements, provenance
```

## What NOT to trust yet

- `source/drawing.png` is **not a doodle**. It was re-inked *from* the ground
  truth mesh with `benchmarks/tools/gen_doodle_from_stl.py`, so its silhouette
  is (by construction) the mesh silhouette. Using it for fidelity scoring
  would be scoring the mesh against itself. It exists only as a sheet-layout
  placeholder until the user draws real ink.
- `manifest.reference` is `kind: no_ground_truth`,
  `authority: candidate_from_open_dataset`. The measurements
  (volume/extents/euler/genus) are informational only until a real doodle
  exists for the cell.
- The ABC release ships **no unit key** in its meta/stats files; meshes are
  treated as nominal millimetres and every GT STL is uniformly scaled so the
  max extent is exactly 120 mm (`source.scale_to_mm` records the factor).

## Selection (deterministic)

- Selection seed **derived from the UTC date**: `int(YYYYMMDD)` =
  `20261022` (not hand-picked). `random.Random(seed)` chooses the chunk and
  the candidate ids, so re-running reproduces the same list.
- **Screening stats**: 30 candidate model ids screened inside the single
  seed-derived chunk `abc_0036` (20 primary candidates + 10 extra scanned
  specifically for the axisymmetric requirement — no other chunks were
  downloaded). 21/30 passed all machine checks (17/20 primary, 4/10 extra);
  the first 8 passing primary candidates in ascending id (list) order were
  kept — no cherry-picking for looks. Failures: 2 multi-component, 2 over
  50k triangles, 1 not watertight (1949 components), 4 rejected only by the
  extent screen before unit inference.
- Filters (trimesh): `is_watertight`, exactly 1 component (`mesh.split()`),
  < 50 000 triangles, `volume > 0` and consistent winding, max extent within
  [20, 400] mm after unit inference (chunk STLs carry no unit key; metres
  inferred by magnitude and normalised — recorded per case in
  `manifest.source.unit_original` / `scale_to_mm`).
- **Axisymmetric flag**: recorded per case as `axisymmetric_flag`
  (two near-equal principal inertias + near-constant radial silhouette).
  **0 of 30 screened candidates passed the axisymmetric check**, so the
  "at least 2 axisymmetric" preference was not forceable and no swap was
  performed (see `manifest.selection.selection_note`).
- Source of the meshes: chunk archive `abc_0036_stl2_v00.7z`
  (`https://archive.nyu.edu/rest/bitstreams/88772/retrieve`, listed in
  `stl2_v00.txt` line 37) — files `<id>_<guid>_trimesh_NNN.stl`; the Onshape
  document metadata comes from `abc_0036_meta_v00.7z`
  (`https://archive.nyu.edu/rest/bitstreams/88769/retrieve`) and the geometry
  stats yml from `abc_0036_stat_v00.7z`. Each manifest records the chunk
  URLs, the per-model entry name, and the SHA-256 of the downloaded STL.

## Case inventory (draft, no ground truth)

| cell | ABC id | tri | extents mm (x·y·z) | vol mm³ | genus | shape (inferred from measurements) | axisym |
|---|---|---|---|---|---|---|---|
| 001 | 00360047 | 504 | 28.8·28.8·120 | 78 140 | 0 | flanged/twisted tube along Z | no |
| 002 | 00360794 | 10 836 | 120·6.5·120 | 61 605 | 9 | thin perforated plate (9 cuts) | no |
| 003 | 00360968 | 508 | 120·57·18 | 114 764 | 0 | low flat block | no |
| 004 | 00361746 | 396 | 120·80·13.3 | 127 618 | 0 | flat plate/wedge | no |
| 005 | 00361897 | 44 | 80·120·100 | 781 976 | 0 | rectangular solid (box) | no |
| 006 | 00362157 | 3 012 | 120·109·1.7 | 20 459 | 4 | thin perforated sheet (4 cuts) | no |
| 007 | 00362462 | 14 854 | 120·48.6·27.2 | 146 487 | 0 | curved low solid | no |
| 008 | 00362827 | 2 132 | 120·73.8·55.4 | 87 607 | 1 | solid with one through-hole | no |

Shape column is an *inference* from topology/measurements, not a label from
the dataset — the ABC release ships no semantic labels. All `scale_to_mm`
values normalise the downloaded (metres-inferred) mesh to max extent 120 mm.

## Provenance & license

ABC dataset; copyright owned by the creators; distributed under the Onshape
Terms of Use 1.g.i. Cite: *ABC: A Big CAD Model Dataset For Geometric Deep
Learning* (Koch, Matl, Li, Qi, Ge, Fu — 2019). Each manifest repeats the
citation and the chunk URLs the files were fetched from, plus the SHA-256 of
the downloaded STL.

## Honest data-access notes (discovered during wiring)

- The per-file URL scheme
  `https://deep-geometry.github.io/abc-dataset/data/<id>_<guid>_<fmt>_000.<ext>`
  only resolves for a handful of demo models on gh-pages; for general model
  ids it 404s. The bulk archives on `archive.nyu.edu` (referenced by
  `stl2_v00.txt` & co.) are the working per-model source.
- Chunk archives are **mislabelled relative to the list names** on the
  mirror: the archive listed as `abc_0036_stl2_v00.7z` actually contains
  `<id>_<guid>_trimesh_000.stl` files (the trimesh-exported watertight STL —
  the same mesh pipeline the `stl2` binary format refers to), and the
  `ofs_v00` chunks contain featurescript YAML. Selections use archives whose
  verified contents match what is documented in each manifest.
- `meta_000.yml`/stats as described in the paper (with a `unit` field) are
  not present in the released archives; `meta.yml` in these cells is the
  verbatim stats YAML (geometry stats), and the Onshape document summary is
  kept under `source/document_metadata.yml`.

## How to regenerate

```bash
S=~/.hermes/profiles/doodle-to-cad/cache/scratch/abc   # or any scratch dir
cd $S
# 1. master chunk lists (one line per chunk: <archive-url> <name>):
for k in stl2 meta stat; do curl -sL -o ${k}_v00.txt \
  https://deep-geometry.github.io/abc-dataset/data/${k}_v00.txt; done
# 2. seed-derived chunk (~4.9 GB; pick.py/pick_v3.py print the chunk number):
curl -sL -o chunks/stl2_0036.7z "$(sed -n '37p' stl2_v00.txt | awk '{print $1}')"
curl -sL -o chunks/meta_0036.7z "$(sed -n '37p' meta_v00.txt | awk '{print $1}')"
curl -sL -o chunks/stat_0036.7z "$(sed -n '37p' stat_v00.txt | awk '{print $1}')"
# 3. select candidates (needs trimesh/numpy/cv2 from the repo venv + py7zr):
uv venv .venv && uv pip install --python .venv/bin/python py7zr
REPO=/tmp/doodle-brep-95  # any doodle-to-cad checkout with the repo venv built
PYTHONPATH=$REPO/.venv/lib/python3.11/site-packages \
  .venv/bin/python pick_v3.py > results3.json
# 4. build cells (same interpreter); one call per case index 1..8:
PYTHONPATH=$REPO/.venv/lib/python3.11/site-packages \
  .venv/bin/python build_case.py "$(jq -c '.results[] | select(.model_id=="<ID>")' results3.json)" <NNN>
```

`build_case.py` regenerates everything under the case dir; the placeholder
doodle uses seed = `selection_seed + NNN` (recorded per case in
`manifest.doodle_generation.seed`).

## Selection seed

```
selection_seed = 20261022   # int(datetime.now(timezone.utc).strftime('%Y%m%d'))
chunk          = 0036       # sorted(Random(seed).sample(range(100),4))[0]
candidates     = 20 ids sampled with the same RNG, kept-first-8-wins
```
