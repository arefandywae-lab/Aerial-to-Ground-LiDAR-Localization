cd /mnt/a/SlamProject
python3 -c "import torch,kornia;print(torch.__version__,torch.version.cuda,kornia.__version__)"
python3 -c "import kornia.feature as f;print([n for n in dir(f) if n.lower() in ('lightglue','xfeat','disk','dedodev2','lightglueonnx')])"
pip list 2>/dev/null | grep -i -E "tensorrt|onnx|lightglue|torch|roma"
df -h /root | tail -1; which git trtexec
