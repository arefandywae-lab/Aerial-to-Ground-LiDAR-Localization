"""Which of the two interleaved /clock streams do image header stamps follow? usage: which_clock.py SESSION_BAG"""
import sys

import numpy as np

sys.path.insert(0, "/mnt/a/SlamProject/ros")
from eval_ate import read

d = read(sys.argv[1], ["/clock", "/camera/image_raw", "/gt/poses"])
c = d["/clock"]
t = np.array([m.clock.sec + m.clock.nanosec * 1e-9 for _, m in c])
lt = np.array([x for x, _ in c])
ramp = t[0] + 0.004 * np.arange(len(t))  # ideal single clock (only valid if no dropped ticks; checked below)
low = t[np.abs(t - np.minimum.accumulate(t[::-1])[::-1]) < 1e-9]  # running-min from the right = the lagging stream
r = t - np.interp(lt, lt[::50], np.minimum.reduceat(t, np.arange(0, len(t), 50)))
lead = r > 0.1
print(f"clock samples {len(t)}: lagging-stream {int((~lead).sum())}, leading-stream {int(lead.sum())} (lead by median {np.median(r[lead]):.3f} s)")
# is the lagging stream itself a clean 4 ms ramp?
lag_t = t[~lead]
print("lagging stream steps: unique", np.unique(np.round(np.diff(lag_t), 4))[:6])
img_t = np.array([m.header.stamp.sec + m.header.stamp.nanosec * 1e-9 for _, m in d["/camera/image_raw"]])
print(f"images {len(img_t)}: stamp diffs unique {np.unique(np.round(np.diff(img_t), 3))[:8]}, monotone {bool(np.all(np.diff(img_t) > 0))}")
# do image stamps coincide with a sample of the lagging stream or the leading stream?
on_lag = np.isclose(img_t[:, None], lag_t[None, :], atol=2e-3).any(1).mean()
lead_t = t[lead]
on_lead = np.isclose(img_t[:, None], lead_t[None, :], atol=2e-3).any(1).mean() if len(lead_t) else 0
print(f"image stamps within 2 ms of a lagging-stream sample: {on_lag:.2f}, of a leading-stream sample: {on_lead:.2f}")
print("sim time at end of lagging stream:", lag_t[-1], "| image stamp range:", img_t[0], img_t[-1])
