#!/bin/bash
# background-leak filter (CRISTAL-style) in the renderer: oracle diagnosis on oldtown12 and grid11 (reference oldtown12 oracle (5 m,10 deg) 13.3 %, grid11 56.2 %)
while ! grep -q SPLAT_DONE /mnt/a/SlamProject/scripts/splat.log; do sleep 20; done
cd /mnt/a/SlamProject/vps
export M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1LF_RETR=megaloc M1LF_COARSE=0 M1LF_FP16=0 M1LF_MATCHER=disklg M1LF_K=50
for W in oldtown12 grid11; do for L in 0.25 0.05; do
  D=/root/data/w_$W; echo "=== $W leak $L"
  M1_LEAK=$L M1_MAP=$D/map_f2.npz M1_VIEWS=$D/views.npy DIAG_MAPIMG=$D/ud_img DIAG_QUERIES=$D/ugs_img python3 /mnt/a/SlamProject/scripts/urban_diag.py 2>&1 | grep -E "D1|D2|Error|Traceback"
  echo 1 > /proc/sys/vm/drop_caches
done; done
echo LEAK_DONE
