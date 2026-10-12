"""V1 step 1 (GPU, once): run the single-frame localizer over a whole session and keep, per frame, the PnP pose and the inlier correspondences (2D pixels, 3D map points) so that
multi-frame solutions can be computed offline on the CPU for several odometry-noise levels. Same prior simulation as the harness (GT xy + N(0, PRIOR_SIGMA^2)).
usage: seq_collect.py QUERY_SESSION OUT.npz   env as vps/m1lf.py + PRIOR_SIGMA, M1LF_PRIOR_R"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, "/mnt/a/SlamProject/vps")
import m1lf
from harness import load_session

q = load_session(sys.argv[1])
M = m1lf.Method()
M.prepare("/root/data/ud0_img")
sigma = float(os.environ.get("PRIOR_SIGMA", 5))
rng = np.random.default_rng(12345)
poses, p2s, p3s, inls, hyps, hinl = [], [], [], [], [], []
for i, path in enumerate(q["images"]):
    img = cv2.imread(path)
    prior = q["T"][i][:2, 3] + rng.normal(0, sigma, 2)
    M.last_corr = None
    T, info = M.localize(img, q["K"], prior_xy=None if os.environ.get("NO_PRIOR") == "1" else prior)  # NO_PRIOR=1: global retrieval (for the kidnapped-start MCL test)
    poses.append(T if T is not None else np.full((4, 4), np.nan))
    inls.append(info.get("inliers", 0))
    c = getattr(M, "last_corr", None)
    p2s.append(c[0] if (T is not None and c is not None) else np.zeros((0, 2)))
    p3s.append(c[1] if (T is not None and c is not None) else np.zeros((0, 3)))
    h = getattr(M, "last_hyp", None)
    if h is not None:  # multi-hypothesis (M1LF_HYP=N): padded to N poses per frame
        n_h = int(os.environ["M1LF_HYP"])
        hyps.append(np.array([x[0] for x in h] + [np.full((4, 4), np.nan)] * (n_h - len(h))))
        hinl.append(np.array([x[1] for x in h] + [0] * (n_h - len(h))))
    if i % 50 == 0:
        print(i, len(q["images"]), flush=True)
extra = dict(hyp=np.array(hyps), hinl=np.array(hinl)) if hyps else {}
np.savez(sys.argv[2], poses=np.array(poses), gt=q["T"], inl=np.array(inls), K=q["K"],
         p2=np.array(p2s, dtype=object), p3=np.array(p3s, dtype=object), **extra)
print("saved", sys.argv[2])
