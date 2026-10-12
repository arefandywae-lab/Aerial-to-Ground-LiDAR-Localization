import sys, numpy as np
sys.path.insert(0, "/mnt/a/SlamProject/ros")
import eval_ate
for sess, od in (("/root/data/ud0", "/root/data/lio_ud0/odom"), ("/root/data/w_grid11/ud", "/root/data/w_grid11/lio/odom")):
    a = eval_ate.align(sess, od, "drone", "/gt/drone"); g, ep, err, R = a["gt"], a["est"], a["err"], a["R"]
    pe = np.linalg.norm(np.diff(ep, axis=0), axis=1); pg = np.linalg.norm(np.diff(g, axis=0), axis=1)
    print(sess, "poses", len(ep), "| odom path", round(float(pe.sum()), 0), "m, gt path (interp) ", round(float(pg.sum()), 0), "m | odom step median", round(float(np.median(pe)), 3), "max", round(float(pe.max()), 2), "| gt step max", round(float(pg.max()), 2))
    print("   err every 10 %:", [round(float(err[int(i * len(err) / 10)]), 1) for i in range(10)], "worst at index", int(np.argmax(err)), "of", len(err))
