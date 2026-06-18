#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
btn_html_slides.py — 贝泰妮品牌 HTML 幻灯片生成器

从 JSON/YAML/Markdown 配置 → 输出 BTN 品牌 HTML 幻灯片
6 种页面模板：cover / toc / stat / two-column / cta / thanks
特性：
  1. 文字可编辑（contenteditable + localStorage 自动保存）
  2. 视频内嵌（<video> + bilibili BV 号 + 本地 mp4）
  3. 自动内联所有 CSS/JS（单文件自包含）
  4. 内置 btn-corporate.css 主题

用法：
  python btn_html_slides.py --config report.yaml --output report.html
  python btn_html_slides.py --config report.json --output report.html --self-contained
  python btn_html_slides.py --config report.json --output report.html --no-inline  # 不内联资源

配置文件格式（YAML/JSON）：
  meta:
    title: "贝泰妮物流部·设备组 2026 H1 汇报"
    brand: "贝泰妮集团"
    footer: "贝泰妮集团 物流部"
  pages:
    - type: cover
      kicker: "2026 · 年中汇报"
      title: "设备组<br><span>年中汇报</span>"
      lede: "培训资料系统 V3 · 改造案例 · 技术升级"
    - type: toc
      kicker: "Agenda"
      title: "汇报四件事"
      items:
        - n: "01"
          t: "设备文件管理"
          d: "培训资料系统 V2.1 → V3"
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# 路径
BASE = Path(__file__).resolve().parent.parent.parent  # 主对话/
SCRIPT_DIR = Path(__file__).resolve().parent

# 资源路径
RES_CSS_FILES = [
    BASE / "skills/html-ppt/assets/fonts.css",
    BASE / "skills/html-ppt/assets/base.css",
    BASE / "btn_corporate/assets/btn-corporate.css",
    BASE / "skills/html-ppt/assets/animations/animations.css",
]
RES_RUNTIME_JS = BASE / "skills/html-ppt/assets/runtime.js"


# ============== 配置加载 ==============

def load_config(path: Path) -> Dict:
    """加载 YAML/JSON/Markdown 配置"""
    if not path.exists():
        print(f"[err] config 文件不存在: {path}")
        sys.exit(1)

    suffix = path.suffix.lower()
    raw = path.read_text(encoding="utf-8")

    if suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            print("[err] 需要 PyYAML: pip install pyyaml")
            sys.exit(1)
        return yaml.safe_load(raw)
    elif suffix == ".json":
        return json.loads(raw)
    elif suffix in (".md", ".markdown"):
        return parse_markdown_config(raw)
    else:
        # 尝试 JSON
        try:
            return json.loads(raw)
        except Exception:
            print(f"[err] 不识别的配置文件格式: {suffix}")
            sys.exit(1)


def parse_markdown_config(raw: str) -> Dict:
    """极简 Markdown 配置解析

    格式：
      # title: 贝泰妮物流部·设备组 2026 H1 汇报
      # brand: 贝泰妮集团
      # footer: 贝泰妮集团 物流部

      ## cover
      kicker: 2026 · 年中汇报
      title: 设备组\\n年中汇报
      lede: 培训资料系统 V3

      ## toc
      items:
        - 01 | 设备文件管理 | 培训资料系统 V2.1 → V3
        - 02 | 关键数据 | 5 份 / 5 个 B 站
    """
    meta: Dict[str, Any] = {}
    pages: List[Dict] = []
    current_page: Optional[Dict] = None
    current_type: Optional[str] = None

    lines = raw.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # 跳过空行
        if not line.strip():
            i += 1
            continue

        # 一级标题 # → meta
        if line.startswith("# ") and not line.startswith("## "):
            kv = line[2:].split(":", 1)
            if len(kv) == 2:
                meta[kv[0].strip()] = kv[1].strip()
            i += 1
            continue

        # 二级标题 ## → 新页面
        if line.startswith("## "):
            if current_page:
                pages.append(current_page)
            current_type = line[3:].strip().lower()
            current_page = {"type": current_type}
            i += 1
            continue

        # 普通内容行
        if current_page is not None:
            # 简单 key: value
            m = re.match(r"^(\w+):\s*(.+)$", line)
            if m:
                key = m.group(1).strip()
                val = m.group(2).strip()
                # 处理 list
                if val.startswith("[") and val.endswith("]"):
                    try:
                        current_page[key] = json.loads(val)
                    except Exception:
                        current_page[key] = val
                # 处理 yaml-like list  - 01 | 标题 | 描述
                elif "|" in val and key in ("items", "kpis", "cases"):
                    items = [x.strip() for x in val.split("|")]
                    current_page[key] = items
                else:
                    current_page[key] = val
            else:
                # 多行 raw 文本（video:、kicker: 等）— 跳过细节
                pass
        i += 1

    if current_page:
        pages.append(current_page)

    return {"meta": meta, "pages": pages}


