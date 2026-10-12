#!/bin/bash
# After an unclean WSL shutdown: find empty/unreadable data files and unreadable bags.
cd /root; source /opt/ros/jazzy/setup.bash
echo "zero-size files under /root/data (excluding images):"; find /root/data -type f -size 0 -not -path "*/images/*" | head
python3 - <<'PY'
import glob, os, numpy as np
bad = []
for f in sorted(glob.glob("/root/data/*.npz") + glob.glob("/root/data/*_img/*.npy") + glob.glob("/root/data/*.npy") + glob.glob("/mnt/a/SlamProject/results/**/*.npy", recursive=True)):
    try:
        a = np.load(f, allow_pickle=False)
        if hasattr(a, "files"):
            for k in a.files: a[k].shape
    except Exception as e:
        bad.append((f, type(e).__name__))
print("unreadable npy/npz:", bad or "none")
for d in sorted(glob.glob("/root/data/*_img")):
    n = len(os.listdir(d + "/images")); T = np.load(d + "/poses.npy")
    if n != len(T): print("MISMATCH", d, n, len(T))
print("session image/pose counts consistent")
PY
for b in ud0 ug1 q1v2 q2v2 q3v2 s0v2; do
  python3 -c "
import sys; sys.path.insert(0,'/mnt/a/SlamProject/ros')
from eval_ate import read
d=read('/root/data/$b',['/clock']); print('$b clock msgs', len(d['/clock']))" 2>&1 | tail -1
done
ls -la /root/data/lio_ud0/odom 2>/dev/null | head -4
