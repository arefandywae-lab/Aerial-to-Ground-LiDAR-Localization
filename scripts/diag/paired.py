"""Paired per-query comparison of two *_err.npy runs at (0.25 m, 2 deg) and (5 m, 10 deg). usage: paired.py A.npy B.npy"""
import sys
import numpy as np
a, b = np.load(sys.argv[1]), np.load(sys.argv[2])
for name, (t, r) in (("0.25m/2deg", (.25, 2)), ("5m/10deg", (5, 10))):
    ca = (a[:, 0] <= t) & (a[:, 1] <= r); cb = (b[:, 0] <= t) & (b[:, 1] <= r)
    print(f"{name}: A {ca.sum()} B {cb.sum()} | A-only {(ca&~cb).sum()} B-only {(cb&~ca).sum()}")
