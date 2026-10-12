#!/bin/bash
# With sensors actively rendering (bridge subscribes to camera/lidar), is the clock irregular on the GZ side or only on the ROS side?
# usage: clock_probe4.sh WORLD.sdf
source /opt/ros/jazzy/setup.bash
R=/mnt/a/SlamProject/ros
pkill -f "gz sim" 2>/dev/null; pkill -f parameter_bridge 2>/dev/null; sleep 1
gz sim -s -r --headless-rendering "$1" > /tmp/probe_gz.log 2>&1 &
sleep 10
ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=$R/bridge.yaml > /tmp/probe_br.log 2>&1 &
sleep 5
ros2 topic echo /camera/image_raw --field header.stamp > /dev/null 2>&1 &   # keep a ROS-side image subscriber alive too
sleep 12   # sim time ~ 25-30 s when sampling starts
( timeout 20 gz topic -e -t /clock > /tmp/probe_gzclock.txt 2>/dev/null ) &
( timeout 20 ros2 topic echo /clock --field clock > /tmp/probe_roclock.txt 2>/dev/null ) &
wait %4 %5 2>/dev/null; sleep 21
python3 - <<'EOF'
import re
g = open("/tmp/probe_gzclock.txt").read()
t = [int(a) + int(b) * 1e-9 for a, b in re.findall(r"sim\s*\{\s*sec:\s*(\d+)\s*nsec:\s*(\d+)", g)]
bad = sum(1 for x, y in zip(t, t[1:]) if y <= x)
print(f"GZ  side: samples {len(t)}, non-increasing {bad}, range {t[0]:.2f}..{t[-1]:.2f}" if t else "GZ side: none")
r = open("/tmp/probe_roclock.txt").read()
t = [int(a) + int(b) * 1e-9 for a, b in re.findall(r"sec:\s*(\d+)\s*nanosec:\s*(\d+)", r)]
bad = sum(1 for x, y in zip(t, t[1:]) if y <= x)
print(f"ROS side: samples {len(t)}, non-increasing {bad}, range {t[0]:.2f}..{t[-1]:.2f}" if t else "ROS side: none")
EOF
pkill -f parameter_bridge; pkill -f "ros2 topic"; pkill -f "gz sim"