# ============== 页面渲染 ==============

def esc(s: Any) -> str:
    """HTML 转义"""
    if s is None:
        return ""
    s = str(s)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_cover(p: Dict, idx: int, total: int) -> str:
    """封面页 — 品牌蓝渐变 + 大标题"""
    kicker = esc(p.get("kicker", ""))
    title = esc(p.get("title", "Untitled"))
    lede = esc(p.get("lede", ""))
    show_logo = p.get("logo", True)

    logo_html = ""
    if show_logo:
        logo_html = '''<div class="btn-logo" style="margin-bottom:48px">
      <span class="mark">BTN</span>
      <span class="label">
        <span class="name">贝泰妮集团</span>
        <span class="sub">BOTANEE GROUP</span>
      </span>
    </div>'''

    return f'''
  <!-- Page {idx}: 封面 -->
  <section class="slide brand-bg is-active" data-title="封面" data-page-type="cover">
    <div class="hero-deco"></div>
    {logo_html}
    <p class="kicker" contenteditable="true">{kicker}</p>
    <h1 class="h1 anim-fade-up" data-anim="fade-up" style="font-size:96px;line-height:1.05;margin:24px 0 32px" contenteditable="true">{title}</h1>
    <p class="lede" style="font-size:24px;margin-top:24px" contenteditable="true">{lede}</p>
    <div class="deck-footer" style="margin-top:auto">
      <span class="brand" contenteditable="true">__FOOTER__</span>
      <span class="slide-number" data-current="{idx}" data-total="{total}"></span>
    </div>
  </section>'''


def render_toc(p: Dict, idx: int, total: int) -> str:
    """目录页 — 大数字 + 列表"""
    kicker = esc(p.get("kicker", "Agenda"))
    title = esc(p.get("title", "目录"))
    items = p.get("items", [])
    lede = esc(p.get("lede", ""))

    items_html = "\n".join([
        f'<li><span class="n">{esc(item.get("n", str(i+1).zfill(2)))}</span><span class="t" contenteditable="true">{esc(item.get("t", ""))}</span><span class="d" contenteditable="true">{esc(item.get("d", ""))}</span></li>'
        for i, item in enumerate(items)
    ])

    lede_html = f'<p class="lede" style="margin-top:12px" contenteditable="true">{lede}</p>' if lede else ""

    return f'''
  <!-- Page {idx}: 目录 -->
  <section class="slide" data-title="目录" data-page-type="toc">
    <p class="kicker" contenteditable="true">{kicker}</p>
    <h2 class="h2" contenteditable="true">{title}</h2>
    {lede_html}
    <ol class="toc-list anim-stagger-list" data-anim-target>
      {items_html}
    </ol>
    <div class="deck-footer">
      <span class="brand" contenteditable="true">__FOOTER__</span>
      <span class="slide-number" data-current="{idx}" data-total="{total}"></span>
    </div>
  </section>'''


