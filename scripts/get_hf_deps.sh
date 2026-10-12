#!/bin/bash
# Debian owns typing_extensions (no pip RECORD): shadow it from /usr/local instead of uninstalling it.
cd /root
pip install --break-system-packages --ignore-installed typing_extensions huggingface_hub safetensors 2>&1 | grep -v WARNING | tail -4
python3 -c "import huggingface_hub, safetensors, torch; print('hf_hub', huggingface_hub.__version__, '| safetensors', safetensors.__version__, '| torch ok', torch.cuda.is_available())"
