#!/bin/bash
# DECISIVE TEST: M1-LoFTR (drone LiDAR map, ground-level virtual views, MegaLoc retrieval) on a quarter of the ground-camera queries along the streets.
cd /root
pkill -f run_latency_sweep 2>/dev/null; pkill -f "harness.py" 2>/dev/null; sleep 2
python3 - <<'PY'
import os, shutil, numpy as np
src, dst = "/root/data/ug1_img", "/root/data/ug1s_img"
shutil.rmtree(dst, ignore_errors=True); os.makedirs(dst + "/images")
names = sorted(os.listdir(src + "/images"))[::4]
T = np.load(src + "/poses.npy")[::4]
for i, n in enumerate(names):
    os.symlink(f"{src}/images/{n}", f"{dst}/images/{i:05d}.png")
np.save(dst + "/poses.npy", T); shutil.copy(src + "/K.npy", dst + "/K.npy")
print("subset", len(names), "queries")
PY
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0.npz M1_ZFAR=120 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_K=50 M1LF_TOPN=12 M1LF_COARSE=1 M1LF_FP16=0
python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/ug1s_img --out ../results/urban/m1_ug1s.json --seed 0 2>&1 | grep -E "M1LF map|\"n\"|localized|recall|median|latency_ms_p50|latency_ms_p95|gate40"
echo 1 > /proc/sys/vm/drop_caches
echo URBAN_M1_DONE
