"""Learned confidence gate ("System One" accept/reject head) for the M1 localizer.

Input per query: features logged by vps/m1l.py (inlier stats, retrieval margin, agreement between the PnP pose and the retrieved render's pose, ...).
Label: the returned pose is usable at (0.5 m, 5 deg) by default (GATE_LABEL=strict for (0.25 m, 2 deg)).  Queries without a pose are excluded (they are already rejected).
Protocol: leave-one-SESSION-out (consecutive frames are near-duplicates, so a random split would leak); logistic regression, standardised features, plain numpy.
Reports per held-out session: AUROC, accepted fraction and precision at fixed gate settings vs the baseline gate "inliers >= N", and Brier score / calibration bins.
usage: confidence_gate.py RUN_PREFIX [RUN_PREFIX ...]   e.g. results/v2/g12_q1v2 results/v2/g12_q2v2 results/v2/g12_q3v2 (needs *_err.npy, *_feat.npy, *_feat_names.json)"""
import json
import os
import sys

import numpy as np


# env: GATE_LABEL = coarse ((5 m, 10 deg): is the pose not grossly wrong) | usable ((0.5 m, 5 deg), the deployment criterion; default) | strict ((0.25 m, 2 deg)); GATE_L2 (ridge); GATE_FEATS = comma list or "all"
LABEL = os.environ.get("GATE_LABEL", "usable")
L2 = float(os.environ.get("GATE_L2", 10.0))
FEATS = os.environ.get("GATE_FEATS", "all")


def load(prefix):
    e = np.load(prefix + "_err.npy")
    f = np.load(prefix + "_feat.npy")
    names = json.load(open(prefix + "_feat_names.json"))["feature_names"]
    f, names = np.c_[f, e[:, 2]], names + ["inliers"]  # the inlier count (the baseline gate's own score) must be available to the model too
    if FEATS != "all":
        keep = [names.index(n) for n in FEATS.split(",")]
        f, names = f[:, keep], [names[i] for i in keep]
    has = np.isfinite(e[:, 0]) & np.isfinite(f).all(1)
    t, r = {"usable": (.5, 5), "strict": (.25, 2), "coarse": (5, 10)}[LABEL]  # coarse = the integrity question: is the accepted pose NOT grossly wrong
    y = ((e[:, 0] <= t) & (e[:, 1] <= r))[has].astype(float)
    return f[has], y, names, len(e), int(np.isfinite(e[:, 0]).sum()), e[has, 2]


def prep(x):
    x = x.copy()
    for j in range(x.shape[1]):
        if x[:, j].min() >= 0 and x[:, j].max() > 20:  # heavy-tailed counts/distances -> log scale
            x[:, j] = np.log1p(x[:, j])
    return x


def fit(x, y, l2=None, it=500):
    l2 = L2 if l2 is None else l2
    mu, sd = x.mean(0), x.std(0) + 1e-9
    z = np.c_[(x - mu) / sd, np.ones(len(x))]
    w = np.zeros(z.shape[1])
    for _ in range(it):  # Newton / IRLS
        p = 1 / (1 + np.exp(-z @ w))
        g = z.T @ (p - y) + l2 * np.r_[w[:-1], 0]
        H = (z.T * (p * (1 - p))) @ z + l2 * np.diag(np.r_[np.ones(len(w) - 1), 0]) + 1e-6 * np.eye(len(w))
        w -= np.linalg.solve(H, g)
    return mu, sd, w


def predict(m, x):
    mu, sd, w = m
    return 1 / (1 + np.exp(-(np.c_[(x - mu) / sd, np.ones(len(x))] @ w)))


def auroc(s, y):
    if y.min() == y.max():
        return float("nan")
    r = np.argsort(np.argsort(s)) + 1
    n1, n0 = y.sum(), len(y) - y.sum()
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def at_precision(s, y, target):
    """largest accepted fraction with precision >= target (accept by descending score)"""
    o = np.argsort(-s)
    prec = np.cumsum(y[o]) / np.arange(1, len(y) + 1)
    ok = np.where(prec >= target)[0]
    return (ok[-1] + 1) / len(y) if len(ok) else 0.0


prefixes = sys.argv[1:]
data = [load(p) for p in prefixes]
names = data[0][2]
print("features:", names)
tot = []
for k, (x, y, _, n, nret, inl) in enumerate(data):
    xtr = np.concatenate([prep(d[0]) for j, d in enumerate(data) if j != k])
    ytr = np.concatenate([d[1] for j, d in enumerate(data) if j != k])
    m = fit(xtr, ytr)
    s = predict(m, prep(x))
    base = inl  # baseline gate score: raw inlier count
    brier = float(np.mean((s - y) ** 2))
    print(f"\n== held-out {prefixes[k].split('/')[-1]}: {n} queries, {nret} with a pose, {int(y.sum())} correct ({y.mean():.1%} of returned); trained on the other sessions ({len(ytr)} poses)")
    print(f"AUROC learned {auroc(s, y):.3f} | inlier-count baseline {auroc(base, y):.3f} | Brier learned {brier:.3f} (constant-rate {np.mean((y.mean() - y) ** 2):.3f})")
    o_l, o_b = np.argsort(-s), np.argsort(-base)
    for frac in (0.5, 0.7, 0.9):  # precision when the gate keeps the top fraction of returned poses (not hostage to the first few items)
        kk = int(frac * len(y))
        print(f"  precision keeping top {frac:.0%}: learned {y[o_l[:kk]].mean():.3f} | inliers>=N {y[o_b[:kk]].mean():.3f}  (all returned: {y.mean():.3f})")
    for tp in (0.9, 0.95, 0.99):
        print(f"  accepted fraction at precision >= {tp:.0%}: learned {at_precision(s, y, tp):6.1%} | inliers>=N {at_precision(base, y, tp):6.1%}")
    bins = np.digitize(s, [.2, .4, .6, .8])
    print("  calibration (mean predicted -> observed correct, n):", [f"{s[bins == b].mean():.2f}->{y[bins == b].mean():.2f} ({int((bins == b).sum())})" for b in range(5) if (bins == b).any()])
    tot.append((auroc(s, y), auroc(base, y)))
mu, sd, w = fit(np.concatenate([prep(d[0]) for d in data]), np.concatenate([d[1] for d in data]))
print("\nweights (standardised features, all sessions):", {n_: round(float(v), 2) for n_, v in zip(names, w[:-1])})
