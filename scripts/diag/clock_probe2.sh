#!/bin/bash
# Reproduce run_session.sh's setup for a few seconds, list ROS /clock publishers, record 6 s, and check sim-time regularity.  usage: clock_probe2.sh WORLD.sdf
source /opt/ros/jazzy/setup.bash
R=/mnt/a/SlamProject/ros
pkill -f "gz sim" 2>/dev/null; pkill -f parameter_bridge 2>/dev/null; sleep 1
rm -rf /root/data/probe_bag
gz sim -s -r --headless-rendering "$1" > /tmp/probe_gz.log 2>&1 &
sleep 12
ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=$R/bridge.yaml > /tmp/probe_br.log 2>&1 &
sleep 5
echo "--- /clock publishers (ROS side) ---"
ros2 topic info /clock -v 2>&1 | grep -E "Publisher count|Node name|Node namespace"
echo "--- processes ---"
pgrep -fa "gz sim|parameter_bridge" | cut -c1-90
timeout 6 ros2 bag record -o /root/data/probe_bag /clock /gt/poses > /tmp/probe_bag.log 2>&1
pkill -f parameter_bridge; pkill -f "gz sim"; sleep 1
python3 /mnt/a/SlamProject/scripts/diag/clock_jumps.py /root/data/probe_bag 2>&1 | head -3
