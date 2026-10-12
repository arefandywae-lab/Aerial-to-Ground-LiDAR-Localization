#!/bin/bash
# Recall-vs-threshold + inlier-gated precision curves for dataset v2 (seed 0; M1-LoFTR is seed-invariant). CPU only.
R=/mnt/a/SlamProject/results/v2; O=/mnt/a/SlamProject/docs/figures
python3 /mnt/a/SlamProject/scripts/plot_recall.py $O/v2_q1_same_direction.png $R/m0_q1v2_s0_err.npy $R/m1lf_q1v2_s0_err.npy
python3 /mnt/a/SlamProject/scripts/plot_recall.py $O/v2_q2_reversed.png $R/m0_q2v2_s0_err.npy $R/m1lf_q2v2_s0_err.npy $R/yaw0_q2v2_err.npy $R/yaw4_q2v2_err.npy
