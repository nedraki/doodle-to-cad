"""Single source of truth for every bench-final metric.

One definition per metric, used by aggregate.py (results.json + RESULTS.md),
audit.py (claim gate) and README.md (headline tables + definitions block are
generated between the AUDIT markers and re-checked verbatim). Before this
module, the same metric was restated independently in four places; the
907eed7 reporting bug was exactly such a restatement drifting.

Rule: a metric records numerator / applicable denominator / excluded count,
plus an end-to-end rate over ALL submitted trials. Conditional rates (over
completed trials only) are always labeled 'conditional'.

Separation invariants (issue #79):
  completion != valid solid != drawing check != reference match != acceptance
  - matching extents and volume is NOT complete shape agreement;
  - genus counts topological connections, never spoke/feature counts;
  - user acceptance is never derived from a score.
"""
import statistics

BACKENDS = ("openscad", "usd-brep")
NO_GT = "no_ground_truth"

# ---------------------------------------------------------------- accessors
def checks(r):
    return r.get("checks") or {}


def build(r):
    return r.get("build") or {}


def product(r):
    return r.get("product") or {}


def done(r):
    return r.get("job_status") == "done"


def exclusion(r):
    """Superseded/excluded marker: {reason, replaced_by} or None.
    An excluded row stays published on disk but is counted in NO metric."""
    return r.get("excluded") or None


def reference_kind(refs, drawing):
    v = refs.get(drawing) or {}
    return v.get("kind", NO_GT)


def has_reference(refs, drawing):
    return reference_kind(refs, drawing) != NO_GT


# ---------------------------------------------------------------- registry
# basis:
#   submitted          denominator = every published, non-excluded trial
#   done               denominator = completed, non-excluded trials
#   done_with_reference  denominator = completed trials whose drawing has a
#                      real reference; rows without reference are NOT
#                      applicable (never counted as failures) and are
#                      reported in `excluded`
METRICS = [
    dict(
        id="completion", label="completed", basis="submitted",
        definition=("Trial reached the terminal state job_status == 'done' with a "
                    "published result record. Error and cancelled trials are "
                    "outcomes, not completions, and stay published."),
        predicate=lambda r, refs: done(r)),
    dict(
        id="valid_solid", label="valid solid", basis="done",
        definition=("Harness re-measured the run STL independently: watertight AND "
                    "exactly 1 component (checks.build_success). This measures the "
                    "solid only; it says nothing about drawing agreement."),
        predicate=lambda r, refs: done(r) and checks(r).get("build_success") is True),
    dict(
        id="drawing_fidelity", label="drawing/fidelity", basis="done",
        definition=("Harness re-ran projection scores on (source drawing, run "
                    "geometry evidence, run view renders); every assigned direction "
                    "scored >= 0.45. Drawing agreement only; not dimensions, not "
                    "volume, not a reference match."),
        predicate=lambda r, refs: done(r) and checks(r).get("fidelity_pass") is True),
    dict(
        id="ref_extents", label="ref extents", basis="done_with_reference",
        definition=("Sorted run extents vs sorted reference extents, every axis "
                    "within 2%. Applies only where a real reference exists."),
        predicate=lambda r, refs: done(r) and checks(r).get("extents_pass") is True),
    dict(
        id="ref_topology", label="ref genus", basis="done_with_reference",
        definition=("genus == frozen reference genus where a ground truth exists. "
                    "Genus counts topological connections (tunnels/holes); it does "
                    "NOT prove feature placement and never establishes a spoke or "
                    "opening count."),
        predicate=lambda r, refs: done(r) and checks(r).get("genus_pass") is True),
    dict(
        id="ref_volume", label="ref volume", basis="done_with_reference",
        definition=("abs(volume - reference volume) / reference volume <= 0.02 "
                    "where a ground truth exists."),
        predicate=lambda r, refs: done(r) and checks(r).get("volume_pass") is True),
    dict(
        id="reference_dims_topo_vol", label="ref dims/topo/vol", basis="done_with_reference",
        definition=("extents AND genus AND volume all pass against a real reference. "
                    "This is NOT complete shape agreement: matching outside "
                    "dimensions, connection count and volume can still miss feature "
                    "placement, and such rows may fail the projection gates."),
        predicate=lambda r, refs: (done(r) and all(
            checks(r).get(k) is True for k in ("extents_pass", "genus_pass", "volume_pass")))),
    dict(
        id="automatic_overall_pass", label="automatic overall_pass", basis="done",
        definition=("checks.overall_pass == true: every automatic gate the harness "
                    "could evaluate is green. Includes no-ground-truth rows, so it "
                    "is NOT a reference match and never called one."),
        predicate=lambda r, refs: done(r) and checks(r).get("overall_pass") is True),
    dict(
        id="plan_acceptance", label="plan-accepted", basis="submitted",
        definition=("Frozen-plan product acceptance (TRIAL-PLAN.json "
                    "product_acceptance): openscad result.success (agent accepted, "
                    "score >= 70); usd-brep evaluation.status != 'failed'. For "
                    "usd-brep 'not failed' means automatic checks passed, still "
                    "unverified - NOT full acceptance. Counted over ALL submitted "
                    "trials (end-to-end) and over completed trials (conditional)."),
        predicate=lambda r, refs: done(r) and _acceptance(r)),
    dict(
        id="strict_full_acceptance", label="strict full acceptance", basis="submitted",
        definition=("usd-brep evaluation.status == 'passed'. The current evaluator "
                    "never emits 'passed' (brep_checks.py emits failed|unverified), "
                    "so this count is 0 by design; it is published under its "
                    "historical frozen-plan label, not silently changed."),
        predicate=lambda r, refs: done(r) and r["backend"] == "usd-brep"
        and product(r).get("status") == "passed"),
    dict(
        id="automatic_checks_unverified", label="automatic-checks unverified", basis="submitted",
        definition=("usd-brep rows with evaluation.status == 'unverified': "
                    "automatic checks passed, no human verification yet. Reported "
                    "separately from failed and from full acceptance."),
        predicate=lambda r, refs: done(r) and r["backend"] == "usd-brep"
        and product(r).get("status") == "unverified"),
    dict(
        id="user_acceptance", label="user acceptance", basis="submitted",
        definition=("User decision 'accepted' recorded on the review page (#80) "
                    "bound to the displayed artifact hash. Never derived from a "
                    "score. Not collected in this dataset until decisions exist."),
        predicate=lambda r, refs: False),  # wired when review decisions exist
]

