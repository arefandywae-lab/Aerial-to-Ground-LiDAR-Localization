#!/usr/bin/env bash
# Record one session in the urban world (headless). usage: run_urban_session.sh WORLD.sdf drone|ground "WAYPOINTS" OUT_DIR [speed]
#  drone : "x,y,z;..."  fly_waypoints.py (yaw follows travel direction); records LiDAR, IMU, camera, stamped GT
#  ground: "x,y;..."    drive_waypoints.py; records camera + stamped GT (camera-only vehicle)
set -em
source /opt/ros/jazzy/setup.bash
R=$(dirname "$(readlink -f "$0")")
MODE=$2
gz sim -s -r --headless-rendering "$1" > /tmp/gz.log 2>&1 & GZ=$!
sleep 25
ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=$R/bridge_urban.yaml > /tmp/br.log 2>&1 & BR=$!
sleep 6
if [ "$MODE" = drone ]; then
  TOPICS="/clock /drone/lidar/points /drone/imu /drone/camera/image_raw /drone/camera/camera_info /gt/drone"
else
  TOPICS="/clock /ground/camera/image_raw /ground/camera/camera_info /gt/ground"
fi
ros2 bag record -o "$4" --storage-preset-profile zstd_fast $TOPICS > /tmp/bag.log 2>&1 & BAG=$!
sleep 3   # IMU must be static at the start for FAST-LIO's gravity initialisation
if [ "$MODE" = drone ]; then
  python3 $R/fly_waypoints.py "$3" ${5:-4} /gt/drone /drone/cmd_vel drone
else
  python3 $R/drive_waypoints.py "$3" ${5:-1.0} /gt/ground /cmd_vel robot
fi
sleep 1
kill -INT $BAG; wait $BAG 2>/dev/null || true
pkill -f parameter_bridge; pkill -f "gz sim"; sleep 2
echo "bag: $4"
