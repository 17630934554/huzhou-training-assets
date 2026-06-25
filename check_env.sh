#!/bin/bash
# ============================================================
# 安环巡检系统 - 服务器网络环境检测脚本
# 在服务器上运行此脚本，确认网络连通性
# ============================================================

echo "========================================="
echo "  安环巡检系统 - 服务器环境检测"
echo "========================================="
echo ""

# 1. 网卡信息
echo "【1】网卡信息"
echo "-----------------------------------------"
ip addr show | grep -E "^[0-9]+:|inet " | grep -v "127.0.0.1"
echo ""

# 2. 默认路由
echo "【2】路由表"
echo "-----------------------------------------"
ip route | head -10
echo ""

# 3. 内网连通（NVR）
echo "【3】内网连通性（NVR 192.168.1.64）"
echo "-----------------------------------------"
ping -c 2 -W 2 192.168.1.64 2>&1 | tail -2
echo ""

# 4. 外网连通（飞书API）
echo "【4】外网连通性（飞书API）"
echo "-----------------------------------------"
curl -s -o /dev/null -w "飞书API: HTTP %{http_code}, 耗时 %{time_total}s\n" https://open.feishu.cn/open-apis/bot/v2/hook/ 2>&1
echo ""

# 5. DNS
echo "【5】DNS解析"
echo "-----------------------------------------"
nslookup open.feishu.cn 2>&1 | head -6
echo ""

# 6. GPU检测
echo "【6】GPU检测"
echo "-----------------------------------------"
if command -v nvidia-smi &>/dev/null; then
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1
else
    echo "nvidia-smi 未安装（后续需安装NVIDIA驱动）"
fi
echo ""

# 7. Python环境
echo "【7】Python环境"
echo "-----------------------------------------"
python3 --version 2>&1
pip3 --version 2>&1
echo ""

# 8. 系统信息
echo "【8】系统信息"
echo "-----------------------------------------"
uname -a
cat /etc/os-release 2>/dev/null | grep -E "PRETTY_NAME|VERSION" | head -2
free -h | head -2
echo ""

echo "========================================="
echo "  检测完成，请将以上输出发给我"
echo "========================================="
