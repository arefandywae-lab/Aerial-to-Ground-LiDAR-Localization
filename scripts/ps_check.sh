date
ps -eo pid,etime,cmd | grep -E "gz sim|ros2|rosbag|drive_wayp|world_pipeline|run_all|harness|fly_way|closed_loop" | grep -v grep | cut -c1-130
df -h /root | tail -1; free -m | head -2
ls -la /root/data/w_oldtown12/ug 2>&1 | head -5
