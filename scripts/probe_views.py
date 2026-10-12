import numpy as np
V = np.load("/root/data/views_ud0.npy"); P = V[:, :2, 3]
for q in [(0, -85), (0, -70), (0, -50), (51, -76), (-50, 0)]:
    d = np.linalg.norm(P - np.array(q), axis=1); n = (d < 20).sum()
    print(f"prior {q}: views within 20 m: {n} ({len(np.unique(np.round(P[d<20],0),axis=0))} positions); nearest {d.min():.1f} m")
u = np.unique(np.round(P, 0), axis=0); print("view positions:", len(u), "extent x", u[:,0].min(), u[:,0].max(), "y", u[:,1].min(), u[:,1].max())
print("positions with y<-80:", u[u[:,1] < -80].tolist()[:20])
