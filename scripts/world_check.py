"""Is the drone map of a generated world registered with the true world? Ground-truth robot poses must lie in free space of the map (no obstacle point at robot height within 0.5 m)
and the buildings must be where the SDF says. usage: world_check.py NAME"""
import json, re, sys
import numpy as np
from scipy.spatial import cKDTree
W = sys.argv[1]; D = f"/root/data/w_{W}"
d = np.load(f"{D}/map.npz"); P = d["pts"]
T = np.load(f"{D}/ug_img/poses.npy")[:, :3, 3]
ob = P[(P[:, 2] > 0.6) & (P[:, 2] < 2.0)]; tr = cKDTree(ob[:, :2])
dd, _ = tr.query(T[:, :2])
print(f"{W}: map {len(P)} pts extent {P.min(0).round(0)}..{P.max(0).round(0)}")
print(f"GT robot poses: {len(T)}; distance to nearest map obstacle point: median {np.median(dd):.1f} m, share < 0.5 m: {np.mean(dd < .5):.1%}, share < 1.0 m: {np.mean(dd < 1.0):.1%}")
# SDF building footprints vs map: fraction of map obstacle points (z 2-8 m) falling inside any footprint (+1 m margin)
s = open(f"/root/worlds/{W}.sdf").read()
boxes = []
for m in re.finditer(r'<model name="b[^"]*"><static>true</static><pose>([-\d.]+) ([-\d.]+) ([\d.]+)[^<]*</pose>.*?<size>([\d.]+) ([\d.]+) ([\d.]+)</size>', s, re.S):
    x, y, zc, sx, sy, sz = map(float, m.groups()); boxes.append((x, y, sx, sy))
q = P[(P[:, 2] > 2) & (P[:, 2] < 8)]
inside = np.zeros(len(q), bool)
for x, y, sx, sy in boxes:
    inside |= (np.abs(q[:, 0] - x) <= sx / 2 + 1.0) & (np.abs(q[:, 1] - y) <= sy / 2 + 1.0)
print(f"{len(boxes)} footprints from SDF; map points (z 2-8 m) inside a footprint (+1 m): {inside.mean():.1%}")
# best rigid 2D shift that maximises the share inside (search +-30 m)
best = (inside.mean(), 0, 0)
for dx in range(-30, 31, 3):
    for dy in range(-30, 31, 3):
        ins = np.zeros(len(q), bool)
        for x, y, sx, sy in boxes:
            ins |= (np.abs(q[:, 0] + dx - x) <= sx / 2 + 1.0) & (np.abs(q[:, 1] + dy - y) <= sy / 2 + 1.0)
        if ins.mean() > best[0]: best = (ins.mean(), dx, dy)
print(f"best 2D shift of the map onto the SDF buildings: dx={best[1]} dy={best[2]} (share inside {best[0]:.1%})")
