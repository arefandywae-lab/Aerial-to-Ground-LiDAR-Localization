"""AUDIT: how accurate are the 3D points the pipeline pairs with render pixels? Ground truth = exact SDF geometry (ground plane z = 0, axis-aligned building boxes), ray-cast per pixel.
For GT query poses: render the map like the pipeline does (GPU z-buffer, hole fill), take the provenance point of every sampled pixel, intersect the pixel's viewing ray with the TRUE scene and compare:
  raw      : the provenance point (voxel centre of the nearest map point)
  plane    : the pixel ray intersected with the plane of that point (map normal)  [the M1_PLANE variant]
Errors are split by pixel type (directly splatted vs hole-filled), by range, and ground vs facade; the signed vertical error on ground pixels tests the ~+0.3 m vertical offset seen in poses.
usage: audit_provenance.py QUERY_SESSION N_POSES   env: M1_MAP M1_ZFAR M1_SPLAT M1_RMAX"""
import re
import sys

import numpy as np
import torch

sys.path.insert(0, "/mnt/a/SlamProject/vps")
import m1
import m1lf
from harness import load_session

q = load_session(sys.argv[1])
npose = int(sys.argv[2])
d = np.load(m1.LIDAR_MAP)
P, N = d["pts"].astype(np.float64), d["normals"].astype(np.float64)
Pg = torch.from_numpy(d["pts"]).float().cuda()
K = q["K"]
sdf = open("/root/worlds/urban.sdf").read()
B = np.array([[float(v) for v in m.groups()] for m in re.finditer(
    r'<model name="b[^"]*"><static>true</static><pose>([-\d.]+) ([-\d.]+) [\d.]+.*?<size>([\d.]+) ([\d.]+) ([\d.]+)', sdf, re.S)])  # x y sx sy sz
lo = np.c_[B[:, 0] - B[:, 2] / 2, B[:, 1] - B[:, 3] / 2, np.zeros(len(B))]
hi = np.c_[B[:, 0] + B[:, 2] / 2, B[:, 1] + B[:, 3] / 2, B[:, 4]]


def raycast(o, D):
    """nearest hit of rays o + t D (D: (n,3)) with the ground plane and the boxes -> t (inf if none), kind (0 ground, 1 box)"""
    t = np.full(len(D), np.inf)
    kind = np.zeros(len(D), int)
    with np.errstate(divide="ignore", invalid="ignore"):
        tg = -o[2] / D[:, 2]
        ok = tg > 0
        t[ok] = tg[ok]
        for a, b in zip(lo, hi):
            t1, t2 = (a - o) / D, (b - o) / D
            tn = np.max(np.minimum(t1, t2), axis=1)
            tf = np.min(np.maximum(t1, t2), axis=1)
            hit = (tn <= tf) & (tn > 0.05) & (tn < t)
            t[hit], kind[hit] = tn[hit], 1
    return t, kind


