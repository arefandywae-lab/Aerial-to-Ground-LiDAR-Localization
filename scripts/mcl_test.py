"""Monte Carlo localization (particle filter, 3-DoF: camera x, y, heading) over route 2, offline on the stored single-frame results (CPU only).
Predict: simulated odometry = GT relative motion between consecutive dumped frames + noise (ODO_T of distance, ODO_R deg per metre) + small diffusion.
Update: the PnP pose of the frame (x, y, heading) as an observation with a robust likelihood: (1 - EPS) N(obs; particle, sigma) + EPS * uniform, so a wrong pose cannot drag the cloud; sigma_xy grows when the frame has few inliers.
Initial cloud = GT + N(0, 5 m) in xy and N(0, 10 deg) in heading (same prior assumption as the single-frame runs). Output = weighted mean; confidence = particle spread.
Compared with the single-frame PnP pose on the same frames and with the single-frame inlier gate. usage: mcl_test.py SEQ.npz [odo_t=0.01] [odo_r=0.1] [eps=0.2] [n=500]"""
import os
import sys

import numpy as np

d = np.load(sys.argv[1])
START = int(os.environ.get("START", 0))  # begin the filter at this frame (different start places for the kidnapped test)
P, G, inl = d["poses"][START:], d["gt"][START:], d["inl"][START:]
odo_t = float(sys.argv[2]) if len(sys.argv) > 2 else 0.01
odo_r = float(sys.argv[3]) if len(sys.argv) > 3 else 0.1
EPS = float(sys.argv[4]) if len(sys.argv) > 4 else 0.2
NP = int(sys.argv[5]) if len(sys.argv) > 5 else 500
rng = np.random.default_rng(int(os.environ.get("SEED", 3)))
n = len(G)
wrap = lambda a: (a + np.pi) % (2 * np.pi) - np.pi


def state(T):
    return np.array([T[0, 3], T[1, 3], np.arctan2(T[1, 2], T[0, 2])])  # camera x, y, heading of the optical axis


gt = np.array([state(T) for T in G])
MH = os.environ.get("MULTIHYP") == "1" and "hyp" in d.files  # observation = mixture over the per-view PnP hypotheses of the frame (seq_collect with M1LF_HYP=N)
HMIN = int(os.environ.get("HMIN", 30))
hyp = [[state(T) for T, k in zip(d["hyp"][t], d["hinl"][t]) if np.isfinite(T[0, 0]) and k >= HMIN] for t in range(START, START + len(G))] if MH else None
obs = np.array([state(T) if np.isfinite(T[0, 0]) else np.full(3, np.nan) for T in P])
INJ = float(os.environ.get("INJECT", 0))  # fraction of particles re-seeded around the observation after each update (recovery from a collapsed cloud)
INLMIN = int(os.environ.get("INLMIN", 0))  # observations with fewer inliers are ignored (acts as the confidence gate)
UNI = float(os.environ.get("UNI", 0))  # fraction of the lowest-weight particles re-drawn uniformly over the map every frame (keeps global diversity; KIDNAP mode only)
SXY = float(os.environ.get("SXY", 0.6))
KID = os.environ.get("KIDNAP") == "1"  # global start: no position/heading prior; particles uniform over the route bounding box + 30 m, random heading
if KID:
    lo, hi = gt[:, :2].min(0) - 30, gt[:, :2].max(0) + 30
    part = np.c_[rng.uniform(lo, hi, (NP, 2)), rng.uniform(-np.pi, np.pi, NP)]
else:
    part = np.c_[gt[0, :2] + rng.normal(0, 5, (NP, 2)), gt[0, 2] + np.radians(rng.normal(0, 10, NP))]
