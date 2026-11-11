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


# 片段特征：回滚/处置/诊断片段常被误当作文件。首行命中这些即以片段计 0 分。
FRAGMENT_HEAD = re.compile(
    r"^(?:#\s*(?:方案|链|路径|回滚|止血|处置|注意)|"
    r"kubectl|git|helm|kustomize|chmod|promtool|yq|curl|go|docker|kind|ct |bash|\./|"
    r"[^\s#].*→)"
)
# 完整文件特征：命中即以完整计 2 分。
COMPLETE_HEAD = re.compile(
    r"^(?:#!|apiVersion:|kind:|metadata:|spec:|name:|dependencies:|"
    r"values:|controllers:|rules:|groups:|global:|replicaCount:|"
    r"FROM |ARG |package |module |provider |resource |terraform)"
)


def score_block(body):
    """0=明显片段，1=中性，2=像完整文件。用于同路径多段代码块时挑权威副本。"""
    lines = [l.strip() for l in body.splitlines() if l.strip()]
    if not lines:
        return 0
    head = lines[0]
    if FRAGMENT_HEAD.match(head):
        return 0
    if COMPLETE_HEAD.match(head):
        return 2
    return 1


def is_match(path, lang):
    lang = (lang or "").strip().lower()
    if path.endswith("Dockerfile"):
        return lang in {"dockerfile", ""}
    ext = os.path.splitext(path)[1].lower()
    return lang in LANG_BY_EXT.get(ext, {"", "text"})


def annotations(text, fences):
    """收集本章所有「路径出现」的位置与是否构成文件标注边界。

    返回 [(start, end, path, is_boundary)]。三类必须排除，都是踩过的坑：
    1) 代码块内部的反引号不是标注，那是代码里的字符串；
    2) 表格行内的路径不是标注——`| `gitops/x.tf` | 说明 |` 只是正文引用，
       把它当标注会让紧随其后的别的文件被错配成这个路径（实测把
       providers.tf 的代码块物化成了 backend.tf）；
    3) 正文里的行内提及（「见 `deploy/base/deployment.yaml`」）也不是标注。
       它不能成为「换了文件」的分界，否则紧跟其后属于上一个文件的代码块
       会被判给这个提及；占位路径（含 `<env>`）同理。
    """
    out = []
    for tok in TOKEN.finditer(text):
        path = tok.group(1).strip()
        if not PATH_OK.match(path):
            continue
        if any(s <= tok.start() <= e for s, e, _, _ in fences):
            continue
        line_start = text.rfind("\n", 0, tok.start()) + 1
        prefix = text[line_start:tok.start()]
        if prefix.lstrip().startswith("|"):
            continue
        head = prefix.strip()
        # 标注形态：独占段首 / 列表项开头 / 加粗包裹（本书 §N.4 的固定写法）
        is_boundary = head in {"", "-", "*", "**", ">", "> **"} or (
            head.endswith("**") and text[tok.end():tok.end() + 2] == "**")
        if "<" in path or ">" in path:
            is_boundary = False
        out.append((tok.start(), tok.end(), path, is_boundary))
    return out


