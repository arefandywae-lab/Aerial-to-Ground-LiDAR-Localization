cd /mnt/a/SlamProject
python3 scripts/hyp_oracle.py /root/data/seq_ug2_hyp_global.npz 30 2>&1 | grep -v -i warn
