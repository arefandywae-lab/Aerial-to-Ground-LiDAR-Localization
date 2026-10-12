#!/usr/bin/env bash
# Replay a session bag through FAST-LIO2, record /Odometry (+ saved map PCD) into OUT_DIR.
# usage: run_lio.sh SESSION_BAG OUT_DIR [play_rate]
set -em
source /opt/ros/jazzy/setup.bash
source /root/ws/install/setup.bash
R=$(dirname "$(readlink -f "$0")")
# env: LIO_CFG (default fastlio_sim.yaml), LIDAR_TOPIC (/lidar/points), IMU_TOPIC (/imu)
CFG=${LIO_CFG:-$R/fastlio_sim.yaml}; LT=${LIDAR_TOPIC:-/lidar/points}; IT=${IMU_TOPIC:-/imu}
mkdir -p "$2"; rm -rf "$2/odom" "$2/sorted"
# replay in sim-time order (a loaded recorder can deliver messages ~0.5 s late; FAST-LIO drops IMU that goes back in time)
python3 $R/resort_bag.py "$1" "$2/sorted" /clock $IT $LT > "$2/resort.log" 2>&1
cd "$2"
python3 $R/lidar_prep.py --ros-args -p use_sim_time:=true -p in_topic:=$LT > prep.log 2>&1 & PREP=$!
ros2 run fast_lio fastlio_mapping --ros-args --params-file $CFG -p use_sim_time:=true > lio.log 2>&1 & LIO=$!
ros2 bag record -o odom --storage-preset-profile zstd_fast /Odometry /cloud_registered > rec.log 2>&1 & REC=$!
sleep 3
ros2 bag play sorted --clock --rate ${3:-1.0} --topics /clock $LT $IT > play.log 2>&1
sleep 2
kill -INT $REC; wait $REC 2>/dev/null || true
pkill -f fastlio_mapping; pkill -f lidar_prep.py; sleep 1
ls -la "$2"
