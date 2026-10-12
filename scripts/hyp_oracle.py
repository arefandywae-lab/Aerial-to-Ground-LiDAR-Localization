"""Oracle test for the multi-hypothesis idea: in global mode, is a CORRECT pose (<= 5 m, 10 deg) among the per-view PnP hypotheses of a frame, and how often when the top-1 pose is wrong?
usage: hyp_oracle.py SEQ_hyp_global.npz [HMIN=30]"""
import sys
import numpy as np
d = np.load(sys.argv[1]); H, hi, G, P, inl = d["hyp"], d["hinl"], d["gt"], d["poses"], d["inl"]
hmin = int(sys.argv[2]) if len(sys.argv) > 2 else 30
def ok(T, Tg):
    if not np.isfinite(T[0, 0]): return False
    c = np.clip((np.trace(T[:3, :3].T @ Tg[:3, :3]) - 1) / 2, -1, 1)
    return np.linalg.norm(T[:3, 3] - Tg[:3, 3]) <= 5 and np.degrees(np.arccos(c)) <= 10
n = len(G)
top1 = np.array([ok(P[t], G[t]) for t in range(n)])
good = np.array([[ok(H[t, h], G[t]) and hi[t, h] >= hmin for h in range(H.shape[1])] for t in range(n)])
anyg = good.any(1)
nv = (hi >= hmin).sum(1)
print(f"{n} frames, global mode, hypotheses = per-view PnP of the 8 best shortlisted views (valid if >= {hmin} inliers)")
print(f"top-1 (pooled PnP) correct: {top1.mean():.1%} | a correct hypothesis exists among the 8: {anyg.mean():.1%} | among frames where top-1 is wrong ({int((~top1).sum())}): {anyg[~top1].mean():.1%}")
print(f"median valid hypotheses per frame {np.median(nv):.0f}; frames with >=1 valid: {(nv>0).mean():.1%}; wrong share of valid hypotheses {1-good.sum()/max(nv.sum(),1):.1%}")
