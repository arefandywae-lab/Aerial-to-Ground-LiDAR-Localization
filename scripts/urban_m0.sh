#!/bin/bash
# Series B first result: M0 (image map from the DRONE camera, GT-posed) on GROUND-camera queries along the streets.
cd /mnt/a/SlamProject/vps
mkdir -p ../results/urban
python3 /mnt/a/SlamProject/scripts/coverage_urban.py /root/data/map_ud0.npz
python3 harness.py --method m0 --map /root/data/ud0_img --queries /root/data/ug1_img --out ../results/urban/m0_ug1_s0.json --seed 0 2>&1 | grep -E 'M0 map|"n"|localized|recall|median|latency_ms_p50|gate40'
