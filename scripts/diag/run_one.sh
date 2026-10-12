#!/bin/bash
# run one harness job with visible errors. usage: run_one.sh METHOD QUERIES_SESSION SEED   (map = s0v2, M1 map = map_s0v2.npz)
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_s0v2.npz M1LF_FP16=0 M1LF_COARSE=1
python3 harness.py --method $1 --map /root/data/s0v2_img --queries /root/data/$2_img --out ../results/v2/$1_$2_s$3.json --seed $3 2>&1 | grep -v Warn | tail -${4:-12}
