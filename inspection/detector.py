#!/usr/bin/env python3
"""
AnHuan Inspection AI - Core Detection Engine (Server Edition)

Architecture:
  Hikvision Cameras -> NVR -> RTSP(FFmpeg subprocess) -> YOLO(Ultralytics)
  -> Detect violations -> Screenshot+Clip -> feishu_alert.py -> Feishu Group + Bitable

Supports H.265/HEVC via FFmpeg subprocess (no NVR codec change needed)
A/B/C tier camera scheduling
"""

import os
import sys
import cv2
import time
import yaml
import json
import ssl
import signal
import logging
import subprocess
import numpy as np
from datetime import datetime
from pathlib import Path
from threading import Thread, Lock, Event
from collections import defaultdict

# Fix SSL certificate verification issues on Windows
ssl._create_default_https_context = ssl._create_unverified_context

# Ensure feishu_alert.py is importable
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from feishu_alert import send_alert, DETECTION_SCENES
except ImportError:
    print("[ERROR] Cannot import feishu_alert.py, make sure it's in the same directory")
    sys.exit(1)

try:
    from ultralytics import YOLO
except ImportError:
    print("[ERROR] Missing ultralytics, install: pip install ultralytics")
    sys.exit(1)


# ============================================================
# FFmpeg helper - find FFmpeg binary
# ============================================================

def find_ffmpeg():
    """Find FFmpeg binary: try imageio-ffmpeg first, then system PATH"""
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).exists():
            return exe
    except ImportError:
        pass

    import shutil
    exe = shutil.which("ffmpeg")
    if exe:
        return exe

    return None


FFMPEG_EXE = find_ffmpeg()


# ============================================================
# FFmpeg-based RTSP reader (supports H.265/HEVC)
# ============================================================

class FFmpegRTSPReader:
    """Read RTSP stream via FFmpeg subprocess - supports all codecs including H.265

    Uses fixed output resolution (640x360) for reliable frame reading.
    No need to probe stream resolution or guess frame size.
    """

    OUT_WIDTH = 640
    OUT_HEIGHT = 360
    FRAME_SIZE = OUT_WIDTH * OUT_HEIGHT * 3  # 691200 bytes (BGR24)

    def __init__(self, rtsp_url, logger=None):
        self.rtsp_url = rtsp_url
        self.logger = logger
        self.process = None

    def open(self):
        """Start FFmpeg subprocess to decode RTSP stream"""
        if not FFMPEG_EXE:
            if self.logger:
                self.logger.error("[FFmpeg] No FFmpeg found! Install: pip install imageio-ffmpeg")
            return False

        cmd = [
            FFMPEG_EXE,
            "-rtsp_transport", "tcp",
            "-stimeout", "5000000",       # 5s RTSP timeout
            "-i", self.rtsp_url,
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-an", "-sn",
            "-s", f"{self.OUT_WIDTH}x{self.OUT_HEIGHT}",  # Force fixed output size
            "-"
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=10 * 1024 * 1024,
            )
            if self.logger:
                self.logger.info(f"[FFmpeg] Subprocess started, waiting for first frame...")
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FFmpeg] Failed to start: {e}")
            return False

    def read(self):
        """Read a single frame. Returns (success, frame)"""
        if not self.process or self.process.poll() is not None:
            return False, None

        raw = self.process.stdout.read(self.FRAME_SIZE)
        if len(raw) != self.FRAME_SIZE:
            return False, None

        frame = np.frombuffer(raw, dtype=np.uint8).reshape(
            (self.OUT_HEIGHT, self.OUT_WIDTH, 3)
        )
        return True, frame

    def release(self):
        """Stop FFmpeg subprocess"""
        if self.process:
            try:
                self.process.kill()
                self.process.wait(timeout=3)
            except Exception:
                pass
            self.process = None

    def isOpened(self):
        """Check if reader is active"""
        return self.process is not None and self.process.poll() is None


# ============================================================
# Logging setup
# ============================================================

def setup_logging(cfg: dict):
    level = getattr(logging, cfg.get("logging", {}).get("level", "INFO").upper())
    log_file = cfg.get("logging", {}).get("file", "logs/detector.log")
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
# Config loading
# ============================================================

def load_config(path: str = None) -> dict:
    if path is None:
        path = SCRIPT_DIR / "config.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ============================================================
# Screenshot & Video clip storage
# ============================================================

