"""D0 (zero viewpoint gap): render the urban LiDAR map at each query's OWN GT pose and match the real query image against that render with LoFTR, then PnP from the render's provenance.
If this still fails, the cause is the appearance gap between real street-level images and the map renders (not retrieval, not view-grid density).
Also reports a render-quality proxy and saves side-by-side examples. env as vps/m1lf.py (M1_MAP, M1_ZFAR)."""
import sys

import cv2
import numpy as np
import torch
from kornia.feature import LoFTR

sys.path.insert(0, "/mnt/a/SlamProject/vps")
import m1l
import m1lf
from harness import load_session, pose_err
from m1 import shade

q = load_session("/root/data/ug1s_img")
d = np.load(m1l.LIDAR_MAP)
Pg = torch.from_numpy(d["pts"]).float().cuda()


class Shim(m1l.Method):  # reuse _pose without prepare()
    pass


M = Shim()
M.K, M.P = q["K"], d["pts"].astype(np.float64)
M.loftr = LoFTR(pretrained="outdoor").cuda().eval()
rows, examples = [], []
with torch.no_grad():
    for i, p in enumerate(q["images"]):
        img = cv2.imread(p)
        T = q["T"][i]
        rend, ids = shade(m1lf.render_gpu(Pg, T, q["K"]), d["rgb"])
        M.ids, M.RT = [ids], [T]
        o = M.loftr({"image0": m1l.gray_t(img), "image1": m1l.gray_t(rend)})
        ok = o["confidence"] > m1l.CONF
        n = int(ok.sum())
        Tp, info = M._pose([(n, 0, o["keypoints0"][ok].cpu().numpy(), o["keypoints1"][ok].cpu().numpy())], q["K"])
        dt, dr = pose_err(Tp, T) if Tp is not None else (np.inf, np.inf)
        filled = float((ids >= 0).mean())
        rows.append((n, info.get("inliers", 0), dt, dr, filled))
        if i in (10, 60, 110, 160):
            examples.append(np.hstack([img, rend]))
rows = np.array(rows)
ok55 = (rows[:, 2] <= 5) & (rows[:, 3] <= 10)
ok05 = (rows[:, 2] <= .5) & (rows[:, 3] <= 5)
print(f"D0 render at the query's GT pose, {len(rows)} queries: confident matches median {np.median(rows[:, 0]):.0f} (p90 {np.percentile(rows[:, 0], 90):.0f}), "
      f"inliers median {np.median(rows[:, 1]):.0f} | pose returned {np.isfinite(rows[:, 2]).mean():.1%} | within (5 m,10 deg) {ok55.mean():.1%} | within (0.5 m,5 deg) {ok05.mean():.1%} | "
      f"render pixels with a map point (after hole fill) median {np.median(rows[:, 4]):.2f}")
cv2.imwrite("/mnt/a/SlamProject/docs/figures/urban_d0_examples.png", np.vstack(examples))
