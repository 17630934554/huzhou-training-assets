#!/usr/bin/env python3
"""
安环巡检 AI 检测系统 - 核心检测引擎（服务器版）

架构：
  海康摄像头 → NVR → RTSP取流(OpenCV) → YOLO推理(Ultralytics)
  → 检测违规 → 截图+短视频 → feishu_alert.py 推飞书群 + 写多维表格

部署环境：
  服务器主机（有内网 + 外网，无需4G Dongle）
  支持 A/B/C 三层摄像头分层调度：
    A层 - 重点区域实时推理（2fps持续）
    B层 - 一般区域轮询推理（每2分钟轮换一批）
    C层 - 仅录像备查，不做AI推理
"""

import os
import sys
import cv2
import time
import yaml
import json
import signal
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from threading import Thread, Lock, Event
from collections import defaultdict

# 确保 feishu_alert.py 可导入
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from feishu_alert import send_alert, DETECTION_SCENES
except ImportError:
    print("[ERROR] 无法导入 feishu_alert.py，请确保同目录下存在该文件")
    sys.exit(1)

try:
    from ultralytics import YOLO
except ImportError:
    print("[ERROR] 缺少 ultralytics 库，请安装: pip install ultralytics")
    sys.exit(1)


# ============================================================
# 日志配置
# ============================================================

def setup_logging(cfg: dict):
    level = getattr(logging, cfg.get("logging", {}).get("level", "INFO").upper())
    log_file = cfg.get("logging", {}).get("file", "/data/logs/detector.log")
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("detector")


# ============================================================
# 配置加载
# ============================================================

def load_config(path: str = None) -> dict:
    """加载 YAML 配置文件"""
    if path is None:
        path = SCRIPT_DIR / "config.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ============================================================
# 截图 & 视频片段保存
# ============================================================

