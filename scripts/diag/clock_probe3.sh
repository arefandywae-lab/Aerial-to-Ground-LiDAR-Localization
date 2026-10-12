#!/bin/bash
# Who publishes gz /clock? Start one server, wait past the usual onset (~sim 26 s), then list publishers.  usage: clock_probe3.sh WORLD.sdf
source /opt/ros/jazzy/setup.bash
pkill -f "gz sim" 2>/dev/null; sleep 1
gz sim -s -r --headless-rendering "$1" > /tmp/probe_gz.log 2>&1 &
sleep 40
echo "--- gz topic -i /clock ---"
gz topic -i -t /clock 2>&1 | head -12
echo "--- gz sim processes ---"
pgrep -fa "gz sim" | cut -c1-100
echo "--- partition / env ---"
env | grep -E "^GZ_|^IGN_|ROS_DOMAIN|ROS_LOCALHOST"
echo "--- /clock sim samples (6 s) ---"
timeout 6 gz topic -e -t /clock > /tmp/probe_clock.txt 2>/dev/null
python3 - <<'EOF'
import re
s = open("/tmp/probe_clock.txt").read()
t = [int(a) + int(b) * 1e-9 for a, b in re.findall(r"sim\s*\{\s*sec:\s*(\d+)\s*nsec:\s*(\d+)", s)]
bad = sum(1 for x, y in zip(t, t[1:]) if y <= x)
print(f"samples {len(t)} non-increasing {bad} range {t[0]:.2f}..{t[-1]:.2f}" if t else "none")
EOF
pkill -f "gz sim"
