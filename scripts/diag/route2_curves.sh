#!/bin/bash
cd /mnt/a/SlamProject/results/urban
python3 /mnt/a/SlamProject/scripts/gate_curve.py route2_prior_s5r20_err.npy route2_global_err.npy | grep -E "==|   40 |   80 |  150 "
