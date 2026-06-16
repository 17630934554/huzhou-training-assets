#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
repack_zip.py - 重打包 training_hosting.zip 用于手动部署兜底
当 Cloudflare Pages 关联 GitHub 失败时，可用此脚本重新打包 hosting/ 为 zip，
然后大刘手动拖到 Cloudflare Pages 控制台（V2.1 部署方式）。

用法：
  python3 scripts/repack_zip.py
  python3 scripts/repack_zip.py --output ../training_hosting.zip
"""

import os
import sys
import zipfile
import argparse
from pathlib import Path
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="重打包 hosting/ 为 zip")
    parser.add_argument("--hosting-dir", default="..", help="hosting/ 目录路径（默认上级目录）")
    parser.add_argument("--output", default="../training_hosting.zip", help="输出 zip 路径")
    args = parser.parse_args()

    hosting_dir = Path(args.hosting_dir).resolve()
    output_zip = Path(args.output).resolve()

    if not hosting_dir.is_dir():
        print(f"❌ hosting 目录不存在: {hosting_dir}")
        sys.exit(1)

    # 收集要打包的文件
    files_to_pack = []
    for f in hosting_dir.rglob("*"):
        if f.is_file():
            # 跳过备份/缓存/zip
            rel = f.relative_to(hosting_dir)
            parts = rel.parts
            if any(p.startswith(".") for p in parts):
                continue
            if any(p in ("_old_qr_backup", "__pycache__", "qr") for p in parts):
                continue
            if f.suffix in (".zip", ".pyc"):
                continue
            files_to_pack.append(f)

    print(f"📦 打包 {len(files_to_pack)} 个文件到 {output_zip}")

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for f in files_to_pack:
            rel = f.relative_to(hosting_dir)
            zf.write(f, arcname=str(rel))
            print(f"  + {rel}")

    size_mb = output_zip.stat().st_size / 1024 / 1024
    print(f"✅ 打包完成: {output_zip} ({size_mb:.2f}MB)")

    # 显示 zip 内容
    with zipfile.ZipFile(output_zip, "r") as zf:
        print(f"\n📋 zip 内 {len(zf.namelist())} 个文件:")
        for name in sorted(zf.namelist()):
            info = zf.getinfo(name)
            print(f"  {name}  ({info.file_size / 1024:.0f}KB)")


if __name__ == "__main__":
    main()
