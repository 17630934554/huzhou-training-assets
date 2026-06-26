#!/usr/bin/env python3
"""
安环巡检系统 - 飞书群告警推送模块
用于 AI 检测到违规时自动推送告警到飞书群 + 写入多维表格

架构：
  海康摄像头 → NVR → 边缘盒子(YOLO推理) → 本脚本 → 飞书Webhook + 多维表格API

网络要求：
  边缘盒子通过 4G Dongle 出站访问飞书 API（内网无外网出口）
"""

import json
import time
import requests
from datetime import datetime
from pathlib import Path

# ============================================================
# 配置
# ============================================================

# 飞书群机器人 Webhook
FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/fe6f6996-0036-431b-b687-d57b4021e1a8"

# 飞书多维表格（安环巡检记录）
BASE_TOKEN = "WNsFbGQEOaIANusrozfcY43Hn8b"
TABLE_ID = "tblP5a7Lcx20IioF"

# 多维表格字段 ID 映射（建表时生成，字段名 → field_id）
FIELD_IDS = {
    "编号": "fldD9whuiK",        # auto_number, 只读
    "隐患类型": "fldLrxgkPA",    # select
    "优先级": "fldO8sHqYq",      # select
    "发现时间": "fldKHCrlg6",    # datetime
    "监控点位": "fld7uLUpJT",    # text
    "证据截图": "fldpitny6v",    # attachment
    "证据视频": "fld1jDmpZB",    # attachment
    "来源": "fldk3JApbn",        # select
    "责任人": "fldZzs1H3y",      # user
    "整改状态": "fld4dWHPyM",    # select
    "整改截止": "fldWBAh81t",    # datetime
    "整改照片": "fld5BsMdYT",    # attachment
    "整改说明": "fld5veifuc",    # text
}

# 12个AI检测场景 → 隐患类型 + 优先级映射
DETECTION_SCENES = {
    "fire_smoke":       {"type": "火焰/烟雾",         "priority": "P0紧急"},
    "fire_exit_block":  {"type": "消防通道堵塞",       "priority": "P0紧急"},
    "no_helmet":        {"type": "未戴安全帽",         "priority": "P0紧急"},
    "forklift_intrude": {"type": "叉车区闯入",         "priority": "P0紧急"},
    "fire_ext_missing": {"type": "消防器材遮挡/缺失",   "priority": "P1重要"},
    "person_fall":      {"type": "人员跌倒",           "priority": "P1重要"},
    "cabinet_open":     {"type": "电气柜门未关",       "priority": "P1重要"},
    "floor_liquid":     {"type": "地面积水/油污",       "priority": "P1重要"},
    "unauth_area":      {"type": "非授权区域闯入",      "priority": "P1重要"},
    "stack_overheight": {"type": "货物堆高超标",       "priority": "P2一般"},
    "forklift_speed":   {"type": "叉车超速",           "priority": "P2一般"},
    "equip_leak":       {"type": "设备异常(跑冒滴漏)",  "priority": "P2一般"},
}

# 优先级 → 卡片颜色
PRIORITY_COLORS = {
    "P0紧急": "red",
    "P1重要": "orange",
    "P2一般": "blue",
}

# 优先级 → emoji
PRIORITY_EMOJI = {
    "P0紧急": "🔴",
    "P1重要": "🟠",
    "P2一般": "🔵",
}

# ============================================================
# 飞书群告警推送
# ============================================================