def render_stat(p: Dict, idx: int, total: int) -> str:
    """KPI 数字页 — 4 个大数字"""
    kicker = esc(p.get("kicker", "Result"))
    title = esc(p.get("title", "关键数据"))
    lede = esc(p.get("lede", ""))
    kpis = p.get("kpis", [])

    kpi_items = []
    for i, k in enumerate(kpis):
        gold = " gold" if i % 4 in (1, 3) else ""  # 错位金色
        v = esc(k.get("v", "0"))
        l = esc(k.get("l", ""))
        kpi_items.append(f'<div class="kpi{gold}"><div class="v" contenteditable="true">{v}</div><div class="l" contenteditable="true">{l}</div></div>')

    lede_html = f'<p class="lede" style="margin-top:12px" contenteditable="true">{lede}</p>' if lede else ""

    # 可选引用块
    quote_html = ""
    if p.get("quote"):
        quote = p["quote"]
        quote_html = f'''
    <div class="btn-quote" style="margin-top:32px">
      <div class="tag">{esc(quote.get("tag", "交付"))}</div>
      <div class="body" contenteditable="true">{esc(quote.get("body", ""))}</div>
      <div class="who" contenteditable="true">— {esc(quote.get("who", ""))}</div>
    </div>'''

    return f'''
  <!-- Page {idx}: 关键数据 -->
  <section class="slide" data-title="关键数据" data-page-type="stat">
    <p class="kicker" contenteditable="true">{kicker}</p>
    <h2 class="h2" contenteditable="true">{title}</h2>
    {lede_html}
    <div class="kpi-row anim-stagger-list" data-anim-target>
      {''.join(kpi_items)}
    </div>{quote_html}
    <div class="deck-footer">
      <span class="brand" contenteditable="true">__FOOTER__</span>
      <span class="slide-number" data-current="{idx}" data-total="{total}"></span>
    </div>
  </section>'''


def render_two_column(p: Dict, idx: int, total: int) -> str:
    """双栏页 — 时间线 + 成就卡（V3 风格）"""
    kicker = esc(p.get("kicker", ""))
    title = esc(p.get("title", ""))
    lede = esc(p.get("lede", ""))
    timeline = p.get("timeline", [])
    achievements = p.get("achievements", [])

    # 时间线 HTML
    timeline_items = []
    for i, t in enumerate(timeline):
        gold = " gold" if i % 2 == 1 else ""
        timeline_items.append(f'''<div class="item{gold}">
          <div class="time" contenteditable="true">{esc(t.get("time", ""))}</div>
          <div class="what" contenteditable="true">{esc(t.get("what", ""))}</div>
          <div class="why" contenteditable="true">{esc(t.get("why", ""))}</div>
        </div>''')

    timeline_html = f'<div class="btn-timeline anim-stagger-list" data-anim-target>{"".join(timeline_items)}</div>' if timeline else ""

    # 成就卡 HTML
    achv_items = []
    for a in achievements:
        achv_items.append(f'''<div class="a">
          <div class="icon" contenteditable="true">{esc(a.get("icon", "0"))}</div>
          <div class="t" contenteditable="true">{esc(a.get("t", ""))}</div>
          <div class="d" contenteditable="true">{esc(a.get("d", ""))}</div>
        </div>''')

    achv_html = f'<div class="achv-grid anim-stagger-list" data-anim-target>{"".join(achv_items)}</div>' if achievements else ""

    lede_html = f'<p class="lede" style="margin-top:12px" contenteditable="true">{lede}</p>' if lede else ""

    return f'''
  <!-- Page {idx}: 双栏 -->
  <section class="slide" data-title="{esc(title)}" data-page-type="two-column">
    <p class="kicker" contenteditable="true">{kicker}</p>
    <h2 class="h2" contenteditable="true">{title}</h2>
    {lede_html}
    <div style="display:grid;grid-template-columns:1.1fr .9fr;gap:48px;margin-top:32px">
      {timeline_html}
      {achv_html}
    </div>
    <div class="deck-footer">
      <span class="brand" contenteditable="true">__FOOTER__</span>
      <span class="slide-number" data-current="{idx}" data-total="{total}"></span>
    </div>
  </section>'''


