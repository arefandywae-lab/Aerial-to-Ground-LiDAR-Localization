#!/bin/bash
# C-render ladder, benchmarked by D0 (render at the query's own GT pose; baseline 8.8 %, naive fill 35.1 %).
cd /mnt/a/SlamProject/vps
python3 /mnt/a/SlamProject/scripts/fill_colors2.py /root/data/map_ud0.npz /root/data/map_ud0_f2.npz 1.0 16 0.8
export M1_ZFAR=120
d0() { echo "--- $1"; M1_MAP=$2 M1_SPLAT=$3 M1_RMAX=$4 python3 /mnt/a/SlamProject/scripts/urban_d0.py 2>&1 | grep -v -i warn | sed 's/^/    /'; }
d0 "class-aware fill, splat 0.03 m / 4 px (as before)"  /root/data/map_ud0_f2.npz 0.03 4
d0 "class-aware fill, splat 0.12 m / 4 px"              /root/data/map_ud0_f2.npz 0.12 4
d0 "class-aware fill, splat 0.12 m / 8 px"              /root/data/map_ud0_f2.npz 0.12 8
echo 1 > /proc/sys/vm/drop_caches
echo C_RENDER_DONE
