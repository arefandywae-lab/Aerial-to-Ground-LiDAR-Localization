cd /mnt/a/SlamProject
for v in "INJECT=0 SXY=1.5" "INJECT=0.1 SXY=0.6" "INJECT=0.1 SXY=1.5" "INJECT=0.2 SXY=1.5"; do echo "== $v (odo 1%+0.1, EPS 0.5)"; env $v python3 scripts/mcl_test.py /root/data/seq_ug2_disklg.npz 0.01 0.1 0.5 2>&1 | grep -E "MCL estimate|spread < 0.7"; done
