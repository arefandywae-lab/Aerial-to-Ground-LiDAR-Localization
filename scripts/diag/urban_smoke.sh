#!/bin/bash
# C-smoke: does urban.sdf load, what is the real-time factor, do all bridged topics carry data, do the drone and ground robot move on command?
# Needs the GPU to itself (do not run next to an evaluation). Output is a plain report; nothing is recorded.
cd /root
source /opt/ros/jazzy/setup.bash
R=/mnt/a/SlamProject
pkill -f "gz sim" 2>/dev/null; pkill -f parameter_bridge 2>/dev/null; pkill -f fly_waypoints 2>/dev/null; pkill -f drive_waypoints 2>/dev/null; sleep 1
mkdir -p /root/worlds
python3 $R/worlds/gen_urban.py --out /root/worlds/urban.sdf | tail -1
gz sim -s -r --headless-rendering /root/worlds/urban.sdf > /tmp/urban_gz.log 2>&1 &
GZ=$!
sleep 25
echo "--- gz alive: $(pgrep -fc 'gz sim')  | errors in gz log:"; grep -iE "error|fail|cannot|not found" /tmp/urban_gz.log | head -8
echo "--- gz topics of interest"; gz topic -l | grep -E "clock|drone|^/camera|/lidar|/imu|cmd_vel|/model/.*/pose$"
echo "--- real-time factor over 10 s (sim s per wall s)"
python3 - <<'PY'
import re, subprocess, time
def sim():
    out = subprocess.run(["timeout", "3", "gz", "topic", "-e", "-n", "1", "-t", "/clock"], capture_output=True, text=True).stdout
    m = re.search(r"sim\s*\{\s*sec:\s*(\d+)\s*nsec:\s*(\d+)", out)
    return int(m[1]) + int(m[2]) * 1e-9 if m else None
a, ta = sim(), time.time()
time.sleep(10)
b, tb = sim(), time.time()
print("sim", a, "->", b, "RTF", round((b - a) / (tb - ta), 2) if a is not None and b is not None else "n/a")
PY
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader
ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=$R/ros/bridge_urban.yaml > /tmp/urban_br.log 2>&1 &
sleep 6
echo "--- ros topics"; ros2 topic list | grep -E "clock|drone|ground|gt|cmd_vel"
for t in /drone/lidar/points /drone/imu /drone/camera/image_raw /drone/camera/camera_info /ground/camera/image_raw /gt/drone /gt/ground; do
  if timeout 8 ros2 topic echo --once $t > /tmp/smoke_msg.txt 2>/dev/null; then echo "OK   $t  ($(wc -c < /tmp/smoke_msg.txt) bytes)"; else echo "FAIL $t (no message in 8 s)"; fi
done
echo "--- ground GT frames"; timeout 5 ros2 topic echo --once /gt/ground 2>/dev/null | grep -E "child_frame_id" | sort -u | head -8
echo "--- drone GT frames";  timeout 5 ros2 topic echo --once /gt/drone  2>/dev/null | grep -E "child_frame_id" | sort -u | head -8
pos() { timeout 5 ros2 topic echo --once $1 2>/dev/null | python3 -c "
import sys,re
t=sys.stdin.read(); blocks=t.split('- header')
for b in blocks:
    if re.search(r'child_frame_id: $2\n', b):
        v=[float(x) for x in re.findall(r'^\s+[xyz]: (-?[\d.e+-]+)', b.split('rotation')[0], re.M)]
        print(v); break
"; }
echo "--- drone before:"; pos /gt/drone drone
python3 $R/ros/fly_waypoints.py "-90,-90,45;-60,-90,45" 4 > /tmp/fly.log 2>&1 &
FLY=$!
sleep 14
echo "--- drone after 14 s (target -60,-90,45):"; pos /gt/drone drone
kill $FLY 2>/dev/null
echo "--- ground before:"; pos /gt/ground robot
python3 $R/ros/drive_waypoints.py "0,-60" 0.8 /gt/ground /cmd_vel robot > /tmp/drive.log 2>&1 &
DRV=$!
sleep 14
echo "--- ground after 14 s (target 0,-60):"; pos /gt/ground robot
kill $DRV 2>/dev/null
pkill -f parameter_bridge; pkill -f "gz sim"
echo SMOKE_DONE
