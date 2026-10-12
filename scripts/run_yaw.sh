#!/bin/bash
# Does adding yawed virtual viewpoints fix the reversed-direction queries (q2v2)? Same STEP everywhere so only the yaw set changes.
#  A: yaws=0 (as before) step 6   B: yaws=0,90,180,270 step 6 on q2v2   C: B on q1v2 (regression check). Deterministic across seeds -> seed 0 only.
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_s0v2.npz M1LF_FP16=0 M1LF_COARSE=1 M1L_STEP=6
run() { python3 harness.py --method m1lf --map /root/data/s0v2_img --queries /root/data/$2_img --out ../results/v2/$3.json --seed 0 2>&1 \
  | grep -E 'M1LF map|localized|recall@0.25|recall@5|latency_ms_p50|gate40_prec' | tr -d ' \n'; echo; }
echo "== A yaws=0 q2v2";            M1LF_YAWS=0 run x q2v2 yaw0_q2v2
echo "== B yaws=0,90,180,270 q2v2"; M1LF_YAWS=0,90,180,270 run x q2v2 yaw4_q2v2
echo "== C yaws=0,90,180,270 q1v2"; M1LF_YAWS=0,90,180,270 run x q1v2 yaw4_q1v2
echo YAW_DONE
