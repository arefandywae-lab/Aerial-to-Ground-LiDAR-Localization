#!/bin/bash
# C-heldout: the render settings (class-aware fill, splat 0.12 m) were chosen on ug1s (every 4th query, offset 0). Evaluate on DISJOINT queries (every 4th, offset 2) with no re-tuning.
cd /root
python3 - <<'PY'
import os, shutil, numpy as np
src, dst = "/root/data/ug1_img", "/root/data/ug1h_img"
shutil.rmtree(dst, ignore_errors=True); os.makedirs(dst + "/images")
names = sorted(os.listdir(src + "/images"))[2::4]
T = np.load(src + "/poses.npy")[2::4]
for i, n in enumerate(names):
    os.symlink(f"{src}/images/{n}", f"{dst}/images/{i:05d}.png")
np.save(dst + "/poses.npy", T); shutil.copy(src + "/K.npy", dst + "/K.npy")
print("held-out subset", len(names), "queries")
PY
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_COARSE=1 M1LF_FP16=0 M1LF_K=50 M1LF_TOPN=12
echo "--- held-out, prior sigma 5 m radius 20 m"
PRIOR_SIGMA=5 M1LF_PRIOR_R=20 python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/ug1h_img --out ../results/urban/heldout_prior_s5r20.json --seed 0 2>&1 | grep -E "\"n\"|localized|recall|median_t|latency_ms_p50" | tr -d ' \n'; echo
echo "--- held-out, no prior (global)"
python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/ug1h_img --out ../results/urban/heldout_global.json --seed 0 2>&1 | grep -E "\"n\"|localized|recall|median_t|latency_ms_p50" | tr -d ' \n'; echo
echo 1 > /proc/sys/vm/drop_caches
echo HELDOUT_DONE
