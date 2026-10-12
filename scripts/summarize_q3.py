"""q3v2 results stratified by how far the query's yaw (relative to its nearest map pose) is from the virtual yaws {0,90,180,270}.
misalignment m = distance in degrees to the nearest multiple of 90 (0 = aligned, 45 = worst). usage: summarize_q3.py [results/v2]"""
import sys

import numpy as np

D = sys.argv[1] if len(sys.argv) > 1 else "/mnt/a/SlamProject/results/v2"
T = np.load("/root/data/q3v2_img/poses.npy")
S = np.load("/root/data/s0v2_img/poses.npy")
nn = np.array([np.linalg.norm(S[:, :3, 3] - p[:3, 3], axis=1).argmin() for p in T])
yaw = lambda M: np.degrees(np.arctan2(M[:, 1, 2], M[:, 0, 2]))
d = np.abs((yaw(T) - yaw(S[nn]) + 180) % 360 - 180)  # 0..180
m = np.abs(((d + 45) % 90) - 45)  # distance to nearest multiple of 90
bins = [(0, 15), (15, 30), (30, 46)]
print(f"q3v2: n={len(T)}; misalignment bins (deg) counts: " + ", ".join(f"{a}-{b}: {int(((m >= a) & (m < b)).sum())}" for a, b in bins))
print(f"{'run':10s} {'bin':>7s} {'n':>4s} {'good(.25m,2deg)':>16s} {'ok(5m,10deg)':>13s} {'wrong':>6s} {'no pose':>8s}")
for run in ("m0_q3v2_s0", "yaw0_q3v2", "yaw4_q3v2"):
    try:
        e = np.load(f"{D}/{run}_err.npy")
    except FileNotFoundError:
        continue
    dt, dr = e[:, 0], e[:, 1]
    ret = np.isfinite(dt)
    good = ret & (dt <= .25) & (dr <= 2)
    ok5 = ret & (dt <= 5) & (dr <= 10)
    wrong = ret & ~ok5
    for a, b in [(0, 46)] + bins:
        s = (m >= a) & (m < b)
        print(f"{run:10s} {('all' if (a, b) == (0, 46) else f'{a}-{b}'):>7s} {int(s.sum()):4d} {good[s].mean():16.1%} {ok5[s].mean():13.1%} {int(wrong[s].sum()):6d} {int((~ret[s]).sum()):8d}")
