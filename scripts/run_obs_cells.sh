#!/bin/bash
python3 /mnt/a/SlamProject/scripts/obs_count.py /root/data/map_ud0.npz /root/data/ud0_img /root/data/obs_count_ud0.npy
python3 /mnt/a/SlamProject/scripts/obs_cells.py /root/data/map_ud0.npz /root/data/obs_count_ud0.npy
echo 1 > /proc/sys/vm/drop_caches
