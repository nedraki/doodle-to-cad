# Held-out generality set (210-213)

Four categories never used in any tuning: house, butterfly, boat, anchor.
Owner drew them cold for the generality question (quality arm, N=2, cache
off, jail: peak RSS 167 MiB / 12G cap).

Machine: own-gates 2/8 accepted, one-judge 1/8 (anchor t2).
Visual audit (sheet, per-row PASS/ALMOST/FAIL):
  house t1 ALMOST (roof missing in front/top), house t2 PASS
  butterfly t1 FAIL, t2 FAIL (wings = stubs)   [t2 was own-ACCEPTED at 92.8]
  boat t1/t2 ALMOST (sail on wrong plane, portholes missing)
  anchor t1 ALMOST (flukes sideways), t2 ALMOST-borderline-FAIL
    [t2 was the one judge-accepted build]

Findings:
1. The owner's rejection theme generalizes: on 4 UNSEEN categories the
   dominant failure is exterior parts (wings/sail/flukes/roof) dropped or
   on the wrong plane — same class as flower petals / scooter flaps.
2. Both machine accepts (butterfly t2, anchor t2) are human FAIL/ALMOST.
   The new part-position gate (committed after generation started) would
   have refused butterfly t2 (wing coverage 0.12-0.16 < 0.25 floor).
3. Gate coverage limit, measured: exterior parts drawn as DISJOINT closed
   contours are caught (butterfly, flower); parts touching the outline
   (roof, sail) or drawn as open strokes (anchor flukes) produce no region
   -> unmeasured, never fails. That is the next gap.
4. Over-block again: house t2 (visually the most faithful build) rejected
   by aspect (drawing 1.24 vs render 0.73) + genus opening demand — same
   tension as the owner-PASS fixtures from run 3.

Artifacts: heldout-sheet.png (drawing | front | top | iso, judge chips),
generation log + raw.json per cell under the A/B scratch dir
(ab-lamp-family sibling: heldout-gen/).

## Part-gate v2 (boundary-sharing) result on this set

Fixing pointPolygonTest(measureDist=True) made the boundary-share branch
live. Roof (coverage .82, door 1.0 -> silent; pixel truth overruled the
visual reviewer's "roof missing in front" claim) and the boat SAIL (1-2%
material, both trials -> flagged) are now measured. Anchor flukes stay
open strokes -> unmeasured (accepted limitation).
Cost paid on the 41-cell set: scooter-t3 and mug-t1 (both ALMOST) gained
new reject flags. PASS tier stays fully silent. Machine-accept set:
6 -> 2 (the 2 survivors are the known person-t2 GETTING THERE pair).
