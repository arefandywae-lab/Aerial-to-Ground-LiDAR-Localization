cd /mnt/a/SlamProject
echo "== route 3 (held-out), FROZEN settings SXY 1.5 INJECT 0.1 EPS 0.5 odo 1%+0.1"
INJECT=0.1 SXY=1.5 python3 scripts/mcl_test.py /root/data/seq_ug3_disklg.npz 0.01 0.1 0.5 2>&1 | grep -v -i warn | cut -c1-260
echo "== route 3, odo 3%+0.3 (same frozen filter)"
INJECT=0.1 SXY=1.5 python3 scripts/mcl_test.py /root/data/seq_ug3_disklg.npz 0.03 0.3 0.5 2>&1 | grep -E "MCL estimate|spread < 0.7|spread < 1.0" | cut -c1-260
echo "== route 3, original 4p settings (SXY 0.6, no inject, EPS 0.2)"
python3 scripts/mcl_test.py /root/data/seq_ug3_disklg.npz 0.01 0.1 0.2 2>&1 | grep -E "MCL estimate|spread < 0.7" | cut -c1-260
