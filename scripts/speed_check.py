import sys, numpy as np
sys.path.insert(0, "/mnt/a/SlamProject/ros")
import eval_ate
for b in ("/root/data/ud0", "/root/data/w_grid11/ud"):
    r = eval_ate.gt_track(b, "drone", "/gt/drone")
    t, p = (r[0], r[1]) if isinstance(r, tuple) else (r["t"], r["p"])
    t, p = np.asarray(t), np.asarray(p)
    v = np.linalg.norm(np.diff(p[:, :3], axis=0), axis=1) / np.maximum(np.diff(t), 1e-6)
    print(b, "duration", round(t[-1] - t[0], 1), "s, path", round(float(np.sum(np.linalg.norm(np.diff(p[:, :3], axis=0), axis=1))), 1), "m, speed median", round(float(np.median(v)), 2), "p95", round(float(np.percentile(v, 95)), 2), "max", round(float(v.max()), 1))
