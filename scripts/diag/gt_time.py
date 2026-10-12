"""Inspect GT/clock timestamps of a session bag. usage: gt_time.py SESSION_BAG"""
import sys

import numpy as np

sys.path.insert(0, "/mnt/a/SlamProject/ros")
from eval_ate import read

d = read(sys.argv[1], ["/clock", "/gt/poses"])
clk = np.array([(t, m.clock.sec + m.clock.nanosec * 1e-9) for t, m in d["/clock"]])
lt = np.array([t for t, _ in d["/gt/poses"]])
print(f"clock msgs {len(clk)}: log-time diffs>0 {np.all(np.diff(clk[:,0])>=0)}, sim-time diffs: min {np.diff(clk[:,1]).min():.4f} max {np.diff(clk[:,1]).max():.4f} "
      f"zero {(np.diff(clk[:,1])==0).sum()} neg {(np.diff(clk[:,1])<0).sum()}")
gt_t = np.interp(lt, clk[:, 0], clk[:, 1])
df = np.diff(gt_t)
print(f"gt msgs {len(lt)}: log-time sorted {np.all(np.diff(lt)>=0)}; mapped sim-time diff min {df.min():.5f} zero {(df==0).sum()} neg {(df<0).sum()}")
print(f"clock log-time range {clk[0,0]:.2f}..{clk[-1,0]:.2f} | gt log-time range {lt[0]:.2f}..{lt[-1]:.2f}")
print("first clock samples:", clk[:4].tolist())
print("first/last sim t:", clk[0, 1], clk[-1, 1])
