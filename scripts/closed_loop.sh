#!/bin/bash
# Closed-loop run in Gazebo. usage: closed_loop.sh WORLD.sdf "ROUTE" OUT.npz [speed] [seed]
# The node loads the map/views first (several minutes), THEN the simulator starts, so the robot does not wait with the clock running.
WORLD=$1; ROUTE=$2; OUT=$3; SPEED=${4:-1.0}; export SEED=${5:-0}
source /opt/ros/jazzy/setup.bash
R=/mnt/a/SlamProject
export M1_MAP=${M1_MAP:-/root/data/map_ud0_f2.npz} M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=${M1_VIEWS:-/root/data/views_ud0.npy} M1LF_RETR=megaloc M1LF_COARSE=0 M1LF_FP16=0 M1LF_MATCHER=disklg M1LF_K=20 M1LF_PRIOR_R=20 M1LF_PRIOR_STRICT=1 M1LF_MAXD=8
export MAP_IMG=${MAP_IMG:-/root/data/ud0_img}
python3 -X faulthandler $R/ros/closed_loop.py "$ROUTE" "$OUT" $SPEED > /tmp/cl_node.log 2>&1 & NODE=$!
for i in $(seq 1 180); do grep -q "ready" /tmp/cl_node.log && break; sleep 5; done
gz sim -s -r --headless-rendering "$WORLD" > /tmp/gz.log 2>&1 & GZ=$!
sleep 25
ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=$R/ros/bridge_urban.yaml > /tmp/br.log 2>&1 & BR=$!
wait $NODE
pkill -f parameter_bridge; pkill -f "gz sim"; sleep 2
grep -E "RESULT|Error|Traceback" /tmp/cl_node.log | tail -n 5
echo 1 > /proc/sys/vm/drop_caches
echo CLOSEDLOOP_DONE
