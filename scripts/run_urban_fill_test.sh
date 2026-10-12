#!/bin/bash
# Causal test: fill unseen map points' colour from coloured neighbours, then D0 (render at the query's own GT pose) again.
cd /mnt/a/SlamProject/vps
python3 /mnt/a/SlamProject/scripts/fill_colors.py /root/data/map_ud0.npz /root/data/map_ud0_filled.npz 0.75 5
sed -i 's#urban_d0_examples.png#urban_d0_examples_filled.png#' /mnt/a/SlamProject/scripts/urban_d0.py
export M1_MAP=/root/data/map_ud0_filled.npz M1_ZFAR=120
python3 /mnt/a/SlamProject/scripts/urban_d0.py 2>&1 | grep -v -i warn
sed -i 's#urban_d0_examples_filled.png#urban_d0_examples.png#' /mnt/a/SlamProject/scripts/urban_d0.py
echo 1 > /proc/sys/vm/drop_caches