def send_alert(scene_key: str, camera_location: str,
               screenshot_path: str = None, video_clip_path: str = None,
               responsible_person: str = None):
    """
    检测到违规时调用：推飞书群告警卡片

    Args:
        scene_key: 检测场景 key，对应 DETECTION_SCENES
        camera_location: 监控点位名称
        screenshot_path: 证据截图本地路径
        video_clip_path: 证据视频本地路径
        responsible_person: 责任人 open_id（可选，用于 @人）
    """
    scene = DETECTION_SCENES.get(scene_key)
    if not scene:
        print(f"[WARN] 未知检测场景: {scene_key}")
        return

    hazard_type = scene["type"]
    priority = scene["priority"]
    color = PRIORITY_COLORS[priority]
    emoji = PRIORITY_EMOJI[priority]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 构建飞书卡片
    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🚨 安环巡检告警 - {hazard_type}"
                },
                "template": color
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            f"**隐患类型**：{hazard_type}\n"
                            f"**优先级**：{emoji} {priority}\n"
                            f"**监控点位**：{camera_location}\n"
                            f"**发现时间**：{now}\n"
                            f"**来源**：AI自动检测"
                        )
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "📎 证据截图已自动写入[安环巡检记录表]"
                        f"(https://xdp7r8eri5.feishu.cn/base/{BASE_TOKEN})，"
                        "请责任人及时处理"
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "查看巡检记录"
                            },
                            "url": f"https://xdp7r8eri5.feishu.cn/base/{BASE_TOKEN}",
                            "type": "primary"
                        }
                    ]
                }
            ]
        }
    }

    # P2一般不推群，只写表格
    if priority == "P2一般":
        print(f"[INFO] P2一般告警，仅写入表格，不推群: {hazard_type} @ {camera_location}")
        return write_to_base(hazard_type, priority, camera_location, now, screenshot_path, video_clip_path)

    # P0/P1 推群
    try:
        resp = requests.post(
            FEISHU_WEBHOOK_URL,
            json=card,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        result = resp.json()
        if result.get("StatusCode") == 0 or result.get("code") == 0:
            print(f"[OK] 飞书告警推送成功: {hazard_type} @ {camera_location}")
        else:
            print(f"[ERROR] 飞书推送失败: {result}")
    except Exception as e:
        print(f"[ERROR] 飞书推送异常: {e}")

    # 同时写入多维表格
    return write_to_base(hazard_type, priority, camera_location, now, screenshot_path, video_clip_path)


# ============================================================
# 多维表格写入（需配合飞书应用 tenant_access_token）
# ============================================================

def write_to_base(hazard_type: str, priority: str, camera_location: str,
                  detect_time: str, screenshot_path: str = None,
                  video_clip_path: str = None):
    """
    写入飞书多维表格（安环巡检记录表）
    需要飞书应用的 tenant_access_token 权限

    注意：附件字段需要先上传素材再回写 record
    此函数记录基础字段；附件上传需调用 upload_attachment() 后再更新 record
    """
    # 此处需要 tenant_access_token，从环境变量或配置读取
    # 实际部署时配置飞书应用凭证
    token = get_tenant_token()
    if not token:
        print("[WARN] 无 tenant_access_token，跳过多维表格写入")
        return None

    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/{TABLE_ID}/records"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 整改截止：P0=2小时, P1=24小时, P2=72小时
    deadline_hours = {"P0紧急": 2, "P1重要": 24, "P2一般": 72}
    deadline_ts = int(time.time() * 1000) + deadline_hours.get(priority, 24) * 3600 * 1000

    detect_ts = int(datetime.strptime(detect_time, "%Y-%m-%d %H:%M").timestamp() * 1000)

    fields = {
        "隐患类型": hazard_type,
        "优先级": priority,
        "发现时间": detect_ts,
        "监控点位": camera_location,
        "来源": "AI检测",
        "整改状态": "待整改",
        "整改截止": deadline_ts,
    }

    body = {"fields": fields}

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=10)
        result = resp.json()
        if result.get("code") == 0:
            record_id = result["data"]["record"]["record_id"]
            print(f"[OK] 多维表格写入成功: record_id={record_id}")
            # 附件上传后更新此 record
            if screenshot_path:
                upload_attachment(token, record_id, "证据截图", screenshot_path)
            if video_clip_path:
                upload_attachment(token, record_id, "证据视频", video_clip_path)
            return record_id
        else:
            print(f"[ERROR] 多维表格写入失败: {result}")
            return None
    except Exception as e:
        print(f"[ERROR] 多维表格写入异常: {e}")
        return None


def upload_attachment(token: str, record_id: str, field_name: str, file_path: str):
    """上传附件到多维表格记录"""
    url = (
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_TOKEN}"
        f"/tables/{TABLE_ID}/records/{record_id}/attachments"
    )
    headers = {"Authorization": f"Bearer {token}"}
    field_id = FIELD_IDS.get(field_name)

    try:
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"field_id": field_id}
            resp = requests.post(url, files=files, data=data, headers=headers, timeout=30)
            result = resp.json()
            if result.get("code") == 0:
                print(f"[OK] 附件上传成功: {field_name} → {file_path}")
            else:
                print(f"[ERROR] 附件上传失败: {result}")
    except Exception as e:
        print(f"[ERROR] 附件上传异常: {e}")


def get_tenant_token() -> str:
    """
    获取飞书应用 tenant_access_token
    实际部署时配置 APP_ID / APP_SECRET 环境变量
    """
    import os
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        return ""

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    body = {"app_id": app_id, "app_secret": app_secret}
    try:
        resp = requests.post(url, json=body, timeout=10)
        result = resp.json()
        return result.get("tenant_access_token", "")
    except Exception:
        return ""


# ============================================================
# CLI 测试入口
# ============================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("用法: python feishu_alert.py <场景key> <监控点位>")
        print(f"可用场景: {', '.join(DETECTION_SCENES.keys())}")
        print("示例: python feishu_alert.py fire_smoke '仓库A区-主通道'")
        sys.exit(1)

    scene = sys.argv[1]
    location = sys.argv[2]
    send_alert(scene, location)
