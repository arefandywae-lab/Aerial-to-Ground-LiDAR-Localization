"""V1 step 2 (CPU): multi-frame pose. For frame t, take the last N frames; their camera poses in the map are T_t . Delta_j where Delta_j is the relative pose from frame t to frame j given by odometry
(simulated: GT relative pose + noise growing with distance, ODO_T of the travelled distance and ODO_R deg per metre; zero noise = perfect odometry). ONE 6-DoF pose T_t is solved by minimising the Huber
reprojection error of all inlier correspondences of the window frames (each frame's 3D map points projected with its own implied pose). Frames whose residual stays high are dropped and the solve repeated.
Compared with the single-frame pose of frame t (same correspondences, no odometry), on the same frames.
usage: seq_solve.py SEQ.npz [N=5] [odo_t=0.01] [odo_r=0.1] [stride=1]   (stride: use every stride-th earlier frame)"""
import sys

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot

d = np.load(sys.argv[1], allow_pickle=True)
N = int(sys.argv[2]) if len(sys.argv) > 2 else 5
odo_t = float(sys.argv[3]) if len(sys.argv) > 3 else 0.01
odo_r = float(sys.argv[4]) if len(sys.argv) > 4 else 0.1
stride = int(sys.argv[5]) if len(sys.argv) > 5 else 1
P, G, K, p2, p3, inl = d["poses"], d["gt"], d["K"], d["p2"], d["p3"], d["inl"]
rng = np.random.default_rng(7)
n = len(G)


def noisy_rel(Ta, Tb):
    """relative pose of frame b in frame a's camera frame, with odometry-like noise growing with the distance between the frames"""
    rel = np.linalg.inv(Ta) @ Tb
    dist = np.linalg.norm(rel[:3, 3])
    rel = rel.copy()
    dR = Rot.from_rotvec(np.radians(rng.normal(0, odo_r * dist, 3))).as_matrix()
    rel[:3, :3] = rel[:3, :3] @ dR
    rel[:3, 3] += rng.normal(0, odo_t * dist, 3)
    return rel


def residuals(x, frames):
    Tt = np.eye(4)
    Tt[:3, :3] = Rot.from_rotvec(x[:3]).as_matrix()
    Tt[:3, 3] = x[3:]
    out = []
    for rel, a2, a3 in frames:
        Tc = Tt @ rel  # camera-to-world of frame j implied by T_t and odometry
        Xc = (a3 - Tc[:3, 3]) @ Tc[:3, :3]
        z = np.maximum(Xc[:, 2], 1e-3)
        out.append(np.c_[K[0, 0] * Xc[:, 0] / z + K[0, 2], K[1, 1] * Xc[:, 1] / z + K[1, 2]] - a2)
    return np.concatenate(out).ravel()


def err(T, Tg):
    dt = np.linalg.norm(T[:3, 3] - Tg[:3, 3])
    c = np.clip((np.trace(T[:3, :3].T @ Tg[:3, :3]) - 1) / 2, -1, 1)
    return dt, np.degrees(np.arccos(c))


rows = []
for t in range(n):
    if not np.isfinite(P[t, 0, 0]) or len(p2[t]) < 12:
        continue
    idx = [j for j in range(t - (N - 1) * stride, t + 1, stride) if j >= 0 and np.isfinite(P[j, 0, 0]) and len(p2[j]) >= 12]
    if t not in idx or len(idx) < 2:
        continue
    frames = [(noisy_rel(G[t], G[j]), p2[j], p3[j]) for j in idx]  # odometry knows the relative pose t -> j (GT + noise)
    x0 = np.r_[Rot.from_matrix(P[t][:3, :3]).as_rotvec(), P[t][:3, 3]]
    keep = list(range(len(frames)))
    for _ in range(2):  # drop frames that disagree with the joint solution, then re-solve
        sol = least_squares(residuals, x0, args=([frames[k] for k in keep],), loss="huber", f_scale=2.0, max_nfev=40)
        per = []
        for k in keep:
            r = residuals(sol.x, [frames[k]]).reshape(-1, 2)
            per.append(np.median(np.linalg.norm(r, axis=1)))
        keep2 = [k for k, m in zip(keep, per) if m < 6.0]
        if t not in [idx[k] for k in keep2] or len(keep2) < 2 or len(keep2) == len(keep):
            break
        keep, x0 = keep2, sol.x
    Tm = np.eye(4)
    Tm[:3, :3] = Rot.from_rotvec(sol.x[:3]).as_matrix()
    Tm[:3, 3] = sol.x[3:]
    rows.append((t, *err(P[t], G[t]), *err(Tm, G[t]), inl[t], len(keep)))
r = np.array(rows)
single_ok = (r[:, 1] <= 5) & (r[:, 2] <= 10)
multi_ok = (r[:, 3] <= 5) & (r[:, 4] <= 10)
print(f"N={N} stride={stride} odometry noise {odo_t:.1%} of distance + {odo_r} deg/m | {len(r)} frames with a single-frame pose and >= 1 earlier frame")
for name, m in (("all returned poses", np.ones(len(r), bool)), ("gate >= 80 inliers (single-frame count)", r[:, 5] >= 80)):
    a, b = r[m], m
    print(f"  {name:42s} n={m.sum():3d} | single: within (5m,10deg) {single_ok[m].mean():5.1%}, (1m,5deg) {np.mean((a[:,1]<=1)&(a[:,2]<=5)):5.1%}, (0.5m,5deg) {np.mean((a[:,1]<=.5)&(a[:,2]<=5)):5.1%}, median {np.median(a[:,1]):.3f} m"
          f" | multi: within (5m,10deg) {multi_ok[m].mean():5.1%}, (1m,5deg) {np.mean((a[:,3]<=1)&(a[:,4]<=5)):5.1%}, (0.5m,5deg) {np.mean((a[:,3]<=.5)&(a[:,4]<=5)):5.1%}, median {np.median(a[:,3]):.3f} m")
print(f"  gross-wrong (> 5 m or > 10 deg): single {(~single_ok).sum()} -> multi {(~multi_ok).sum()} of {len(r)}  | wrong->right {np.sum(~single_ok & multi_ok)}, right->wrong {np.sum(single_ok & ~multi_ok)}")
