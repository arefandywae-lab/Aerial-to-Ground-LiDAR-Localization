"""Which parts of the drone-built LiDAR map did the drone camera colour? (C-coverage, map-based preliminary: LiDAR points, not GT surface.)
Uncoloured points are those with no camera observation (build_lidar_map fills them with 128). Classes from the PCA normal: ground/roof (|nz|>0.8), facade (|nz|<0.3), other.
usage: coverage_urban.py MAP.npz"""
import sys

import numpy as np

d = np.load(sys.argv[1])
p, n, rgb = d["pts"], d["normals"], d["rgb"]
unc = (rgb == 128).all(1)  # exact 128 grey = never seen (a real pixel being exactly (128,128,128) is negligible)
az = np.abs(n[:, 2])
cls = np.where(az > .8, "ground/roof", np.where(az < .3, "facade", "other"))
print(f"{len(p)} points, uncoloured {unc.mean():.1%}")
for c in ("ground/roof", "facade", "other"):
    m = cls == c
    print(f"  {c:11s}: {m.mean():5.1%} of points, uncoloured {unc[m].mean():5.1%}")
fac = cls == "facade"
for lo, hi in ((-1, 0.5), (0.5, 5), (5, 15), (15, 40)):
    m = fac & (p[:, 2] >= lo) & (p[:, 2] < hi)
    if m.any():
        print(f"  facade z {max(lo, 0):>4.1f}-{hi:>4.1f} m: {m.sum():8d} pts, uncoloured {unc[m].mean():5.1%}")
# facade orientation: horizontal normal heading (which way the wall faces)
hd = np.degrees(np.arctan2(n[fac, 1], n[fac, 0])) % 360
for name, a, b in (("faces +x (east)", 315, 45), ("faces +y (north)", 45, 135), ("faces -x (west)", 135, 225), ("faces -y (south)", 225, 315)):
    m = ((hd >= a) & (hd < b)) if a < b else ((hd >= a) | (hd < b))
    print(f"  facade {name:17s}: {m.sum():8d} pts, uncoloured {unc[fac][m].mean():5.1%}")
# street level, where the ground robot sees: z < 3 m, facades
low = fac & (p[:, 2] < 3)
print(f"street-level facade points (z<3 m): {low.sum()}, uncoloured {unc[low].mean():.1%}")
