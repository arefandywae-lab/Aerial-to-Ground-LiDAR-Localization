#!/bin/bash
mkdir -p /root/worlds
for sp in "grid 11" "oldtown 12" "suburb 13" "bridge 14" "canyon 15"; do set -- $sp; python3 /mnt/a/SlamProject/worlds/gen_city.py --style $1 --seed $2 --out /root/worlds/$1$2.sdf; done
cp /root/worlds/*_layout.png /mnt/a/SlamProject/docs/figures/ 2>/dev/null
