#!/bin/bash
cd /root; source /opt/ros/jazzy/setup.bash; source /root/ws/install/setup.bash
python3 /mnt/a/SlamProject/ros/eval_ate.py /root/data/s0v2 /root/data/lio_s0v2/odom
