#!/usr/bin/env python3
"""把 chapters/ 与 appendices/ 装配成可交付的三种形态。

产物（dist/）：
  一次变更的旅程.docx   Word 稿，交稿/评审主用（标题层级、页码、代码块、表格）
  一次变更的旅程.pdf    A4 打印稿，逐页带「页码 / 总页数」
  一次变更的旅程.epub   电子书，按章分节、带导航

设计取舍：
  - 不引 pandoc（本机没有，也不希望构建依赖外部二进制）；Markdown 解析自己写，
    只覆盖本书实际用到的子集：标题、段落、代码块、管道表格、列表、引用块、分隔线。
  - PDF 用本机 Edge 的 headless 打印（Chromium 内核，CJK 与表格排版可靠），
    再用 pypdf + reportlab 盖页码——Chromium 的 @page 不支持 CSS 计数器。
  - 书内 `.md` 相对链接仍降级为「只留文字」（单文件形态里跨文件路径没有意义）；
    http(s) 外链与「详见/参见/回扣/回到 第 N 章」在装配期转成真链接：
    HTML/PDF 用 #chNN、EPUB 用 chNN.xhtml、DOCX 用章标题书签 + w:hyperlink。
    正文 .md 不写链接标记，避免污染物化与角标闸门。

用法：
  python hack/build_dist.py [--only docx|pdf|epub] [--keep-html]
"""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
TITLE = "一次变更的旅程"
SUBTITLE = "Kubernetes 应用部署与管理运维最佳实践"

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/microsoft-edge",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]


# ---------------------------------------------------------------------------
# 一、Markdown 解析（只覆盖本书用到的语法子集）
# ---------------------------------------------------------------------------
CJK = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")


def _join(prev: str, nxt: str) -> str:
    if not prev:
        return nxt
    if CJK.match(prev[-1]) or CJK.match(nxt[0]):
        return prev + nxt
    return prev + " " + nxt


def split_table_cells(line: str) -> list[str]:
    """按 GFM 口径把一行管道表格切成单元格。

    本书的检查清单大量把命令写在表格的反引号里，命令自身含 `|`（shell 管道、
    grep 分支、PromQL 正则）。早期直接用 `split("|")` 会把它们当成列分隔符：
    HTML 侧多输出一个 <td>，DOCX 侧用 max() 取列数给整张表补出空列，
    成品表现就是「部分行的右边多出一列」。

    三条规则：
      1) `\\|` 是字面管道，不切列，渲染时反转义成 `|`（与 GitHub / GFM 一致）；
      2) 反引号 code span 内的 `|` 也不切列（宽容兜底，防止漏转义时静默毁版式；
         源码规范由 check-consistency.sh 第 8 步把关）；
      3) 其余 `|` 为列分隔符，首尾边界管道产生的空元素丢弃。
    """
    cells, buf = [], []
    in_code = False
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if ch == "\\" and i + 1 < n and line[i + 1] == "|":
            buf.append("|")
            i += 2
            continue
        if ch == "`":
            in_code = not in_code
            buf.append(ch)
            i += 1
            continue
        if ch == "|" and not in_code:
            cells.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    cells.append("".join(buf))
    if cells and not cells[0].strip():
        cells.pop(0)
    if cells and not cells[-1].strip():
        cells.pop()
    return [c.strip() for c in cells]


# 章级显式交叉引用：只认带引导词的形态。全书「第 N 章」字面提及 2300+ 处，
# 大量是标题、目录、叙述和代码块字符串；全量转链必然误伤，故收窄到 4 个引导词。
# 命中后产出逻辑目标 `chNN`，由各形态自己拼 #chNN / chNN.xhtml / Word 书签。
CHAPTER_REF = re.compile(r"(?:详见|参见|回扣|回到)\s*第?\s*(\d{1,2})\s*章")
VALID_CHAPTERS = set(range(1, 32))


def _emit_plain(buf: str, bold: bool, out: list) -> None:
    """把一段普通文字按章引用切开，未命中部分保持原样。"""
    if not buf:
        return
    pos = 0
    for m in CHAPTER_REF.finditer(buf):
        num = int(m.group(1))
        if num not in VALID_CHAPTERS:
            continue  # 拼错/越界的章号不转链，留给闸门报错
        if m.start() > pos:
            out.append(("bold" if bold else "plain", buf[pos:m.start()], None))
        out.append(("boldlink" if bold else "link", m.group(0), "ch%02d" % num))
        pos = m.end()
    if pos < len(buf):
        out.append(("bold" if bold else "plain", buf[pos:], None))


