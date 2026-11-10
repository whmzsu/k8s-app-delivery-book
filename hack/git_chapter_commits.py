#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为 chapters/chNN.md 与 references/chNN.yaml 建立逐章提交，并按附录 D 打章节 tag。

前置：其余资产、附录与工具文件已先行提交。tag 名称从 book/case-evolution.md
的 31 章演进表读取，保证与附录 D 只有一份真相源。

用法：python hack/git_chapter_commits.py [--dry-run]
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
DRY = "--dry-run" in sys.argv


def run(args, check=True):
    if DRY:
        print("  $ " + " ".join(args))
        return subprocess.CompletedProcess(args, 0)
    return subprocess.run(args, check=check)


def main():
    evo = open("book/case-evolution.md", encoding="utf-8").read()
    rows = re.findall(
        r"(?m)^\|\s*(\d{1,2})\s*\|.*?`\s*(ch\d{2}-[a-z0-9-]+)\s*`\s*\|", evo)
    tags = {int(n): tag for n, tag in rows}
    assert len(tags) == 31, "演进表应含 31 个 tag，实际 %d" % len(tags)

    for n in range(1, 32):
        ch = "chapters/ch%02d.md" % n
        ref = "references/ch%02d.yaml" % n
        assert os.path.exists(ch) and os.path.exists(ref), (ch, ref)
        run(["git", "add", ch, ref])
        staged = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if staged.returncode == 0:
            print("ch%02d 无变更，跳过提交" % n)
        else:
            run(["git", "commit", "-q", "-m",
                 "docs: 第 %d 章成稿与引用登记（v1.0 初稿）" % n])
        tag = tags[n]
        run(["git", "tag", "-f", "-a", tag, "-m",
             "第 %d 章 · 附录 D 章节快照" % n])
        print("ch%02d -> %s" % (n, tag))
    print("完成：31 章逐章提交与 tag 已就位（--dry-run=%s）" % DRY)


if __name__ == "__main__":
    main()