class AlertStorage:
    def __init__(self, cfg: dict):
        self.screenshot_dir = Path(cfg.get("storage", {}).get("screenshot_dir", "alerts/screenshots"))
        self.video_dir = Path(cfg.get("storage", {}).get("video_dir", "alerts/videos"))
        self.clip_duration = cfg.get("storage", {}).get("clip_duration", 5)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.video_dir.mkdir(parents=True, exist_ok=True)

    def save_screenshot(self, frame, camera_name: str, scene_key: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = camera_name.replace("/", "-").replace(" ", "_")
        filename = f"{safe_name}_{scene_key}_{ts}.jpg"
        filepath = self.screenshot_dir / filename
        cv2.imwrite(str(filepath), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return str(filepath)

    def save_video_clip(self, rtsp_url: str, camera_name: str, scene_key: str,
                        duration: int = None) -> str:
        duration = duration or self.clip_duration
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = camera_name.replace("/", "-").replace(" ", "_")
        filename = f"{safe_name}_{scene_key}_{ts}.mp4"
        filepath = self.video_dir / filename

        ffmpeg = FFMPEG_EXE or "ffmpeg"
        cmd = [
            ffmpeg, "-y",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-movflags", "+faststart",
            str(filepath)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=duration + 10)
            if result.returncode == 0 and filepath.exists():
                return str(filepath)
            else:
                logging.getLogger("detector").warning(f"ffmpeg video clip failed")
                return None
        except subprocess.TimeoutExpired:
            logging.getLogger("detector").warning("ffmpeg video clip timeout")
            return None
        except FileNotFoundError:
            logging.getLogger("detector").warning("ffmpeg not found, skip video clip")
            return None


# ============================================================
# Cooldown manager
# ============================================================

class CooldownManager:
    def __init__(self):
        self.last_alert = defaultdict(float)
        self.lock = Lock()

    def can_alert(self, camera_id: int, scene_key: str, cooldown: int) -> bool:
        key = (camera_id, scene_key)
        now = time.time()
        with self.lock:
            last = self.last_alert[key]
            if now - last >= cooldown:
                self.last_alert[key] = now
                return True
            return False


# ============================================================
# Single camera detection thread
# ============================================================

class CameraDetector(Thread):
    """Single camera RTSP reader + YOLO detection (supports H.265 via FFmpeg)"""

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
        self.logger.info(f"[Start] Camera {self.camera_name} (CH {self.camera_id})")

        while self.running:
            reader = None
            try:
                # Try FFmpeg reader first (supports H.265)
                if FFMPEG_EXE:
                    reader = FFmpegRTSPReader(self.rtsp_url, self.logger)
                    if not reader.open():
                        self.logger.error(f"[Connect] {self.camera_name} FFmpeg open failed, retry in 5s")
                        reader = None
                        time.sleep(5)
                        continue
                    self.logger.info(f"[Connect] {self.camera_name} using FFmpeg reader (H.265 OK)")
                else:
                    # Fallback to OpenCV (H.264 only)
                    reader = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
                    reader.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    if not reader.isOpened():
                        self.logger.error(f"[Connect] {self.camera_name} OpenCV open failed, retry in 5s")
                        reader = None
                        time.sleep(5)
                        continue
                    self.logger.info(f"[Connect] {self.camera_name} using OpenCV reader")

                interval = 1.0 / self.inference_fps
                last_infer = 0
                first_frame = True

                while self.running:
                    if isinstance(reader, FFmpegRTSPReader):
                        ret, frame = reader.read()
                    else:
                        ret, frame = reader.read()

                    if not ret or frame is None:
                        self.logger.warning(f"[Stream] {self.camera_name} lost, reconnecting...")
                        break

                    if first_frame:
                        self.logger.info(f"[Connect] {self.camera_name} first frame OK, shape={frame.shape}")
                        first_frame = False

                    now = time.time()
                    if now - last_infer < interval:
                        continue
                    last_infer = now

                    self._detect_frame(frame)

            except Exception as e:
                self.logger.error(f"[Error] {self.camera_name}: {e}")
            finally:
                if reader:
                    if isinstance(reader, FFmpegRTSPReader):
                        reader.release()
                    else:
                        reader.release()

            if self.running:
                time.sleep(3)

        self.logger.info(f"[Stop] Camera {self.camera_name}")

    def _detect_frame(self, frame):
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
                self.logger.error(f"[Detect] {self.camera_name} {scene_key}: {e}")

    def _check_detection(self, result, target_classes: list, cfg: dict) -> bool:
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
        self.logger.info(f"[ALERT] {self.camera_name} - {cfg.get('description', scene_key)}")
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
            self.logger.error(f"[Push] {e}")

    def stop(self):
        self.running = False


# ============================================================
# B-tier polling scheduler
# ============================================================

class PollingScheduler(Thread):
    def __init__(self, channels: list, models: dict, scene_cfg: dict,
                 storage: AlertStorage, cooldown_mgr: CooldownManager,
                 logger: logging.Logger, polling_cfg: dict):
        super().__init__(daemon=True)
        self.channels = channels
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
        if not self.channels:
            self.logger.info("[Polling] No B-tier cameras, skip")
            return

        self.logger.info(
            f"[Polling] B-tier start, {len(self.channels)} cameras, "
            f"batch={self.batch_size}, interval={self.interval_sec}s"
        )

        while self.running:
            for i in range(0, len(self.channels), self.batch_size):
                if not self.running:
                    break
                batch = self.channels[i:i + self.batch_size]
                self.logger.info(f"[Polling] Batch {i//self.batch_size + 1}")
                self._stop_batch()
                self._start_batch(batch)
                wait_end = time.time() + self.interval_sec
                while time.time() < wait_end and self.running:
                    time.sleep(1)
                if self.running:
                    time.sleep(self.switch_gap)

        self._stop_batch()
        self.logger.info("[Polling] Stopped")

    def _start_batch(self, batch: list):
        self.active_detectors = []
        for channel in batch:
            detector = CameraDetector(
                channel=channel, models=self.models, scene_cfg=self.scene_cfg,
                storage=self.storage, cooldown_mgr=self.cooldown, logger=self.logger,
            )
            detector.inference_fps = 1
            self.active_detectors.append(detector)
            detector.start()

    def _stop_batch(self):
        for d in self.active_detectors:
            d.stop()
        self.active_detectors.clear()
        time.sleep(1)

    def stop(self):
        self.running = False


# ============================================================
# Main controller
# ============================================================

class InspectionSystem:
    def __init__(self, config_path: str = None):
        self.cfg = load_config(config_path)
        self.logger = setup_logging(self.cfg)
        self.storage = AlertStorage(self.cfg)
        self.cooldown_mgr = CooldownManager()
        self.detectors_a = []
        self.polling_scheduler = None
        self.models = {}
        self._load_models()

    def _load_models(self):
        model_cfg = self.cfg.get("model", {})
        device = model_cfg.get("device", "cuda")

        import torch
        if device == "cuda" and not torch.cuda.is_available():
            self.logger.warning("[Model] CUDA not available, fallback to CPU")
            device = "cpu"

        general_path = model_cfg.get("path", "yolov8n.pt")
        self.logger.info(f"[Model] Loading: {general_path}")
        self.models["path"] = YOLO(general_path)
        self.models["path"].to(device)

        for key in ["helmet_model", "fire_smoke_model"]:
            model_path = model_cfg.get(key)
            if model_path and Path(model_path).exists():
                self.logger.info(f"[Model] Loading: {key} = {model_path}")
                self.models[key] = YOLO(model_path)
                self.models[key].to(device)
            else:
                self.logger.info(f"[Model] {key} not found ({model_path}), using general model")
                self.models[key] = self.models["path"]

        if device == "cuda":
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_mem / 1024**3
            self.logger.info(f"[Model] GPU: {gpu_name}, VRAM: {gpu_mem:.1f}GB")

        self.logger.info(f"[Model] Ready, device: {device}")

    def _build_rtsp_urls(self):
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
        self._build_rtsp_urls()

        nvr = self.cfg.get("nvr", {})
        scene_cfg = self.cfg.get("scenes", {})
        channels = nvr.get("channels", [])

        tier_a = [ch for ch in channels if ch.get("tier", "A") == "A"]
        tier_b = [ch for ch in channels if ch.get("tier") == "B"]
        tier_c = [ch for ch in channels if ch.get("tier") == "C"]

        self.logger.info(
            f"[System] Cameras: A={len(tier_a)} (realtime) / "
            f"B={len(tier_b)} (polling) / C={len(tier_c)} (record only)"
        )

        if FFMPEG_EXE:
            self.logger.info(f"[System] FFmpeg: {FFMPEG_EXE} (H.265 supported)")
        else:
            self.logger.warning("[System] No FFmpeg! H.265 streams will fail. Install: pip install imageio-ffmpeg")

        for channel in tier_a:
            detector = CameraDetector(
                channel=channel, models=self.models, scene_cfg=scene_cfg,
                storage=self.storage, cooldown_mgr=self.cooldown_mgr, logger=self.logger,
            )
            self.detectors_a.append(detector)
            detector.start()

        self.logger.info(f"[System] A-tier {len(self.detectors_a)} cameras started")

        polling_cfg = nvr.get("polling", {})
        if tier_b and polling_cfg.get("enabled", True):
            self.polling_scheduler = PollingScheduler(
                channels=tier_b, models=self.models, scene_cfg=scene_cfg,
                storage=self.storage, cooldown_mgr=self.cooldown_mgr,
                logger=self.logger, polling_cfg=polling_cfg,
            )
            self.polling_scheduler.start()

        if tier_c:
            self.logger.info(f"[System] C-tier {len(tier_c)} record-only: " + ", ".join(ch["name"] for ch in tier_c))

        self.logger.info(f"[System] Ready! Realtime: {len(self.detectors_a)}" + (f" + Polling: {len(tier_b)}" if tier_b else ""))

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("[System] Interrupted, stopping...")
            self.stop()

    def stop(self):
        for d in self.detectors_a:
            d.stop()
        if self.polling_scheduler:
            self.polling_scheduler.stop()
        self.logger.info("[System] Stopped")


# ============================================================
# Entry point
# ============================================================

def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else None

    print("=" * 50)
    print("  AnHuan Inspection AI - Server Edition")
    print("=" * 50)
    print()

    # Network check
    import requests
    try:
        r = requests.get("https://open.feishu.cn", timeout=5)
        print(f"  Feishu API: OK (HTTP {r.status_code})")
    except Exception as e:
        print(f"  Feishu API: FAIL ({e})")

    # FFmpeg check
    if FFMPEG_EXE:
        print(f"  FFmpeg: {FFMPEG_EXE}")
    else:
        print("  FFmpeg: NOT FOUND (H.265 will fail!)")

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
