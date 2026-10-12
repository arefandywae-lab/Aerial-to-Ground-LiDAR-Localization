#!/bin/bash
# Finish dataset v2 evaluation after recovering q2v2: re-dump q2v2 images, run M0 and M1-LoFTR(f0c1) x 3 seeds on q2v2.
cd /root
source /opt/ros/jazzy/setup.bash
rm -rf /root/data/q2v2_img
python3 /mnt/a/SlamProject/vps/dump_session.py /root/data/q2v2 /root/data/q2v2_img 3 2>&1 | tail -1
sync
python3 - <<'EOF'
import numpy as np
T = np.load("/root/data/q2v2_img/poses.npy"); print("q2v2 poses", T.shape, "cam z", T[:, 2, 3].mean().round(3))
EOF
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_s0v2.npz
for s in 0 1 2; do
  python3 harness.py --method m0 --map /root/data/s0v2_img --queries /root/data/q2v2_img --out ../results/v2/m0_q2v2_s$s.json --seed $s > /dev/null 2>&1
  M1LF_FP16=0 M1LF_COARSE=1 python3 harness.py --method m1lf --map /root/data/s0v2_img --queries /root/data/q2v2_img \
    --out ../results/v2/m1lf_q2v2_s$s.json --seed $s > /dev/null 2>&1
  echo "done q2v2 seed $s"
done
echo FINISH_DONE
