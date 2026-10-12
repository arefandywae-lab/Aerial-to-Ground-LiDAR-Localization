#!/bin/bash
# Start ONE headless Gazebo server on a world, sample the gz /clock topic (sim field only), report monotonicity.  usage: clock_probe.sh WORLD.sdf
source /opt/ros/jazzy/setup.bash
pkill -f "gz sim" 2>/dev/null; sleep 1
gz sim -s -r --headless-rendering "$1" > /tmp/probe_gz.log 2>&1 &
GZ=$!
sleep 15
echo "gz sim processes: $(pgrep -fc 'gz sim')"
timeout 8 gz topic -e -t /clock > /tmp/probe_clock.txt 2>/dev/null
python3 - <<'EOF'
import re
s = open("/tmp/probe_clock.txt").read()
t = [int(a) + int(b) * 1e-9 for a, b in re.findall(r"sim\s*\{\s*sec:\s*(\d+)\s*nsec:\s*(\d+)", s)]
bad = sum(1 for x, y in zip(t, t[1:]) if y <= x)
print(f"sim-clock samples {len(t)}, non-increasing steps {bad}, range {t[0]:.3f}..{t[-1]:.3f}" if t else "no samples parsed: " + s[:200])
EOF
kill $GZ 2>/dev/null; pkill -f "gz sim"; sleep 1
