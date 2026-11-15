# Increment 3-5 evidence: the resumable harness driving a REAL trial against the
# REAL vLLM endpoint + REAL OpenSCAD docker kernel, showing fingerprint,
# tri-state gates and cache replay economics from actual run artifacts.
# Inputs: two campaign dirs produced by scripts/evaluate_quality.py
#   $1 = cold campaign (no cache), $2 = cache campaign (3 trials)
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

cold_dir, warm_dir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])

def verdict(campaign: Path) -> dict:
    cells = sorted(campaign.glob("*/trial-*/verdict.json"))
    assert cells, f"no verdicts under {campaign}"
    return [json.loads(p.read_text()) for p in cells], json.loads((campaign / "environment.json").read_text())

cold, cold_env = verdict(cold_dir)
warm, warm_env = verdict(warm_dir)
c0 = cold[0]
trials = sorted(warm, key=lambda v: v["trial"])

fig = plt.figure(figsize=(13.5, 8.2))
gs = fig.add_gridspec(2, 2, hspace=.35, wspace=.25)

# 1: tri-state gate panel of the real run
ax1 = fig.add_subplot(gs[0, 0])
gates = c0.get("gates_state") or {}
labels, colors = list(gates.keys()), []
palette = {"pass": "#2e7d32", "fail": "#c62828", "unmeasured": "#9e9e9e"}
for i, g in enumerate(labels):
    ax1.barh(i, 1, color=palette.get(gates[g], "#9e9e9e"))
    ax1.text(1.02, i, gates[g], va="center", fontsize=9)
ax1.set_yticks(range(len(labels))); ax1.set_yticklabels(labels, fontsize=9)
ax1.set_xlim(0, 1.4); ax1.set_xticks([])
ax1.set_title(f"gates_state (real run, accepted={c0.get('accepted')}, "
              f"verified={c0.get('verified_acceptance')})", fontsize=10)

# 2: extents vs ground truth (machine numbers)
ax2 = fig.add_subplot(gs[0, 1])
gt = c0.get("gt_extents_mm") or [0, 0, 0]
got = c0.get("extents_mm") or [0, 0, 0]
import numpy as np
x = np.arange(3)
ax2.bar(x - .18, gt, .36, label="ground truth", color="#607d8b")
ax2.bar(x + .18, got, .36, label="generated mesh", color="#00897b")
ax2.set_xticks(x); ax2.set_xticklabels(["X width", "Y depth", "Z height"])
ax2.set_ylabel("mm"); ax2.legend(fontsize=8)
err = [abs(g - t) / max(t, 1) for g, t in zip(got, gt)]
ax2.set_title(f"extents vs GT (rel. error {', '.join(f'{e:.1%}' for e in err)}) "
              f"genus={c0.get('genus_total')} inverted={c0.get('inverted_solids')}", fontsize=10)

# 3: fingerprint (real provenance stamped into result.json)
ax3 = fig.add_subplot(gs[1, 0])
ax3.axis("off")
fp = c0.get("fingerprint") or {}
lines = [f"git_rev: {fp.get('git_rev')}", f"kernel:  {json.dumps(fp.get('kernel'))}",
         f"base_url:{fp.get('base_url')}"] + [f"  prompt {k} = {v}" for k, v in (fp.get("prompts") or {}).items()]
ax3.text(0, 1, "\n".join(lines), fontsize=9, family="monospace", va="top")
ax3.set_title("fingerprint recorded in every result.json", fontsize=10)

# 4: cache replay economics (real wall-clock)
ax4 = fig.add_subplot(gs[1, 1])
names, secs, hits, misses = [], [], [], []
for v in trials:
    cs = v.get("cache_stats") or {}
    tag = f"trial {v['trial']}\nfill (miss={cs.get('misses',0)})" if v["trial"] == 1 else \
          f"trial {v['trial']}\nreplay (hits={cs.get('hits',0)}/miss={cs.get('misses',0)})"
    names.append(tag); secs.append(v.get("wall_seconds") or 0)
    hits.append(cs.get("hits", 0)); misses.append(cs.get("misses", 0))
bars = ax4.bar(range(len(names)), secs, color=["#8d6e63", "#5c6bc0", "#5c6bc0"])
for i, s in enumerate(secs):
    ax4.text(i, s + 2, f"{s:.0f}s", ha="center", fontsize=9)
ax4.set_xticks(range(len(names))); ax4.set_xticklabels(names, fontsize=8)
ax4.set_ylim(0, max(secs) * 1.18)
ax4.set_ylabel("wall seconds"); ax4.set_title("same doodle repeated: identical LLM payloads replay from cache", fontsize=10)

fig.suptitle(f"increment 3-5 evidence — case {c0.get('case')} on {cold_env.get('requested_model')} @ {cold_env.get('model_endpoint')}", fontsize=11)
fig.savefig(out, dpi=110)
print("WROTE", out)
