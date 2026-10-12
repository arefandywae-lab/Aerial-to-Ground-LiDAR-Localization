#!/bin/bash
# 1) new dump_session on legacy v1 bag must reproduce the existing poses exactly; 2) legacy path must REFUSE the shuffled probe2 bag;
# 3) receive-order check for /imu and /lidar/points (FAST-LIO replays in receive order).
source /opt/ros/jazzy/setup.bash
R=/mnt/a/SlamProject
rm -rf /root/data/regress_s0
python3 $R/vps/dump_session.py /root/data/s0 /root/data/regress_s0 3 2>&1 | tail -1
python3 - <<'EOF'
import numpy as np
a = np.load("/root/data/s0_img/poses.npy"); b = np.load("/root/data/regress_s0/poses.npy")
sa = np.load("/root/data/s0_img/stamps.npy"); sb = np.load("/root/data/regress_s0/stamps.npy")
print("v1 regression: n", len(a), len(b), "| stamps equal", np.array_equal(sa, sb), "| max pose diff", float(np.abs(a - b).max()) if a.shape == b.shape else "shape differs")
EOF
python3 $R/vps/dump_session.py /root/data/probe2 /root/data/regress_p2 2>&1 | grep -E "ValueError|images" | cut -c1-160
python3 - <<'EOF'
import sys; sys.path.insert(0, "/mnt/a/SlamProject/ros")
import numpy as np
from eval_ate import read
d = read("/root/data/probe2", ["/imu", "/lidar/points"])
for k, v in d.items():
    t = np.array([m.header.stamp.sec + m.header.stamp.nanosec * 1e-9 for _, m in v])
    print(f"probe2 {k}: {len(t)} msgs, out-of-order in receive order {int((np.diff(t) <= 0).sum())}, max backward jump {max(0, -np.diff(t).min()):.3f} s")
EOF
rm -rf /root/data/regress_s0 /root/data/regress_p2
