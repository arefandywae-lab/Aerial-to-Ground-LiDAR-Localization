source /opt/ros/jazzy/setup.bash
timeout 10 ros2 topic echo /gt/ground --once 2>/dev/null | grep -A3 "translation" | head -n 5
timeout 6 ros2 topic echo /cmd_vel --once 2>/dev/null | head -n 8
timeout 5 ros2 topic echo /clock --once 2>/dev/null | head -n 3
