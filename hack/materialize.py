#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把各章 §N.4 中带路径标注的代码块物化到 examples/by-chapter/chNN/<path>。

为什么按章分目录：同一路径（如 deploy/base/deployment.yaml）会在多章出现，
后面的章给的是「增量 / patch」而非完整文件；按章物化可避免互相覆盖，
并与附录 D 的章节 tag 一一对应。

用法：
  python hack/materialize.py --clean     # 重新生成（默认行为）
  python hack/materialize.py --check     # CI：生成到临时目录并比对，不改动工作区
"""
import filecmp
import glob
import os
import re
import shutil
import sys
import tempfile

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


def generate(out_dir):
    """把章内代码块写到 out_dir，返回 (manifest, skipped)。"""
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
            dest = os.path.join(out_dir, "ch" + n, path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8", newline="\n") as f:
                f.write(body.rstrip() + "\n")
            manifest.append((n, path, len(body.splitlines())))
    with open(os.path.join(out_dir, "_manifest.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("# 章节配置物化清单\n\n")
        f.write("> 由 `hack/materialize.py` 从 `chapters/chNN.md` 的路径标注与相邻代码块生成；\n")
        f.write("> 与附录 D 的章节 tag 一一对应。章内代码块是权威副本，本目录是其可复制形态。\n\n")
        f.write("| 章 | 物化路径 | 行数 |\n|---|---|---|\n")
        for n, path, lines in manifest:
            f.write("| %s | `examples/by-chapter/ch%s/%s` | %d |\n" % (n, n, path, lines))
        f.write("\n## 跳过（%d）\n\n" % len(skipped))
        for n, path, why in skipped:
            f.write("- ch%s `%s`：%s\n" % (n, path, why))
    return manifest, skipped


def rel_files(base):
    out = {}
    for root, _, files in os.walk(base):
        for name in files:
            p = os.path.join(root, name)
            out[os.path.relpath(p, base).replace("\\", "/")] = p
    return out


def compare(expected_dir, actual_dir):
    """返回差异描述列表；空列表表示一致。"""
    e, a = rel_files(expected_dir), rel_files(actual_dir)
    diff = []
    for k in sorted(set(a) - set(e)):
        diff.append("多出：" + k)
    for k in sorted(set(e) - set(a)):
        diff.append("缺失：" + k)
    for k in sorted(set(e) & set(a)):
        with open(e[k], "rb") as f1, open(a[k], "rb") as f2:
            if f1.read().replace(b"\r\n", b"\n") != f2.read().replace(b"\r\n", b"\n"):
                diff.append("内容不同：" + k)
    return diff


def main():
    check = "--check" in sys.argv
    if check:
        work = tempfile.mkdtemp(prefix="book-materialize-")
        target = work
    else:
        work = None
        target = OUT
        if "--clean" in sys.argv and os.path.isdir(OUT):
            shutil.rmtree(OUT)

    manifest, skipped = generate(target)
    print("物化 %d 个文件，覆盖 %d 章；跳过 %d 个标签" % (
        len(manifest), len({x[0] for x in manifest}), len(skipped)))

    if check:
        try:
            diff = compare(target, OUT)
            if diff:
                print("examples/by-chapter/ 与章内代码块不一致（%d 处）：" % len(diff), file=sys.stderr)
                for d in diff[:30]:
                    print("  " + d, file=sys.stderr)
                print("修复：python hack/materialize.py --clean", file=sys.stderr)
                return 1
            print("一致性：examples/by-chapter/ 与章节代码块完全一致")
        finally:
            shutil.rmtree(work, ignore_errors=True)
    else:
        print("清单：examples/by-chapter/_manifest.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
