#!/bin/bash
# ============================================================
# 安环巡检 AI 检测系统 - 一键部署脚本（服务器版）
# 适用于 Ubuntu 20.04/22.04 + NVIDIA GPU + 有外网环境
# ============================================================

set -e

INSTALL_DIR="/opt/inspection"
DATA_DIR="/data"

echo "========================================="
echo "  安环巡检 AI 检测系统 - 一键部署"
echo "  服务器版 · 有外网"
echo "========================================="
echo ""

# ---- 1. 系统检测 ----
echo "【1/7】系统检测..."
if ! command -v nvidia-smi &>/dev/null; then
    echo "  ⚠️  NVIDIA 驱动未检测到，正在安装..."
    sudo apt update
    sudo apt install -y nvidia-driver-535
    echo "  ✅ 驱动已安装，需要重启后继续"
    echo "  请运行: sudo reboot && bash $0"
    exit 0
else
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "未知")
    echo "  ✅ GPU: $GPU_INFO"
fi

# ---- 2. 安装系统依赖 ----
echo ""
echo "【2/7】安装系统依赖..."
sudo apt update
sudo apt install -y \
    python3-pip python3-venv ffmpeg \
    libgl1-mesa-gtk libglib2.0-0 \
    net-tools iproute2

echo "  ✅ 系统依赖已安装"

# ---- 3. 创建目录 ----
echo ""
echo "【3/7】创建目录..."
sudo mkdir -p $INSTALL_DIR
sudo mkdir -p $DATA_DIR/alerts/screenshots
sudo mkdir -p $DATA_DIR/alerts/videos
sudo mkdir -p $DATA_DIR/logs
sudo chown -R $USER:$USER $INSTALL_DIR
sudo chown -R $USER:$USER $DATA_DIR
echo "  ✅ 目录已创建"

# ---- 4. 复制项目文件 ----
echo ""
echo "【4/7】复制项目文件..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp -v $SCRIPT_DIR/detector.py $INSTALL_DIR/
cp -v $SCRIPT_DIR/feishu_alert.py $INSTALL_DIR/
cp -v $SCRIPT_DIR/config.yaml $INSTALL_DIR/
cp -v $SCRIPT_DIR/requirements.txt $INSTALL_DIR/
cp -v $SCRIPT_DIR/inspection.service $INSTALL_DIR/
echo "  ✅ 项目文件已复制到 $INSTALL_DIR"

# ---- 5. 安装 Python 依赖 ----
echo ""
echo "【5/7】安装 Python 依赖..."
cd $INSTALL_DIR

# 使用虚拟环境
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

echo "  ✅ Python 依赖已安装"

# 验证 PyTorch + CUDA
python3 -c "
import torch
if torch.cuda.is_available():
    print(f'  ✅ CUDA 可用: {torch.cuda.get_device_name(0)}')
else:
    print('  ⚠️  CUDA 不可用，将使用 CPU（速度较慢）')
"

# ---- 6. 首次模型下载 ----
echo ""
echo "【6/7】下载 YOLOv8n 模型..."
python3 -c "
from ultralytics import YOLO
m = YOLO('yolov8n.pt')
print('  ✅ YOLOv8n 模型已就绪')
"

# ---- 7. 配置提醒 ----
echo ""
echo "【7/7】配置提醒"
echo "========================================="
echo ""
echo "  ⚠️  请修改以下配置后再启动："
echo ""
echo "  1. 编辑配置文件："
echo "     nano $INSTALL_DIR/config.yaml"
echo ""
echo "  2. 必改项："
echo "     - nvr.host       → NVR 实际 IP"
echo "     - nvr.username   → NVR 用户名"
echo "     - nvr.password   → NVR 密码"
echo "     - feishu.app_id  → 飞书应用 App ID"
echo "     - feishu.app_secret → 飞书应用 App Secret"
echo ""
echo "  3. 添加摄像头通道（按实际点位填写）"
echo ""
echo "  4. 配置完成后启动："
echo "     cd $INSTALL_DIR && source venv/bin/activate"
echo "     python3 detector.py"
echo ""
echo "  5. 设为开机自启："
echo "     sudo cp $INSTALL_DIR/inspection.service /etc/systemd/system/"
echo "     sudo systemctl daemon-reload"
echo "     sudo systemctl enable inspection"
echo "     sudo systemctl start inspection"
echo ""
echo "========================================="
echo "  部署完成！"
echo "========================================="