def render_cta(p: Dict, idx: int, total: int) -> str:
    """改造案例页 — 多个引用块"""
    kicker = esc(p.get("kicker", "Optimization"))
    title = esc(p.get("title", "改造案例"))
    lede = esc(p.get("lede", ""))
    cases = p.get("cases", [])

    # 处理 markdown-style list 形式: "TAG | TITLE | BODY | WHO"
    case_items = []
    for i, c in enumerate(cases):
        if isinstance(c, str) and "|" in c:
            parts = [x.strip() for x in c.split("|")]
            if len(parts) >= 3:
                c = {"tag": parts[0], "title": parts[1], "body": parts[2], "who": parts[3] if len(parts) > 3 else ""}

        tag_bg = "background:var(--btn-gold)" if (i % 3 == 1) else ""
        anim_delay = f"animation-delay:.{i*100}ms" if i > 0 else ""
        case_items.append(f'''<div class="btn-quote anim-fade-up" data-anim="fade-up" style="{anim_delay}">
        <div class="tag" style="{tag_bg}">{esc(c.get("tag", f"CASE {i+1:02d}"))}</div>
        <div class="body" contenteditable="true"><strong>{esc(c.get("title", ""))}</strong> — {esc(c.get("body", ""))}</div>
        <div class="who" contenteditable="true">— {esc(c.get("who", ""))}</div>
      </div>''')

    lede_html = f'<p class="lede" style="margin-top:12px" contenteditable="true">{lede}</p>' if lede else ""

    return f'''
  <!-- Page {idx}: 改造案例 -->
  <section class="slide" data-title="改造案例" data-page-type="cta">
    <p class="kicker" contenteditable="true">{kicker}</p>
    <h2 class="h2" contenteditable="true">{title}</h2>
    {lede_html}
    <div style="display:grid;grid-template-columns:1fr;gap:18px;margin-top:28px;max-width:980px">
      {''.join(case_items)}
    </div>
    <div class="deck-footer">
      <span class="brand" contenteditable="true">__FOOTER__</span>
      <span class="slide-number" data-current="{idx}" data-total="{total}"></span>
    </div>
  </section>'''


def render_thanks(p: Dict, idx: int, total: int) -> str:
    """结束页 — 品牌渐变 + 大字"""
    kicker = esc(p.get("kicker", ""))
    title = esc(p.get("title", "感谢聆听"))
    lede = esc(p.get("lede", ""))
    show_logo = p.get("logo", True)
    show_hints = p.get("hints", True)

    logo_html = ""
    if show_logo:
        logo_html = '''<div class="btn-logo" style="margin-bottom:32px">
      <span class="mark">BTN</span>
      <span class="label">
        <span class="name">贝泰妮集团</span>
        <span class="sub">BOTANEE GROUP</span>
      </span>
    </div>'''

    hints_html = '<div style="font-size:14px;opacity:.85;letter-spacing:.08em">← → 翻页 · T 切主题 · A 切动效 · F 全屏</div>' if show_hints else ""

    return f'''
  <!-- Page {idx}: 结束 -->
  <section class="slide brand-bg center tc" data-title="结束" data-page-type="thanks">
    <div class="hero-deco gold"></div>
    {logo_html}
    {f'<p class="kicker" contenteditable="true">{kicker}</p>' if kicker else ''}
    <h1 class="h1 anim-rise-in" data-anim="rise-in" style="font-size:128px;line-height:1;margin:32px 0" contenteditable="true">{title}</h1>
    {f'<p class="lede" style="font-size:22px;margin:24px 0 32px" contenteditable="true">{lede}</p>' if lede else ''}
    {hints_html}
    <div class="deck-footer" style="margin-top:48px">
      <span class="brand" contenteditable="true">__FOOTER__</span>
      <span class="slide-number" data-current="{idx}" data-total="{total}"></span>
    </div>
  </section>'''


