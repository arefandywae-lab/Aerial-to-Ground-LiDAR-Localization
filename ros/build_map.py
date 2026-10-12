#!/usr/bin/env python3
"""Accumulate FAST-LIO /cloud_registered (world frame) into one voxel-downsampled map.
usage: build_map.py ODOM_BAG OUT.npy [voxel=0.1]   -> Nx3 float32 (ASCII PCD written next to it)"""
import sys

import numpy as np
from eval_ate import read
from sensor_msgs_py import point_cloud2


def main(bag, out, voxel=0.1):
    pts = []
    for _, m in read(bag, ["/cloud_registered"])["/cloud_registered"]:
        a = point_cloud2.read_points_numpy(m, field_names=("x", "y", "z"))
        pts.append(np.floor(a / voxel).astype(np.int32))  # voxelise per scan to bound memory
    k = np.unique(np.concatenate(pts), axis=0)
    m = ((k + 0.5) * voxel).astype(np.float32)
    np.save(out, m)
    with open(out.replace(".npy", ".pcd"), "w") as f:
        f.write(f"VERSION .7\nFIELDS x y z\nSIZE 4 4 4\nTYPE F F F\nCOUNT 1 1 1\nWIDTH {len(m)}\nHEIGHT 1\n"
                f"VIEWPOINT 0 0 0 1 0 0 0\nPOINTS {len(m)}\nDATA ascii\n")
        np.savetxt(f, m, fmt="%.3f")
    print(f"map: {len(m)} voxels @ {voxel}m, extent {m.min(0)} .. {m.max(0)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0.1)
