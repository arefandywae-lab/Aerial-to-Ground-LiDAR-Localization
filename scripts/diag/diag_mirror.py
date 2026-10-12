"""Test: wrong poses = point reflection of the GT camera through the room centre (180 deg about the vertical axis at the origin)?
If so, pos error ~= 2*|xy_gt|. CPU only."""
import numpy as np

Q = np.load("/root/data/q1_img/poses.npy")
e = np.load("/mnt/a/SlamProject/results/m1l_q1_s0_err.npy")
dt, dr = e[:, 0], e[:, 1]
wrong = np.isfinite(dt) & ((dt > 5) | (dr > 10))
r = np.linalg.norm(Q[:, :2, 3], axis=1)
ratio = dt[wrong] / (2 * r[wrong])
print(f"wrong n={wrong.sum()}: pos_err / (2*|xy_gt|) median {np.median(ratio):.2f}, within 0.9-1.1: {np.mean((ratio>.9)&(ratio<1.1)):.2f}")
print("wrong rot err (deg) median %.0f, within 170-180: %.2f" % (np.median(dr[wrong]), np.mean(dr[wrong] > 170)))
ok = np.isfinite(dt) & ~wrong
print(f"correct poses |xy_gt| median {np.median(r[ok]):.1f} m | wrong poses |xy_gt| median {np.median(r[wrong]):.1f} m")