METRIC_BY_ID = {m["id"]: m for m in METRICS}


def _acceptance(r):
    """Frozen-plan acceptance for a completed row (see plan_acceptance)."""
    p = product(r)
    if r["backend"] == "openscad":
        return p.get("accepted") is True
    return p.get("status") is not None and p.get("status") != "failed"


# ---------------------------------------------------------------- compute
def applicable_rows(rows, refs, metric):
    """Rows entering the denominator for `metric`; excluded rows never count."""
    rows = [r for r in rows if not exclusion(r)]
    basis = metric["basis"]
    if basis == "submitted":
        return rows
    if basis == "done":
        return [r for r in rows if done(r)]
    # done_with_reference
    return [r for r in rows if done(r) and has_reference(refs, r["drawing"])]


def compute(rows_by_backend, refs, decisions=None):
    """rows_by_backend: {backend: [row...]}. Returns the full metric table."""
    decisions = decisions or {}
    out = {}
    for backend, rows in rows_by_backend.items():
        published = [r for r in rows if r.get("backend") == backend]
        excl_rows = [r for r in published if exclusion(r)]
        counted = [r for r in published if not exclusion(r)]
        done_rows = [r for r in counted if done(r)]
        entry = {
            "submitted": len(counted),
            "done": len(done_rows),
            "excluded": [{"drawing": r["drawing"], "trial": r.get("trial"),
                          "reason": exclusion(r).get("reason"),
                          "replaced_by": exclusion(r).get("replaced_by")}
                         for r in excl_rows],
            "metrics": {},
        }
        for m in METRICS:
            if m["id"] == "user_acceptance":
                n_user = sum(1 for k, v in decisions.items()
                             if k.startswith(backend + "|") and v.get("decision") == "accepted")
                entry["metrics"][m["id"]] = {
                    "numerator": n_user, "applicable": len(counted),
                    "excluded": 0,
                    "conditional_rate": _rate(n_user, len(counted)),
                    "e2e_rate": _rate(n_user, len(counted)),
                    "note": "not collected" if not decisions else "bound to artifact hash",
                }
                continue
            app = applicable_rows(counted, refs, m)
            num = sum(1 for r in app if m["predicate"](r, refs))
            if m["basis"] == "done_with_reference":
                # 'excluded' must be EXACTLY the not-applicable (no reference)
                # completed rows — errored trials are not n/a, they are
                # non-completions already visible in the completion metric.
                excl = len(done_rows) - len(app)
            else:
                excl = 0
            entry["metrics"][m["id"]] = {
                "numerator": num, "applicable": len(app),
                "excluded": excl,
                "conditional_rate": _rate(num, len(done_rows)),
                "e2e_rate": _rate(num, len(counted)),
            }
        walls = [r["wall_seconds"] for r in done_rows if r.get("wall_seconds")]
        entry["median_wall_s"] = (round(statistics.median(walls)) if walls else None)
        out[backend] = entry
    return out