def generate(out_dir):
    """把章内代码块写到 out_dir，返回 (manifest, skipped, decisions)。"""
    manifest, skipped, decisions = [], [], []
    for ch in sorted(glob.glob(os.path.join(CHAPTERS, "ch*.md"))):
        n = os.path.basename(ch)[2:4]
        text = open(ch, encoding="utf-8").read()
        fences = [(m.start(), m.end(), m.group(1), m.group(2)) for m in FENCE.finditer(text)]
        # 同一路径在本章可能出现多次（完整文件 + 后续片段）。先整章收集，再按
        # 「完整度优先、其次最完整（行数最多）、再其次靠前」选出权威副本，
        # 避免后出现的回滚片段覆盖掉前面可运行的完整文件（见 D-36）。
        chosen, seen = {}, set()
        anns = annotations(text, fences)
        boundaries = [a[0] for a in anns if a[3]]
        for idx, (tok_s, tok_e, path, _) in enumerate(anns):
            # 归属边界：一个代码块属于它之前最近的那条**标注**。中间若出现新的标注，
            # 说明文件已经切换，不能跨过去配对——只靠 600 字符窗口时，删掉一段
            # 无关内容就会把相邻文件的代码块吸进来（实测 backend.tf 被配成
            # providers.tf 的 18 行块），这类漂移在 diff 里极难发现。
            nxt = next((b for b in boundaries if b > tok_e), len(text))
            # 占位路径（含 <env> 之类尖括号）不是具体文件，跳过（Windows 也不允许 < > 作目录名）
            if "<" in path or ">" in path:
                skipped.append((n, path, "占位路径（含 <>/模板占位），不物化"))
                continue
            candidates = [(s, lang, body) for s, e, lang, body in fences
                          if s > tok_e and s < nxt and s - tok_e <= 600]
            # 同一路径标注后可能先出现别的代码块（如 diff、命令输出），
            # 取第一个语言与文件类型相符的块，避免误物化
            matching = [c for c in candidates if is_match(path, c[1])]
            if not matching:
                if candidates:
                    skipped.append((n, path, "相邻代码块语言与文件类型不符：" + (candidates[0][1] or "无")))
                continue
            s, lang, body = matching[0]
            if (n, path, s) in seen:
                continue
            seen.add((n, path, s))
            # 可执行脚本必须有 shebang；章节里常把「回滚/处置命令」也标注成 hack/*.sh，
            # 那类片段只会误导读者（bash -n 还可能侥幸通过），一律不物化。
            if path.endswith(".sh"):
                head = next((l.strip() for l in body.splitlines() if l.strip()), "")
                if not head.startswith("#!"):
                    skipped.append((n, path, "无 shebang，判定为命令行片段，不物化"))
                    continue
            cand = (score_block(body), len(body.splitlines()), -s, s, body)
            prev = chosen.get(path)
            if prev is None:
                chosen[path] = cand
            # 记「行数 + 完整度」而不记 L 行号：行号会随正文任何增删漂移，
            # 让生成物在无关改动里持续 churn，且读者也无从核对。
            elif cand[:3] > prev[:3]:
                decisions.append((n, path, "选 %d 行（完整度 %d）那份，弃 %d 行（完整度 %d）那份" % (
                    cand[1], cand[0], prev[1], prev[0])))
                chosen[path] = cand
            else:
                decisions.append((n, path, "保留 %d 行（完整度 %d）那份，弃 %d 行（完整度 %d）那份" % (
                    prev[1], prev[0], cand[1], cand[0])))

        for path, (score, nlines, _, _, body) in chosen.items():
            dest = os.path.join(out_dir, "ch" + n, path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8", newline="\n") as f:
                f.write(body.rstrip() + "\n")
            manifest.append((n, path, nlines))

    manifest.sort()
    # 同一路径若最终仍物化了（用了另一段完整块），就不再记「跳过」，避免清单自相矛盾
    done = {(x[0], x[1]) for x in manifest}
    skipped = [x for x in skipped if (x[0], x[1]) not in done]
    with open(os.path.join(out_dir, "_manifest.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("# 章节配置物化清单\n\n")
        f.write("> 由 `hack/materialize.py` 从 `chapters/chNN.md` 的路径标注与相邻代码块生成；\n")
        f.write("> 与附录 D 的章节 tag 一一对应。章内代码块是权威副本，本目录是其可复制形态。\n\n")
        f.write("| 章 | 物化路径 | 行数 |\n|---|---|---|\n")
        for n, path, lines in manifest:
            f.write("| %s | `examples/by-chapter/ch%s/%s` | %d |\n" % (n, n, path, lines))
        if decisions:
            f.write("\n## 同路径多块裁决（%d）\n\n" % len(decisions))
            f.write("> 同一路径在一章内出现多次时，按「完整度 → 行数 → 位置」选权威副本；\n")
            f.write("> 被弃的多为回滚/处置片段，不当可复制文件。\n\n")
            for n, path, why in decisions:
                f.write("- ch%s `%s`：%s\n" % (n, path, why))
        f.write("\n## 跳过（%d）\n\n" % len(skipped))
        for n, path, why in skipped:
            f.write("- ch%s `%s`：%s\n" % (n, path, why))
    return manifest, skipped, decisions


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

    manifest, skipped, decisions = generate(target)
    print("物化 %d 个文件，覆盖 %d 章；同路径多块裁决 %d 处；跳过 %d 个标签" % (
        len(manifest), len({x[0] for x in manifest}), len(decisions), len(skipped)))

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