def render_section(p: Dict, idx: int, total: int) -> str:
    """章节页 — 大数字章节标题"""
    section_num = esc(p.get("section_num", str(idx).zfill(2)))
    kicker = esc(p.get("kicker", ""))
    title = esc(p.get("title", ""))
    lede = esc(p.get("lede", ""))

    return f'''
  <!-- Page {idx}: 章节 -->
  <section class="slide" data-title="章节" data-page-type="section">
    <div class="section-num" contenteditable="true">{section_num}</div>
    {f'<span class="section-kicker" contenteditable="true">{kicker}</span>' if kicker else ''}
    <h2 class="h2" style="font-size:64px;line-height:1.1;margin-top:14px" contenteditable="true">{title}</h2>
    {f'<p class="lede" style="margin-top:20px;font-size:20px" contenteditable="true">{lede}</p>' if lede else ''}
    <div class="deck-footer">
      <span class="brand" contenteditable="true">__FOOTER__</span>
      <span class="slide-number" data-current="{idx}" data-total="{total}"></span>
    </div>
  </section>'''


def render_video(p: Dict, idx: int, total: int) -> str:
    """视频页 — 嵌入视频"""
    kicker = esc(p.get("kicker", ""))
    title = esc(p.get("title", ""))
    lede = esc(p.get("lede", ""))
    video_src = p.get("video", "")
    video_type = p.get("video_type", "mp4")
    bv_id = p.get("bv_id", "")
    tip = esc(p.get("tip", ""))

    if bv_id:
        # bilibili BV 号嵌入
        # 去掉 BV 前缀（B 站 API 只需要数字）
        bvid = bv_id.replace("BV", "").replace("bv", "")
        video_html = f'''<iframe src="//player.bilibili.com/player.html?bvid=BV{bvid}&autoplay=0&high_quality=1"
                scrolling="no" frameborder="no" framespacing="0" allowfullscreen="true"
                style="width:100%;height:480px;border-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,0.1);background:#000"></iframe>'''
    elif video_src:
        # 本地 mp4 或远程 URL
        if not video_src.startswith(("http://", "https://", "/", "./", "../")):
            video_src = "./" + video_src
        video_html = f'''<video controls preload="metadata" style="width:100%;max-height:480px;display:block;border-radius:12px;background:#000;box-shadow:0 4px 16px rgba(0,0,0,0.1)">
        <source src="{esc(video_src)}" type="video/{esc(video_type)}">
        您的浏览器不支持 video 标签。
      </video>'''
    else:
        video_html = '<div style="background:#f5f5f5;padding:80px;text-align:center;border-radius:12px;color:#999">未配置视频</div>'

    tip_html = f'<div class="video-tip" style="background:#fef3c7;color:#92400e;padding:10px 16px;border-radius:8px;font-size:13px;margin-top:10px;border-left:3px solid #f59e0b">{tip}</div>' if tip else ""

    return f'''
  <!-- Page {idx}: 视频 -->
  <section class="slide" data-title="视频" data-page-type="video">
    <p class="kicker" contenteditable="true">{kicker}</p>
    <h2 class="h2" contenteditable="true">{title}</h2>
    {f'<p class="lede" style="margin-top:12px" contenteditable="true">{lede}</p>' if lede else ''}
    <div style="margin-top:28px;max-width:920px">
      {video_html}
      {tip_html}
    </div>
    <div class="deck-footer">
      <span class="brand" contenteditable="true">__FOOTER__</span>
      <span class="slide-number" data-current="{idx}" data-total="{total}"></span>
    </div>
  </section>'''


