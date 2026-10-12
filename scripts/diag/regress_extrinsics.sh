#!/bin/bash
# New dump (extrinsics read from bag) vs the dataset already produced with the hard-coded ground-robot offset: must be identical.
cd /root
source /opt/ros/jazzy/setup.bash
rm -rf /root/data/regress_q1v2
python3 /mnt/a/SlamProject/vps/dump_session.py /root/data/q1v2 /root/data/regress_q1v2 3 2>&1 | grep -E "extrinsic|images"
python3 - <<'PY'
import numpy as np
a = np.load("/root/data/q1v2_img/poses.npy"); b = np.load("/root/data/regress_q1v2/poses.npy")
sa = np.load("/root/data/q1v2_img/stamps.npy"); sb = np.load("/root/data/regress_q1v2/stamps.npy")
print("shapes", a.shape, b.shape, "| stamps equal", np.array_equal(sa, sb), "| max |pose diff|", float(np.abs(a - b).max()) if a.shape == b.shape else "n/a")
PY
rm -rf /root/data/regress_q1v2
