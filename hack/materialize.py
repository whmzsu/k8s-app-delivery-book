#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把各章 §N.4 中带路径标注的代码块物化到 examples/by-chapter/chNN/<path>。

为什么按章分目录：同一路径（如 deploy/base/deployment.yaml）会在多章出现，
后面的章给的是「增量 / patch」而非完整文件；按章物化可避免互相覆盖，
并与附录 D 的章节 tag 一一对应。

用法：python hack/materialize.py [--clean]
"""
import glob
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "examples", "by-chapter")
CHAPTERS = os.path.join(ROOT, "chapters")

TOKEN = re.compile(r"`([^`\n]+)`")
FENCE = re.compile(r"```([^\n]*)\n(.*?)\n```", re.S)
PATH_OK = re.compile(
    r"^(?:hack|deploy|gitops|docker|cmd|scripts|examples|ci|otel|policy|observability|terraform)/"
    r".+\.[A-Za-z0-9]+$|^docker/Dockerfile$|^go\.mod$"
)
LANG_BY_EXT = {
    ".yaml": {"yaml", "yml", ""}, ".yml": {"yaml", "yml", ""},
    ".sh": {"bash", "sh", "shell", ""}, ".go": {"go", ""},
    ".json": {"json", ""}, ".py": {"python", "py", ""},
    ".tpl": {"yaml", "gotmpl", "tpl", ""}, ".mod": {"go", ""},
    ".tf": {"hcl", "terraform", ""}, ".conf": {"", "text", "nginx"},
}


def is_match(path, lang):
    lang = (lang or "").strip().lower()
    if path.endswith("Dockerfile"):
        return lang in {"dockerfile", ""}
    ext = os.path.splitext(path)[1].lower()
    return lang in LANG_BY_EXT.get(ext, {"", "text"})


def main():
    if "--clean" in sys.argv and os.path.isdir(OUT):
        shutil.rmtree(OUT)
    manifest, skipped, seen = [], [], set()
    for ch in sorted(glob.glob(os.path.join(CHAPTERS, "ch*.md"))):
        n = os.path.basename(ch)[2:4]
        text = open(ch, encoding="utf-8").read()
        fences = [(m.start(), m.end(), m.group(1), m.group(2)) for m in FENCE.finditer(text)]
        for tok in TOKEN.finditer(text):
            path = tok.group(1).strip()
            if not PATH_OK.match(path):
                continue
            # 跳过代码块内部的反引号路径
            if any(s <= tok.start() <= e for s, e, _, _ in fences):
                continue
            candidates = [(s, lang, body) for s, e, lang, body in fences
                          if s > tok.end() and s - tok.end() <= 600]
            # 同一路径标注后可能先出现别的代码块（如 diff、命令输出），
            # 取第一个语言与文件类型相符的块，避免误物化
            matching = [c for c in candidates if is_match(path, c[1])]
            if not matching:
                if candidates:
                    skipped.append((n, path, "相邻代码块语言与文件类型不符：" + (candidates[0][1] or "无")))
                continue
            s, lang, body = matching[0]
            key = (n, path, s)
            if key in seen:
                continue
            seen.add(key)
            dest = os.path.join(OUT, "ch" + n, path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8", newline="\n") as f:
                f.write(body.rstrip() + "\n")
            manifest.append((n, path, len(body.splitlines())))
    with open(os.path.join(OUT, "_manifest.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("# 章节配置物化清单\n\n")
        f.write("> 由 `hack/materialize.py` 从 `chapters/chNN.md` 的路径标注与相邻代码块生成；\n")
        f.write("> 与附录 D 的章节 tag 一一对应。章内代码块是权威副本，本目录是其可复制形态。\n\n")
        f.write("| 章 | 物化路径 | 行数 |\n|---|---|---|\n")
        for n, path, lines in manifest:
            f.write("| %s | `examples/by-chapter/ch%s/%s` | %d |\n" % (n, n, path, lines))
        f.write("\n## 跳过（%d）\n\n" % len(skipped))
        for n, path, why in skipped:
            f.write("- ch%s `%s`：%s\n" % (n, path, why))
    print("物化 %d 个文件，覆盖 %d 章；跳过 %d 个标签" % (
        len(manifest), len({x[0] for x in manifest}), len(skipped)))
    print("清单：examples/by-chapter/_manifest.md")


if __name__ == "__main__":
    main()
