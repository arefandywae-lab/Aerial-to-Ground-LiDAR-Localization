"""A33 stage 1 (no download): vector retrieval over rendered views using pooled LoFTR-backbone features.
Does the correct render appear in the top-k of a cosine-similarity search? "Correct render" = a database view within POS_TOL m of the query and within YAW_TOL deg of its heading.
Database = renders of the room map at the mapping poses (STEP) x yaws; queries = q1v2 (same direction), q2v2 (reversed), q3v2 (spins).
usage: retrieval_recall.py [grid=2x2,3x4,...]   env: M1_MAP, M1L_STEP, M1LF_YAWS (as vps/m1lf.py)"""
import os
import sys
import time

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from kornia.feature import LoFTR

sys.path.insert(0, "/mnt/a/SlamProject/vps")
import m1
import m1lf
from harness import load_session

POS_TOL, YAW_TOL = 1.5, 45.0
GRIDS = [tuple(int(v) for v in g.split("x")) for g in (sys.argv[1] if len(sys.argv) > 1 else "1x1,2x2,3x4").split(",")]
step = int(os.environ.get("M1L_STEP", 6))
yaws = [float(v) for v in os.environ.get("M1LF_YAWS", "0,90,180,270").split(",")]

s = load_session("/root/data/s0v2_img")
d = np.load(m1.LIDAR_MAP)
Pg = torch.from_numpy(d["pts"]).float().cuda()
net = LoFTR(pretrained="outdoor").cuda().eval()


def gray(img):
    return torch.from_numpy(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)).float().div(255)[None, None]


@torch.no_grad()
def feats(batch):  # list of (1,1,H,W) cpu tensors -> (B,256,H/8,W/8) coarse backbone features
    out = []
    for i in range(0, len(batch), 16):
        fc, _ = net.backbone(torch.cat(batch[i:i + 16]).cuda())
        out.append(fc)
    return torch.cat(out)


def descr(fc, grid):
    v = F.adaptive_avg_pool2d(fc, grid).flatten(2)  # (B,256,cells)
    v = F.normalize(v, dim=1)  # per-cell L2 so cells weigh equally
    return F.normalize(v.flatten(1), dim=1)


t0 = time.time()
views, rgbs = [], []
for T0 in s["T"][::step]:
    for yaw in yaws:
        T = T0.copy()
        c, sn = np.cos(np.radians(yaw)), np.sin(np.radians(yaw))
        T[:3, :3] = np.array([[c, -sn, 0], [sn, c, 0], [0, 0, 1]]) @ T0[:3, :3]
        views.append(T)
        rgbs.append(gray(m1.shade(m1lf.render_gpu(Pg, T, s["K"]), d["rgb"])[0]))
print(f"database: {len(views)} renders in {time.time()-t0:.0f} s")
fdb = feats(rgbs)
heading = lambda T: np.degrees(np.arctan2(T[1, 2], T[0, 2]))
hdb = np.array([heading(T) for T in views])
pdb = np.array([T[:3, 3] for T in views])
ddb = {g: descr(fdb, g) for g in GRIDS}
print("descriptor dims:", {f"{g[0]}x{g[1]}": ddb[g].shape[1] for g in GRIDS})
for q in ("q1v2", "q2v2", "q3v2"):
    qs = load_session(f"/root/data/{q}_img")
    t0 = time.time()
    fq = feats([gray(cv2.imread(p)) for p in qs["images"]])
    tq = time.time() - t0
    pq = np.array([T[:3, 3] for T in qs["T"]])
    hq = np.array([heading(T) for T in qs["T"]])
    ok = (np.linalg.norm(pq[:, None] - pdb[None], axis=2) < POS_TOL) & (np.abs((hq[:, None] - hdb[None] + 180) % 360 - 180) < YAW_TOL)
    has = ok.any(1)
    print(f"\n{q}: {len(pq)} queries, {int(has.sum())} have a correct render in the database (upper bound {has.mean():.1%}); backbone {1e3*tq/len(pq):.0f} ms/query")
    for g in GRIDS:
        sim = descr(fq, g) @ ddb[g].T
        rank = torch.argsort(sim, dim=1, descending=True).cpu().numpy()
        r = []
        for k in (1, 5, 10, 20, 50):
            hit = np.take_along_axis(ok, rank[:, :k], 1).any(1)
            r.append(f"R@{k} {hit[has].mean():.1%}")
        print(f"  grid {g[0]}x{g[1]}: " + " | ".join(r))
