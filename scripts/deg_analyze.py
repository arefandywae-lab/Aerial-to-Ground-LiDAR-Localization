import numpy as np, sys
E = np.load(sys.argv[1]); n = int(sys.argv[2]) if len(sys.argv) > 2 else 285
names = ["clean", "noise", "blur", "dark", "bright", "cast", "barrel", "jpeg"]
print(f"{'variant':8s} {'pose':>6s} {'(5m,10deg)':>11s} {'(0.5m,5deg)':>12s} {'median m':>9s}")
for i, nm in enumerate(names):
    e = E[i * n:(i + 1) * n]; ok = np.isfinite(e[:, 0])
    print(f"{nm:8s} {ok.mean():6.0%} {np.mean(ok & (e[:,0] <= 5) & (e[:,1] <= 10)):11.1%} {np.mean(ok & (e[:,0] <= .5) & (e[:,1] <= 5)):12.1%} {np.nanmedian(np.where(ok, e[:,0], np.nan)):9.2f}")
