#!/bin/bash
# Recover q2v2 after the unclean VM shutdown: rebuild bag metadata from the mcap, verify readability, re-dump images.
cd /root
source /opt/ros/jazzy/setup.bash
ros2 bag reindex -s mcap /root/data/q2v2 2>&1 | tail -3
ls -l /root/data/q2v2
python3 - <<'EOF'
import sys; sys.path.insert(0, "/mnt/a/SlamProject/ros")
import numpy as np
from eval_ate import read, gt_track
try:
    d = read("/root/data/q2v2", ["/clock", "/camera/image_raw", "/gt/model"])
    print({k: len(v) for k, v in d.items()})
    t, p, q = gt_track("/root/data/q2v2")
    print("gt_track ok:", len(t), "samples,", f"{t[-1]-t[0]:.1f} s, path {np.linalg.norm(np.diff(p[:, :2], axis=0), axis=1).sum():.1f} m, last pos {p[-1].round(2)}")
    print("READABLE")
except Exception as e:
    print("UNREADABLE:", type(e).__name__, str(e)[:200])
EOF
