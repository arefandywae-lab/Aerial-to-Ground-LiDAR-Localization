"""Give never-observed map points (rgb exactly 128 = build_lidar_map's 'unseen' grey) the colour of their nearest coloured neighbours within RADIUS m (mean of up to K).
Points with no coloured neighbour in reach stay grey. Hypothesis under test: the speckled renders come from grey (unseen) points interleaved with coloured ones.
usage: fill_colors.py IN.npz OUT.npz [radius=0.75] [k=5]"""
import sys

import numpy as np
from scipy.spatial import cKDTree

d = np.load(sys.argv[1])
p, n, rgb = d["pts"], d["normals"], d["rgb"].copy()
R = float(sys.argv[3]) if len(sys.argv) > 3 else 0.75
K = int(sys.argv[4]) if len(sys.argv) > 4 else 5
unseen = (rgb == 128).all(1)
tree = cKDTree(p[~unseen])
cols = rgb[~unseen].astype(np.float32)
dist, idx = tree.query(p[unseen], k=K, distance_upper_bound=R)
valid = np.isfinite(dist)
w = valid.astype(np.float32)
c = np.where(valid[..., None], cols[np.minimum(idx, len(cols) - 1)], 0).sum(1) / np.maximum(w.sum(1), 1)[:, None]
has = w.sum(1) > 0
tmp = rgb[unseen]
tmp[has] = np.clip(c[has], 0, 255).astype(np.uint8)
rgb[unseen] = tmp
still = (rgb == 128).all(1)
print(f"unseen before {unseen.mean():.1%}, after fill {still.mean():.1%} (radius {R} m, k {K})")
np.savez(sys.argv[2], pts=p, normals=n, rgb=rgb)