def _rate(n, d):
    return f"{n}/{d} ({100.0 * n / d:.0f}%)" if d else "n/a"


# ---------------------------------------------------------------- report text
# The two functions below are the ONLY generators of headline table text.
# aggregate.py writes them; audit.py recomputes and compares verbatim.
TBL_HEAD_END_TO_END = (
    "End-to-end rates over ALL submitted trials (every trial the harness was "
    "asked to run, including errors and refusals):\n\n"
    "| backend | submitted | completed | valid solid | drawing/fidelity | "
    "ref dims/topo/vol (X=no-ref) | plan-accepted | unverified (BRep) | user acceptance |")
TBL_SEP = "|---|---|---|---|---|---|---|---|---|"
TBL_HEAD_CONDITIONAL = (
    "Conditional rates over COMPLETED trials only (clearly labeled: these "
    "exclude errored trials from the denominator):\n\n"
    "| backend | done | valid solid | drawing/fidelity | "
    "ref dims/topo/vol (X=no-ref) | plan-accepted | strict full accept (hist.) | median wall (s) |")


def e2e_table_lines(stats):
    lines = [TBL_HEAD_END_TO_END, TBL_SEP]
    for backend, s in stats.items():
        mt = s["metrics"]
        rdm = mt["reference_dims_topo_vol"]
        ua = mt["user_acceptance"]
        lines.append(
            f"| {backend} | {s['submitted']} | {mt['completion']['e2e_rate']} | "
            f"{mt['valid_solid']['e2e_rate']} | {mt['drawing_fidelity']['e2e_rate']} | "
            f"{rdm['e2e_rate']} ({rdm['excluded']} no-ref) | "
            f"{mt['plan_acceptance']['e2e_rate']} | "
            f"{mt['automatic_checks_unverified']['e2e_rate']} | "
            f"{'not collected' if ua['numerator'] == 0 and ua['note'] == 'not collected' else ua['e2e_rate']} |")
    return lines


def conditional_table_lines(stats):
    lines = [TBL_HEAD_CONDITIONAL, TBL_SEP]
    for backend, s in stats.items():
        mt = s["metrics"]
        rdm = mt["reference_dims_topo_vol"]
        lines.append(
            f"| {backend} | {s['done']} | {mt['valid_solid']['conditional_rate']} | "
            f"{mt['drawing_fidelity']['conditional_rate']} | "
            f"{rdm['conditional_rate']} ({rdm['excluded']} no-ref) | "
            f"{mt['plan_acceptance']['conditional_rate']} | "
            f"{mt['strict_full_acceptance']['conditional_rate']} | "
            f"{s['median_wall_s']} |")
    return lines


def definitions_block_lines():
    lines = ["<!-- AUDIT:METRICS:BEGIN (generated from metrics.py - audit.py compares verbatim) -->",
             "Every metric is defined once, in `metrics.py`; the tables above recompute",
             "from these definitions. A metric records numerator/applicable-denominator",
             "and keeps these separations: completion != valid solid != drawing check",
             "!= reference match != user acceptance.", ""]
    for m in METRICS:
        lines.append(f"- **{m['label']}** (`{m['id']}`, basis: {m['basis']}): {m['definition']}")
    lines.append("<!-- AUDIT:METRICS:END -->")
    return lines


def tables_block_lines(stats):
    return (["<!-- AUDIT:TABLE:BEGIN (generated by aggregate.py from metrics.py - audit.py compares verbatim) -->"]
            + e2e_table_lines(stats) + [""] + conditional_table_lines(stats)
            + ["<!-- AUDIT:TABLE:END -->"])