def inline(text: str, _bold: bool = False) -> list[tuple[str, str, str | None]]:
    """把一段文字切成 (样式, 文本, 链接目标) 序列。

    样式 ∈ plain/bold/code/boldcode/link/boldlink；第三项仅链接样式非 None，
    值为逻辑章号 `chNN` 或外链 URL。支持嵌套：**加粗里带 `代码`** 会拆成
    bold + boldcode 两段，否则反引号会原样漏到版面上。
    """
    out: list[tuple[str, str, str | None]] = []
    buf = ""
    i, n = 0, len(text)
    while i < n:
        if text.startswith("**", i):
            j = text.find("**", i + 2)
            if j > 0:
                _emit_plain(buf, _bold, out)
                buf = ""
                for style, chunk, href in inline(text[i + 2:j], True):
                    if style in ("code", "boldcode"):
                        out.append(("boldcode", chunk, None))
                    elif style in ("link", "boldlink"):
                        out.append(("boldlink", chunk, href))
                    else:
                        out.append(("bold", chunk, None))
                i = j + 2
                continue
        if text[i] == "`":
            j = text.find("`", i + 1)
            if j > i + 1:
                _emit_plain(buf, _bold, out)
                buf = ""
                out.append(("boldcode" if _bold else "code", text[i + 1:j], None))
                i = j + 1
                continue
        if text[i] == "[":
            m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", text[i:])
            if m:
                _emit_plain(buf, _bold, out)
                buf = ""
                label, url = m.group(1), m.group(2)
                if url.startswith(("http://", "https://")):
                    out.append(("boldlink" if _bold else "link", label, url))
                else:
                    # 书内 .md / 相对路径链接在单文件形态里没有意义，按原设计只留文字
                    out.append(("bold" if _bold else "plain", label, None))
                i += m.end()
                continue
        buf += text[i]
        i += 1
    _emit_plain(buf, _bold, out)
    return [x for x in out if x[1]]


def parse_md(text: str) -> list[dict]:
    lines = text.split("\n")
    blocks: list[dict] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        s = line.strip()

        if not s:
            i += 1
            continue

        # 代码块
        if s.startswith("```"):
            lang = s[3:].strip()
            i += 1
            body = []
            while i < n and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1
            blocks.append({"kind": "code", "lang": lang, "text": "\n".join(body)})
            continue

        # 图片：`![alt](../assets/diagrams/x.svg)`，路径相对 chapters/ 或 appendices/
        m = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", s)
        if m:
            blocks.append({"kind": "image", "alt": m.group(1).strip(), "src": m.group(2).strip()})
            i += 1
            continue

        # 分隔线
        if re.fullmatch(r"-{3,}|\*{3,}", s):
            blocks.append({"kind": "hr"})
            i += 1
            continue

        # 标题
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            blocks.append({"kind": "h%d" % len(m.group(1)), "text": m.group(2).strip()})
            i += 1
            continue

        # 表格
        if "|" in s and i + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", lines[i + 1]):
            header = split_table_cells(s)
            i += 2
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append(split_table_cells(lines[i]))
                i += 1
            blocks.append({"kind": "table", "head": header, "rows": rows})
            continue

        # 引用块
        if s.startswith(">"):
            body = []
            while i < n and (lines[i].strip().startswith(">") or not lines[i].strip()):
                if not lines[i].strip():
                    if i + 1 < n and not lines[i + 1].strip().startswith(">"):
                        break
                    body.append("")
                else:
                    body.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            txt = "\n".join(body).strip()
            if txt:
                blocks.append({"kind": "quote", "text": txt})
            continue

        # 列表
        m = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", line)
        if m:
            ordered = bool(re.match(r"\d", m.group(2)))
            items = []
            while i < n:
                mm = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", lines[i])
                if mm:
                    items.append(mm.group(3).strip())
                elif lines[i].strip() and items and lines[i].startswith("   "):
                    items[-1] = _join(items[-1], lines[i].strip())
                else:
                    break
                i += 1
            blocks.append({"kind": "ol" if ordered else "ul", "items": items})
            continue

        # 段落
        para = s
        i += 1
        while i < n and lines[i].strip() and not re.match(
                r"^\s*(#{1,4}\s|```|>|[-*+]\s|\d+[.)]\s)", lines[i].strip()) and "|" not in lines[i][:1]:
            if re.fullmatch(r"-{3,}", lines[i].strip()):
                break
            para = _join(para, lines[i].strip())
            i += 1
        blocks.append({"kind": "p", "text": para})

    return blocks


# ---------------------------------------------------------------------------
# 二、装配顺序
# ---------------------------------------------------------------------------
def collect() -> list[dict]:
    docs = []
    toc = os.path.join(ROOT, "全书目录.md")
    if os.path.exists(toc):
        raw = open(toc, encoding="utf-8").read()
        t, b = split_title(raw, "目录")
        docs.append({"id": "toc", "file": "全书目录.md", "title": t,
                     "body": b, "text": raw, "kind": "front"})
    for p in sorted(os.listdir(os.path.join(ROOT, "chapters"))):
        if re.match(r"ch\d\d\.md$", p):
            raw = open(os.path.join(ROOT, "chapters", p), encoding="utf-8").read()
            t, b = split_title(raw, p)
            docs.append({"id": p[:-3], "file": "chapters/" + p, "title": t,
                         "body": b, "text": raw, "kind": "chapter"})
    for p in sorted(os.listdir(os.path.join(ROOT, "appendices"))):
        if p.endswith(".md"):
            raw = open(os.path.join(ROOT, "appendices", p), encoding="utf-8").read()
            t, b = split_title(raw, p)
            docs.append({"id": "ap-" + p[:4], "file": "appendices/" + p, "title": t,
                         "body": b, "text": raw, "kind": "appendix"})
    return docs


def split_title(text: str, fallback: str) -> tuple[str, str]:
    """把文档第一行的 # 标题取出来单独交给版式，正文里不再重复一份。"""
    m = re.match(r"^#\s+(.+?)\s*\n+", text)
    if m:
        return m.group(1).strip(), text[m.end():]
    return fallback, text


