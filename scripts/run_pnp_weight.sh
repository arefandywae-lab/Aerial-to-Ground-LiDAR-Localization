#!/bin/bash
python3 /mnt/a/SlamProject/scripts/pnp_weight_test.py /root/data/seq_ug2.npz 2>&1 | grep -v -i warn
