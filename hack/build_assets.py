#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 docs/ 下的可拷贝工件（runbook / 模板 / ADR / 清单）打包成配套 zip。

这些工件是书里承诺的「可拷贝 artifact」：章节正文内联引用 `docs/*.md`，
但出版的 DOCX/PDF/EPUB 不收纳它们（避免与正文逐字重复）。本脚本把它们
打成独立 zip，作为随书《配套工件包》交付，读者可单独下载、按需打印，
或拷进自己的运维 / 平台工程系统。

产物：dist/一次变更的旅程-工件包.zip
用法：python hack/build_assets.py [--out dist]
"""
import argparse
import datetime
import os
import re
import subprocess
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
DIST = os.path.join(ROOT, "dist")
ZIP_NAME = "一次变更的旅程-工件包.zip"

GROUP_LABEL = {
    "runbooks": "Runbook（事故定位 / 止血 / 验证）",
    "adr": "架构决策记录（ADR）",
    "templates": "模板 / 清单 / 速查 / 决策树",
}


def git_sha():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short=7", "HEAD"], cwd=ROOT,
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def title_of(path):
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^#\s+(.+?)\s*$", line)
                if m:
                    return m.group(1).strip()
    except Exception:
        pass
    return os.path.basename(path)


def group_of(rel):
    parts = rel.split("/")
    if "runbooks" in parts:
        return "runbooks"
    if "adr" in parts:
        return "adr"
    return "templates"


def collect():
    out = []
    for base, _, files in os.walk(DOCS):
        for fn in sorted(files):
            if not fn.endswith(".md"):
                continue
            full = os.path.join(base, fn)
            rel = "docs/" + os.path.relpath(full, DOCS).replace(os.sep, "/")
            out.append((rel, full))
    return sorted(out)


def build_readme(items):
    by = {"runbooks": [], "adr": [], "templates": []}
    for rel, full in items:
        by[group_of(rel)].append((rel, title_of(full)))
    lines = [
        "# 一次变更的旅程 · 配套工件包",
        "",
        "> 本 zip 与《一次变更的旅程》主书配套，包含书中引用的可拷贝工件：",
        "> runbook、模板、清单、决策树与架构决策记录（ADR）。",
        "> 主书正文章节内联引用这些文件，但出版稿不收纳，以免与正文逐字重复。",
        "",
        "## 文件清单",
        "",
    ]
    for key in ("runbooks", "adr", "templates"):
        lines.append("### " + GROUP_LABEL[key])
        lines.append("")
        if by[key]:
            for rel, t in by[key]:
                lines.append("- `%s` — %s" % (rel, t))
        else:
            lines.append("- （无）")
        lines.append("")
    lines += [
        "## 使用建议",
        "",
        "- 直接 `unzip` 后按路径取用；文件名即书中引用路径。",
        "- runbook 适合打印贴墙或导入运维系统；模板 / ADR 适合拷进团队仓库按需改写。",
        "- 构建自 git `%s` · 生成日期 %s" % (
            git_sha(), datetime.date.today().isoformat()),
        "",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DIST)
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)

    items = collect()
    if not items:
        raise SystemExit("docs/ 下未找到任何 .md 工件，中止。")

    readme = build_readme(items)
    zip_path = os.path.join(out, ZIP_NAME)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.md", readme)
        for rel, full in items:
            z.write(full, rel)

    size = os.path.getsize(zip_path)
    print("工件包构建完成：%s" % zip_path)
    print("工件 %d 份 / zip 大小 %d 字节" % (len(items), size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
