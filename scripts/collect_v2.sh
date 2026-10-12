#!/bin/bash
# Dataset v2 (room, distinct textures): map session s0v2 + query sessions q1v2 (1 m outside, same direction) and
# q2v2 (1 m outside, REVERSED direction => ~180 deg yaw change). Headless Gazebo, one session at a time (GPU).
# Waypoints for s0/q1 are the coarse polylines recovered from the v1 GT (scripts/diag/trajectory.py); v1 recorded none.
set -e
R=/mnt/a/SlamProject
source /opt/ros/jazzy/setup.bash
mkdir -p /root/worlds /root/data
python3 $R/worlds/gen_world.py --distinct 1 --seed 0 --out /root/worlds/room_v2.sdf
S0="-11.7,-8.0;-12.0,7.9;11.9,8.0;12.0,-7.9;-11.9,-8.0"
Q1="-11.7,-8.0;-13.0,8.9;12.9,9.0;13.0,-9.0;-12.9,-9.0"
Q2="-13.0,-9.0;13.0,-9.0;13.0,9.0;-13.0,9.0;-13.0,-8.5"
for cfg in "s0v2|$S0" "q1v2|$Q1" "q2v2|$Q2"; do
  name=${cfg%%|*}; wps=${cfg#*|}
  [ -d /root/data/$name ] && { echo "skip $name (exists)"; continue; }
  echo "=== record $name ==="
  bash $R/ros/run_session.sh /root/worlds/room_v2.sdf "$wps" /root/data/$name 0.8
  python3 $R/vps/dump_session.py /root/data/$name /root/data/${name}_img 3  # same subsampling as v1
done
echo COLLECT_DONE
