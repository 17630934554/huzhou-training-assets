#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_urls.py - curl 验证 hosting 5 份资料 URL HTTP 200
部署后用此脚本快速验证 5 份资料是否都还在线。

用法：
  python3 scripts/verify_urls.py
  python3 scripts/verify_urls.py --base-url https://huzhou-training.pages.dev
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
import re


def find_lesson_ids(hosting_dir: Path) -> list:
    """扫描 hosting/ 找所有 lesson_*.html 的编号"""
    ids = []
    for f in hosting_dir.glob("lesson_*.html"):
        m = re.match(r"lesson_(\d+)\.html$", f.name)
        if m:
            ids.append(int(m.group(1)))
    return sorted(ids)


def curl_check(url: str, follow_redirect: bool = True) -> tuple:
    """curl 验证 URL HTTP 200（带 redirect）"""
    cmd = [
        "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}|%{url_effective}",
        "--max-time", "10"
    ]
    if follow_redirect:
        cmd.insert(1, "-L")
    cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        code, final_url = result.stdout.strip().split("|")
        return int(code), final_url
    except Exception as e:
        return 0, str(e)


def main():
    parser = argparse.ArgumentParser(description="验证 hosting 5 份资料 URL")
    parser.add_argument("--base-url", default="https://huzhou-training.pages.dev",
                        help="hosting 基础 URL")
    parser.add_argument("--hosting-dir", default="..", help="hosting/ 目录路径")
    args = parser.parse_args()

    hosting_dir = Path(args.hosting_dir).resolve()
    base_url = args.base_url.rstrip("/")

    lesson_ids = find_lesson_ids(hosting_dir)
    if not lesson_ids:
        print("❌ hosting/ 目录里没找到 lesson_*.html")
        sys.exit(1)

    print(f"🔍 验证 {len(lesson_ids)} 份资料 + 主域名（{base_url}）\n")

    # 验证主域名
    code, final = curl_check(base_url)
    icon = "✅" if code == 200 else "❌"
    print(f"  {icon} {base_url}  →  HTTP {code}  ({final})")

    # 验证每份 lesson
    all_ok = (code == 200)
    for lid in lesson_ids:
        url = f"{base_url}/lesson_{lid}.html"
        code, final = curl_check(url)
        icon = "✅" if code == 200 else "❌"
        print(f"  {icon} lesson_{lid}.html  →  HTTP {code}")
        if code != 200:
            all_ok = False

    print()
    if all_ok:
        print("✅ 全部在线")
    else:
        print("❌ 有 URL 失败，请检查 Cloudflare Pages Deployments")
        sys.exit(1)


if __name__ == "__main__":
    main()
