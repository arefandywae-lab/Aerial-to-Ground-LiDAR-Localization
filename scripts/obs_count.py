"""How many drone images actually see each street-level map point? Decides whether any image-trained map (M3 Gaussian splatting, M4 scene-coordinate regression, M0) can know the street-level facades.
Same visibility test as vps/build_lidar_map.colorize (z-buffer with tolerance), counting observations instead of averaging colours; the count is also saved to OUT.npy.
usage: obs_count.py MAP.npz DRONE_IMG_DIR OUT.npy"""
import sys

import cv2
import numpy as np

sys.path.insert(0, "/mnt/a/SlamProject/vps")
from harness import load_session

d = np.load(sys.argv[1])
p, n = d["pts"].astype(np.float64), d["normals"]
s = load_session(sys.argv[2])
K = s["K"]
h, w = 480, 640
cnt = np.zeros(len(p), np.int16)
tol = 0.15
for i, T in enumerate(s["T"]):
    pc = (p - T[:3, 3]) @ T[:3, :3]
    z = pc[:, 2]
    u = np.round(K[0, 0] * pc[:, 0] / np.maximum(z, 1e-6) + K[0, 2]).astype(int)
    v = np.round(K[1, 1] * pc[:, 1] / np.maximum(z, 1e-6) + K[1, 2]).astype(int)
    ok = (z > 0.3) & (u >= 1) & (u < w - 1) & (v >= 1) & (v < h - 1)
    idx = np.where(ok)[0]
    zb = np.full((h, w), np.inf)
    for du in (-1, 0, 1):
        for dv in (-1, 0, 1):
            np.minimum.at(zb, (v[idx] + dv, u[idx] + du), z[idx])
    vis = idx[z[idx] <= zb[v[idx], u[idx]] + tol]
    cnt[vis] += 1
np.save(sys.argv[3], cnt)
fac = np.abs(n[:, 2]) < 0.3
for name, m in (("all points", np.ones(len(p), bool)), ("ground/roof (|nz|>0.8)", np.abs(n[:, 2]) > 0.8), ("facade z<3 m (what a ground robot sees)", fac & (p[:, 2] < 3)),
                ("facade 3-10 m", fac & (p[:, 2] >= 3) & (p[:, 2] < 10)), ("facade >= 10 m", fac & (p[:, 2] >= 10))):
    c = cnt[m]
    print(f"{name:42s} n={m.sum():8d}  seen by 0 images {np.mean(c == 0):5.1%} | 1 {np.mean(c == 1):5.1%} | 2 {np.mean(c == 2):5.1%} | 3-5 {np.mean((c >= 3) & (c <= 5)):5.1%} | >=6 {np.mean(c >= 6):5.1%} | median {np.median(c):.0f}")
