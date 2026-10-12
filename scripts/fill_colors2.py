"""Class-aware colour fill: a never-observed point (rgb exactly 128) takes the mean colour of up to K coloured neighbours within RADIUS m whose surface orientation agrees
(|n . n'| > COS), so road points do not inherit facade colours at building bases and vice versa. Points without such neighbours stay grey.
usage: fill_colors2.py IN.npz OUT.npz [radius=1.0] [k=16] [cos=0.8]"""
import sys

import numpy as np
from scipy.spatial import cKDTree

d = np.load(sys.argv[1])
p, n, rgb = d["pts"], d["normals"], d["rgb"].copy()
R = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
K = int(sys.argv[4]) if len(sys.argv) > 4 else 16
COS = float(sys.argv[5]) if len(sys.argv) > 5 else 0.8
unseen = (rgb == 128).all(1)
si = np.where(~unseen)[0]
ui = np.where(unseen)[0]
tree = cKDTree(p[si])
dist, idx = tree.query(p[ui], k=K, distance_upper_bound=R)
valid = np.isfinite(dist)
idx = np.minimum(idx, len(si) - 1)
nb = si[idx]  # (U,K) indices into the full arrays
agree = np.abs(np.einsum("uj,ukj->uk", n[ui], n[nb])) > COS
w = (valid & agree).astype(np.float32)
c = (rgb[nb].astype(np.float32) * w[..., None]).sum(1) / np.maximum(w.sum(1), 1)[:, None]
has = w.sum(1) > 0
tmp = rgb[ui]
tmp[has] = np.clip(c[has], 0, 255).astype(np.uint8)
rgb[ui] = tmp
print(f"unseen before {unseen.mean():.1%}, after class-aware fill {(rgb == 128).all(1).mean():.1%} (radius {R} m, k {K}, |cos| > {COS})")
np.savez(sys.argv[2], pts=p, normals=n, rgb=rgb)
