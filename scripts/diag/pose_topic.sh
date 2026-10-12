#!/bin/bash
# Does the PosePublisher topic carry sim-time stamps and frame names (unlike /world/room/dynamic_pose/info)?
source /opt/ros/jazzy/setup.bash
pkill -f "gz sim" 2>/dev/null; pkill -f "bag record" 2>/dev/null; pkill -f parameter_bridge 2>/dev/null; sleep 1
gz sim -s -r --headless-rendering /root/worlds/room.sdf > /tmp/pt_gz.log 2>&1 &
sleep 12
gz topic -l | grep -i pose
echo "--- /model/robot/pose (one msg) ---"
timeout 3 gz topic -e -n 1 -t /model/robot/pose | head -40
echo "--- dynamic_pose/info header ---"
timeout 3 gz topic -e -n 1 -t /world/room/dynamic_pose/info | head -12
pkill -f "gz sim"
