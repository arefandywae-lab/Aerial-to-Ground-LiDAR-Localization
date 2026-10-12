import sys

import numpy as np

sys.path.insert(0, "/mnt/a/SlamProject/ros")
from eval_ate import read

c = read(sys.argv[1], ["/clock"])["/clock"]
t = np.array([m.clock.sec + m.clock.nanosec * 1e-9 for _, m in c])
lt = np.array([x for x, _ in c])
d = np.diff(t)
bad = np.where(np.abs(d - 0.004) > 1e-6)[0]
print("irregular steps:", len(bad), "of", len(d), "| unique step sizes:", np.unique(np.round(d, 4))[:10])
i = bad[0]
print("around first irregularity, sim t:", t[i - 3:i + 8].round(3).tolist())
print("log-time gaps there (ms):", (np.diff(lt)[i - 3:i + 8] * 1e3).round(1).tolist())
# two interleaved clocks? take residual from the dominant 0.004 slope
r = t - (t[0] + 0.004 * np.arange(len(t)))
print("residual (sim t minus ideal ramp) unique-ish values:", np.unique(r.round(3))[:12])
