"""Geometric verification of a generated STL vs benchmark ground truth.

Parses a binary STL, reports extents and, via the Euler characteristic,
the topological genus — for a connected watertight solid, each through-hole
in a plate adds 1 to the genus (chi = V - E + F = 2 - 2g).

Usage: python scripts/verify_stl.py <model.stl> [--target-max 100]
"""
import struct
import sys

import numpy as np


def load_stl(path):
    with open(path, "rb") as f:
        head = f.read(512)
    if head.lstrip().startswith(b"solid") and b"facet" in head:  # ASCII STL
        tris = []
        cur = []
        for line in open(path, "r", errors="ignore"):
            t = line.split()
            if t and t[0] == "vertex":
                cur.append([float(x) for x in t[1:4]])
            elif t and t[0] == "endfacet":
                if len(cur) == 3:
                    tris.append(cur)
                cur = []
        return np.array(tris, dtype=np.float32)
    with open(path, "rb") as f:
        f.read(80)
        (n,) = struct.unpack("<I", f.read(4))
        data = np.frombuffer(f.read(n * 50), dtype=np.uint8).reshape(n, 50)
    tris = data[:, 12:48].copy().view(np.float32).reshape(n, 3, 3)
    return tris


def main():
    path = sys.argv[1]
    target = float(sys.argv[sys.argv.index("--target-max") + 1]) if "--target-max" in sys.argv else None
    tris = load_stl(path)
    v = tris.reshape(-1, 3)
    key = np.round(v, 6)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    V = len(uniq)
    tri = inv.reshape(-1, 3)
    faces = {tuple(sorted(t)) for t in tri}
    F = len(tri)
    edges = set()
    for t in tri:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            edges.add((min(a, b), max(a, b)))
    E = len(edges)
    chi = V - E + F
    genus = (2 - chi) // 2 if (2 - chi) % 2 == 0 else None
    # closed 2-manifold: every edge shared by exactly 2 faces -> 3F == 2E
    edge_defect = abs(3 * F - 2 * E)
    # connectivity via union-find over edges
    parent = list(range(V))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb: parent[ra] = rb
    components = len({find(i) for i in range(V)})
    ext = uniq.max(axis=0) - uniq.min(axis=0)
    print(f"triangles={F} V={V} E={E} chi={chi}")
    print(f"genus={genus}  (through-holes in a simply-connected plate = genus)")
    print(f"components={components}  edge_defect={edge_defect}  (0 = closed manifold)")
    print(f"extents_mm=({ext[0]:.2f}, {ext[1]:.2f}, {ext[2]:.2f})")
    if target:
        print(f"target_max_mm={target}  max_extent={ext.max():.2f}")
        ref = np.array([80.0, 50.0, 100.0])  # benchmark 001 reference ratio
        got = np.sort(ext)[::-1]
        want = np.sort(ref * (target / ref.max()))[::-1]
        rel = np.abs(got - want) / want
        print(f"ratio_vs_reference rel_err=({rel[0]:.3f}, {rel[1]:.3f}, {rel[2]:.3f})")
        print(f"PASS={bool((rel < 0.05).all())}")


if __name__ == "__main__":
    main()
