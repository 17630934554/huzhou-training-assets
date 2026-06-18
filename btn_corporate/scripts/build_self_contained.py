#!/usr/bin/env python3
"""把 btn-deck.html 打包成单文件自包含 HTML，复制到 用户上传/ 走 file_to_url"""
import re
from pathlib import Path

BASE = Path("/app/data/所有对话/主对话")
DECK = BASE / "btn_corporate" / "examples" / "btn-deck.html"
OUT_DIR = BASE / "用户上传"
OUT_FILE = OUT_DIR / "btn-deck-self-contained.html"

# 1) 读 HTML
html = DECK.read_text(encoding="utf-8")

# 2) 读所有外部 CSS
css_files = [
    BASE / "skills/html-ppt/assets/fonts.css",
    BASE / "skills/html-ppt/assets/base.css",
    BASE / "btn_corporate/assets/btn-corporate.css",
    BASE / "skills/html-ppt/assets/animations/animations.css",
]

inline_css_parts = []
for css_path in css_files:
    if css_path.exists():
        inline_css_parts.append("/* === " + css_path.name + " === */\n" + css_path.read_text(encoding="utf-8"))
    else:
        print("[warn] missing: " + str(css_path))

inline_css_block = "\n".join(inline_css_parts)

# 3) 移除所有 <link rel="stylesheet" ...>
html = re.sub(r'<link\s+rel="stylesheet"[^>]*>', '', html)

# 4) 把现有 <style> 块内容 + 内联 CSS 合并到第一个 <style> 块
m = re.search(r'<style[^>]*>(.*?)</style>', html, flags=re.DOTALL)
if m:
    existing = m.group(1)
    merged = inline_css_block + "\n" + existing
    html = re.sub(
        r'<style[^>]*>.*?</style>',
        lambda _m: "<style>\n" + merged + "\n</style>",
        html,
        count=1,
        flags=re.DOTALL
    )
else:
    html = html.replace("</head>", "<style>\n" + inline_css_block + "\n</style>\n</head>")

# 5) data-themes 改成 btn-corporate
html = re.sub(r'data-themes="[^"]*"', 'data-themes="btn-corporate"', html)
# data-theme-base 移除（不再有 ../ 路径）
html = re.sub(r'data-theme-base="[^"]*"', '', html)

# 6) 把 <script src="..."></script> 替换成 inline（用 placeholder 避免 f-string 解析问题）
html = re.sub(
    r'<script\s+src="[^"]*"[^>]*></script>',
    '<script>__RUNTIME_JS_PLACEHOLDER__</script>',
    html
)

# 7) 读 runtime.js 内联
runtime_path = BASE / "skills/html-ppt/assets/runtime.js"
runtime_js = runtime_path.read_text(encoding="utf-8")
runtime_tag = "<script>\n" + runtime_js + "\n</script>"
html = html.replace('<script>__RUNTIME_JS_PLACEHOLDER__</script>', runtime_tag)

# 8) 写出去
OUT_DIR.mkdir(exist_ok=True)
OUT_FILE.write_text(html, encoding="utf-8")
print("[ok] generated: " + str(OUT_FILE))
size = OUT_FILE.stat().st_size
print("     size: " + str(size) + " bytes (" + str(round(size/1024, 1)) + " KB)")