def render_planning(p: Dict, idx: int, total: int) -> str:
    """下半年规划页 — 时间线 + 重点事项"""
    kicker = esc(p.get("kicker", "Planning"))
    title = esc(p.get("title", "下半年规划"))
    lede = esc(p.get("lede", ""))
    timeline = p.get("timeline", [])

    timeline_items = []
    for i, t in enumerate(timeline):
        gold = " gold" if i % 2 == 1 else ""
        timeline_items.append(f'''<div class="item{gold}">
          <div class="time" contenteditable="true">{esc(t.get("time", ""))}</div>
          <div class="what" contenteditable="true">{esc(t.get("what", ""))}</div>
          <div class="why" contenteditable="true">{esc(t.get("why", ""))}</div>
        </div>''')

    lede_html = f'<p class="lede" style="margin-top:12px" contenteditable="true">{lede}</p>' if lede else ""

    return f'''
  <!-- Page {idx}: 下半年规划 -->
  <section class="slide" data-title="下半年规划" data-page-type="planning">
    <p class="kicker" contenteditable="true">{kicker}</p>
    <h2 class="h2" contenteditable="true">{title}</h2>
    {lede_html}
    <div style="display:grid;grid-template-columns:1fr;gap:0;margin-top:24px;max-width:980px">
      <div class="btn-timeline anim-stagger-list" data-anim-target>
        {''.join(timeline_items)}
      </div>
    </div>
    <div class="deck-footer">
      <span class="brand" contenteditable="true">__FOOTER__</span>
      <span class="slide-number" data-current="{idx}" data-total="{total}"></span>
    </div>
  </section>'''


def render_intro(p: Dict, idx: int, total: int) -> str:
    """部门介绍页 — 网格 + 文字"""
    kicker = esc(p.get("kicker", ""))
    title = esc(p.get("title", ""))
    lede = esc(p.get("lede", ""))
    sections = p.get("sections", [])

    section_html = []
    for s in sections:
        section_html.append(f'''<div class="btn-card">
          <div class="num" contenteditable="true">{esc(s.get("num", ""))}</div>
          <h3 class="t" contenteditable="true">{esc(s.get("title", ""))}</h3>
          <div class="d" contenteditable="true">{esc(s.get("body", ""))}</div>
        </div>''')

    lede_html = f'<p class="lede" style="margin-top:12px" contenteditable="true">{lede}</p>' if lede else ""

    return f'''
  <!-- Page {idx}: 部门介绍 -->
  <section class="slide" data-title="部门介绍" data-page-type="intro">
    <p class="kicker" contenteditable="true">{kicker}</p>
    <h2 class="h2" contenteditable="true">{title}</h2>
    {lede_html}
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:32px">
      {''.join(section_html)}
    </div>
    <div class="deck-footer">
      <span class="brand" contenteditable="true">__FOOTER__</span>
      <span class="slide-number" data-current="{idx}" data-total="{total}"></span>
    </div>
  </section>'''


# 模板调度器
RENDERERS = {
    "cover": render_cover,
    "toc": render_toc,
    "stat": render_stat,
    "two-column": render_two_column,
    "cta": render_cta,
    "thanks": render_thanks,
    "section": render_section,
    "video": render_video,
    "planning": render_planning,
    "intro": render_intro,
}


# ============== 主组装 ==============

