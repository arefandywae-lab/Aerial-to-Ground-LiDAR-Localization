#!/bin/bash
ls -la --time-style=full-iso /root/data/seq_ug2.npz
python3 - <<'PY'
import numpy as np
d = np.load("/root/data/seq_ug2.npz", allow_pickle=False) if False else np.load("/root/data/seq_ug2.npz")
print("keys:", d.files)
PY
ps -eo pid,etime,cmd | grep -E "seq_collect|harness" | grep -v grep | cut -c1-90
date
