#!/bin/bash
# Plumbing control: M0 with the drone images as BOTH map and queries must localize (near-)perfectly. If not, the 0 % on ground queries could be a pipeline bug.
cd /mnt/a/SlamProject/vps
python3 harness.py --method m0 --map /root/data/ud0_img --queries /root/data/ud0_img --out /root/m0_ctrl.json --seed 0 2>&1 | grep -E 'M0 map|"n"|localized|recall@0.25|recall@5|median'
