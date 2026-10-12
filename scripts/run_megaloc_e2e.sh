#!/bin/bash
# End-to-end with vector retrieval on the room (same map/yaw set/step as results/v2/yaw4_*): MegaLoc top-50 -> coarse LoFTR -> full LoFTR on 12 -> PnP.
# Compare with yaw4_q2v2 (53.3 % strict, 5 wrong), yaw4_q3v2 (56.9 %, 13 wrong), yaw4_q1v2 (85.0 %, 5 wrong) which brute-forced all 236 renders.
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_s0v2.npz M1LF_FP16=0 M1LF_COARSE=1 M1L_STEP=6 M1LF_YAWS=0,90,180,270 M1LF_RETR=megaloc M1LF_K=50
for q in q2v2 q3v2 q1v2; do
  python3 harness.py --method m1lf --map /root/data/s0v2_img --queries /root/data/${q}_img --out ../results/v2/mega_${q}.json --seed 0 > /root/mega_${q}.log 2>&1
  echo "done $q"; grep -E 'localized|recall@0.25|recall@5|latency_ms_p50|latency_ms_p95' ../results/v2/mega_${q}.json | tr -d ' \n'; echo
  echo 1 > /proc/sys/vm/drop_caches
done
echo MEGA_E2E_DONE
