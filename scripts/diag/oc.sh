#!/bin/bash
source /opt/ros/jazzy/setup.bash
for b in "$@"; do echo "== $b"; python3 /mnt/a/SlamProject/scripts/diag/order_check.py /root/data/$b 2>&1 | grep -v "^\[" ; done
