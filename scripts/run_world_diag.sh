#!/bin/bash
# retrieval vs matching per world (urban_diag.py D1/D2/D3) with the DISK+LightGlue configuration. Oracle view = nearest virtual view to the true pose.
cd /mnt/a/SlamProject/vps
export M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1LF_RETR=megaloc M1LF_COARSE=0 M1LF_FP16=0 M1LF_MATCHER=disklg M1LF_K=50
run() {  # name map_f2 views mapimg queries
  echo "=== $1"; M1_MAP=$2 M1_VIEWS=$3 DIAG_MAPIMG=$4 DIAG_QUERIES=$5 DIAG_OUT=/mnt/a/SlamProject/results/worlds/diag_$1.npz python3 /mnt/a/SlamProject/scripts/urban_diag.py 2>&1 | grep -E "queries,|D1|D2|D3 median|Error|Traceback"
  echo 1 > /proc/sys/vm/drop_caches
}
run orig /root/data/map_ud0_f2.npz /root/data/views_ud0.npy /root/data/ud0_img /root/data/ug2s_img
for W in grid11 bridge14 oldtown12 canyon15; do D=/root/data/w_$W; run $W $D/map_f2.npz $D/views.npy $D/ud_img $D/ugs_img; done
echo DIAG_DONE
