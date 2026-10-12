#!/bin/bash
cd /mnt/a/SlamProject
P="results/v2/mega_q1v2 results/v2/mega_q2v2 results/v2/mega_q3v2"
for cfg in "usable|10|all" "usable|10|inliers,inl_ratio,spread,top1,margin" "usable|10|inliers,inl_ratio,spread,top1,margin,d_render_t,d_render_rot"; do
  IFS='|' read -r lab l2 feats <<< "$cfg"
  echo "################ label=$lab l2=$l2 feats=$feats"
  GATE_LABEL=$lab GATE_L2=$l2 GATE_FEATS=$feats python3 scripts/confidence_gate.py $P 2>&1 | grep -E "held-out|AUROC|precision keeping|Brier|weights" 
done
