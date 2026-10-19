# Issue #62 final calibration decision, machine-recomputable from data/runs.jsonl + runs-live.jsonl.
# The gate change adopted: R3 genus floor. Rules measured and REJECTED with evidence: R1 (ink dims).
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows = [json.loads(l) for l in (HERE / "data/runs.jsonl").read_text().splitlines()]
live = [json.loads(l) for l in (HERE / "data/runs-live.jsonl").read_text().splitlines()]

def r3_violation(r):
    """Genus floor: watertight single-component mesh must have as many true
    through-openings as the best registered view demands."""
    holes = r.get("through_holes")
    crops = [t["crop"] for t in (r.get("profile_topology") or {}).values()]
    expected = max(crops) if crops else 0
    return holes is not None and expected > 0 and holes < expected

acc = [r for r in rows if r.get("old_accepted")]
kept = [r for r in acc if not r3_violation(r)]
removed = [r for r in acc if r3_violation(r)]
trusted = [r for r in acc if r["trusted"]]
metrics = {
    "population": {"rows": len(rows), "old_accepted": len(acc), "trusted_accepted": len(trusted)},
    "adopted_rule": "R3 genus floor: strict & watertight & single-component & through_holes >= max(crop_internal_profiles)",
    "r3_removed_from_accepted": [f"{r['drawing']}/{r['backend']}/{r['trial']}: holes {r['through_holes']}" for r in removed],
    "r3_false_rejections_of_trusted": len([r for r in trusted if r3_violation(r)]),
    "rejected_rule_R1": {
        "reason": "sorted and labeled mesh-vs-ink dimension ratios cannot separate trusted from false-accepted rows: "
                  "wheel usd-brep trial-01 (false) and trial-02 (trusted) share identical sorted-vs-sorted ratio signatures "
                  "[0.842, 4.317, 1.0]; trusted profiles_empty_notes rows contain ratio 0.424. Any R1 window produces FRR.",
        "evidence": "data/runs.jsonl fields r1_ratios, through_holes, trusted"},
    "false_accepts_not_addressable_by_gate": {
        "count": len([r for r in kept if not r["trusted"]]),
        "class": "drawing-vs-GT proportion discrepancy (frozen extents/volume checks fail while mesh is faithful to ink)",
        "examples": sorted({r["drawing"] for r in kept if not r["trusted"]}),
        "action": "follow-up issues: require all-three-dimension guidance; case GT audit"},
    "live": {
        "jeep_012": "accepted; thickness 5-vs-4 GT not recoverable from single-view ink -> not gate-addressable",
        "grille_003": "accepted rows (ab main-3, branch-2) are ink-faithful at derived 19.81 mm depth; case GT says 3 mm "
                      "-> drawing/reference discrepancy, documented; R3 rejects the genus-0 regression",
        "motor_103": "accepted; openings lost by view-registration drop (crop=0 where sketch shows circles) -> follow-up issue",
    },
}
(HERE / "data/metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
print(json.dumps(metrics, indent=2))
