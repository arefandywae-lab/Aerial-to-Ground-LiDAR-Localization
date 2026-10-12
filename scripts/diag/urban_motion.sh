#!/bin/bash
# C-smoke part 2: real-time factor WITH the bridge (sensors rendering) and whether drone / ground robot follow commands. Nothing is recorded.
cd /root
source /opt/ros/jazzy/setup.bash
R=/mnt/a/SlamProject
P="python3 $R/scripts/diag/gt_pos.py"
pkill -f "gz sim" 2>/dev/null; pkill -f parameter_bridge 2>/dev/null; pkill -f fly_waypoints 2>/dev/null; pkill -f drive_waypoints 2>/dev/null; sleep 1
gz sim -s -r --headless-rendering /root/worlds/urban.sdf > /tmp/urban_gz.log 2>&1 &
sleep 25
ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=$R/ros/bridge_urban.yaml > /tmp/urban_br.log 2>&1 &
sleep 8
python3 - <<'PY'
import re, subprocess, time
def sim():
    out = subprocess.run(["timeout", "3", "gz", "topic", "-e", "-n", "1", "-t", "/clock"], capture_output=True, text=True).stdout
    m = re.search(r"sim\s*\{\s*sec:\s*(\d+)\s*nsec:\s*(\d+)", out)
    return int(m[1]) + int(m[2]) * 1e-9 if m else None
a, ta = sim(), time.time(); time.sleep(15); b, tb = sim(), time.time()
print("RTF with sensors active:", round((b - a) / (tb - ta), 2) if a and b else "n/a")
PY
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader
echo "drone start:  $($P /gt/drone drone)"
python3 $R/ros/fly_waypoints.py "-90,-90,45;-60,-90,45" 4 > /tmp/fly.log 2>&1 &
FLY=$!
sleep 6;  echo "drone +6 s:   $($P /gt/drone drone)"
sleep 8;  echo "drone +14 s:  $($P /gt/drone drone)   (target -60,-90,45)"
kill $FLY 2>/dev/null; wait $FLY 2>/dev/null; tail -3 /tmp/fly.log
echo "ground start: $($P /gt/ground robot)"
python3 $R/ros/drive_waypoints.py "0,-60" 0.8 /gt/ground /cmd_vel robot > /tmp/drive.log 2>&1 &
DRV=$!
sleep 14; echo "ground +14 s: $($P /gt/ground robot)   (target 0,-60)"
kill $DRV 2>/dev/null; wait $DRV 2>/dev/null; tail -3 /tmp/drive.log
pkill -f parameter_bridge; pkill -f "gz sim"
echo MOTION_DONE
