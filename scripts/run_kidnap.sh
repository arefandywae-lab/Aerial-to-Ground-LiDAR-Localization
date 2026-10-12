cd /mnt/a/SlamProject
for n in 2000 5000; do KIDNAP=1 python3 scripts/mcl_test.py /root/data/seq_ug2.npz 0.01 0.1 0.5 $n 2>&1 | grep -v -i warn | head -n 4; done