def build_html(config: Dict, inline: bool = True) -> str:
    """从 config 构造 HTML"""
    meta = config.get("meta", {})
    pages = config.get("pages", [])

    if not pages:
        print("[err] 配置里没有任何页面（pages: [])")
        sys.exit(1)

    title = esc(meta.get("title", "贝泰妮汇报幻灯片"))
    footer = esc(meta.get("footer", "贝泰妮集团 物流部"))

    # 渲染所有页面
    rendered_pages = []
    total = len(pages)
    for i, p in enumerate(pages, 1):
        page_type = p.get("type", "").lower()
        renderer = RENDERERS.get(page_type)
        if not renderer:
            print(f"[warn] 未知页面类型: {page_type}（page {i}），跳过")
            continue
        rendered = renderer(p, i, total)
        rendered = rendered.replace("__FOOTER__", footer)
        rendered_pages.append(rendered)

    body = "\n".join(rendered_pages)

    if inline:
        # 内联所有 CSS
        css_block = build_inline_css()
        runtime_js_inline = build_inline_js()
        head_styles = f"<style>\n{css_block}\n</style>"
        head_links = ""  # 移除所有 <link rel="stylesheet">
        script_tag = f"<script>\n{runtime_js_inline}\n</script>"
        theme_attr = 'data-themes="btn-corporate"'
    else:
        head_styles = ""
        head_links = '''<link rel="stylesheet" href="../../skills/html-ppt/assets/fonts.css">
  <link rel="stylesheet" href="../../skills/html-ppt/assets/base.css">
  <link rel="stylesheet" href="../assets/btn-corporate.css">
  <link rel="stylesheet" href="../../skills/html-ppt/assets/animations/animations.css">'''
        script_tag = '<script src="../../skills/html-ppt/assets/runtime.js"></script>'
        theme_attr = 'data-themes="btn-corporate" data-theme-base="../../skills/html-ppt/assets/themes/"'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="btn-corporate">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
{head_links}
{head_styles}
<style>
/* ========== BTN 品牌专用 inline 增强 ========== */
.slide{{position:relative}}
.slide.brand-bg{{
  background:linear-gradient(135deg,#0a2540 0%,#1d4ed8 100%);
  color:#fff;
}}
.slide.brand-bg .kicker{{color:rgba(255,255,255,.85)}}
.slide.brand-bg h1,.slide.brand-bg h2,.slide.brand-bg h3{{color:#fff}}
.slide.brand-bg .lede{{color:rgba(255,255,255,.85)}}
.slide.brand-bg .deck-footer{{border-top-color:rgba(255,255,255,.18);color:rgba(255,255,255,.7)}}
.slide.brand-bg .deck-footer .brand{{color:#fff}}
.slide.brand-bg .btn-logo .label .name{{color:#fff}}
.slide.brand-bg .btn-logo .label .sub{{color:rgba(255,255,255,.6)}}

.toc-list{{list-style:none;padding:0;margin:32px 0;max-width:780px}}
.toc-list li{{
  display:flex;align-items:baseline;gap:24px;
  padding:18px 0;
  border-bottom:1px solid var(--border);
  font-size:24px;font-weight:500;color:var(--accent);
  transition:padding-left .25s var(--ease);
}}
.toc-list li:hover{{padding-left:8px}}
.toc-list li .n{{
  font-size:36px;font-weight:800;line-height:1;
  background:var(--grad);
  -webkit-background-clip:text;background-clip:text;
  -webkit-text-fill-color:transparent;color:transparent;
  min-width:60px;
}}
.toc-list li .t{{flex:1}}
.toc-list li .d{{font-size:14px;color:var(--text-3);font-weight:400}}

/* ========== 编辑模式视觉提示 ========== */
[contenteditable="true"]{{
  outline:none;
  transition:background .15s var(--ease);
  border-radius:4px;
  padding:2px 4px;
  margin:-2px -4px;
}}
[contenteditable="true"]:hover{{background:rgba(29,78,216,.06)}}
[contenteditable="true"]:focus{{background:rgba(29,78,216,.12);box-shadow:0 0 0 2px rgba(29,78,216,.3)}}

/* 编辑模式提示条 */
.edit-hint{{
  position:fixed;bottom:16px;left:50%;transform:translateX(-50%);
  background:var(--accent);color:#fff;
  padding:6px 14px;border-radius:999px;
  font-size:11px;letter-spacing:.1em;
  z-index:9999;opacity:0;pointer-events:none;
  transition:opacity .25s var(--ease);
}}
body.edit-mode .edit-hint{{opacity:1}}
</style>
</head>
<body {theme_attr}>
<div class="deck">
{body}
</div>
<div class="edit-hint">✏️ 编辑模式 · 自动保存到 localStorage</div>
{script_tag}
<script>
/* ========== 文字可编辑 + localStorage 自动保存 ========== */
(function(){{
  var STORAGE_KEY = 'btn-deck-content-{title}';
  var saved = '';
  try {{ saved = localStorage.getItem(STORAGE_KEY) || ''; }} catch(e) {{}}
  if (saved) {{
    try {{
      var data = JSON.parse(saved);
      document.querySelectorAll('[contenteditable="true"]').forEach(function(el){{
        var key = el.dataset.key || el.outerHTML.slice(0, 80);
        if (data[key] !== undefined) {{ el.innerHTML = data[key]; }}
      }});
    }} catch(e) {{}}
  }}

  // 给每个可编辑元素加 data-key（用 outerHTML 头 80 字符当 key）
  document.querySelectorAll('[contenteditable="true"]').forEach(function(el){{
    el.dataset.key = el.outerHTML.slice(0, 80);
    el.addEventListener('input', function(){{
      var data = {{}};
      document.querySelectorAll('[contenteditable="true"]').forEach(function(e){{
        data[e.dataset.key] = e.innerHTML;
      }});
      try {{ localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); }} catch(e) {{}}
    }});
  }});

  // 双击进入编辑模式（点击空白退出）
  var body = document.body;
  body.addEventListener('dblclick', function(e){{
    if (e.target.closest('[contenteditable]')) return;
    var isEditing = body.classList.toggle('edit-mode');
    document.querySelectorAll('[contenteditable="true"]').forEach(function(el){{
      el.contentEditable = isEditing ? 'true' : 'false';
    }});
  }});
}})();
</script>
</body>
</html>
"""
    return html


def build_inline_css() -> str:
    """读所有外部 CSS 文件并合并"""
    parts = []
    for css_path in RES_CSS_FILES:
        if css_path.exists():
            parts.append(f"/* === {css_path.name} === */\n{css_path.read_text(encoding='utf-8')}")
        else:
            print(f"[warn] CSS 资源缺失: {css_path}")
    return "\n".join(parts)


def build_inline_js() -> str:
    """读 runtime.js"""
    if RES_RUNTIME_JS.exists():
        return RES_RUNTIME_JS.read_text(encoding="utf-8")
    print(f"[warn] runtime.js 资源缺失: {RES_RUNTIME_JS}")
    return "/* runtime.js 缺失，请检查路径 */"


# ============== CLI ==============

def main():
    parser = argparse.ArgumentParser(
        description="贝泰妮品牌 HTML 幻灯片生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python btn_html_slides.py --config report.yaml --output report.html
  python btn_html_slides.py --config report.json --output report.html
  python btn_html_slides.py --config report.json --output report.html --no-inline
        """
    )
    parser.add_argument("--config", "-c", required=True, help="配置文件路径（YAML/JSON/Markdown）")
    parser.add_argument("--output", "-o", required=True, help="输出 HTML 路径")
    parser.add_argument("--no-inline", action="store_true", help="不内联 CSS/JS（用相对路径）")
    parser.add_argument("--self-contained", action="store_true", help="强制内联（默认就是内联）")

    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    output_path = Path(args.output).resolve()

    print(f"[info] 加载配置: {config_path}")
    config = load_config(config_path)
    n_pages = len(config.get("pages", []))
    print(f"[info] 解析到 {n_pages} 页")

    inline = not args.no_inline
    print(f"[info] 内联模式: {'是' if inline else '否'}")

    html = build_html(config, inline=inline)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    size = output_path.stat().st_size
    print(f"[ok] 生成: {output_path}")
    print(f"     size: {size} bytes ({round(size/1024, 1)} KB)")
    print(f"     pages: {n_pages}")


if __name__ == "__main__":
    main()
