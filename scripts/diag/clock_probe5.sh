#!/bin/bash
# Isolate the trigger. usage: clock_probe5.sh WORLD.sdf MODE   MODE = drive | bag | both
# Always: gz server + bridge (sensors rendering). drive = run drive_waypoints.py; bag = ros2 bag record of the real topic set.
source /opt/ros/jazzy/setup.bash
R=/mnt/a/SlamProject/ros
MODE=$2
pkill -f "gz sim" 2>/dev/null; pkill -f parameter_bridge 2>/dev/null; pkill -f drive_waypoints 2>/dev/null; sleep 1
rm -rf /root/data/probe_$MODE
gz sim -s -r --headless-rendering "$1" > /tmp/probe_gz.log 2>&1 &
sleep 10
ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=$R/bridge.yaml > /tmp/probe_br.log 2>&1 &
sleep 5
if [ "$MODE" = bag ] || [ "$MODE" = both ]; then
  ros2 bag record -o /root/data/probe_$MODE --storage-preset-profile zstd_fast /clock /lidar/points /imu /camera/image_raw /camera/camera_info /gt/poses > /tmp/probe_bag.log 2>&1 &
  BAG=$!
fi
sleep 2
if [ "$MODE" = drive ] || [ "$MODE" = both ]; then
  python3 $R/drive_waypoints.py "-12,-8;12,-8;12,8;-12,8" 0.8 > /dev/null 2>&1 &
fi
sleep 12                      # reach sim ~ 25-30 s
timeout 25 gz topic -e -t /clock > /tmp/probe_gzclock.txt 2>/dev/null
[ -n "$BAG" ] && { kill -INT $BAG; wait $BAG 2>/dev/null; }
pkill -f drive_waypoints; pkill -f parameter_bridge; pkill -f "gz sim"
python3 - <<'EOF'
import re
g = open("/tmp/probe_gzclock.txt").read()
t = [int(a) + int(b) * 1e-9 for a, b in re.findall(r"sim\s*\{\s*sec:\s*(\d+)\s*nsec:\s*(\d+)", g)]
bad = sum(1 for x, y in zip(t, t[1:]) if y <= x)
print(f"GZ-side clock: samples {len(t)}, non-increasing {bad}, range {t[0]:.2f}..{t[-1]:.2f}" if t else "GZ side: none")
EOF
[ -d /root/data/probe_$MODE ] && python3 /mnt/a/SlamProject/scripts/diag/clock_jumps.py /root/data/probe_$MODE 2>&1 | head -1
