#!/usr/bin/env bash
# Record one session: world sdf + waypoints -> rosbag2 in OUT. Headless.
# usage: run_session.sh world.sdf "x,y;x,y;..." OUT_DIR [speed]
set -em  # -m: job control, so background jobs accept SIGINT (needed to finalize the bag)
source /opt/ros/jazzy/setup.bash
R=$(dirname "$(readlink -f "$0")")
gz sim -s -r --headless-rendering "$1" > /tmp/gz.log 2>&1 & GZ=$!
sleep 12
ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=$R/bridge.yaml > /tmp/br.log 2>&1 & BR=$!
sleep 5
ros2 bag record -o "$3" --storage-preset-profile zstd_fast /clock /lidar/points /imu /camera/image_raw /camera/camera_info /gt/poses /gt/model > /tmp/bag.log 2>&1 & BAG=$!
sleep 2
python3 $R/drive_waypoints.py "$2" ${4:-0.8}
sleep 1
kill -INT $BAG; wait $BAG 2>/dev/null || true
pkill -f parameter_bridge; pkill -f "gz sim"; sleep 2
echo "bag: $3"
