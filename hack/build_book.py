#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""装配全书单一 Markdown 稿件（CI 上传为 artifact）。

章节与附录保持仓库里的原文件不变，这里只做拼接，不改动任何正文：
  前言/目录 → 第 1–31 章 → 附录 A–I → 生成说明
用法：python hack/build_book.py [--out dist]
"""
import argparse
import datetime
import glob
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git_sha():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short=7", "HEAD"], cwd=ROOT,
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)

    chapters = sorted(glob.glob(os.path.join(ROOT, "chapters", "ch*.md")))
    appendices = sorted(glob.glob(os.path.join(ROOT, "appendices", "*.md")))
    assert len(chapters) == 31, "章节数应为 31，实际 %d" % len(chapters)
    assert len(appendices) == 9, "附录数应为 9，实际 %d" % len(appendices)

    parts = [
        "# 一次变更的旅程：Kubernetes 应用部署与管理运维最佳实践",
        "",
        "> v1.0 完整初稿 · 构建自 `%s` · 生成日期 %s" % (
            git_sha(), datetime.date.today().isoformat()),
        "> 本文件由 `hack/build_book.py` 自动装配，章节与附录的权威副本在仓库原路径。",
        "",
        "---",
        "",
    ]

    toc = os.path.join(ROOT, "全书目录.md")
    if os.path.exists(toc):
        parts += [open(toc, encoding="utf-8").read().rstrip(), "", "---", ""]

    for group, files in (("正文", chapters), ("附录", appendices)):
        parts += ["<!-- %s 开始 -->" % group, ""]
        for f in files:
            text = open(f, encoding="utf-8").read().rstrip()
            parts += [text, "", "---", ""]
        parts += ["<!-- %s 结束 -->" % group, ""]

    parts += [
        "## 生成说明",
        "",
        "- 章节：`chapters/ch01.md` – `ch31.md`（31 章）",
        "- 附录：`appendices/附录A…I.md`（9 份）",
        "- 参考文献附录 I 由 `references/chNN.yaml` 自动生成，勿手工编辑",
        "- 章内相对链接在单一稿件中可能失效，请以仓库目录结构为准",
        "- 校验：`./hack/check-consistency.sh`",
        "",
    ]

    dest = os.path.join(out, "一次变更的旅程.md")
    with open(dest, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(parts))
    han = len(re.findall(r"[\u4e00-\u9fff]", "\n".join(parts)))
    print("装配完成：%s" % dest)
    print("章节 %d / 附录 %d / 汉字 %d" % (len(chapters), len(appendices), han))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
