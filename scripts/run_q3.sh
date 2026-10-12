#!/bin/bash
# Evaluate on the held-out-yaw set q3v2: M0, M1-LoFTR with yaw 0 only (control), M1-LoFTR with yaw 0/90/180/270. Same step (6) for both M1 runs. Seed 0 (M1 is seed-invariant).
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_s0v2.npz M1LF_FP16=0 M1LF_COARSE=1 M1L_STEP=6
Q=/root/data/q3v2_img
python3 harness.py --method m0 --map /root/data/s0v2_img --queries $Q --out ../results/v2/m0_q3v2_s0.json --seed 0 > /dev/null 2>&1; echo "m0 done"
M1LF_YAWS=0 python3 harness.py --method m1lf --map /root/data/s0v2_img --queries $Q --out ../results/v2/yaw0_q3v2.json --seed 0 > /dev/null 2>&1; echo "yaw0 done"
M1LF_YAWS=0,90,180,270 python3 harness.py --method m1lf --map /root/data/s0v2_img --queries $Q --out ../results/v2/yaw4_q3v2.json --seed 0 > /dev/null 2>&1; echo "yaw4 done"
echo Q3_EVAL_DONE
