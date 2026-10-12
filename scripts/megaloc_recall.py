"""A33 stage 2: MegaLoc global descriptors (8448-d, L2-normalised) over the same rendered views and queries as scripts/retrieval_recall.py -> recall@k under the same criterion
(database view within POS_TOL m and YAW_TOL deg of the query's GT pose). Forward-pass time is measured on the GPU with synchronisation, excluding image decoding.
env: M1_MAP, M1L_STEP, M1LF_YAWS as in vps/m1lf.py. The model is loaded from the torch.hub cache (gmberton/MegaLoc + Hugging Face gberton/MegaLoc)."""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, "/mnt/a/SlamProject/vps")
import m1
import m1lf
from harness import load_session

POS_TOL, YAW_TOL = 1.5, 45.0
step = int(os.environ.get("M1L_STEP", 6))
yaws = [float(v) for v in os.environ.get("M1LF_YAWS", "0,90,180,270").split(",")]
H, W = 238, 322  # multiples of 14, keeps the 4:3 aspect (the model resizes to multiples of 14 itself)
MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1).cuda()
STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1).cuda()

model = torch.hub.load("gmberton/MegaLoc", "get_trained_model", trust_repo=True).cuda().eval()


def prep(bgr_list):
    x = torch.from_numpy(np.stack([cv2.cvtColor(b, cv2.COLOR_BGR2RGB) for b in bgr_list])).cuda().permute(0, 3, 1, 2).float() / 255
    x = F.interpolate(x, size=(H, W), mode="bilinear", antialias=True, align_corners=False)
    return (x - MEAN) / STD


@torch.inference_mode()
def embed(bgr_list, bs=32):
    out, t = [], 0.0
    for i in range(0, len(bgr_list), bs):
        x = prep(bgr_list[i:i + bs])
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        out.append(model(x))
        torch.cuda.synchronize()
        t += time.perf_counter() - t0
    return torch.cat(out), t


s = load_session("/root/data/s0v2_img")
d = np.load(m1.LIDAR_MAP)
Pg = torch.from_numpy(d["pts"]).float().cuda()
views, imgs = [], []
for T0 in s["T"][::step]:
    for yaw in yaws:
        T = T0.copy()
        c, sn = np.cos(np.radians(yaw)), np.sin(np.radians(yaw))
        T[:3, :3] = np.array([[c, -sn, 0], [sn, c, 0], [0, 0, 1]]) @ T0[:3, :3]
        views.append(T)
        imgs.append(m1.shade(m1lf.render_gpu(Pg, T, s["K"]), d["rgb"])[0])
fdb, tdb = embed(imgs)
heading = lambda T: np.degrees(np.arctan2(T[1, 2], T[0, 2]))
hdb = np.array([heading(T) for T in views])
pdb = np.array([T[:3, 3] for T in views])
print(f"database {len(views)} renders; MegaLoc forward {1e3*tdb/len(views):.1f} ms/image (batched, GPU-synchronised)")
for q in ("q1v2", "q2v2", "q3v2"):
    qs = load_session(f"/root/data/{q}_img")
    with ThreadPoolExecutor(8) as ex:
        qi = list(ex.map(cv2.imread, qs["images"]))
    fq, tq = embed(qi)
    pq = np.array([T[:3, 3] for T in qs["T"]])
    hq = np.array([heading(T) for T in qs["T"]])
    ok = (np.linalg.norm(pq[:, None] - pdb[None], axis=2) < POS_TOL) & (np.abs((hq[:, None] - hdb[None] + 180) % 360 - 180) < YAW_TOL)
    has = ok.any(1)
    rank = torch.argsort(fq @ fdb.T, dim=1, descending=True).cpu().numpy()
    r = [f"R@{k} {np.take_along_axis(ok, rank[:, :k], 1).any(1)[has].mean():.1%}" for k in (1, 5, 10, 20, 50)]
    print(f"{q}: {len(pq)} queries ({int(has.sum())} answerable, bound {has.mean():.1%}), forward {1e3*tq/len(pq):.1f} ms/image | " + " | ".join(r))
