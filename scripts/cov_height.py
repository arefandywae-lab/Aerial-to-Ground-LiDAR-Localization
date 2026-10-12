"""Colour coverage of the drone map by height band: share of map points that no drone image saw (rgb exactly 128,128,128 in map.npz). Street-level facades are what the ground camera looks at."""
import sys, numpy as np
print(f"{'world':10s} " + " ".join(f"z[{a},{b})".rjust(11) for a, b in ((0, .6), (.6, 3), (3, 8), (8, 20), (20, 70))) + "   n(z 0.6-3 m)")
for w in sys.argv[1:]:
    d = np.load(f"/root/data/w_{w}/map.npz") if w != "ud0" else np.load("/root/data/map_ud0.npz")
    P, C = d["pts"], d["rgb"]; unseen = (C == 128).all(1)
    row = []
    for a, b in ((0, .6), (.6, 3), (3, 8), (8, 20), (20, 70)):
        m = (P[:, 2] >= a) & (P[:, 2] < b); row.append(f"{unseen[m].mean():10.0%} " if m.any() else "        n/a ")
    m = (P[:, 2] >= .6) & (P[:, 2] < 3)
    print(f"{w:10s} " + " ".join(row) + f"   {int(m.sum())}")
