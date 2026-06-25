# 安环巡检 AI 检测系统 - 部署文档

> 服务器版 · 有外网环境 · 无需4G Dongle

---

## 系统要求

| 项目 | 最低要求 | 推荐 |
|------|---------|------|
| CPU | i5-10400 | i5-12400 / i7-12700 |
| 内存 | 8GB | 16GB DDR4 |
| 显卡 | GTX 1660 (6GB) | RTX 3060 (12GB) |
| 硬盘 | 256GB SSD | 512GB SSD + 1TB HDD |
| 系统 | Ubuntu 20.04 | Ubuntu 22.04 LTS |
| 网络 | 内网可达NVR + 外网可达飞书 | 同左 |

---

## 部署步骤

### 第1步：确认网络连通

在服务器上运行环境检测脚本：

```bash
bash check_env.sh
```

确认以下两项都是 ✅：
- 内网 NVR 可达（ping 192.168.1.64）
- 外网飞书 API 可达（curl https://open.feishu.cn）

**如果单网卡同时访问内网和外网**，需确认路由正确：
```bash
# 查看路由
ip route
# 应该能看到内网网段（如 192.168.1.0/24）和默认路由（外网出口）
```

**如果双网卡**，需要配置策略路由：
```bash
# 假设 eth0 是内网（192.168.1.x），eth1 是外网
# 内网路由
ip route add 192.168.1.0/24 dev eth0
# 外网走默认路由
ip route add default via <外网网关> dev eth1
```

### 第2步：安装 NVIDIA 驱动 + CUDA

```bash
# 安装 NVIDIA 驱动
sudo apt update
sudo apt install -y nvidia-driver-535

# 重启
sudo reboot

# 验证
nvidia-smi
# 应该能看到 GPU 信息和显存

# 安装 CUDA Toolkit（如需从源码编译）
# Ubuntu 22.04 推荐 CUDA 12.x
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install -y cuda-toolkit-12-4
```

### 第3步：安装 Python 依赖

```bash
# 系统包
sudo apt install -y python3-pip ffmpeg libgl1-mesa-gtk

# 创建工作目录
sudo mkdir -p /opt/inspection
sudo chown $USER:$USER /opt/inspection

# 复制项目文件
cp detector.py feishu_alert.py config.yaml requirements.txt /opt/inspection/

# 安装 Python 依赖
cd /opt/inspection
pip3 install -r requirements.txt

# 验证 PyTorch + CUDA
python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
# 应该输出 CUDA: True, GPU: NVIDIA GeForce RTX 3060
```

### 第4步：修改配置文件

```bash
nano /opt/inspection/config.yaml
```

**必改项**（搜索 ⚠️ 标记）：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `nvr.host` | NVR 实际内网 IP | `192.168.1.64` |
| `nvr.username` | NVR 登录用户名 | `admin` |
| `nvr.password` | NVR 登录密码 | `your_password` |
| `feishu.app_id` | 飞书应用 App ID | `cli_xxx` |
| `feishu.app_secret` | 飞书应用 App Secret | `xxx` |

**摄像头通道**：按实际点位填写，每路一个 `- id` 条目：
- `tier: A` — 重点区域（实时AI，2fps持续推理）
- `tier: B` — 一般区域（轮询AI，每2分钟轮换一批）
- `tier: C` — 仅录像（不做AI推理，不占算力）

**RTSP 地址格式**（海康威视）：
```
rtsp://用户名:密码@NVR_IP:554/Streaming/Channels/通道号01
```
- 通道1主码流：`.../Channels/101`
- 通道2主码流：`.../Channels/201`
- 通道1子码流：`.../Channels/102`（分辨率低，省算力）

**建议**：A层用主码流（清晰），B层用子码流（省算力）

### 第5步：创建数据目录

```bash
sudo mkdir -p /data/alerts/screenshots /data/alerts/videos /data/logs
sudo chown -R $USER:$USER /data
```

