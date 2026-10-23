# Corrected capability-check runs

Selected evidence: **runs/004**. Selection is the final runner revision, not
selection of the best geometric outcome. Original evidence is untouched.

| Run | Outcome and reason retained |
| --- | --- |
| 001 | All workers failed because resolving the interpreter symlink bypassed the worker virtual environment. Inputs and complete error logs retained. |
| 002 | c1 failed its kernel guard; c2 failed an incorrect checker expectation of radius = setback. Corrected to the established radius/sqrt(2) contract. Other cases passed. |
| 003 | Same geometry results as 004; retained before isolating the runner's cases import from other evidence tools. |
| 004 | c2–c6 initial and edited checks pass; c7 initial passes (no edit defined); c1 fails its USD round-trip guard and its edit is not attempted. Runner exits 1, deliberately. |

001 and 002 were development executions in /tmp, copied here unchanged.
003 and 004 were executed directly here and include exact runner source snapshots.
All four include a frozen plan, environment, per-attempt recipes, worker
stdout/stderr, diagnostics or error records, and results. No trials are omitted.
A SHA-256 manifest covers the retained run files; it detects accidental changes,
not independent certification. Verify from this directory using:

```
sha256sum --check RUNS.sha256
```

For a new run use a new `--output` directory. Do not replace 004 or reuse the
historical evidence directory. Review all failures before designating another
run. The original demo server still shows historical evidence, not these runs.
The five edited success cases are checked against their actual geometry;
regression tests prove that substituting their initial meshes fails.
