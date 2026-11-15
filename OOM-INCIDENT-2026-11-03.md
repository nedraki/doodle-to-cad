# Incident Report — OOM kills traced to SNAP3D batch runs

**Date:** 2026-11-03 · **Host:** spark-8322 (DGX Spark, GB10, 121 GiB unified LPDDR5x)
**Audience:** doodle-to-cad Hermes profile (and any agent working this repo)
**Status:** Root cause confirmed. Engine & Hermes harness exonerated. Fixes NOT yet applied — see §6.

---

## 1. What happened

Between **Nov 1 17:26** and **Nov 3 02:03**, the Linux kernel OOM-killed five python
processes (~123–124 GB anon-RSS each) and the vLLM inference engine died once as
collateral damage (NVRM `NV_ERR_NO_MEMORY`, Nov 2 23:14:56). The user experienced this as
"the inference engine dies out of memory whenever I work on doodle-to-cad".

This box has **one memory pool shared by CPU and GPU**: the vLLM engine
(`qwen3.8-flash` container) holds ~91 GiB resident (77 GiB weights + KV + activations),
leaving **~30 GiB of headroom for everything else**. Anything that grows past that ceiling
triggers a global OOM; the kernel always executes the largest debtor.

## 2. Root cause (confirmed)

The **SNAP3D exploration runs** launched by this profile's agent:
`/tmp/doodle-snap3d/scripts/snap3d_run.py` (trimesh + MuJoCo "drop test" physics).

`traces_for()` → `doodle_to_cad/snap3d/sim.py::drop_frames/_rollout` **appends per-frame
poses without a max-step or divergence cap**. For unstable cases (the log showed
`arm_l unstable`, `head fallen`, worst displacement 443) the rollout never converges, so
the frame list grows unbounded — multiplied by modes (`drop`, `reverse`) × stages
(`raw→PGE→CGR`) × the 9-case batch × parts up to 200k faces × 30k-point surface sampling.
Stable cases finish small and fine; **an unstable case steps forever until the kernel
kills the process at ~124 GB**. Every retry reproduced it identically — it looked like a
leak but is an unbounded loop.

Why the engine died too: while the snap3d python ate the pool, the GPU driver could not
allocate (`NVRM: Out of memory @ mem_desc.c:1359`) and the EngineCore crashed. The engine
is a victim, not a culprit.

## 3. Evidence chain (each kernel kill ↔ each agent launch)

| Kernel OOM kill | Agent action (from profile `state.db` transcripts) |
|---|---|
| Nov 1 17:26:21, pid 1803178 | terminal command at cwd `/tmp/doodle-snap3d`; tool result at 17:26:24 returned **empty output** (killed mid-run) |
| Nov 2 23:24:49, pid 3901299 | background spawns 23:17:27 (pid 3900675) & 23:17:32 (pid 3900743) + foreground rerun; agent transcript: *"Both processes vanished with zero output — something killed them at spawn"* |
| Nov 3 00:56:07, pid 4017443 | `===BATCH===` (9 cases, 73 GLB parts) spawned 00:48:38, pid 4016388 |
| Nov 3 01:56:59, pid 4122800 | background process spawned 01:51:07, pid **4122792** (victim = pid+8, same lineage) |
| Nov 3 02:03:33, pid 4124151 | "try again" retry of the same batch |

Corroborating: Hermes backends (desktop `serve`/gateway) run under
`user.slice/user-1000.slice/session-N.scope`, so **agent-spawned pythons share the exact
cgroup fingerprint of the victims** (uid 1000, session scope) — while the containerized
engine is root in `system.slice/docker-*.scope` and was never the executed process.
Hermes harness itself peaked at a few hundred MB per process; `hermes doctor` and live
inference/tool-call smoke tests all passed on Nov 3.

## 4. Operating rules for this profile (follow these in future sessions)

1. **Never re-run a snap3d batch that was previously killed** (`zero output`, `exit_code`
   with empty result, or `signal 9`/`killed`) without first bounding the rollout for the
   offending case. Blind retries reproduced the OOM 5×.
2. **Wrap every heavy batch run in a memory jail**, e.g.:
   `systemd-run --user --scope -p MemoryMax=20G -p TimeoutStopSec=10 -- .venv/bin/python scripts/snap3d_run.py ...`
   (or `ulimit -v` prefix). The run must die inside its own cgroup, never globally —
   a global OOM drags the inference engine down with it and costs the user a ~10-minute
   engine restart plus every live Hermes session.
3. **Cap rollouts**: `sim.py::_rollout`/`drop_frames` must enforce a max-step budget and a
   divergence bailout (e.g. displacement runaway), and record per-case peak RSS
   (`resource.getrusage`) in `report.json`. A pathological case must fail as
   `"timeout"/"diverged"` in the report, not as a kernel kill. *(Not yet implemented — see §6.)*
4. **Treat "unstable/fallen" physics results as a red flag** before scaling: run one case
   with the jail + step cap first, check peak RSS, then batch.
5. **If a background process vanishes with zero output**, suspect the OOM killer: check
   `journalctl -k --since "-2 hours" | grep -i oom` before assuming a code bug.

## 5. Machine context worth knowing

- Engine: container `qwen3.8-flash`, image `vllm-node-b12x`, serves
  `nvidia/Qwen3.8-Flash-Next-FP4-Local` (port 8000). Boot ≈ 9–10 min — **never** conclude
  "provider down" from connection errors during that window.
- Never run a second model load (vLLM recipe, HF download with cache warm, or any
  torch/diffusers job) while the engine is up: the b12x loader prepares A16 weights in
  host RAM and OOMs the same way. One model load at a time.
- `hermes doctor` on Nov 3: profiles other than gaming1 (this one included) still default
  to `local-inference-lab/Qwen3.8-Flash-Next-NVFP4`, which the engine does NOT serve →
  404 unless the session overrides the model (this profile hit exactly that at Nov 1
  17:08). Aligning the profile default was deemed out of scope here; ask the user.

## 6. Status of fixes

| Item | Status |
|---|---|
| gaming1-use-case profile model.default + provider stale (cron 404, failure_streak 118) | **Fixed & verified** (cron `last_status: ok`, streak 0, validation run passed) |
| vLLM recipe / earlyoom wrapper | Working as designed; engine healthy (RestartCount 0) |
| `sim.py` rollout step cap + divergence bailout | **NOT applied** — user deferred; implement before next snap3d batch |
| Memory-jail wrapper for agent batch runs | **NOT applied** — proposed in §4.2 |

## 7. How to verify independently

```bash
# kernel evidence
journalctl -k --since "2026-11-01" | grep -iE "oom|out of memory|killed process"
# container-vs-user fingerprint
cat /proc/$(docker inspect -f '{{.State.Pid}}' qwen3.8-flash)/cgroup   # system.slice/docker-*
# agent transcripts
sqlite3 ~/.hermes/profiles/doodle-to-cad/state.db \
  "SELECT datetime(timestamp,'unixepoch','+1 hour'),role,tool_name,substr(content,1,200)
   FROM messages WHERE timestamp BETWEEN 1793657000 AND 1793668500 ORDER BY timestamp"
```

Full triage runbook lives in the Hermes skill **`vllm-spark-oom-triage`**.
