#!/bin/bash
# Approved download (user): MegaLoc code (GitHub gmberton/MegaLoc, MIT, reviewed: no network/exec beyond the hub weights download)
# + weights (Hugging Face gberton/MegaLoc, model.safetensors). Needs huggingface_hub + safetensors (small pure-python wheels) and torchvision.
cd /root
python3 -c "import huggingface_hub, safetensors" 2>/dev/null || pip install --break-system-packages huggingface_hub safetensors 2>&1 | tail -1
python3 - <<'PY'
import os, torch
m = torch.hub.load("gmberton/MegaLoc", "get_trained_model", trust_repo=True)
print("loaded; parameters %.1f M" % (sum(p.numel() for p in m.parameters()) / 1e6))
for root, _, files in os.walk(os.path.expanduser("~/.cache/huggingface")):
    for f in files:
        p = os.path.join(root, f)
        if f.endswith(".safetensors") or os.path.islink(p):
            print("file:", f, round(os.path.getsize(p) / 1e6), "MB")
x = torch.rand(2, 3, 322, 322)
with torch.inference_mode():
    y = m.cuda()(x.cuda())
print("output", tuple(y.shape), "norms", [round(v, 4) for v in y.norm(dim=1).tolist()])
PY
du -sh ~/.cache/huggingface ~/.cache/torch/hub 2>/dev/null