# ---------------------------------------------------------------------------
# 三、DOCX
# ---------------------------------------------------------------------------
def build_docx(docs: list[dict], dest: str) -> dict:
    from docx import Document
    from docx.enum.section import WD_SECTION
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.shared import Cm, Pt, RGBColor

    doc = Document()

    # 页面
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.4)
    sec.top_margin, sec.bottom_margin = Cm(2.5), Cm(2.3)

    def set_cjk(style, latin="Times New Roman", east="宋体", size=None, bold=None):
        style.font.name = latin
        if size:
            style.font.size = Pt(size)
        if bold is not None:
            style.font.bold = bold
        rpr = style.element.get_or_add_rPr()
        rf = rpr.find(qn("w:rFonts"))
        if rf is None:
            rf = OxmlElement("w:rFonts")
            rpr.append(rf)
        rf.set(qn("w:eastAsia"), east)
        rf.set(qn("w:ascii"), latin)
        rf.set(qn("w:hAnsi"), latin)

    def cjk(run, east="宋体", latin="Times New Roman"):
        """给 run 指定东亚字体；python-docx 不直接暴露 w:eastAsia。"""
        rpr = run._element.get_or_add_rPr()
        rf = rpr.find(qn("w:rFonts"))
        if rf is None:
            rf = OxmlElement("w:rFonts")
            rpr.append(rf)
        rf.set(qn("w:eastAsia"), east)
        rf.set(qn("w:ascii"), latin)
        rf.set(qn("w:hAnsi"), latin)

    normal = doc.styles["Normal"]
    set_cjk(normal, "Times New Roman", "宋体", 10.5)
    normal.paragraph_format.line_spacing = 1.45
    normal.paragraph_format.space_after = Pt(3)

    for name, size, before, after in (("Heading 1", 22, 0, 18),
                                      ("Heading 2", 14, 14, 8),
                                      ("Heading 3", 12, 10, 6),
                                      ("Heading 4", 11, 8, 4)):
        st = doc.styles[name]
        set_cjk(st, "Times New Roman", "黑体", size, True)
        st.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
        st.paragraph_format.space_before = Pt(before)
        st.paragraph_format.space_after = Pt(after)
        st.paragraph_format.keep_with_next = True
        st.paragraph_format.line_spacing = 1.2

    # 页脚页码
    footer_p = sec.footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer_p.add_run()
    for el, attr in (("w:fldChar", {"w:fldCharType": "begin"}),
                     ("w:instrText", None),
                     ("w:fldChar", {"w:fldCharType": "end"})):
        e = OxmlElement(el)
        if attr:
            for k, v in attr.items():
                e.set(qn(k), v)
        else:
            e.set(qn("xml:space"), "preserve")
            e.text = " PAGE "
        run._r.append(e)
    footer_p.runs[0].font.size = Pt(9)

    # 封面
    for _ in range(6):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(TITLE)
    r.font.size = Pt(36)
    r.font.bold = True
    r.font.name = "黑体"
    cjk(r, "黑体", "Times New Roman")
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run("—— " + SUBTITLE)
    r2.font.size = Pt(16)
    cjk(r2, "黑体", "Times New Roman")
    doc.add_paragraph()
    for line in ("七篇 31 章 + 附录 A–I", "贯穿案例 order-demo ｜ 版本基线 Kubernetes 1.32+"):
        pc = doc.add_paragraph()
        pc.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rr = pc.add_run(line)
        rr.font.size = Pt(11)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    stats = {"code": 0, "table": 0, "para": 0, "image": 0}

    bookmark_seq = [0]

    def add_bookmark(par, name):
        """给章标题打书签，供正文 w:hyperlink w:anchor 跳转。"""
        bookmark_seq[0] += 1
        bid = str(bookmark_seq[0])
        start = OxmlElement("w:bookmarkStart")
        start.set(qn("w:id"), bid)
        start.set(qn("w:name"), name)
        end = OxmlElement("w:bookmarkEnd")
        end.set(qn("w:id"), bid)
        # pPr 必须是段落首个子元素，书签起点插在它后面
        ppr = par._p.find(qn("w:pPr"))
        par._p.insert(1 if ppr is not None else 0, start)
        par._p.append(end)

    def add_link(par, chunk, href, size, bold):
        """内部书签链接 / 外部 URL 链接（python-docx 无原生 hyperlink API）。"""
        h = OxmlElement("w:hyperlink")
        if href.startswith(("http://", "https://")):
            rid = par.part.relate_to(href, RT.HYPERLINK, is_external=True)
            h.set(qn("r:id"), rid)
        else:
            h.set(qn("w:anchor"), href)
        r = OxmlElement("w:r")
        rpr = OxmlElement("w:rPr")
        color = OxmlElement("w:color")
        color.set(qn("w:val"), "0563C1")
        rpr.append(color)
        u = OxmlElement("w:u")
        u.set(qn("w:val"), "single")
        rpr.append(u)
        if bold:
            rpr.append(OxmlElement("w:b"))
        if size:
            sz = OxmlElement("w:sz")
            sz.set(qn("w:val"), str(int(size * 2)))
            rpr.append(sz)
        r.append(rpr)
        t = OxmlElement("w:t")
        t.text = chunk
        r.append(t)
        h.append(r)
        par._p.append(h)

    def add_runs(par, text, size=None):
        for style, chunk, href in inline(text):
            if style in ("link", "boldlink"):
                add_link(par, chunk, href or "", size, style == "boldlink")
                continue
            run = par.add_run(chunk)
            if size:
                run.font.size = Pt(size)
            if style in ("bold", "boldcode"):
                run.bold = True
            if style in ("code", "boldcode"):
                run.font.name = "Consolas"
                cjk(run, "宋体", "Consolas")
                run.font.size = Pt((size or 10.5) - 1)

    for d in docs:
        blocks = parse_md(d["body"])
        # 文档标题
        first = None
        h1 = doc.add_heading(level=1)
        h1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        h1.add_run(d["title"])
        # 章级交叉引用的目标只有 chNN；附录/目录不打书签，避免非 ASCII 书签名
        if d["kind"] == "chapter":
            add_bookmark(h1, d["id"])
        if docs.index(d):
            h1.paragraph_format.page_break_before = True

        for b in blocks:
            k = b["kind"]
            if k == "image":
                svg_path = os.path.normpath(os.path.join(ROOT, "chapters", b["src"]))
                png_dir = os.path.join(ROOT, "build", "diagrams")
                os.makedirs(png_dir, exist_ok=True)
                png_path = os.path.join(png_dir, os.path.basename(svg_path) + ".png")
                ok = os.path.exists(png_path) and os.path.getsize(png_path) > 2048
                if not ok:
                    ok = os.path.exists(svg_path) and svg_to_png(svg_path, png_path)
                if ok:
                    doc.add_picture(png_path, width=Cm(15.5))
                    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                else:
                    rn = doc.add_paragraph()
                    rn.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = rn.add_run(f"［图：{b['alt']}（矢量版见 PDF / EPUB）］")
                    run.italic = True
                    run.font.size = Pt(9)
                if b["alt"]:
                    cap = doc.add_paragraph()
                    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    rc = cap.add_run(b["alt"])
                    rc.italic = True
                    rc.font.size = Pt(9)
                stats["image"] += 1
            elif k == "code":
                par = doc.add_paragraph()
                pf = par.paragraph_format
                pf.left_indent = Cm(0.4)
                pf.space_before = Pt(4)
                pf.space_after = Pt(6)
                pf.line_spacing = 1.0
                if b["text"].count("\n") <= 28:
                    pf.keep_together = True
                run = par.add_run(b["text"])
                run.font.name = "Consolas"
                cjk(run, "宋体", "Consolas")
                run.font.size = Pt(8.5)
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:fill"), "F4F4F6")
                par._p.get_or_add_pPr().append(shd)
                stats["code"] += 1
            elif k == "table":
                cols = max(len(b["head"]), *(len(r) for r in b["rows"])) if b["rows"] else len(b["head"])
                tbl = doc.add_table(rows=1, cols=cols)
                tbl.style = "Table Grid"
                tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                for j, cell in enumerate(b["head"]):
                    c = tbl.rows[0].cells[j]
                    c.text = ""
                    add_runs(c.paragraphs[0], cell, 9)
                    c.paragraphs[0].runs and setattr(c.paragraphs[0].runs[0], "bold", True)
                    for r in c.paragraphs[0].runs:
                        r.bold = True
                for row in b["rows"]:
                    cells = tbl.add_row().cells
                    for j in range(cols):
                        cells[j].text = ""
                        if j < len(row):
                            add_runs(cells[j].paragraphs[0], row[j], 9)
                doc.add_paragraph().paragraph_format.space_after = Pt(4)
                stats["table"] += 1
            elif k in ("ul", "ol"):
                for idx, item in enumerate(b["items"], 1):
                    par = doc.add_paragraph()
                    par.paragraph_format.left_indent = Cm(0.9)
                    par.paragraph_format.first_line_indent = Cm(-0.5)
                    par.paragraph_format.space_after = Pt(2)
                    lead = f"{idx}. " if k == "ol" else "· "
                    par.add_run(lead)
                    add_runs(par, item)
            elif k == "quote":
                for line in [x for x in b["text"].split("\n") if x.strip()]:
                    par = doc.add_paragraph()
                    par.paragraph_format.left_indent = Cm(0.8)
                    par.paragraph_format.space_after = Pt(2)
                    add_runs(par, line, 9.5)
                    for r in par.runs:
                        r.font.color.rgb = RGBColor(0x44, 0x44, 0x44)
            elif k == "hr":
                continue
            elif k in ("h2", "h3", "h4"):
                lvl = int(k[1])
                # 标题同样过 add_runs：否则标题里的章引用只在 HTML/EPUB 可点，
                # Word 里退化成纯文本，三形态不一致。
                add_runs(doc.add_heading(level=lvl), b["text"])
            else:
                par = doc.add_paragraph()
                par.paragraph_format.first_line_indent = Pt(21)
                add_runs(par, b["text"])
                stats["para"] += 1

    doc.save(dest)
    return stats