class AlertStorage:
    """告警截图和短视频存储"""

    def __init__(self, cfg: dict):
        self.screenshot_dir = Path(cfg.get("storage", {}).get("screenshot_dir", "/data/alerts/screenshots"))
        self.video_dir = Path(cfg.get("storage", {}).get("video_dir", "/data/alerts/videos"))
        self.clip_duration = cfg.get("storage", {}).get("clip_duration", 5)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.video_dir.mkdir(parents=True, exist_ok=True)

    def save_screenshot(self, frame, camera_name: str, scene_key: str) -> str:
        """保存告警截图，返回文件路径"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = camera_name.replace("/", "-").replace(" ", "_")
        filename = f"{safe_name}_{scene_key}_{ts}.jpg"
        filepath = self.screenshot_dir / filename
        cv2.imwrite(str(filepath), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return str(filepath)

    def save_video_clip(self, rtsp_url: str, camera_name: str, scene_key: str,
                        duration: int = None) -> str:
        """
        用 ffmpeg 从 RTSP 流截取短视频片段
        注意：此方法通过 ffmpeg 另开一路取流，确保截取的是告警时刻的画面
        """
        duration = duration or self.clip_duration
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = camera_name.replace("/", "-").replace(" ", "_")
        filename = f"{safe_name}_{scene_key}_{ts}.mp4"
        filepath = self.video_dir / filename

        cmd = [
            "ffmpeg", "-y",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-movflags", "+faststart",
            str(filepath)
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, timeout=duration + 10
            )
            if result.returncode == 0 and filepath.exists():
                return str(filepath)
            else:
                logging.getLogger("detector").warning(
                    f"ffmpeg 视频截取失败: {result.stderr.decode()[:200]}"
                )
                return None
        except subprocess.TimeoutExpired:
            logging.getLogger("detector").warning("ffmpeg 视频截取超时")
            return None
        except FileNotFoundError:
            logging.getLogger("detector").warning("ffmpeg 未安装，跳过视频截取")
            return None


# ============================================================
# 防抖/冷却管理
# ============================================================

class CooldownManager:
    """管理同一摄像头同一场景的告警冷却时间，防止重复告警"""

    def __init__(self):
        self.last_alert = defaultdict(float)  # (camera_id, scene_key) → timestamp
        self.lock = Lock()

    def can_alert(self, camera_id: int, scene_key: str, cooldown: int) -> bool:
        """检查是否可以告警（冷却时间已过）"""
        key = (camera_id, scene_key)
        now = time.time()
        with self.lock:
            last = self.last_alert[key]
            if now - last >= cooldown:
                self.last_alert[key] = now
                return True
            return False


# ============================================================
# 单路摄像头检测线程
# ============================================================

class CameraDetector(Thread):
    """单路摄像头的 RTSP 取流 + YOLO 检测"""

    def __init__(self, channel: dict, models: dict, scene_cfg: dict,
                 storage: AlertStorage, cooldown_mgr: CooldownManager,
                 logger: logging.Logger):
        super().__init__(daemon=True)
        self.channel = channel
        self.camera_id = channel["id"]
        self.camera_name = channel["name"]
        self.rtsp_url = channel["rtsp_url"]
        self.models = models
        self.scene_cfg = scene_cfg
        self.storage = storage
        self.cooldown = cooldown_mgr
        self.logger = logger
        self.running = True
        self.inference_fps = 2
        self.frame_count = 0

    def run(self):
        """主循环：取流 → 检测 → 告警"""
        self.logger.info(f"[启动] 摄像头 {self.camera_name} (通道 {self.camera_id})")

        while self.running:
            cap = None
            try:
                cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                if not cap.isOpened():
                    self.logger.error(f"[连接失败] {self.camera_name}，5秒后重试")
                    time.sleep(5)
                    continue

                interval = 1.0 / self.inference_fps
                last_infer = 0

                while self.running:
                    ret, frame = cap.read()
                    if not ret:
                        self.logger.warning(f"[取流中断] {self.camera_name}，重连中...")
                        break

                    now = time.time()
                    if now - last_infer < interval:
                        continue
                    last_infer = now

                    self._detect_frame(frame)

            except Exception as e:
                self.logger.error(f"[异常] {self.camera_name}: {e}")
            finally:
                if cap:
                    cap.release()

            if self.running:
                time.sleep(3)

        self.logger.info(f"[停止] 摄像头 {self.camera_name}")

    def _detect_frame(self, frame):
        """对单帧执行检测"""
        for scene_key, cfg in self.scene_cfg.items():
            if not cfg.get("enabled", False):
                continue

            model_key = cfg.get("model", "path")
            model = self.models.get(model_key)
            if model is None:
                continue

            min_conf = cfg.get("min_confidence", 0.5)
            target_classes = cfg.get("classes", [])
            cooldown_sec = cfg.get("cooldown", 60)

            try:
                results = model(frame, conf=min_conf, verbose=False)

                for result in results:
                    detected = self._check_detection(result, target_classes, cfg)
                    if detected:
                        if self.cooldown.can_alert(self.camera_id, scene_key, cooldown_sec):
                            self._trigger_alert(frame, scene_key, cfg)
            except Exception as e:
                self.logger.error(f"[检测异常] {self.camera_name} {scene_key}: {e}")

    def _check_detection(self, result, target_classes: list, cfg: dict) -> bool:
        """检查 YOLO 结果是否命中目标"""
        if len(result.boxes) == 0:
            return False
        if not target_classes:
            return len(result.boxes) > 0
        for box in result.boxes:
            cls_id = int(box.cls[0])
            cls_name = result.names.get(cls_id, "")
            if cls_name in target_classes:
                return True
        return False

    def _trigger_alert(self, frame, scene_key: str, cfg: dict):
        """触发告警：截图 + 视频片段 + 推飞书"""
        self.logger.info(
            f"[告警] {self.camera_name} - {cfg.get('description', scene_key)}"
        )
        screenshot_path = self.storage.save_screenshot(frame, self.camera_name, scene_key)
        video_path = None

        try:
            send_alert(
                scene_key=scene_key,
                camera_location=self.camera_name,
                screenshot_path=screenshot_path,
                video_clip_path=video_path,
            )
        except Exception as e:
            self.logger.error(f"[推送失败] {e}")

    def stop(self):
        self.running = False


# ============================================================
# B层轮询调度器
# ============================================================

class PollingScheduler(Thread):
    """B层摄像头轮询调度：分批取流推理，每批跑固定时长后切换下一批"""

    def __init__(self, channels: list, models: dict, scene_cfg: dict,
                 storage: AlertStorage, cooldown_mgr: CooldownManager,
                 logger: logging.Logger, polling_cfg: dict):
        super().__init__(daemon=True)
        self.channels = channels          # B层通道列表
        self.models = models
        self.scene_cfg = scene_cfg
        self.storage = storage
        self.cooldown = cooldown_mgr
        self.logger = logger
        self.batch_size = polling_cfg.get("batch_size", 20)
        self.interval_sec = polling_cfg.get("interval_sec", 120)
        self.switch_gap = polling_cfg.get("switch_gap", 5)
        self.running = True
        self.active_detectors = []

    def run(self):
        """轮询主循环"""
        if not self.channels:
            self.logger.info("[轮询] 无B层摄像头，跳过")
            return

        self.logger.info(
            f"[轮询] 启动B层调度，共 {len(self.channels)} 路，"
            f"每批 {self.batch_size} 路，每批 {self.interval_sec}s"
        )

        while self.running:
            # 按批次轮询
            for i in range(0, len(self.channels), self.batch_size):
                if not self.running:
                    break

                batch = self.channels[i:i + self.batch_size]
                self.logger.info(
                    f"[轮询] 切换到批次 {i//self.batch_size + 1}，"
                    f"通道 {batch[0]['id']}-{batch[-1]['id']}"
                )

                # 停止上一批
                self._stop_batch()

                # 启动当前批
                self._start_batch(batch)

                # 等待本轮时长
                wait_end = time.time() + self.interval_sec
                while time.time() < wait_end and self.running:
                    time.sleep(1)

                # 切换间隔
                if self.running:
                    time.sleep(self.switch_gap)

        self._stop_batch()
        self.logger.info("[轮询] 已停止")

    def _start_batch(self, batch: list):
        """启动一批B层摄像头检测"""
        self.active_detectors = []
        for channel in batch:
            detector = CameraDetector(
                channel=channel,
                models=self.models,
                scene_cfg=self.scene_cfg,
                storage=self.storage,
                cooldown_mgr=self.cooldown,
                logger=self.logger,
            )
            detector.inference_fps = 1  # 轮询路降低帧率
            self.active_detectors.append(detector)
            detector.start()

    def _stop_batch(self):
        """停止当前批次的检测器"""
        for d in self.active_detectors:
            d.stop()
        self.active_detectors.clear()
        time.sleep(1)  # 等待线程退出

    def stop(self):
        self.running = False


# ============================================================
# 主控制器
# ============================================================

class InspectionSystem:
    """安环巡检 AI 检测系统主控（服务器版·支持A/B/C三层调度）"""

    def __init__(self, config_path: str = None):
        self.cfg = load_config(config_path)
        self.logger = setup_logging(self.cfg)
        self.storage = AlertStorage(self.cfg)
        self.cooldown_mgr = CooldownManager()
        self.detectors_a = []       # A层实时检测器
        self.polling_scheduler = None  # B层轮询调度器
        self.models = {}
        self._load_models()

    def _load_models(self):
        """加载 YOLO 模型"""
        model_cfg = self.cfg.get("model", {})
        device = model_cfg.get("device", "cuda")

        # 检查 CUDA 可用性
        import torch
        if device == "cuda" and not torch.cuda.is_available():
            self.logger.warning("[模型] CUDA 不可用，回退到 CPU（速度会显著降低）")
            device = "cpu"

        # 通用目标检测模型
        general_path = model_cfg.get("path", "yolov8n.pt")
        self.logger.info(f"[模型] 加载通用模型: {general_path}")
        self.models["path"] = YOLO(general_path)
        self.models["path"].to(device)

        # 安环专用模型（如果存在）
        for key in ["helmet_model", "fire_smoke_model"]:
            model_path = model_cfg.get(key)
            if model_path and Path(model_path).exists():
                self.logger.info(f"[模型] 加载专用模型: {key} = {model_path}")
                self.models[key] = YOLO(model_path)
                self.models[key].to(device)
            else:
                self.logger.info(f"[模型] 专用模型 {key} 不存在({model_path})，使用通用模型兜底")
                self.models[key] = self.models["path"]

        # 打印 GPU 信息
        if device == "cuda":
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_mem / 1024**3
            self.logger.info(f"[模型] GPU: {gpu_name}, 显存: {gpu_mem:.1f}GB")

        self.logger.info(f"[模型] 加载完成，设备: {device}")

    def _build_rtsp_urls(self):
        """替换 RTSP URL 中的占位符"""
        nvr = self.cfg.get("nvr", {})
        host = nvr.get("host", "192.168.1.64")
        port = nvr.get("port", 554)
        username = nvr.get("username", "admin")
        password = nvr.get("password", "admin123")

        for ch in nvr.get("channels", []):
            url_template = ch.get("rtsp_url", "")
            ch["rtsp_url"] = url_template.format(
                host=host, port=port, username=username, password=password
            )

    def start(self):
        """启动检测系统（A层实时 + B层轮询 + C层跳过）"""
        self._build_rtsp_urls()

        nvr = self.cfg.get("nvr", {})
        scene_cfg = self.cfg.get("scenes", {})
        channels = nvr.get("channels", [])

        # 按层级分组
        tier_a = [ch for ch in channels if ch.get("tier", "A") == "A"]
        tier_b = [ch for ch in channels if ch.get("tier") == "B"]
        tier_c = [ch for ch in channels if ch.get("tier") == "C"]

        self.logger.info(
            f"[系统] 摄像头分层: A层{len(tier_a)}路(实时) / "
            f"B层{len(tier_b)}路(轮询) / C层{len(tier_c)}路(仅录像)"
        )

        # ---- A层：持续实时推理 ----
        for channel in tier_a:
            detector = CameraDetector(
                channel=channel,
                models=self.models,
                scene_cfg=scene_cfg,
                storage=self.storage,
                cooldown_mgr=self.cooldown_mgr,
                logger=self.logger,
            )
            self.detectors_a.append(detector)
            detector.start()

        self.logger.info(f"[系统] A层 {len(self.detectors_a)} 路实时检测已启动")

        # ---- B层：轮询推理 ----
        polling_cfg = nvr.get("polling", {})
        if tier_b and polling_cfg.get("enabled", True):
            self.polling_scheduler = PollingScheduler(
                channels=tier_b,
                models=self.models,
                scene_cfg=scene_cfg,
                storage=self.storage,
                cooldown_mgr=self.cooldown_mgr,
                logger=self.logger,
                polling_cfg=polling_cfg,
            )
            self.polling_scheduler.start()
        elif tier_b:
            self.logger.info("[系统] B层轮询已禁用，跳过")

        # ---- C层：仅录像，不启动检测 ----
        if tier_c:
            self.logger.info(
                f"[系统] C层 {len(tier_c)} 路仅录像备查: " +
                ", ".join(ch["name"] for ch in tier_c)
            )

        self.logger.info(
            f"[系统] 启动完成！实时推理 {len(self.detectors_a)} 路"
            + (f" + 轮询 {len(tier_b)} 路" if tier_b else "")
        )

        # 主线程等待
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("[系统] 收到中断信号，停止中...")
            self.stop()

    def stop(self):
        """停止所有检测线程"""
        for d in self.detectors_a:
            d.stop()
        if self.polling_scheduler:
            self.polling_scheduler.stop()
        self.logger.info("[系统] 已停止")


# ============================================================
# 入口
# ============================================================

def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else None

    # 检查网络连通性
    logger = logging.getLogger("detector")
    print("=" * 50)
    print("  安环巡检 AI 检测系统 - 服务器版")
    print("=" * 50)
    print()

    # 简易网络检测
    import requests
    try:
        r = requests.get("https://open.feishu.cn", timeout=5)
        print(f"  ✅ 飞书API可达 (HTTP {r.status_code})")
    except Exception as e:
        print(f"  ❌ 飞书API不可达: {e}")
        print("     请检查服务器外网连通性！")

    print()

    system = InspectionSystem(config_path)

    def signal_handler(sig, frame):
        system.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    system.start()


if __name__ == "__main__":
    main()
