"""Route 2 per street segment (nearest polyline segment of the commanded waypoints). prior run, gate >= 80 and no gate.
Also reports where the drone flew relative to each segment's facades (drone lanes: y = -75, -25, 25, 75 along x, yaw following travel)."""
import sys
import numpy as np
W = np.array([[0, -85], [0, -50], [50, -50], [50, 0], [-50, 0], [-50, -50], [0, -50]], float)  # start (0,-85) then the commanded waypoints
names = ["start x=0 north (same dir as ug1)", "y=-50 east (ug1: west)", "x=50 north (ug1: south)", "y=0 west (novel street)", "x=-50 south (ug1: north)", "y=-50 east (ug1: west)"]
e = np.load("/mnt/a/SlamProject/results/urban/route2_prior_s5r20_err.npy"); T = np.load("/root/data/ug2s_img/poses.npy")
P = T[:, :2, 3]
def dseg(p, a, b):
    t = np.clip(np.dot(p - a, b - a) / np.dot(b - a, b - a), 0, 1); return np.linalg.norm(p - (a + t * (b - a)))
seg = np.array([np.argmin([dseg(p, W[i], W[i + 1]) for i in range(6)]) for p in P])
dt, dr, inl = e[:, 0], e[:, 1], e[:, 2]
print(f"{'segment':40s} {'n':>4s} | no gate: returned, within(5m,10deg) of all, gross-wrong of all | gate>=80: accepted, gross-wrong of all, within 1m")
for i, nm in enumerate(names):
    m = seg == i
    if not m.any(): continue
    ok = np.isfinite(dt) & (dt <= 5) & (dr <= 10)
    a = m & np.isfinite(dt) & (inl >= 80)
    print(f"{nm:40s} {m.sum():4d} | {np.mean(np.isfinite(dt[m])):5.1%} {np.mean(ok[m]):5.1%} {np.mean(np.isfinite(dt[m]) & ~ok[m]):5.1%} | {a.sum()/m.sum():5.1%} {np.sum(a & ~ok)/m.sum():5.1%} {np.mean((dt[a]<=1)&(dr[a]<=5)) if a.any() else float('nan'):5.1%}")