# ---------------------------------------------------------------------------
# 四、HTML（供 PDF 与 EPUB 复用）
# ---------------------------------------------------------------------------
CSS = """
@page { size: A4; margin: 20mm 18mm 18mm 18mm; }
html { -webkit-print-color-adjust: exact; }
body { font-family: "Songti SC", "SimSun", "宋体", serif; font-size: 10.5pt;
       line-height: 1.62; color: #1a1a1a; }
h1 { font-family: "Heiti SC", "SimHei", "黑体", sans-serif; font-size: 21pt;
     text-align: center; margin: 0 0 14pt; page-break-before: always;
     page-break-after: avoid;
     bookmark-level: 1; bookmark-label: content(text); }
h1.first { page-break-before: avoid; }
h2 { font-family: "Heiti SC", "SimHei", "黑体", sans-serif; font-size: 14pt;
     margin: 16pt 0 8pt; page-break-after: avoid;
     bookmark-level: 2; bookmark-label: content(text); }
h3 { font-family: "Heiti SC", "SimHei", "黑体", sans-serif; font-size: 12pt;
     margin: 12pt 0 6pt; page-break-after: avoid; }
h4 { font-family: "Heiti SC", "SimHei", "黑体", sans-serif; font-size: 11pt;
     margin: 10pt 0 4pt; page-break-after: avoid; }
p { margin: 0 0 5pt; text-align: justify; text-indent: 2em; }
h1 + p, h2 + p, h3 + p, h4 + p, blockquote p, li p { text-indent: 0; }
pre { background: #f4f4f6; border-left: 2.5pt solid #c9c9d4; padding: 6pt 8pt;
      font-family: Consolas, "Courier New", monospace; font-size: 8.2pt;
      line-height: 1.34; white-space: pre-wrap; word-break: break-all;
      page-break-inside: avoid; margin: 6pt 0 8pt; text-indent: 0; }
code { font-family: Consolas, "Courier New", monospace; font-size: 9pt;
       background: #f2f2f4; padding: 0 1.5pt; }
pre code { background: none; padding: 0; font-size: inherit; }
table { border-collapse: collapse; width: 100%; font-size: 8.8pt; margin: 6pt 0 10pt;
        page-break-inside: auto; }
th, td { border: 0.5pt solid #b9b9c2; padding: 3pt 4pt; vertical-align: top;
         text-align: left; text-indent: 0; }
th { background: #ececf1; font-family: "Heiti SC", "SimHei", "黑体", sans-serif; }
tr { page-break-inside: avoid; }
blockquote { margin: 6pt 0 8pt; padding: 2pt 0 2pt 9pt; border-left: 2.5pt solid #d8d8e0;
             color: #3f3f46; font-size: 9.6pt; }
figure.diagram { margin: 8pt -7mm 10pt; text-align: center; text-indent: 0;
                 page-break-inside: avoid; }
figure.diagram svg { width: 100%; max-width: none; height: auto; }
figure.diagram figcaption { font-size: 8.8pt; color: #52525b; text-indent: 0;
                            margin-top: 4pt; text-align: center; }
p.diagram-missing { color: #b00020; text-align: center; text-indent: 0;
                    border: 0.5pt dashed #b00020; padding: 4pt; }
blockquote p { text-indent: 0; margin: 0 0 3pt; }
ul, ol { margin: 4pt 0 8pt 1.4em; padding: 0; }
li { margin: 0 0 2.5pt; text-align: justify; }
hr { display: none; }
.cover { text-align: center; page-break-after: always; }
.cover .t { font-family: "Heiti SC", "SimHei", "黑体", sans-serif; font-size: 34pt;
            margin: 150pt 0 10pt; letter-spacing: 2pt; }
.cover .s { font-size: 15pt; color: #3a3a42; margin-bottom: 60pt; }
.cover .m { font-size: 10.5pt; color: #55555f; line-height: 2; }
"""


