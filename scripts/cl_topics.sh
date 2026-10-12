source /opt/ros/jazzy/setup.bash
ros2 topic list 2>/dev/null | grep -E "gt|camera|cmd_vel|clock"
timeout 8 ros2 topic hz /ground/camera/image_raw 2>&1 | tail -n 2
timeout 5 ros2 topic echo /cmd_vel --once 2>&1 | head -n 8
tail -n 3 /tmp/cl_node.log | cut -c1-200
