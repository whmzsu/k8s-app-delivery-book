#!/usr/bin/env python3
"""把章节正文里的「内部写作脚手架」抽取到 book/chapter-notes/ 存档。

背景（P6 出书面 / D-42）：
    31 章正文中都残留三类只有作者能看懂的写作过程记录——
      1. 章首 `> **初稿状态**：本章为 v1.0 完整初稿……扩写点见章末「终稿扩写清单」。`
      2. 章末 `**终稿扩写清单**：① …… ✅（2026-11-11 已扩写，+约 3000 字）`
      3. 章末 `**一致性备注**：…… ` （含已被裁决关闭的「待裁决冲突 A/B」）
    这些是写作脚手架，不能出现在成书里。本脚本把它们整块搬到
    book/chapter-notes/chNN.md 存档（内容零丢失），正文只保留读者可见的部分。

用法：
    python hack/extract-notes.py            # 执行抽取（幂等：已抽过的章会跳过）
    python hack/extract-notes.py --check    # 只检查是否有残留，不改文件
"""

from __future__ import annotations

import glob
import os
import re
import sys

CHAPTERS = sorted(glob.glob("chapters/ch*.md"))
NOTES_DIR = os.path.join("book", "chapter-notes")

STATUS_RE = re.compile(r"^> \*\*初稿状态\*\*：.*$", re.M)
TAIL_MARK = "**终稿扩写清单**"


def split_chapter(text: str) -> tuple[str, str, str]:
    """返回 (正文, 状态行, 章末笔记块)。状态行或笔记块不存在时对应为空串。"""
    status = ""
    body = text

    m = STATUS_RE.search(body)
    if m:
        status = m.group(0)
        # 同时去掉紧邻的 blockquote 分隔行 `>`，避免留下孤立的引用符
        for pat in (">\n" + status + "\n", status + "\n"):
            if pat in body:
                body = body.replace(pat, "", 1)
                break

    tail = ""
    i = body.find(TAIL_MARK)
    if i != -1:
        tail = body[i:]
        body = body[:i].rstrip("\n") + "\n"

    return body, status, tail


def note_doc(ch: str, title: str, status: str, tail: str) -> str:
    parts = [
        f"# {title} 写作笔记",
        "",
        "> 本文件由 `hack/extract-notes.py` 从 `chapters/"
        f"{ch}.md` 正文移出，仅供写作过程存档，**不进入成书**。",
        "",
    ]
    if status:
        parts += ["## 原章首状态行", "", status.lstrip("> ").strip(), ""]
    if tail:
        parts += ["## 原章末写作笔记", "", tail.strip(), ""]
    return "\n".join(parts)


def main() -> int:
    check_only = "--check" in sys.argv
    os.makedirs(NOTES_DIR, exist_ok=True)

    touched, skipped, residual = 0, 0, []

    for path in CHAPTERS:
        ch = os.path.basename(path)[:-3]          # ch08
        with open(path, encoding="utf-8", newline="") as fh:
            text = fh.read()

        body, status, tail = split_chapter(text)
        if not status and not tail:
            skipped += 1
            continue

        if check_only:
            residual.append(f"{path}: 状态行={bool(status)} 笔记块={bool(tail)}")
            continue

        # 章标题取正文第一行，用于存档文档抬头
        first = body.split("\n", 1)[0].lstrip("# ").strip()

        note_path = os.path.join(NOTES_DIR, f"{ch}.md")
        existing = ""
        if os.path.exists(note_path):
            with open(note_path, encoding="utf-8") as fh:
                existing = fh.read()

        doc = note_doc(ch, first, status, tail)
        # 幂等保护：存档已存在且内容相同则不重复写
        if existing != doc:
            with open(note_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(doc)

        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        touched += 1

    if check_only:
        if residual:
            print("发现写作脚手架残留（应清空）：")
            for r in residual:
                print("  " + r)
            return 1
        print(f"OK：{len(CHAPTERS)} 章正文均无写作脚手架残留")
        return 0

    print(f"抽取完成：{touched} 章已外迁，{skipped} 章无脚手架；存档目录 {NOTES_DIR}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