def load_diagram(src: str) -> str | None:
    """把 SVG 内联进 HTML。

    不引外部二进制（mermaid-cli / node）：图以 SVG 入库，构建期读文件内联。
    内联而非 `![]()` 引外部文件，是为了让 PDF / EPUB / DOCX 三形态拿到同一份
    矢量内容——引相对路径时 Chromium 打印与 epub 打包的基准目录不同，很容易
    「Markdown 里看得见、成品里是破图」。
    """
    path = os.path.normpath(os.path.join(ROOT, "chapters", src))
    if not path.endswith(".svg") or not os.path.exists(path):
        return None
    txt = open(path, encoding="utf-8").read()
    txt = re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", txt)
    txt = re.sub(r"^\s*<!DOCTYPE[^>]*>\s*", "", txt, flags=re.I)
    return txt.strip()


def svg_to_png(svg_path: str, png_path: str) -> bool:
    """用构建链已有的 Edge/Chrome 把 SVG 转 PNG，供 DOCX 嵌入。

    python-docx 不支持 SVG（Word 的 SVG 支持没有开放 API），而再引一个
    cairosvg/svglib 依赖与「构建只靠 python + Edge」的既有约定冲突。
    转换失败时返回 False，调用方降级为文字图注——不静默丢图。
    """
    edge = find_edge()
    if not edge:
        return False
    try:
        head = open(svg_path, encoding="utf-8").read()
        mw = re.search(r'\bwidth="(\d+(?:\.\d+)?)"', head)
        mh = re.search(r'\bheight="(\d+(?:\.\d+)?)"', head)
        w = int(float(mw.group(1))) if mw else 900
        h = int(float(mh.group(1))) if mh else 520
        png_abs = os.path.abspath(png_path)
        if os.path.exists(png_abs):
            os.remove(png_abs)
        profile = tempfile.mkdtemp(prefix="bd-png-")
        subprocess.run([edge, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--user-data-dir={profile}",
                        f"--window-size={w},{h}", f"--screenshot={png_abs}",
                        "file:///" + os.path.abspath(svg_path).replace("\\", "/")],
                       capture_output=True, timeout=90)
        shutil.rmtree(profile, ignore_errors=True)
    except Exception:
        return False
    return os.path.exists(png_abs) and os.path.getsize(png_abs) > 2048


