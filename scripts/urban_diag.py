"""Why does M1 get ~10 % on the urban ground queries?  Three separable factors, measured on the same 205 queries (ug1s):
 D2 retrieval:  is a view close to the GT pose in MegaLoc's top-k?  ("close" = within 4 m and 30 deg: the view grid is 6 m / 45 deg)
 D1 oracle:     LoFTR + PnP against the view nearest to the GT pose (perfect retrieval): does matching/rendering work when retrieval is not the problem?
 D3 appearance: fraction of coloured (non-grey) pixels in the oracle view, and how success depends on it; plus the oracle view's distance/yaw gap.
env as vps/m1lf.py (M1_MAP, M1_ZFAR, M1_VIEWS, M1LF_RETR=megaloc)."""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import torch

sys.path.insert(0, "/mnt/a/SlamProject/vps")
import m1l
import m1lf
from harness import load_session, pose_err
from m1 import shade

QS = os.environ.get("DIAG_QUERIES", "/root/data/ug1s_img")
q = load_session(QS)
M = m1lf.Method()
M.prepare(os.environ.get("DIAG_MAPIMG", "/root/data/ud0_img"))
n = len(M.RT)
pv = np.array([T[:3, 3] for T in M.RT])
hv = np.array([np.degrees(np.arctan2(T[1, 2], T[0, 2])) for T in M.RT])
pq = np.array([T[:3, 3] for T in q["T"]])
hq = np.array([np.degrees(np.arctan2(T[1, 2], T[0, 2])) for T in q["T"]])
dpos = np.linalg.norm(pq[:, None] - pv[None], axis=2)
dyaw = np.abs((hq[:, None] - hv[None] + 180) % 360 - 180)
close = (dpos < 4.0) & (dyaw < 30.0)
oracle = np.argmin(dpos + 0.05 * dyaw, axis=1)
print(f"{len(pq)} queries, {n} views; oracle view gap: position median {np.median(dpos[np.arange(len(pq)), oracle]):.2f} m (max {dpos[np.arange(len(pq)), oracle].max():.2f}), "
      f"yaw median {np.median(dyaw[np.arange(len(pq)), oracle]):.0f} deg (max {dyaw[np.arange(len(pq)), oracle].max():.0f}); queries with any view within 4 m/30 deg: {close.any(1).mean():.1%}")

# D2 retrieval recall
with ThreadPoolExecutor(8) as ex:
    imgs = list(ex.map(cv2.imread, q["images"]))
with torch.inference_mode():
    fq = torch.cat([m1lf.mega_embed(M.mega, imgs[i:i + 32]) for i in range(0, len(imgs), 32)])
rank = torch.argsort(fq @ M.desc.T, dim=1, descending=True).cpu().numpy()
has = close.any(1)
print("D2 retrieval (queries that have a close view): " + " | ".join(
    f"R@{k} {np.take_along_axis(close, rank[:, :k], 1).any(1)[has].mean():.1%}" for k in (1, 5, 10, 20, 50, 100)))

# D1 oracle matching + D3 appearance
rows = []
with torch.no_grad():
    for i, img in enumerate(imgs):
        j = int(oracle[i])
        qg = m1l.gray_t(img)
        M._qf = None
        k0, k1 = M._kp(qg, M._g(j), vi=j if m1lf.MATCHER == "disklg" else None)  # the configured matcher (M1LF_MATCHER)
        nconf = len(k0)
        T, info = M._pose([(nconf, j, k0, k1)], q["K"])
        dt, dr = pose_err(T, q["T"][i]) if T is not None else (np.inf, np.inf)
        rows.append((nconf, info.get("inliers", 0), dt, dr))
rows = np.array(rows)
ok55 = (rows[:, 2] <= 5) & (rows[:, 3] <= 10)
ok05 = (rows[:, 2] <= .5) & (rows[:, 3] <= 5)
print(f"D1 oracle retrieval: pose returned {np.isfinite(rows[:, 2]).mean():.1%} | within (5 m,10 deg) {ok55.mean():.1%} | within (0.5 m,5 deg) {ok05.mean():.1%} | median confident matches {np.median(rows[:, 0]):.0f}, median inliers {np.median(rows[:, 1]):.0f}")
# colour fraction of the oracle views (re-render the 205 chosen views in colour)
d = np.load(m1l.LIDAR_MAP)
Pg = torch.from_numpy(d["pts"]).float().cuda()
col = []
for i in range(len(pq)):
    im, _ = shade(m1lf.render_gpu(Pg, M.RT[int(oracle[i])], q["K"]), d["rgb"])
    spread = im.astype(int).max(2) - im.astype(int).min(2)
    nonsky = ~(np.abs(im.astype(int) - 218).max(2) < 3)
    col.append(float(((spread > 12) & nonsky).sum() / max(nonsky.sum(), 1)))
col = np.array(col)
for lo, hi in ((0, .1), (.1, .25), (.25, .5), (.5, 1.01)):
    m = (col >= lo) & (col < hi)
    if m.any():
        print(f"D3 oracle view colour fraction {lo:.2f}-{hi:.2f}: n={int(m.sum()):3d}, within (5 m,10 deg) {ok55[m].mean():.1%}, median confident matches {np.median(rows[m, 0]):.0f}")
print(f"D3 median coloured fraction of oracle views {np.median(col):.2f}")
hit50 = np.take_along_axis(close, rank[:, :50], 1).any(1)  # a close view is among the MegaLoc top-50
out = os.environ.get("DIAG_OUT")
if out:
    np.savez(out, hit50=hit50, has_close=has, oracle_ok=ok55, oracle_matches=rows[:, 0], oracle_inl=rows[:, 1], oracle_dpos=dpos[np.arange(len(pq)), oracle], colour=col, pos=pq)
    print("saved", out)
