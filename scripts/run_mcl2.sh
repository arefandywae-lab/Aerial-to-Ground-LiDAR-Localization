cd /mnt/a/SlamProject
for cfg in "0.01 0.1 0.2" "0.03 0.3 0.5"; do python3 scripts/mcl_test.py /root/data/seq_ug2_disklg.npz $cfg 2>&1 | grep -v -i warn; echo; done