def render_html_body(blocks: list[dict], first_h1: str | None, cls: str = "",
                     link_prefix: str = "#", link_suffix: str = "") -> str:
    # HTML/PDF 是单文件（#chNN）；EPUB 每章一个 xhtml（chNN.xhtml）。
    # 逻辑目标统一由 inline() 产出，这里只负责拼目标，解析逻辑不重复。
    def ih(text: str) -> str:
        return inline_html(text, link_prefix, link_suffix)

    out = []
    if first_h1:
        out.append(f'<h1 class="{cls}">{html.escape(first_h1)}</h1>')
    for b in blocks:
        k = b["kind"]
        if k == "image":
            svg = load_diagram(b["src"])
            if svg:
                cap = f"<figcaption>{ih(b['alt'])}</figcaption>" if b["alt"] else ""
                out.append(f'<figure class="diagram">{svg}{cap}</figure>')
            else:
                # 缺失必须显式可见：静默忽略会让「Markdown 正常、成品没有图」重演
                out.append(f'<p class="diagram-missing">［图示缺失：{html.escape(b["src"])}］</p>')
        elif k == "code":
            out.append("<pre><code>%s</code></pre>" % html.escape(b["text"]))
        elif k == "table":
            out.append("<table><thead><tr>")
            out += [f"<th>{ih(c)}</th>" for c in b["head"]]
            out.append("</tr></thead><tbody>")
            for row in b["rows"]:
                out.append("<tr>" + "".join(f"<td>{ih(c)}</td>" for c in row) + "</tr>")
            out.append("</tbody></table>")
        elif k in ("ul", "ol"):
            tag = "ul" if k == "ul" else "ol"
            out.append(f"<{tag}>" + "".join(f"<li>{ih(x)}</li>" for x in b["items"]) + f"</{tag}>")
        elif k == "quote":
            paras = "".join(f"<p>{ih(x)}</p>" for x in b["text"].split("\n") if x.strip())
            out.append(f"<blockquote>{paras}</blockquote>")
        elif k == "hr":
            continue
        elif k in ("h2", "h3", "h4"):
            tag = k
            out.append(f"<{tag}>{ih(b['text'])}</{tag}>")
        else:
            out.append(f"<p>{ih(b['text'])}</p>")
    return "\n".join(out)


def inline_html(text: str, prefix: str = "#", suffix: str = "") -> str:
    out = []
    for style, chunk, href in inline(text):
        if style in ("link", "boldlink"):
            esc = html.escape(chunk)
            if href and href.startswith(("http://", "https://")):
                url = html.escape(href, quote=True)
            else:
                url = html.escape(prefix + (href or "") + suffix, quote=True)
            a = f'<a href="{url}">{esc}</a>'
            out.append(f"<strong>{a}</strong>" if style == "boldlink" else a)
        elif style == "bold":
            out.append(f"<strong>{html.escape(chunk)}</strong>")
        elif style == "boldcode":
            out.append(f"<strong><code>{html.escape(chunk)}</code></strong>")
        elif style == "code":
            out.append(f"<code>{html.escape(chunk)}</code>")
        else:
            out.append(html.escape(chunk))
    return "".join(out)


def build_html(docs: list[dict], dest: str) -> None:
    parts = [f"<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
             f"<title>{TITLE}</title><style>{CSS}</style></head><body>",
             '<div class="cover">'
             f'<div class="t">{TITLE}</div><div class="s">—— {SUBTITLE}</div>'
             '<div class="m">七篇 31 章 + 附录 A–I<br>贯穿案例 order-demo ｜ 版本基线 Kubernetes 1.32+</div>'
             "</div>"]
    for d in docs:
        blocks = parse_md(d["body"])
        parts.append(f'<section id="{d["id"]}">')
        parts.append(render_html_body(blocks, d["title"]))
        parts.append("</section>")
    parts.append("</body></html>")
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(parts))


# ---------------------------------------------------------------------------
# 五、PDF
# ---------------------------------------------------------------------------
def find_edge() -> str | None:
    for p in EDGE_CANDIDATES:
        if os.path.exists(p):
            return p
    return shutil.which("msedge") or shutil.which("microsoft-edge") or shutil.which("chrome")


def build_pdf(html_path: str, dest: str) -> int:
    edge = find_edge()
    if not edge:
        raise RuntimeError("找不到 Edge/Chrome，无法打印 PDF")
    # 用「确保不存在」的临时路径：实测 Edge 对预创建的空目标文件偶尔不写盘
    # （表现为 pypdf 读到空文件），故不依赖 tempfile.mkstemp 的预建行为
    import time
    tmp_pdf = os.path.join(tempfile.gettempdir(),
                           f"bdout_{os.getpid()}_{int(time.time() * 1000)}.pdf")
    if os.path.exists(tmp_pdf):
        os.remove(tmp_pdf)
    url = "file:///" + os.path.abspath(html_path).replace("\\", "/")
    cmd = [edge, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
           f"--print-to-pdf={tmp_pdf}", url]
    subprocess.run(cmd, check=True, timeout=600,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(tmp_pdf) or os.path.getsize(tmp_pdf) == 0:
        raise RuntimeError("Edge 未产出 PDF（空文件）")

    # 盖页码 + 自建书签：Chromium 不支持 @page 计数器，也不保证
    # --generate-pdf-document-outline 稳定生效（实测同管线 550→0→空文件），
    # 故书签改为由 HTML 标题结构显式生成，页码按 stamped 页面文本定位
    from io import BytesIO
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas

    reader = PdfReader(tmp_pdf)
    total = len(reader.pages)
    writer = PdfWriter()
    writer.append(reader)

    for i, page in enumerate(writer.pages, 1):
        w = float(page.mediabox.width)
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=(w, float(page.mediabox.height)))
        c.setFont("Helvetica", 8.5)
        c.setFillGray(0.45)
        c.drawCentredString(w / 2, 16, f"{i} / {total}")
        c.save()
        buf.seek(0)
        page.merge_page(PdfReader(buf).pages[0])

    build_pdf_outline(writer, html_path, total)

    with open(dest, "wb") as fh:
        writer.write(fh)
    try:
        os.remove(tmp_pdf)
    except OSError:
        pass
    return total


