cd /mnt/a/SlamProject
echo "== route 3 oracle"; python3 scripts/hyp_oracle.py /root/data/seq_ug3_hyp_global.npz 30 2>&1 | grep -v -i warn
echo "== route 3, FROZEN multi-hyp settings SXY 1.0 EPS 0.5 HMIN 60, kidnapped start, 5000 particles"
KIDNAP=1 MULTIHYP=1 SXY=1.0 HMIN=60 python3 scripts/mcl_test.py /root/data/seq_ug3_hyp_global.npz 0.01 0.1 0.5 5000 2>&1 | grep -E "KIDNAPPED|MCL estimate|spread < 0.7|spread < 1.0" | cut -c1-250
echo "== same, odometry 3%+0.3"
KIDNAP=1 MULTIHYP=1 SXY=1.0 HMIN=60 python3 scripts/mcl_test.py /root/data/seq_ug3_hyp_global.npz 0.03 0.3 0.5 5000 2>&1 | grep -E "KIDNAPPED|MCL estimate" | cut -c1-250
