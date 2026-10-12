"""Street-level facade observation counts per 25 m cell (needs obs_count_ud0.npy from obs_count.py), next to the route-2 per-street error picture.
usage: obs_cells.py MAP.npz COUNTS.npy"""
import sys
import numpy as np
d = np.load(sys.argv[1]); p, n = d["pts"], d["normals"]; c = np.load(sys.argv[2])
m = (np.abs(n[:, 2]) < 0.3) & (p[:, 2] < 3)
cells = {}
for pt, cc in zip(p[m], c[m]):
    cells.setdefault((int(np.floor(pt[0] / 25)), int(np.floor(pt[1] / 25))), []).append(cc)
print("street-level facade points (z<3 m) per 25 m cell: share seen by 0 images | median count   (cell index x,y; x from -4 (west) to 3, y from -4 (south) to 3)")
ys = sorted({k[1] for k in cells}, reverse=True); xs = sorted({k[0] for k in cells})
print("       " + "".join(f"x={x:+d}        " for x in xs))
for y in ys:
    row = f"y={y:+d}  "
    for x in xs:
        a = np.array(cells.get((x, y), []))
        row += (f"{np.mean(a == 0):4.0%} |{np.median(a):3.0f}   " if len(a) > 50 else "   -  |  -   ") + "  "
    print(row)
