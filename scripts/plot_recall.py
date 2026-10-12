#!/usr/bin/env python3
"""Plot recall-vs-threshold curves and inlier-gated precision from results/*_err.npy.
usage: plot_recall.py OUT.png RESULT.npy [RESULT.npy ...]  (label from basename)"""
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

TH_T = np.linspace(0.05, 5, 200)
TH_R = np.linspace(0.5, 15, 200)


def main(out, paths):
    fig, ax = plt.subplots(1, 3, figsize=(14, 4))
    for p in paths:
        e = np.load(p)
        dt, dr = e[:, 0], e[:, 1]
        inl = e[:, 2] if e.shape[1] > 2 else None
        name = os.path.basename(p).replace("_err.npy", "")
        ax[0].plot(TH_T, [(dt <= t).mean() for t in TH_T], label=name)
        ax[1].plot(TH_R, [(dr <= r).mean() for r in TH_R], label=name)
        if inl is not None:
            gates = np.unique(inl[inl > 0])[::max(1, len(np.unique(inl[inl > 0])) // 30)]
            ax[2].plot(gates, [((inl >= g) & (dt <= 5) & (dr <= 10)).sum() / max(1, (inl >= g).sum()) for g in gates],
                       label=name)
    for a, (xl, yl, t) in zip(ax, [("translation thresh (m)", "recall", "Translation recall"),
                                   ("rotation thresh (deg)", "recall", "Rotation recall"),
                                   ("inlier gate", "precision @ (5m,10deg)", "Inlier-gated precision")]):
        a.set(xlabel=xl, ylabel=yl, title=t)
        a.grid(True, alpha=.3)
        a.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    print(f"wrote {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
