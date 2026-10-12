#!/bin/bash
cd /root
python3 -c "import PIL; print('pillow', PIL.__version__)"
pip install --break-system-packages --no-deps torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124 2>&1 | tail -2
python3 -c "import torch, torchvision; print('torch', torch.__version__, '| torchvision', torchvision.__version__, '| cuda', torch.cuda.is_available())"
