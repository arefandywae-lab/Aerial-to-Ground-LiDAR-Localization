"""One-off: convert seq_ug2.npz written by the OLD seq_collect (pickled ragged object arrays, our own file from this session, never external data) into the pickle-free format.
usage: convert_seq.py IN.npz OUT.npz"""
import sys
import numpy as np
d = np.load(sys.argv[1], allow_pickle=True)  # trusted: produced locally by scripts/seq_collect.py (old version) moments ago
p2, p3 = list(d["p2"]), list(d["p3"])
off = np.cumsum([0] + [len(x) for x in p2])
np.savez(sys.argv[2], poses=d["poses"], gt=d["gt"], inl=d["inl"], K=d["K"], off=off, p2=np.concatenate(p2), p3=np.concatenate(p3))
print("converted", len(p2), "frames,", int(off[-1]), "correspondences")
