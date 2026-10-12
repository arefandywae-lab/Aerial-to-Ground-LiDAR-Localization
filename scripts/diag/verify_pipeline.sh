#!/bin/bash
# End-to-end check of the fixed recording pipeline on a short drive: stamped GT present, dump works, resort fixes sensor order.
set -e
source /opt/ros/jazzy/setup.bash
R=/mnt/a/SlamProject
rm -rf /root/data/s0v2 /root/data/s0v2_img /root/data/probe* /root/data/vp /root/data/vp_img /root/data/vp_sorted
python3 $R/worlds/gen_world.py --distinct 1 --seed 0 --out /root/worlds/room_v2.sdf
grep -c publish_model_pose /root/worlds/room_v2.sdf
bash $R/ros/run_session.sh /root/worlds/room_v2.sdf "-11.7,-8.0;-12.0,7.9;11.9,8.0" /root/data/vp 0.8 2>&1 | tail -1
python3 - <<'EOF'
import sys; sys.path.insert(0, "/mnt/a/SlamProject/ros")
from eval_ate import read
d = read("/root/data/vp", ["/gt/model"])["/gt/model"]
m = d[0][1]
print("gt/model msgs", len(d), "| transforms:", [(x.header.frame_id, x.child_frame_id, x.header.stamp.sec) for x in m.transforms][:6])
EOF
python3 $R/vps/dump_session.py /root/data/vp /root/data/vp_img 3 2>&1 | tail -1
python3 $R/ros/resort_bag.py /root/data/vp /root/data/vp_sorted 2>&1 | tail -1
python3 - <<'EOF'
import sys; sys.path.insert(0, "/mnt/a/SlamProject/ros")
import numpy as np
from eval_ate import read, gt_track
for b in ("/root/data/vp", "/root/data/vp_sorted"):
    d = read(b, ["/imu", "/lidar/points", "/clock"])
    out = []
    for k, v in d.items():
        t = np.array([(m.clock.sec + m.clock.nanosec * 1e-9) if k == "/clock" else (m.header.stamp.sec + m.header.stamp.nanosec * 1e-9) for _, m in v])
        out.append(f"{k} back-steps {int((np.diff(t) <= 0).sum())}")
    print(b, "|", ", ".join(out))
t, p, q = gt_track("/root/data/vp")
print(f"gt_track: {len(t)} samples, dt median {np.median(np.diff(t))*1e3:.1f} ms, start pos {p[0].round(2)}")
P = np.load("/root/data/vp_img/poses.npy")
print("cam z mean", P[:, 2, 3].mean().round(3), "(v1 was 0.45)")
EOF
