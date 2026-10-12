#!/bin/bash
cd /mnt/a/SlamProject/vps
python3 viewpoints.py /root/data/map_ud0.npz /root/data/views_ud0.npy 6 8 0.44
cp /root/data/views_ud0_layout.png /mnt/a/SlamProject/docs/figures/urban_viewpoints.png
python3 - <<'PY'
import numpy as np
T = np.load("/root/data/views_ud0.npy")
R = T[:, :3, :3]
print("orthonormal:", bool(np.allclose(np.einsum("nij,nkj->nik", R, R), np.eye(3), atol=1e-9)), "| det +1:", bool(np.allclose(np.linalg.det(R), 1)))
print("forward axes horizontal:", bool(np.allclose(R[:, 2, 2], 0)), "| camera z:", np.unique(T[:, 2, 3]))
PY
