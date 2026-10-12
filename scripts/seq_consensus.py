"""V1b (CPU): multi-frame CONSENSUS. The plain joint solve (seq_solve.py) let wrong-but-self-consistent frames (aliasing) pull correct frames away. Here, for frame t, every frame j in the window implies a pose for t:
T_t^(j) = P_j . rel(t,j)^-1 (rel = odometry-like relative pose, GT + noise growing with distance). The largest cluster of implied poses (within CLUSTER_M metres and CLUSTER_DEG degrees of a member) is the consensus;
only its frames enter the joint reprojection solve; the cluster size is the confidence (a vote count). Reported against the single-frame inlier gate on the same frames.
usage: seq_consensus.py SEQ.npz [N=7] [odo_t=0.01] [odo_r=0.1] [stride=1]"""
import sys

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot

d = np.load(sys.argv[1])  # plain arrays only (written by seq_collect.py), no pickle
N = int(sys.argv[2]) if len(sys.argv) > 2 else 7
odo_t = float(sys.argv[3]) if len(sys.argv) > 3 else 0.01
odo_r = float(sys.argv[4]) if len(sys.argv) > 4 else 0.1
stride = int(sys.argv[5]) if len(sys.argv) > 5 else 1
P, G, K, inl, off = d["poses"], d["gt"], d["K"], d["inl"], d["off"]
p2 = [d["p2"][off[i]:off[i + 1]] for i in range(len(off) - 1)]
p3 = [d["p3"][off[i]:off[i + 1]] for i in range(len(off) - 1)]
CLUSTER_M, CLUSTER_DEG = 1.5, 15.0
rng = np.random.default_rng(7)
n = len(G)


def noisy_rel(Ta, Tb):
    rel = np.linalg.inv(Ta) @ Tb
    dist = np.linalg.norm(rel[:3, 3])
    rel = rel.copy()
    rel[:3, :3] = rel[:3, :3] @ Rot.from_rotvec(np.radians(rng.normal(0, odo_r * dist, 3))).as_matrix()
    rel[:3, 3] += rng.normal(0, odo_t * dist, 3)
    return rel


def err(T, Tg):
    c = np.clip((np.trace(T[:3, :3].T @ Tg[:3, :3]) - 1) / 2, -1, 1)
    return np.linalg.norm(T[:3, 3] - Tg[:3, 3]), np.degrees(np.arccos(c))


def residuals(x, frames):
    Tt = np.eye(4)
    Tt[:3, :3] = Rot.from_rotvec(x[:3]).as_matrix()
    Tt[:3, 3] = x[3:]
    out = []
    for rel, a2, a3 in frames:
        Tc = Tt @ rel
        Xc = (a3 - Tc[:3, 3]) @ Tc[:3, :3]
        z = np.maximum(Xc[:, 2], 1e-3)
        out.append(np.c_[K[0, 0] * Xc[:, 0] / z + K[0, 2], K[1, 1] * Xc[:, 1] / z + K[1, 2]] - a2)
    return np.concatenate(out).ravel()


rows = []
for t in range(n):
    if not np.isfinite(P[t, 0, 0]) or len(p2[t]) < 12:
        continue
    idx = [j for j in range(t - (N - 1) * stride, t + 1, stride) if j >= 0 and np.isfinite(P[j, 0, 0]) and len(p2[j]) >= 12]
    if t not in idx:
        continue
    rel = {j: noisy_rel(G[t], G[j]) for j in idx}
    imp = {j: P[j] @ np.linalg.inv(rel[j]) for j in idx}  # pose of t implied by frame j
    best = []
    for j in idx:  # largest cluster around each member
        c = [k for k in idx if np.linalg.norm(imp[k][:3, 3] - imp[j][:3, 3]) < CLUSTER_M and err(imp[k], imp[j])[1] < CLUSTER_DEG]
        if len(c) > len(best) or (len(c) == len(best) and sum(inl[k] for k in c) > sum(inl[k] for k in best)):
            best = c
    ref = max(best, key=lambda k: inl[k])
    x0 = np.r_[Rot.from_matrix(imp[ref][:3, :3]).as_rotvec(), imp[ref][:3, 3]]
    frames = [(rel[k], p2[k], p3[k]) for k in best]
    sol = least_squares(residuals, x0, args=(frames,), loss="huber", f_scale=2.0, max_nfev=40)
    Tm = np.eye(4)
    Tm[:3, :3] = Rot.from_rotvec(sol.x[:3]).as_matrix()
    Tm[:3, 3] = sol.x[3:]
    rows.append((t, *err(P[t], G[t]), *err(Tm, G[t]), inl[t], len(best), len(idx)))
r = np.array(rows)
s_ok = (r[:, 1] <= 5) & (r[:, 2] <= 10)
m_ok = (r[:, 3] <= 5) & (r[:, 4] <= 10)
m1 = (r[:, 3] <= 1) & (r[:, 4] <= 5)
m05 = (r[:, 3] <= .5) & (r[:, 4] <= 5)
print(f"N={N} stride={stride} odometry noise {odo_t:.1%}/m + {odo_r} deg/m: {len(r)} frames with a single-frame pose")
sg = r[:, 5] >= 80
print(f"single-frame gate >= 80 inliers : accepted {sg.mean():5.1%} | within (5m,10deg) {s_ok[sg].mean():5.1%} | gross-wrong accepted {np.sum(sg & ~s_ok) / len(r):5.1%} of all | within (1m,5deg) {np.mean((r[sg,1]<=1)&(r[sg,2]<=5)):5.1%} | median err {np.median(r[sg,1]):.3f} m")
for votes in range(2, N + 1):
    a = r[:, 6] >= votes
    if a.sum() == 0:
        continue
    print(f"consensus votes >= {votes}: accepted {a.mean():5.1%} | within (5m,10deg) {m_ok[a].mean():5.1%} | gross-wrong accepted {np.sum(a & ~m_ok) / len(r):5.1%} of all | within (1m,5deg) {m1[a].mean():5.1%} | within (0.5m,5deg) {m05[a].mean():5.1%} | median err {np.median(r[a,3]):.3f} m")
need = int(np.ceil(0.8 * N))
both = (r[:, 6] >= need) & sg
print(f"gate>=80 AND votes>={need}          : accepted {both.mean():5.1%} | within (5m,10deg) {m_ok[both].mean():5.1%} | gross-wrong accepted {np.sum(both & ~m_ok) / len(r):5.1%} of all | within (1m,5deg) {m1[both].mean():5.1%} | within (0.5m,5deg) {m05[both].mean():5.1%}")
