"""Check the world-frame registration of the drone LiDAR map against geometry we KNOW from the SDF (ground plane z = 0, building boxes with exact footprints and heights).
 ground  : median z of near-horizontal points on streets (far from every building)
 roofs   : per building, 98th percentile of z inside the footprint vs the true height; median difference
 facades : points with a near-horizontal normal within 1 m of a nominal wall plane: signed offset along the wall normal, median per wall orientation
usage: map_bias.py MAP.npz URBAN.sdf"""
import re
import sys

import numpy as np

d = np.load(sys.argv[1])
p, n = d["pts"], d["normals"]
sdf = open(sys.argv[2]).read()
boxes = []
for m in re.finditer(r'<model name="b[^"]*"><static>true</static><pose>([-\d.]+) ([-\d.]+) ([\d.]+).*?<size>([\d.]+) ([\d.]+) ([\d.]+)', sdf, re.S):
    x, y, _, sx, sy, sz = map(float, m.groups())
    boxes.append((x, y, sx, sy, sz))
B = np.array(boxes)
print(f"{len(B)} buildings from the SDF; map {len(p)} points")

def near_building(xy, margin):
    inside = np.zeros(len(xy), bool)
    for x, y, sx, sy, _ in B:
        inside |= (np.abs(xy[:, 0] - x) < sx / 2 + margin) & (np.abs(xy[:, 1] - y) < sy / 2 + margin)
    return inside

g = (np.abs(n[:, 2]) > 0.9) & (p[:, 2] < 1.0) & ~near_building(p[:, :2], 3.0)
print(f"ground: {g.sum()} street points, z median {np.median(p[g, 2]):+.3f} m, mean {p[g, 2].mean():+.3f}, p10/p90 {np.percentile(p[g, 2], 10):+.3f}/{np.percentile(p[g, 2], 90):+.3f}  (truth 0)")
dz = []
for x, y, sx, sy, sz in B:
    m = (np.abs(p[:, 0] - x) < sx / 2 - 0.5) & (np.abs(p[:, 1] - y) < sy / 2 - 0.5) & (p[:, 2] > 2)
    if m.sum() > 30:
        dz.append(np.percentile(p[m, 2], 98) - sz)
dz = np.array(dz)
print(f"roofs: {len(dz)} buildings, map top - true height: median {np.median(dz):+.3f} m, IQR {np.percentile(dz, 25):+.3f}..{np.percentile(dz, 75):+.3f}")
for name, axis, sgn in (("east wall (x+)", 0, +1), ("west wall (x-)", 0, -1), ("north wall (y+)", 1, +1), ("south wall (y-)", 1, -1)):
    offs = []
    for x, y, sx, sy, sz in B:
        c = (x, y)[axis]
        half = (sx, sy)[axis] / 2
        plane = c + sgn * half
        other = 1 - axis
        lo = (x, y)[other] - (sx, sy)[other] / 2 + 1
        hi = (x, y)[other] + (sx, sy)[other] / 2 - 1
        m = (np.abs(n[:, axis]) > 0.9) & (p[:, 2] > 1) & (p[:, 2] < sz - 1) & (p[:, other] > lo) & (p[:, other] < hi) & (np.abs(p[:, axis] - plane) < 1.0)
        if m.sum() > 50:
            offs.append(np.median((p[m, axis] - plane) * sgn))  # positive = map wall bulges outwards
    if offs:
        print(f"{name}: {len(offs)} walls, outward offset of the map surface: median {np.median(offs):+.3f} m, IQR {np.percentile(offs, 25):+.3f}..{np.percentile(offs, 75):+.3f}")
