#!/bin/bash
# does the render setting (splat radius / max radius in pixels), tuned on the original world, explain the dead matching in oldtown12? oracle diagnosis only.
cd /mnt/a/SlamProject/vps
export M1_ZFAR=120 M1LF_RETR=megaloc M1LF_COARSE=0 M1LF_FP16=0 M1LF_MATCHER=disklg M1LF_K=50
D=/root/data/w_oldtown12
for cfg in "0.06 4" "0.25 4" "0.12 10"; do
  set -- $cfg
  echo "=== oldtown12 splat $1 rmax $2"
  M1_SPLAT=$1 M1_RMAX=$2 M1_MAP=$D/map_f2.npz M1_VIEWS=$D/views.npy DIAG_MAPIMG=$D/ud_img DIAG_QUERIES=$D/ugs_img python3 /mnt/a/SlamProject/scripts/urban_diag.py 2>&1 | grep -E "D1|D2|Error|Traceback"
  echo 1 > /proc/sys/vm/drop_caches
done
echo SPLAT_DONE
