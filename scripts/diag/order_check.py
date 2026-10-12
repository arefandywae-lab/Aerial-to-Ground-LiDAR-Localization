"""Is the 'clock jump' a real time error or receive-order shuffling in the bag? usage: order_check.py SESSION_BAG
- If sorting /clock by its own sim time gives a gap-free, duplicate-free 4 ms ramp, the data is intact and only receive order is shuffled.
- Also: do /gt/poses transforms carry their own sim-time stamp (so GT need not be timed via receive time + /clock interpolation)?"""
import sys

import numpy as np

sys.path.insert(0, "/mnt/a/SlamProject/ros")
from eval_ate import read

d = read(sys.argv[1], ["/clock", "/gt/poses", "/camera/image_raw"])
c = np.array([m.clock.sec + m.clock.nanosec * 1e-9 for _, m in d["/clock"]])
lt = np.array([t for t, _ in d["/clock"]])
s = np.sort(c)
st = np.round(np.diff(s), 4)
print(f"/clock {len(c)}: duplicates {int((st == 0).sum())}, steps after sort-by-sim-time {np.unique(st)[:6]}")
late = np.maximum.accumulate(c) - c  # how far behind the newest already-received clock each message arrives
print(f"receive lag behind newest seen: >0.1 s for {(late > .1).mean():.1%} of msgs, max {late.max():.3f} s")
# receive delay = log time minus (sim->wall mapping fitted on the earliest-arriving messages)
g = d["/gt/poses"]
st0 = g[0][1].transforms[0].header.stamp
print(f"/gt/poses transform header stamp (first msg): {st0.sec}.{st0.nanosec:09d}")
gs = np.array([m.transforms[0].header.stamp.sec + m.transforms[0].header.stamp.nanosec * 1e-9 for _, m in g])
if gs.any():
    gd = np.diff(gs)
    print(f"/gt/poses stamped: {len(gs)} msgs, stamp range {gs[0]:.3f}..{gs[-1]:.3f}, non-increasing in receive order {int((gd <= 0).sum())}, "
          f"after sort unique steps {np.unique(np.round(np.diff(np.unique(gs)), 3))[:5]}")
im = np.array([m.header.stamp.sec + m.header.stamp.nanosec * 1e-9 for _, m in d["/camera/image_raw"]])
print(f"images {len(im)}: out-of-order in receive order {int((np.diff(im) <= 0).sum())}, duplicates {len(im) - len(np.unique(im))}, "
      f"steps after sort {np.unique(np.round(np.diff(np.sort(im)), 3))[:5]}")
