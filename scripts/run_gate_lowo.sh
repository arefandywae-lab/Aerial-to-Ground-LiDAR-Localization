cd /mnt/a/SlamProject
GATE_LABEL=coarse python3 scripts/confidence_gate.py results/urban/disklg_ug2s_prior results/urban/disklg_ug1s_prior results/worlds/grid11_prior results/worlds/bridge14_prior results/worlds/oldtown12_prior 2>&1 | tail -n 40
