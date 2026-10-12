"""Does the ~0.4 m vertical translation bias come from a pitch error that PnP compensates with a vertical shift (rotation-translation coupling for distant structure)?
For accepted poses: rotation error vector (axis-angle of R_gt^T R_pred, expressed in the GT camera frame: rx = about the camera x axis = pitch, ry = yaw, rz = roll) and the translation error in the same frame.
Reports mean rotation error per axis, correlation of ty (down) with rx, and the regression slope (m per rad, comparable to the typical scene depth). Also: ground-plane tilt of the map.
usage: rot_trans_coupling.py PREFIX QUERY_SESSION_DIR MAP.npz [gate=80]"""
import sys

import numpy as np
from scipy.spatial.transform import Rotation as Rot

pre, sess, mp = sys.argv[1], sys.argv[2], sys.argv[3]
gate = float(sys.argv[4]) if len(sys.argv) > 4 else 80
P, G, e = np.load(pre + "_pred.npy"), np.load(sess + "/poses.npy"), np.load(pre + "_err.npy")
ok = np.isfinite(P[:, 0, 0]) & (e[:, 2] >= gate) & (e[:, 0] < 5)
Rr = np.einsum("nji,njk->nik", G[ok, :3, :3], P[ok, :3, :3])  # R_gt^T R_pred (error rotation in the GT camera frame)
rv = Rot.from_matrix(Rr).as_rotvec()  # (rx, ry, rz) in rad, camera frame (x right, y down, z forward)
dt = np.einsum("nji,nj->ni", G[ok, :3, :3], P[ok, :3, 3] - G[ok, :3, 3])
deg = np.degrees(rv)
print(f"{ok.sum()} accepted poses; rotation error per camera axis (deg): mean {deg.mean(0).round(3)}  std {deg.std(0).round(3)}   [x = pitch, y = yaw, z = roll]")
print(f"translation error per camera axis (m):   mean {dt.mean(0).round(3)}  std {dt.std(0).round(3)}")
for name, a, b in (("ty(down) vs pitch rx", dt[:, 1], rv[:, 0]), ("tx(right) vs yaw ry", dt[:, 0], rv[:, 1]), ("tz(fwd) vs pitch rx", dt[:, 2], rv[:, 0])):
    c = np.corrcoef(a, b)[0, 1]
    slope = np.polyfit(b, a, 1)[0]
    print(f"  {name:22s}: correlation {c:+.2f}, slope {slope:+.1f} m/rad")
d = np.load(mp)
p, n = d["pts"], d["normals"]
g = (np.abs(n[:, 2]) > 0.9) & (p[:, 2] < 1.0)
A = np.c_[p[g, 0], p[g, 1], np.ones(g.sum())]
coef, *_ = np.linalg.lstsq(A, p[g, 2], rcond=None)
print(f"map ground plane fit z = {coef[0]:+.5f} x {coef[1]:+.5f} y {coef[2]:+.4f}: tilt {np.degrees(np.hypot(coef[0], coef[1])):.3f} deg, z at +-100 m corners: "
      f"{[round(float(coef[0] * x + coef[1] * y + coef[2]), 3) for x, y in ((100, 100), (100, -100), (-100, 100), (-100, -100))]}")
