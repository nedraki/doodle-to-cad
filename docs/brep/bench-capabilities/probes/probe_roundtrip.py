"""Determinism probe for the c1 USD round-trip defect (issue #82).

Builds c1_fillet_enclosure N times from identical recipe bytes and shows the
worker's round-trip guard rejects it every time:
native 374721.415 vs reloaded 390806.37 — difference = two filled
Ø8x80 holes (pi*16*80*2 = 16085.0).

Run: PYTHONPATH=<repo> <worker-venv>/bin/python docs/brep/bench-capabilities/probes/probe_roundtrip.py
"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))       # bench-capabilities (build_capabilities)
sys.path.insert(0, str(HERE.parents[2]))   # repo
from build_capabilities import build
from cases import CASES, _recipe

case = next(c for c in CASES if c['id'] == 'c1_fillet_enclosure')
base = _recipe(case['id'], case['params'], json.loads(json.dumps(case['ops'])), case['output'])
fails = 0
N = int(sys.argv[1]) if len(sys.argv) > 1 else 4
for i in range(N):
    rec = build(base, f"_flake/c1_run{i}")
    if 'construction_error' in rec:
        fails += 1
        print(i, 'REJECTED:', rec['construction_error']['message'][:110])
    else:
        print(i, 'accepted', (rec.get('diagnostics') or {}).get('solid_volume_mm3'))
print(f"{fails}/{N} builds rejected by the worker's own USD round-trip guard")
sys.exit(0 if fails == N else 1)
