#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_training.py - 培训资料系统 V3 端到端新增一条资料脚本
=================================================================

用法：
  python3 add_training.py \\
    --id 6 \\
    --html my_lesson_6.html \\
    --title "自动分拣机：托盘更换 SOP" \\
    --bvid BV1xxxxxxxx \\
    --duration "4:30"

功能（一条命令完成 3 件事）：
  1. 复制 --html 到 hosting/lesson_{id}.html（标准化文件名）
  2. 重新生成 hosting/index.html（自动加新资料卡片到导航页）
  3. 重新生成 hosting/qr/hosting_{id}_QR卡.png（QR 码指向新 URL）

约束（永久）：
  - **永远不要在 QR 卡或 HTML 里出现 "AI 生成" 或 "湖州仓·设备组"**
  - QR 卡视觉风格：白底+深蓝（#1e40af），简洁美观，标题+QR+URL
  - lesson 编号递增（5 → 6 → 7...），不覆盖已有 lesson

作者：九方（Coze 主 Agent）协助大刘完成
"""

import os
import sys
import json
import shutil
import re
import argparse
from pathlib import Path
from typing import List, Dict, Optional

# ==================== 配置 ====================

SCRIPT_DIR = Path(__file__).resolve().parent  # hosting/
HOSTING_DIR = SCRIPT_DIR  # hosting/lesson_*.html + index.html 都在这里
QR_DIR = HOSTING_DIR / "qr"
QR_DIR.mkdir(exist_ok=True)

# 永久禁词（2026-06-16 大刘要求，QR 卡 & 培训页都不要）
FORBIDDEN_WORDS = ["AI 生成", "湖州仓·设备组"]

# 颜色规范（与 V1/V2 飞书版 QR 卡一致）
COLOR_PRIMARY = "#1e40af"
COLOR_GOLD = "#d4a847"
COLOR_DARK_NAVY = "#0a2a5e"

# 默认 hosting URL
DEFAULT_BASE_URL = "https://huzhou-training.pages.dev"


# ==================== 工具函数 ====================

def log(msg: str, level: str = "INFO"):
    """带颜色日志输出"""
    colors = {
        "INFO": "\033[0;36m",  # cyan
        "OK": "\033[0;32m",  # green
        "WARN": "\033[0;33m",  # yellow
        "ERR": "\033[0;31m",  # red
    }
    color = colors.get(level, "")
    reset = "\033[0m"
    icon = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌"}.get(level, "•")
    print(f"{color}{icon} [{level}]{reset} {msg}")


def check_forbidden_words(text: str, context: str = ""):
    """检查禁词（QR 卡 & HTML 永久禁用）"""
    for word in FORBIDDEN_WORDS:
        if word in text:
            log(f"检测到禁词「{word}」{context}，请修改后重试", "ERR")
            sys.exit(1)


def find_existing_lessons() -> List[int]:
    """扫描 hosting/ 找出现有 lesson 编号（返回排序后的 int 列表）"""
    lessons = []
    for f in HOSTING_DIR.glob("lesson_*.html"):
        match = re.match(r"lesson_(\d+)\.html$", f.name)
        if match:
            lessons.append(int(match.group(1)))
    return sorted(lessons)


# ==================== 步骤 1：复制 HTML ====================

def copy_lesson_html(src_html: Path, target_id: int) -> Path:
    """复制 --html 到 hosting/lesson_{id}.html"""
    target = HOSTING_DIR / f"lesson_{target_id}.html"
    if target.exists():
        log(f"lesson_{target_id}.html 已存在，将被覆盖", "WARN")
    shutil.copy(src_html, target)
    size_kb = target.stat().st_size / 1024
    log(f"已复制 {src_html.name} → lesson_{target_id}.html ({size_kb:.0f}KB)", "OK")
    return target


# ==================== 步骤 2：重新生成 index.html ====================

def extract_lesson_meta(html_path: Path) -> Dict[str, str]:
    """从 lesson_*.html 提取 title 和 meta（用于 index.html 卡片）"""
    html = html_path.read_text(encoding="utf-8", errors="ignore")

    # 提取 <title>...</title>
    title_match = re.search(r"<title>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else html_path.stem

    # 提取 <meta name="description" content="...">
    desc_match = re.search(
        r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE)
    meta = desc_match.group(1).strip() if desc_match else "扫码查看培训资料"

    # 禁词检查
    check_forbidden_words(title, f"in {html_path.name} title")
    check_forbidden_words(meta, f"in {html_path.name} meta")

    return {"title": title, "meta": meta}


def render_index_html(lessons: List[Dict], base_url: str) -> str:
    """生成 hosting/index.html（导航页）"""
    # 按 id 排序
    lessons = sorted(lessons, key=lambda x: x["id"])

    cards_html = "\n".join(
        f'''      <a class="card" href="lesson_{l["id"]}.html">
        <span class="badge">{l["id"]:02d}</span>
        <h2>{l["title"]}</h2>
        <div class="meta">{l["meta"]}</div>
        <span class="arrow">›</span>
      </a>'''
        for l in lessons
    )

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>设备组 · 培训资料</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: "Microsoft YaHei", "微软雅黑", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: linear-gradient(180deg, #f5f7fb 0%, #ffffff 100%);
    color: #1a202c;
    min-height: 100vh;
    padding: 0 0 60px;
  }}
  .header {{
    background: linear-gradient(135deg, {COLOR_DARK_NAVY} 0%, {COLOR_PRIMARY} 100%);
    color: #fff;
    padding: 48px 24px 40px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }}
  .header::before {{
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, transparent 0%, {COLOR_GOLD} 50%, transparent 100%);
  }}
  .header h1 {{
    font-size: 28px;
    font-weight: 600;
    letter-spacing: 2px;
    margin-bottom: 8px;
  }}
  .header .subtitle {{
    font-size: 14px;
    opacity: 0.85;
    letter-spacing: 1px;
  }}
  .container {{
    max-width: 720px;
    margin: 0 auto;
    padding: 32px 20px;
  }}
  .intro {{
    text-align: center;
    color: #4a5568;
    font-size: 14px;
    line-height: 1.8;
    margin-bottom: 32px;
    padding: 0 12px;
  }}
  .grid {{
    display: grid;
    grid-template-columns: 1fr;
    gap: 16px;
  }}
  .card {{
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(10, 42, 94, 0.06), 0 1px 2px rgba(10, 42, 94, 0.04);
    padding: 24px 22px;
    text-decoration: none;
    color: inherit;
    display: block;
    transition: all 0.2s ease;
    border-left: 4px solid {COLOR_PRIMARY};
    position: relative;
  }}
  .card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(10, 42, 94, 0.12), 0 2px 4px rgba(10, 42, 94, 0.06);
    border-left-color: {COLOR_GOLD};
  }}
  .card .badge {{
    display: inline-block;
    background: #f0f4ff;
    color: {COLOR_PRIMARY};
    font-size: 12px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 10px;
    margin-bottom: 12px;
  }}
  .card h2 {{
    font-size: 18px;
    font-weight: 600;
    color: {COLOR_DARK_NAVY};
    margin-bottom: 8px;
    line-height: 1.4;
  }}
  .card .meta {{
    color: #718096;
    font-size: 13px;
    line-height: 1.6;
  }}
  .card .arrow {{
    position: absolute;
    right: 22px;
    top: 50%;
    transform: translateY(-50%);
    color: {COLOR_PRIMARY};
    font-size: 20px;
    font-weight: 300;
  }}
  .footer {{
    text-align: center;
    color: #a0aec0;
    font-size: 12px;
    margin-top: 48px;
    padding-top: 24px;
    border-top: 1px solid #e2e8f0;
  }}
  @media (max-width: 480px) {{
    .header {{ padding: 36px 20px 32px; }}
    .header h1 {{ font-size: 22px; }}
    .container {{ padding: 24px 16px; }}
    .card {{ padding: 20px 18px; }}
    .card h2 {{ font-size: 16px; }}
  }}
</style>
</head>
<body>
  <div class="header">
    <h1>设备组 · 培训资料</h1>
    <div class="subtitle">现场实操 · 扫码即看 · 长期有效</div>
  </div>
  <div class="container">
    <div class="intro">
      共 {len(lessons)} 份设备操作培训资料，每份含<strong style="color:{COLOR_PRIMARY};">现场讲解视频</strong> + <strong style="color:{COLOR_PRIMARY};">操作步骤截图</strong> + <strong style="color:{COLOR_PRIMARY};">故障分析</strong>。<br>
      点击进入查看，长期可访问。
    </div>
    <div class="grid">
{cards_html}
    </div>
    <div class="footer">
      设备组 · 培训资料库 · 长期托管
    </div>
  </div>
</body>
</html>
'''


def regenerate_index_html(lessons: List[Dict], base_url: str) -> Path:
    """重新生成 hosting/index.html（按现有 lesson_*.html 列表）"""
    index_path = HOSTING_DIR / "index.html"
    html = render_index_html(lessons, base_url)
    index_path.write_text(html, encoding="utf-8")
    log(f"已重新生成 index.html（{len(lessons)} 份资料）", "OK")
    return index_path


# ==================== 步骤 3：生成 QR 卡 ====================

def make_qr_card(url: str, title: str, out_path: Path):
    """生成 QR 卡 PNG（白底+深蓝+标题+QR+URL）

    复用 V1/V2 add_training.make_qr_card 视觉风格
    """
    import qrcode
    from PIL import Image, ImageDraw, ImageFont

    # 禁词检查
    check_forbidden_words(title, "in QR card title")
    check_forbidden_words(url, "in QR card url")

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12, border=2
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=COLOR_PRIMARY, back_color="white").convert("RGB")

    def get_font(size: int, bold: bool = False):
        for fp in [
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]:
            if os.path.exists(fp):
                try:
                    return ImageFont.truetype(fp, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    font_sub = get_font(20)
    font_url = get_font(16)

    def tw(t: str, f) -> tuple:
        b = ImageDraw.Draw(Image.new("RGB", (10, 10))).textbbox((0, 0), t, font=f)
        return b[2] - b[0], b[3] - b[1]

    CARD_W, MARGIN, GAP, QR_SIZE = 720, 36, 24, 460

    # 标题自适应字号
    _title_size = 34
    while True:
        _f = get_font(_title_size, bold=True)
        _w, _h = tw(title, _f)
        if _w <= CARD_W - 2 * MARGIN or _title_size <= 20:
            font_title = _f
            title_w, title_h = _w, _h
            break
        _title_size -= 2
    sub_w, sub_h = tw("扫码查看培训资料", font_sub)
    url_w, url_h = tw(url, font_url)

    CARD_H = MARGIN + 8 + title_h + GAP + sub_h + GAP + QR_SIZE + GAP + url_h + MARGIN

    card = Image.new("RGB", (CARD_W, CARD_H), "white")
    draw = ImageDraw.Draw(card)
    # 顶部蓝色装饰条
    draw.rectangle((0, 0, CARD_W, 8), fill=COLOR_PRIMARY)

    y = MARGIN + 8
    draw.text(((CARD_W - title_w) // 2, y), title, font=font_title, fill=COLOR_PRIMARY)
    y += title_h + GAP
    draw.text(((CARD_W - sub_w) // 2, y), "扫码查看培训资料", font=font_sub, fill="#6b7280")
    y += sub_h + GAP

    qr_x = (CARD_W - QR_SIZE) // 2
    draw.rectangle((qr_x - 8, y - 8, qr_x + QR_SIZE + 8, y + QR_SIZE + 8),
                   outline=COLOR_PRIMARY, width=3)
    card.paste(qr_img.resize((QR_SIZE, QR_SIZE), Image.LANCZOS), (qr_x, y))
    y += QR_SIZE + GAP
    draw.text(((CARD_W - url_w) // 2, y), url, font=font_url, fill="#374151")

    card.save(out_path, "PNG", quality=95)
    size_kb = out_path.stat().st_size / 1024
    log(f"QR 卡生成: {out_path.name} ({size_kb:.0f}KB) → {url}", "OK")


def generate_qr_card(lesson_id: int, title: str, base_url: str) -> Path:
    """为指定 lesson 生成 QR 卡"""
    url = f"{base_url}/lesson_{lesson_id}.html"
    qr_name = f"hosting_{lesson_id}_QR卡.png"
    out_path = QR_DIR / qr_name
    make_qr_card(url, title, str(out_path))
    return out_path


# ==================== 主流程 ====================

def main():
    parser = argparse.ArgumentParser(
        description="培训资料系统 V3 端到端新增一条资料脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python3 add_training.py \\
    --id 6 \\
    --html my_lesson_6.html \\
    --title "自动分拣机：托盘更换 SOP" \\
    --bvid BV1xxxxxxxx \\
    --duration "4:30"

输出 3 个文件：
  1. hosting/lesson_{id}.html
  2. hosting/index.html（重新生成，含新卡片）
  3. hosting/qr/hosting_{id}_QR卡.png

下一步：git add + commit + push → Cloudflare Pages 1-2 分钟自动部署
        """
    )
    parser.add_argument("--id", type=int, required=True, help="资料编号（6, 7, 8...）")
    parser.add_argument("--html", type=Path, required=True, help="源 HTML 文件路径")
    parser.add_argument("--title", required=True, help="资料标题（用于 QR 卡和 index.html 卡片）")
    parser.add_argument("--bvid", required=True, help="B 站 BV 号（会嵌入 HTML 的视频 iframe）")
    parser.add_argument("--duration", required=True, help="视频时长（例 4:30 或 270s）")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"hosting 基础 URL（默认 {DEFAULT_BASE_URL}）")
    args = parser.parse_args()

    target_id = args.id
    src_html = args.html.resolve()
    title = args.title.strip()
    bvid = args.bvid.strip()
    duration = args.duration.strip()
    base_url = args.base_url.rstrip("/")

    # === 前置检查 ===
    if not src_html.exists():
        log(f"源 HTML 文件不存在: {src_html}", "ERR")
        sys.exit(1)
    if not src_html.is_file():
        log(f"源 HTML 不是文件: {src_html}", "ERR")
        sys.exit(1)
    if not bvid.startswith("BV"):
        log(f"BV 号格式错误: {bvid}（应以 BV 开头）", "ERR")
        sys.exit(1)

    # 禁词检查（标题）
    check_forbidden_words(title, "in --title")

    # === 检查 lesson 编号冲突 ===
    existing = find_existing_lessons()
    if target_id in existing:
        log(f"lesson_{target_id}.html 已存在，将被覆盖（当前 {existing}）", "WARN")

    log("=" * 60)
    log(f"开始新增培训资料 #{target_id}: {title}")
    log("=" * 60)

    # === 步骤 1：复制 HTML ===
    log(f"[1/3] 复制 HTML 文件...", "INFO")
    copy_lesson_html(src_html, target_id)

    # === 步骤 2：重新生成 index.html ===
    log(f"[2/3] 重新生成 index.html...", "INFO")
    all_lessons = []
    for lid in sorted(existing + [target_id]):
        lesson_html = HOSTING_DIR / f"lesson_{lid}.html"
        if lesson_html.exists():
            meta = extract_lesson_meta(lesson_html)
            all_lessons.append({
                "id": lid,
                "title": meta["title"],
                "meta": meta["meta"],
            })
    index_path = regenerate_index_html(all_lessons, base_url)

    # === 步骤 3：生成 QR 卡 ===
    log(f"[3/3] 生成 QR 卡...", "INFO")
    qr_path = generate_qr_card(target_id, title, base_url)

    # === 完成报告 ===
    log("=" * 60)
    log("✅ 新增完成！", "OK")
    log("=" * 60)
    log(f"  📄 培训页:  {HOSTING_DIR / f'lesson_{target_id}.html'}")
    log(f"  📑 导航页:  {index_path}")
    log(f"  📱 QR 卡:   {qr_path}")
    log(f"  🔗 URL:     {base_url}/lesson_{target_id}.html")
    log("")
    log("下一步操作：", "INFO")
    log("  1. 推上 GitHub 触发自动部署：")
    log("     git add lesson_{}.html index.html".format(target_id))
    log("     git commit -m \"新增 demo{}：{}\"".format(target_id, title))
    log("     git push")
    log("  2. 飞书侧同步（可选）：")
    log("     - 上传 QR 卡到飞书云空间 QR卡/ 目录")
    log("     - 多维表格加一条记录（培训页 + QR卡 字段）")
    log("  3. 等 1-2 分钟 → Cloudflare Pages 自动部署生效")


if __name__ == "__main__":
    main()
