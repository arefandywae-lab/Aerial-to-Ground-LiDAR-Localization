cd /mnt/a/SlamProject
for m in 60 100 150; do echo "== GLOBAL poses, kidnapped start, INLMIN=$m, INJECT=0.1 SXY=1.5, 5000 particles"; env KIDNAP=1 INLMIN=$m INJECT=0.1 SXY=1.5 python3 scripts/mcl_test.py /root/data/seq_ug2_disklg_global.npz 0.01 0.1 0.5 5000 2>&1 | grep -E "KIDNAPPED|MCL estimate|spread < 0.7" | cut -c1-250; done
python3 - <<'PY'
import numpy as np
d=np.load('/root/data/seq_ug2_disklg_global.npz'); G=d['gt']; P=d['poses']; inl=d['inl']
e=np.array([np.linalg.norm(P[i][:3,3]-G[i][:3,3]) for i in range(len(G))])
for m in (40,60,100,150,200): k=inl>=m; print('inl>=',m,'frames',int(k.sum()),'share wrong(>5m)',round(float(np.mean(e[k]>5)),3))
PY
