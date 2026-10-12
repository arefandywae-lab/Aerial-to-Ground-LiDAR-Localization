#!/bin/bash
# Series B step 1: record the drone mapping flight (ud0) and a ground-camera drive along the street grid (ug1), then dump images + GT poses.
cd /root
source /opt/ros/jazzy/setup.bash
R=/mnt/a/SlamProject
mkdir -p /root/worlds /root/data
[ -f /root/worlds/urban.sdf ] || python3 $R/worlds/gen_urban.py --out /root/worlds/urban.sdf
# drone: 4 lanes along x at z=45 (tallest building 35 m), 40 m... 50 m lane spacing, yaw follows travel
UD="-85,-75,45;85,-75,45;85,-25,45;-85,-25,45;-85,25,45;85,25,45;85,75,45;-85,75,45"
# ground: street centre lines (streets at x,y in {-50,0,50}, 10 m wide), start (0,-85) facing +y
UG="0,-50;0,50;50,50;50,-50;-50,-50;-50,50"
[ -d /root/data/ud0 ] || bash $R/ros/run_urban_session.sh /root/worlds/urban.sdf drone "$UD" /root/data/ud0 4
python3 $R/vps/dump_session.py /root/data/ud0 /root/data/ud0_img 5 --frame drone --gt-topic /gt/drone --image /drone/camera/image_raw --info /drone/camera/camera_info 2>&1 | tail -2
[ -d /root/data/ug1 ] || bash $R/ros/run_urban_session.sh /root/worlds/urban.sdf ground "$UG" /root/data/ug1 1.0
python3 $R/vps/dump_session.py /root/data/ug1 /root/data/ug1_img 6 --frame robot --gt-topic /gt/ground --image /ground/camera/image_raw --info /ground/camera/camera_info 2>&1 | tail -2
sync
python3 - <<'PY'
import numpy as np
for n in ("ud0", "ug1"):
    T = np.load(f"/root/data/{n}_img/poses.npy"); print(n, T.shape, "x", T[:, 0, 3].min().round(1), T[:, 0, 3].max().round(1), "y", T[:, 1, 3].min().round(1), T[:, 1, 3].max().round(1), "z mean", T[:, 2, 3].mean().round(2))
PY
sync; echo 1 > /proc/sys/vm/drop_caches
echo URBAN_RECORD_DONE
