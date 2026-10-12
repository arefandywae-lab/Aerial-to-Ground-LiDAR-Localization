#!/bin/bash
# Held-out viewpoint queries in the v2 room: 8 spots on a lane 0.5 m outside the map path, a full 360 deg in-place turn at each
# (yaw covers every angle, incl. 45/135 deg that no virtual yaw of the map was chosen for). Then FAST-LIO is NOT needed (queries only).
cd /root
source /opt/ros/jazzy/setup.bash
WPS="-12.5,-8.5,s;0,-8.5,s;12.5,-8.5,s;12.5,0,s;12.5,8.5,s;0,8.5,s;-12.5,8.5,s;-12.5,0,s"
[ -d /root/data/q3v2 ] && { echo "q3v2 exists, skipping record"; } || bash /mnt/a/SlamProject/ros/run_session.sh /root/worlds/room_v2.sdf "$WPS" /root/data/q3v2 0.8
rm -rf /root/data/q3v2_img
python3 /mnt/a/SlamProject/vps/dump_session.py /root/data/q3v2 /root/data/q3v2_img 3 2>&1 | tail -1
sync
python3 - <<'PY'
import numpy as np
T = np.load("/root/data/q3v2_img/poses.npy"); S = np.load("/root/data/s0v2_img/poses.npy")
d = np.array([np.linalg.norm(S[:, :3, 3] - p[:3, 3], axis=1).min() for p in T])
yaw = np.degrees(np.arctan2(T[:, 1, 2], T[:, 0, 2]))  # camera optical axis (z) heading in the world xy plane
syaw = np.degrees(np.arctan2(S[:, 1, 2], S[:, 0, 2]))
dy = np.array([abs((yaw[i] - syaw[np.linalg.norm(S[:, :3, 3] - T[i, :3, 3], axis=1).argmin()] + 180) % 360 - 180) for i in range(len(T))])
print(f"q3v2: {len(T)} poses | dist to nearest map pose median {np.median(d):.2f} m (max {d.max():.2f}) | yaw diff to that map pose: median {np.median(dy):.0f}, "
      f"histogram 0-30/30-60/60-90/90-120/120-150/150-180: {np.histogram(dy, bins=[0,30,60,90,120,150,181])[0].tolist()}")
PY
echo Q3_DONE