### 第6步：测试运行

```bash
cd /opt/inspection

# 先测试单帧推理（验证模型+GPU正常）
python3 -c "
from ultralytics import YOLO
import torch
print('CUDA:', torch.cuda.is_available())
m = YOLO('yolov8n.pt')
r = m('https://ultralytics.com/images/bus.jpg')
print('检测到', len(r[0].boxes), '个目标')
print('✅ 模型加载和推理正常')
"

# 再启动完整系统
python3 detector.py
# 观察输出，应该看到：
# [系统] 摄像头分层: A层X路(实时) / B层Y路(轮询) / C层Z路(仅录像)
# [启动] 摄像头 xxx (通道 1)
# ...
```

### 第7步：配置飞书应用（多维表格写入）

> 此步为可选，不配置也能推群告警，只是无法自动写入多维表格

1. 访问 [飞书开放平台](https://open.feishu.cn/app) → 创建企业自建应用
2. 添加应用能力：**机器人**
3. 权限管理 → 搜索并开通：
   - `bitable:app` — 多维表格读写
   - `bitable:app:readonly` — 多维表格读取
4. 版本管理 → 创建版本 → 申请发布
5. 获取 `App ID` 和 `App Secret`，填入 `config.yaml` 的 `feishu.app_id` / `feishu.app_secret`
6. 在多维表格中添加应用为协作者（编辑权限）

### 第8步：设为开机自启

```bash
# 复制 service 文件
sudo cp inspection.service /etc/systemd/system/

# 修改 service 文件中的用户名和路径（如需要）
sudo nano /etc/systemd/system/inspection.service

# 启用并启动
sudo systemctl daemon-reload
sudo systemctl enable inspection
sudo systemctl start inspection

# 查看状态
sudo systemctl status inspection

# 查看日志
sudo journalctl -u inspection -f
# 或
tail -f /data/logs/detector.log
```

---

## 常用运维命令

```bash
# 启动
sudo systemctl start inspection

# 停止
sudo systemctl stop inspection

# 重启
sudo systemctl restart inspection

# 查看状态
sudo systemctl status inspection

# 查看实时日志
tail -f /data/logs/detector.log

# 查看GPU使用率
nvidia-smi

# 查看告警截图
ls -lt /data/alerts/screenshots/ | head -20

# 查看告警视频
ls -lt /data/alerts/videos/ | head -20

# 清理30天前的告警文件
find /data/alerts -type f -mtime +30 -delete
```

---

## 性能参考

| 硬件 | A层实时路数 | B层轮询路数 | 显存占用 |
|------|-----------|-----------|---------|
| RTX 3060 12GB | ≤32路 (2fps) | ≤100路 (轮询) | ~3-6GB |
| RTX 4060 8GB | ≤24路 (2fps) | ≤80路 (轮询) | ~2-5GB |
| GTX 1660 6GB | ≤12路 (2fps) | ≤40路 (轮询) | ~2-4GB |
| CPU only | ≤4路 (1fps) | ≤16路 (轮询) | 0 |

> 300路全配置建议：A层30路 + B层100路 + C层170路，1台 RTX 3060 服务器搞定

---

## 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| RTSP连接失败 | NVR IP/密码错误 | 确认 config.yaml 中的 NVR 配置 |
| CUDA不可用 | 驱动未装/版本不匹配 | `nvidia-smi` 检查，重装驱动 |
| 飞书推送失败 | 外网不通/Webhook失效 | `curl` 测试外网 + 飞书API |
| 多维表格写入失败 | 未配置APP_ID/SECRET | 完成第7步飞书应用配置 |
| 误报过多 | 置信度太低 | 调高 `min_confidence`（推荐0.6+） |
| 告警刷屏 | 冷却时间太短 | 调大 `cooldown`（秒） |
| 显存不足 | A层路数太多 | 减少A层，移到B层轮询 |
