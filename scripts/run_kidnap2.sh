cd /mnt/a/SlamProject
for v in "INJECT=0 SXY=0.6" "INJECT=0.1 SXY=1.5"; do echo "== GLOBAL poses, kidnapped start, $v, 5000 particles"; env KIDNAP=1 $v python3 scripts/mcl_test.py /root/data/seq_ug2_disklg_global.npz 0.01 0.1 0.5 5000 2>&1 | grep -v -i warn | cut -c1-250; done