def build_pdf_outline(writer, html_path: str, total: int) -> None:
    """按 HTML 的 h1/h2 文档顺序自建 PDF 书签树。

    - 不依赖 Edge 的 outline 开关（不可靠）；
    - 页码用 stamped 后每页文本反查，并从上一标题页向后单调搜索，
      保证「父页号 ≤ 子页号」的书签树合法。
    """
    raw = open(html_path, encoding="utf-8").read()
    items: list[tuple[int, str]] = []
    for m in re.finditer(r"<h([12])[^>]*>(.*?)</h\1>", raw, re.S | re.I):
        level = int(m.group(1))
        txt = re.sub(r"<[^>]+>", "", m.group(2))
        txt = html.unescape(txt)
        txt = re.sub(r"\s+", " ", txt).strip()
        if txt:
            items.append((level, txt))
    if not items:
        return

    def norm(s: str) -> str:
        return re.sub(r"\s+", "", s or "")

    page_texts = [norm(p.extract_text()) for p in writer.pages]

    def key_of(txt: str) -> str:
        # 章标题「第 N 章　…」取「第 N 章」前缀，足够唯一且免受后续长串干扰
        if "第" in txt and "章" in txt:
            return norm(txt.split("章", 1)[0] + "章")
        return norm(txt)[:8]

    last_page = 0
    stack: dict[int, object] = {}
    for level, txt in items:
        key = key_of(txt)
        page_idx = last_page
        for idx in range(last_page, total):
            if key and key in page_texts[idx]:
                page_idx = idx
                break
        parent = stack.get(level - 1)
        ref = writer.add_outline_item(txt, page_idx, parent=parent)
        stack[level] = ref
        for lv in (level + 1, level + 2):
            stack.pop(lv, None)
        last_page = page_idx


# ---------------------------------------------------------------------------
# 六、EPUB
# ---------------------------------------------------------------------------
EPUB_CSS = """
body { font-family: serif; line-height: 1.6; margin: 0 5%; }
h1 { font-size: 1.5em; text-align: center; margin: 1.2em 0 0.8em; }
h2 { font-size: 1.2em; margin: 1.2em 0 0.5em; }
h3 { font-size: 1.05em; margin: 1em 0 0.4em; }
p { margin: 0 0 0.45em; text-indent: 2em; text-align: justify; }
blockquote p, li p { text-indent: 0; }
pre { background: #f4f4f6; padding: 0.5em; overflow-x: auto; font-size: 0.78em;
      white-space: pre-wrap; word-break: break-all; }
code { font-family: monospace; font-size: 0.9em; }
table { border-collapse: collapse; width: 100%; font-size: 0.8em; margin: 0.6em 0; }
th, td { border: 1px solid #bbb; padding: 0.25em 0.35em; text-align: left; text-indent: 0; }
th { background: #ececf1; }
blockquote { border-left: 3px solid #ccc; margin: 0.6em 0; padding-left: 0.7em; color: #444; }
figure.diagram { margin: 0.8em 0; text-align: center; text-indent: 0; }
figure.diagram svg { max-width: 100%; height: auto; }
figure.diagram figcaption { font-size: 0.8em; color: #555; margin-top: 0.3em; text-align: center; }
p.diagram-missing { color: #b00020; text-align: center; text-indent: 0; }
"""


def xhtml_page(title: str, body: str) -> str:
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-CN" lang="zh-CN">'
            f'<head><meta charset="utf-8"/><title>{html.escape(title)}</title>'
            '<link rel="stylesheet" type="text/css" href="style.css"/></head>'
            f'<body>{body}</body></html>')


