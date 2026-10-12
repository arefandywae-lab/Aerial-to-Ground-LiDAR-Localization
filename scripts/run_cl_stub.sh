#!/bin/bash
export STUB=1 TIMEOUT_X=0.15
bash /mnt/a/SlamProject/scripts/closed_loop.sh /root/worlds/urban.sdf "0,-85;0,-50;50,-50" /mnt/a/SlamProject/results/urban/closedloop_stub.npz 1.0 0