rows = []
idxs = np.linspace(0, len(q["T"]) - 1, npose).astype(int)
for i in idxs:
    T = q["T"][i]
    direct = m1lf.render_gpu(Pg, T, K)
    _, ids = m1.shade(direct.copy(), d["rgb"])
    filled = (direct < 0) & (ids >= 0)
    vv, uu = np.mgrid[0:480:6, 0:640:6]
    vv, uu = vv.ravel(), uu.ravel()
    pid = ids[vv, uu]
    ok = pid >= 0
    vv, uu, pid = vv[ok], uu[ok], pid[ok]
    fl = filled[vv, uu]
    Dc = np.c_[(uu - K[0, 2]) / K[0, 0], (vv - K[1, 2]) / K[1, 1], np.ones(len(uu))]
    D = Dc @ T[:3, :3].T
    o = T[:3, 3]
    t, kind = raycast(o, D)
    good = np.isfinite(t) & (t < 200)
    Xt = o + t[:, None] * D
    Xr = P[pid]
    nn = N[pid]
    nd = np.einsum("ij,ij->i", nn, D)
    with np.errstate(divide="ignore", invalid="ignore"):
        tp = np.einsum("ij,ij->i", nn, Xr - o) / nd
    Xp = np.where((np.abs(nd) / np.linalg.norm(D, axis=1) > 0.25)[:, None] & np.isfinite(tp)[:, None] & (np.abs(tp[:, None] * D + o - Xr).max(1) < 0.5)[:, None], o + tp[:, None] * D, Xr)
    rng_ = t * np.linalg.norm(D, axis=1)
    Xc = (Xr - o) @ T[:3, :3]  # provenance point in the GT camera frame: where would it appear in the image?
    du = K[0, 0] * Xc[:, 0] / Xc[:, 2] + K[0, 2] - uu
    dv = K[1, 1] * Xc[:, 1] / Xc[:, 2] + K[1, 2] - vv
    for j in np.where(good)[0]:
        rows.append((rng_[j], kind[j], fl[j], *(Xr[j] - Xt[j]), *(Xp[j] - Xt[j]), du[j], dv[j], Xc[j, 2] - (Xt[j] - o) @ T[:3, 2]))
r = np.array(rows)
rng_, kind, fl = r[:, 0], r[:, 1].astype(int), r[:, 2].astype(bool)
er, ep = r[:, 3:6], r[:, 6:9]
du, dv, ddep = r[:, 9], r[:, 10], r[:, 11]
print(f"{len(r)} sampled pixels from {len(idxs)} GT poses with a provenance point and a true hit")
def line(name, m):
    if m.sum() < 30:
        return
    print(f"  {name:34s} n={m.sum():6d} | raw: median |err| {np.median(np.linalg.norm(er[m], axis=1)):.3f} m, p90 {np.percentile(np.linalg.norm(er[m], axis=1), 90):.3f}, signed dz {np.median(er[m, 2]):+.3f}"
          f" | plane: median {np.median(np.linalg.norm(ep[m], axis=1)):.3f}, p90 {np.percentile(np.linalg.norm(ep[m], axis=1), 90):.3f}, dz {np.median(ep[m, 2]):+.3f}")
line("all", np.ones(len(r), bool))
line("directly splatted pixels", ~fl)
line("hole-filled pixels", fl)
line("ground (z=0 plane)", kind == 0)
line("facade/roof (boxes)", kind == 1)
for a, b in ((0, 5), (5, 15), (15, 40), (40, 200)):
    line(f"range {a}-{b} m", (rng_ >= a) & (rng_ < b))
print(f"share of sampled pixels that are hole-filled: {fl.mean():.1%}")
print(f"ground pixels, raw signed vertical error: mean {er[kind == 0, 2].mean():+.3f} m, median {np.median(er[kind == 0, 2]):+.3f} m (truth 0)")

print()
print("REPROJECTION of the provenance point under the GT pose (what PnP actually sees): offset to the pixel it was assigned to, in pixels; depth error along the camera z axis in metres")
def rl(name, m):
    if m.sum() < 30:
        return
    print(f"  {name:34s} n={m.sum():6d} | du mean {du[m].mean():+.2f} median {np.median(du[m]):+.2f} | dv mean {dv[m].mean():+.2f} median {np.median(dv[m]):+.2f} | |offset| median {np.median(np.hypot(du[m], dv[m])):.2f} p90 {np.percentile(np.hypot(du[m], dv[m]), 90):.2f} px"
          f" | depth err median {np.median(ddep[m]):+.3f} m")
rl("all", np.ones(len(r), bool))
rl("directly splatted pixels", ~fl)
rl("hole-filled pixels", fl)
rl("ground splatted", (kind == 0) & ~fl)
rl("facade splatted", (kind == 1) & ~fl)
for a, b in ((0, 5), (5, 15), (15, 40), (40, 200)):
    rl(f"splatted, range {a}-{b} m", (~fl) & (rng_ >= a) & (rng_ < b))
