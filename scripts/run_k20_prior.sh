cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_COARSE=0 M1LF_FP16=0 M1LF_MATCHER=disklg M1LF_K=20 PRIOR_SIGMA=5 M1LF_PRIOR_R=20  
python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/ug2s_img --out ../results/urban/disklg_ug2s_prior_k20.json --seed 0 2>&1 | grep -v -i warn | grep -E "localized|recall|median_t|latency_ms_p50|gate40|Error" | tr -d " 
"
