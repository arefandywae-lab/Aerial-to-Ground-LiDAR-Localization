cd /mnt/a/SlamProject
for cfg in "SXY=1.5 EPS=0.5 HMIN=30" "SXY=1.0 EPS=0.5 HMIN=60" "SXY=1.0 EPS=0.3 HMIN=100"; do
  set -- $cfg; export $1 $2 $3
  echo "== MULTIHYP kidnapped start, route 2 global hypotheses, $cfg, 5000 particles"
  KIDNAP=1 MULTIHYP=1 python3 scripts/mcl_test.py /root/data/seq_ug2_hyp_global.npz 0.01 0.1 $EPS 5000 2>&1 | grep -E "KIDNAPPED|MCL estimate|spread < 0.7" | cut -c1-250
done
