"""Confirm: wrong high-inlier poses are cheirality flips (inlier points behind the camera). Runs m1l on a few failing queries."""
import sys

import cv2
import numpy as np
import torch

sys.path.insert(0, "/mnt/a/SlamProject/vps")
import m1l
from harness import load_session

cv2.setRNGSeed(0)
M = m1l.Method()
M.prepare("/root/data/s0_img")
q = load_session("/root/data/q1_img")
for qi in (8, 10, 12, 58, 77, 100):
    img = cv2.imread(q["images"][qi])
    with torch.no_grad():
        qq = m1l.gray_t(img)
        res = []
        for i, g in enumerate(M.g):
            o = M.loftr({"image0": qq, "image1": g})
            ok = o["confidence"] > m1l.CONF
            res.append((int(ok.sum()), i, o["keypoints0"][ok].cpu().numpy(), o["keypoints1"][ok].cpu().numpy()))
    res.sort(key=lambda r: -r[0])
    p2, p3 = [], []
    for n, i, a, b in res[:m1l.TOPK]:
        pid = M.ids[i][np.round(b[:, 1]).astype(int).clip(0, 479), np.round(b[:, 0]).astype(int).clip(0, 639)]
        v = pid >= 0
        p2.append(a[v])
        p3.append(M.P[pid[v]])
    p2, p3 = np.concatenate(p2).astype(np.float64), np.concatenate(p3)
    ok, rv, tv, inl = cv2.solvePnPRansac(p3, p2, M.K, None, iterationsCount=2000, reprojectionError=4.0, flags=cv2.SOLVEPNP_EPNP)
    i = inl.ravel()
    R, _ = cv2.Rodrigues(rv)
    zc = (p3[i] @ R.T + tv.ravel())[:, 2]
    Tgt = np.linalg.inv(q["T"][qi])  # world->cam GT
    zg = (p3 @ Tgt[:3, :3].T + Tgt[:3, 3])[:, 2]
    pr = (p3 @ Tgt[:3, :3].T + Tgt[:3, 3]) @ M.K.T
    rep = np.linalg.norm(pr[:, :2] / pr[:, 2:3] - p2, axis=1)
    cam_pos = -R.T @ tv.ravel()
    print(f"q{qi}: matches {len(p2)} inliers {len(i)} | PnP: frac inliers z<0 = {np.mean(zc<0):.2f}, cam pos {cam_pos.round(1)} | "
          f"GT cam pos {q['T'][qi][:3,3].round(1)} | under GT pose: frac matches z>0 {np.mean(zg>0):.2f}, reproj<4px {np.mean((rep<4)&(zg>0)):.2f}")