def build_epub(docs: list[dict], dest: str) -> None:
    items = []
    for d in docs:
        blocks = parse_md(d["body"])
        items.append((d["id"] + ".xhtml", d["title"],
                      render_html_body(blocks, d["title"],
                                       link_prefix="", link_suffix=".xhtml")))

    with zipfile.ZipFile(dest, "w") as z:
        z.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml",
                   '<?xml version="1.0" encoding="utf-8"?>'
                   '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                   '<rootfiles><rootfile full-path="OEBPS/content.opf" '
                   'media-type="application/oebps-package+xml"/></rootfiles></container>')
        z.writestr("OEBPS/style.css", EPUB_CSS)
        for name, title, body in items:
            z.writestr("OEBPS/" + name, xhtml_page(title, body))
        manifest = "".join(
            f'<item id="c{i}" href="{name}" media-type="application/xhtml+xml"/>'
            for i, (name, _, _) in enumerate(items))
        spine = "".join(f'<itemref idref="c{i}"/>' for i in range(len(items)))
        nav = ('<?xml version="1.0" encoding="utf-8"?>\n'
               '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
               'xml:lang="zh-CN" lang="zh-CN"><head><meta charset="utf-8"/>'
               f'<title>目录</title></head><body><nav epub:type="toc" id="toc"><h1>目录</h1><ol>'
               + "".join(f'<li><a href="{name}">{html.escape(title)}</a></li>'
                         for name, title, _ in items)
               + "</ol></nav></body></html>")
        z.writestr("OEBPS/nav.xhtml", nav)
        opf = ('<?xml version="1.0" encoding="utf-8"?>'
               '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bid">'
               '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
               '<dc:identifier id="bid">urn:uuid:k8s-app-delivery-book-2026</dc:identifier>'
               f'<dc:title>{html.escape(TITLE)}</dc:title>'
               '<dc:creator>本书作者</dc:creator><dc:language>zh-CN</dc:language>'
               '<dc:description>' + html.escape(SUBTITLE) + '</dc:description>'
               '<meta property="dcterms:modified">2026-11-11T00:00:00Z</meta>'
               '</metadata><manifest>'
               '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
               '<item id="css" href="style.css" media-type="text/css"/>'
               + manifest +
               '</manifest><spine>' + spine + '</spine></package>')
        z.writestr("OEBPS/content.opf", opf)


# ---------------------------------------------------------------------------
# 七、装配体检
# ---------------------------------------------------------------------------
def report(docs: list[dict], extra: dict) -> str:
    chs = [d for d in docs if d["kind"] == "chapter"]
    aps = [d for d in docs if d["kind"] == "appendix"]
    total = sum(len(re.findall(r"[\u4e00-\u9fff]", d["text"])) for d in docs)
    cl = set()
    refs = set()
    codes = 0
    tables = 0
    for d in docs:
        cl.update(re.findall(r"CL-[A-Z0-9]{1,2}-\d{2}", d["text"]))
        refs.update(re.findall(r"R-\d{2}-\d{1,2}", d["text"]))
    for d in docs:
        blocks = parse_md(d["body"])
        codes += sum(1 for b in blocks if b["kind"] == "code")
        tables += sum(1 for b in blocks if b["kind"] == "table")

    lines = ["# 装配体检报告", "",
             f"- 章节：{len(chs)} 章；附录：{len(aps)} 个",
             f"- 汉字总计：{total:,}",
             f"- 代码块：{codes} 处；表格：{tables} 张",
             f"- 检查清单编号（CL-*）：{len(cl)} 个不同编号",
             f"- 引用角标（R-*）：{len(refs)} 个不同编号", ""]
    # 章号连贯
    nums = [int(d["id"][2:]) for d in chs]
    gap = [n for n in range(1, max(nums) + 1) if n not in nums] if nums else []
    lines.append(f"- 章号连贯：{'是' if not gap else '缺 ' + str(gap)}")
    # 每章必备段落
    missing = []
    for d in chs:
        for marker, label in (("上线检查清单", "检查清单"), ("依据与延伸阅读", "依据段"),
                              ("本书观点", "本书观点块")):
            if marker not in d["text"]:
                missing.append(f"{d['id']} 缺{label}")
    lines.append(f"- 结构完整性：{'通过' if not missing else '；'.join(missing)}")
    # 附录 I 完整性
    ap_i = [d for d in aps if "参考文献" in d["file"]]
    if ap_i:
        n = len(re.findall(r"(?m)^- \*\*R-", ap_i[0]["text"]))
        lines.append(f"- 附录 I 条目：{n} 条")
    lines += ["", "## 产物", ""]
    for k, v in extra.items():
        lines.append(f"- {k}：{v}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["docx", "pdf", "epub"])
    ap.add_argument("--keep-html", action="store_true")
    ap.add_argument("--out", default=DIST,
                    help="产物输出目录，默认 dist/；目标文件被预览器占用时可指到别处")
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    docs = collect()
    base = os.path.join(out, TITLE)
    extra: dict[str, str] = {}

    try:
        if args.only in (None, "docx"):
            st = build_docx(docs, base + ".docx")
            extra["docx"] = (f"{os.path.getsize(base + '.docx') / 1024 / 1024:.1f} MB；"
                             f"代码块 {st['code']} 处、表格 {st['table']} 张、正文段落 {st['para']} 段")
            print("docx 完成")

        if args.only in (None, "pdf", "epub"):
            html_path = os.path.join(out, "_book.html")
            build_html(docs, html_path)
            if args.only in (None, "pdf"):
                pages = build_pdf(html_path, base + ".pdf")
                extra["pdf"] = f"{pages} 页；{os.path.getsize(base + '.pdf') / 1024 / 1024:.1f} MB"
                print(f"pdf 完成（{pages} 页）")
            if args.only in (None, "epub"):
                build_epub(docs, base + ".epub")
                extra["epub"] = f"{os.path.getsize(base + '.epub') / 1024 / 1024:.1f} MB"
                print("epub 完成")
            if not args.keep_html:
                os.remove(html_path)
    except PermissionError as e:
        print(f"!! 写入被占用：{e.filename}")
        print("   目标文件正在被阅读器/预览器打开；关掉它，或用 --out 指到另一个目录。")
        return 2

    rep = report(docs, extra)
    with open(os.path.join(out, "build-report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(rep)
    print(rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
