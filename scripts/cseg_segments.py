"""Per street segment of route 2: is the failure retrieval (no close view in MegaLoc top-50) or matching (oracle view nearest the GT pose does not localize), and what is the local map colour coverage?
Segments as in route2_segments.py. usage: cseg_segments.py"""
import numpy as np
W = np.array([[0, -85], [0, -50], [50, -50], [50, 0], [-50, 0], [-50, -50], [0, -50]], float)
names = ["start x=0 north", "y=-50 east (1st)", "x=50 north", "y=0 west (novel)", "x=-50 south", "y=-50 east (2nd)"]
d = np.load("/mnt/a/SlamProject/results/urban/cseg_ug2s.npz")
P = d["pos"][:, :2]
def dseg(p, a, b):
    t = np.clip(np.dot(p - a, b - a) / np.dot(b - a, b - a), 0, 1); return np.linalg.norm(p - (a + t * (b - a)))
seg = np.array([np.argmin([dseg(p, W[i], W[i + 1]) for i in range(6)]) for p in P])
print(f"{'segment':20s} {'n':>4s} | close view exists | top-50 hit (of those) | oracle view localizes | oracle matches median | oracle view gap m | colour fraction median")
for i, nm in enumerate(names):
    m = seg == i
    if not m.any(): continue
    hc = d["has_close"][m]
    print(f"{nm:20s} {m.sum():4d} | {hc.mean():16.1%} | {d['hit50'][m][hc].mean() if hc.any() else float('nan'):20.1%} | {d['oracle_ok'][m].mean():20.1%} | {np.median(d['oracle_matches'][m]):21.0f} | {np.median(d['oracle_dpos'][m]):17.2f} | {np.median(d['colour'][m]):.2f}")