w = np.full(NP, 1.0 / NP)
est, spread = np.zeros((n, 3)), np.zeros(n)
for t in range(n):
    if t > 0:  # odometry between frames t-1 and t, expressed in the previous heading frame
        c, s = np.cos(gt[t - 1, 2]), np.sin(gt[t - 1, 2])
        dxy = gt[t, :2] - gt[t - 1, :2]
        rel = np.array([c * dxy[0] + s * dxy[1], -s * dxy[0] + c * dxy[1]])
        dpsi = wrap(gt[t, 2] - gt[t - 1, 2])
        dist = np.linalg.norm(rel)
        rel_n = rel + rng.normal(0, odo_t * dist + 0.01, (NP, 2))
        dpsi_n = dpsi + np.radians(rng.normal(0, odo_r * dist + 0.2, NP))
        c, s = np.cos(part[:, 2]), np.sin(part[:, 2])
        part[:, 0] += c * rel_n[:, 0] - s * rel_n[:, 1]
        part[:, 1] += s * rel_n[:, 0] + c * rel_n[:, 1]
        part[:, 2] = wrap(part[:, 2] + dpsi_n)
    obs_t = hyp[t] if MH else ([obs[t]] if np.isfinite(obs[t, 0]) and inl[t] >= INLMIN else [])
    if obs_t:
        lik = np.zeros(NP)
        for ob in obs_t:
            sxy = SXY * (1.0 if MH else np.clip((80.0 / max(inl[t], 12)) ** 0.5, 0.7, 3.0))
            dxy = np.linalg.norm(part[:, :2] - ob[:2], axis=1)
            dya = wrap(part[:, 2] - ob[2])
            lik += np.exp(-0.5 * (dxy / sxy) ** 2 - 0.5 * (dya / np.radians(1.5 if not MH else 4.0)) ** 2) / len(obs_t)
        w = w * ((1 - EPS) * lik + EPS * 1e-4)
        w /= w.sum()
        if 1.0 / np.sum(w ** 2) < NP / 2:  # resample
            idx = rng.choice(NP, NP, p=w)
            part, w = part[idx], np.full(NP, 1.0 / NP)
    if INJ > 0 and not MH and np.isfinite(obs[t, 0]) and inl[t] >= 40:
        k = int(INJ * NP)
        j = np.argsort(w)[:k]
        part[j] = np.c_[obs[t, :2] + rng.normal(0, 1.0, (k, 2)), obs[t, 2] + np.radians(rng.normal(0, 3, k))]
        w[j] = w.mean(); w /= w.sum()
    if UNI > 0 and KID:
        k = int(UNI * NP)
        j = np.argsort(w)[:k]
        part[j] = np.c_[rng.uniform(lo, hi, (k, 2)), rng.uniform(-np.pi, np.pi, k)]
        w[j] = w.mean(); w /= w.sum()
    m = np.average(part[:, :2], axis=0, weights=w)
    est[t, :2] = m
    est[t, 2] = np.arctan2(np.average(np.sin(part[:, 2]), weights=w), np.average(np.cos(part[:, 2]), weights=w))
    spread[t] = np.sqrt(np.average(np.sum((part[:, :2] - m) ** 2, axis=1), weights=w))
e_xy = np.linalg.norm(est[:, :2] - gt[:, :2], axis=1)
e_ya = np.abs(np.degrees(wrap(est[:, 2] - gt[:, 2])))
s_xy = np.where(np.isfinite(obs[:, 0]), np.linalg.norm(obs[:, :2] - gt[:, :2], axis=1), np.nan)
s_ya = np.where(np.isfinite(obs[:, 0]), np.abs(np.degrees(wrap(obs[:, 2] - gt[:, 2]))), np.nan)
ok = np.isfinite(s_xy)
print(f"route 2, {n} frames ({ok.sum()} with a single-frame pose); odometry noise {odo_t:.1%} + {odo_r} deg per metre; outlier share EPS {EPS}; {NP} particles (planar error x, y and heading only)")
def line(name, m, xy, ya):
    print(f"  {name:44s} n={int(m.sum()):4d} | within (5m,10deg) {np.mean((xy[m] <= 5) & (ya[m] <= 10)):6.1%} | (1m,5deg) {np.mean((xy[m] <= 1) & (ya[m] <= 5)):6.1%} | (0.5m,5deg) {np.mean((xy[m] <= .5) & (ya[m] <= 5)):6.1%} | median xy {np.median(xy[m]):.3f} m | gross-wrong {np.mean((xy[m] > 5) | (ya[m] > 10)):5.1%}")
line("single-frame PnP, frames with a pose", ok, s_xy, s_ya)
line("single-frame PnP, gate >= 80 inliers", ok & (inl >= 80), s_xy, s_ya)
allm = np.ones(n, bool)
skip = np.arange(n) >= 10  # let the filter settle
if KID:  # convergence = first frame from which the estimate stays within 2 m of GT for the rest of the route
    bad = np.where(e_xy > 2.0)[0]
    conv = int(bad[-1] + 1) if len(bad) else 0
    print(f"KIDNAPPED start: converged (stays within 2 m) from frame {conv} of {n}" + (" (never)" if conv >= n else ""))
    skip = np.arange(n) >= min(conv, n - 1)
line("MCL estimate, every frame (after 10 frames)", allm & skip, e_xy, e_ya)
for sp in (1.5, 1.0, 0.7, 0.5):
    line(f"MCL, confident (spread < {sp} m)", (spread < sp) & skip, e_xy, e_ya)
