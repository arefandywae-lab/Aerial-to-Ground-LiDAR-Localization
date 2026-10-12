#!/bin/bash
for f in route2_prior_s5r20 route2_global; do echo "== $f"; python3 /mnt/a/SlamProject/scripts/route2_strata.py /mnt/a/SlamProject/results/urban/${f}_err.npy; done
