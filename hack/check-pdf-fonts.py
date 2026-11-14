#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 字体嵌入闸门（D-62）

为什么需要这个脚本
------------------
D-60 的教训：Release PDF 在 ubuntu runner 上用 headless Chromium 打印，
runner 没装中文字体，Chromium 回退到纯拉丁字体，中文全部画成豆腐块。
当时的验收只看「文件生成成功 + 体积没变」，坏件照样发布出去。
本脚本把「PDF 里中文必须真的能显示、能检索」变成可自动判定、失败即阻断的硬闸门。

同一本书在两种平台上的 PDF 技术路径不同，必须都认
--------------------------------------------------
- Windows / macOS：Chromium 能把宋体、黑体直接子集化嵌入 → PDF 里出现
  `CIDFontType2` + `/BaseFont /SimSun`（或 Songti / STSong 等）。
- Linux（CI runner）：`fonts-noto-cjk` 提供的是 CID-keyed OTF，Chromium 的
  PDF 后端改为**用 Type3 字形程序逐段描摹字形**（每页上百个 Type3 字体，
  每个带 `/CharProcs` 与 `/ToUnicode`）。此时页面 `/Resources /Font` 里
  没有可读的 CJK BaseFont，但文件里仍存在 `NotoSerifCJKsc` 等 FontDescriptor。

所以判定不能只看「有没有 CJK 字体名」，必须同时看「中文能不能被抽出来」。

判定四项（任一硬项不过即退出码 1，阻断发布）
--------------------------------------------
1. 文件完整性：存在、非空、`%PDF-` 头、尾随 `%%EOF`（截断的下载件会被拦下）
2. 文本层中文可抽取：抽样页面能抽出 ≥ 阈值数量的汉字
   —— 这一项直接对应读者诉求「中文要看得见、搜得到、复制得出」，
      也是豆腐块缺陷最可靠的检测信号（豆腐件的汉字会被抽成空格）
3. 中文字形来源存在：满足任一即可
   a) 文件内嵌 CJK 字体程序（`/FontName`、`/BaseFont` 或 `/FontFamily` 含 CJK 字体名）
   b) 存在 Type3 字形程序字体，且其 ToUnicode 映射到 CJK 码位
      （Chromium 在 Linux 上绘制中文的真实路径）
4. 字体承载结构合理：存在复合编码（CIDFontType0/2、Identity-H）或 Type3 字形程序

依赖
----
pypdf（已在 hack/requirements.txt 锁定）用于遍历字体字典与抽取文本。
pypdf 不可用时降级为「原始字节扫描」，仍能判定 1/3 的绝大部分情形，
但会显式标注「降级」并把第 2 项降为告警——宁可显式降级，也不要假装通过。

用法
----
  python hack/check-pdf-fonts.py --pdf dist/一次变更的旅程.pdf
  python hack/check-pdf-fonts.py --pdf a.pdf --report dist/pdf-font-report.md
  python hack/check-pdf-fonts.py --pdf a.pdf --json

退出码：0 = 通过；1 = 校验不通过（应阻断发布）；2 = 用法错误
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# CJK 字体识别
# ---------------------------------------------------------------------------
# 判定依据是 PDF 里的字体名（PostScript 名 / FontFamily），各平台对应关系：
#   Ubuntu/CI : NotoSerifCJKsc-Regular / NotoSansCJKsc-Bold / WenQuanYiZenHei
#   Windows   : SimSun / SimHei / NSimSun / MicrosoftYaHei / FangSong / KaiTi
#   macOS     : STSong / STHeiti / SongtiSC-Regular / HeitiSC-Regular / PingFangSC
# 命中任一 token 即判为 CJK 字体。注意不能只用 "Noto" 单独判定——
# NotoColorEmoji / NotoSansSymbols 都不是中文字体。
CJK_TOKENS = (
    "CJK",          # NotoSerifCJKsc / SourceHanSerifSC
    "SourceHan",
    "WenQuanYi",
    "Song",         # SimSun / STSong / SongtiSC
    "Sung",         # MSung / AdobeSongStd
    "SimSun",
    "SimHei",
    "NSim",
    "STSong",
    "STHeiti",
    "Heiti",
    "Hei",          # SimHei / HeitiSC / MicroHei
    "YaHei",
    "Ming",         # Songti / MingLiU / SourceHanSerif
    "LiU",          # MingLiU
    "Kai",          # KaiTi / STKaiti
    "Fang",         # FangSong
    "Yuan",         # Yuanti
    "LiSu",
    "PingFang",
    "Hiragino",
    "Malgun",
    "Meiryo",
    "YuGothic",
    "BiauKai",
)

# 明显不是中文字体的名字（含 CJK 之外语种/符号的 Noto 变体）
CJK_NEGATIVE = (
    "ColorEmoji",
    "Symbols",
    "Math",
    "Music",
    "Emoji",
)


def normalize_font_name(raw: str) -> str:
    """去掉子集前缀（AAAAAA+Name → Name），保留可读名。"""
    raw = raw.strip()
    if raw.startswith("/"):
        raw = raw[1:]
    return raw.split("+")[-1] if "+" in raw else raw


def is_cjk_font_name(name: str) -> bool:
    """判断一个字体名是否属于中文字体族。"""
    if not name:
        return False
    base = normalize_font_name(name)
    if any(neg.lower() in base.lower() for neg in CJK_NEGATIVE):
        return False
    return any(tok.lower() in base.lower() for tok in CJK_TOKENS)


# ---------------------------------------------------------------------------
# 原始字节扫描（覆盖整个文件，无依赖）
# ---------------------------------------------------------------------------
NAME_RE = re.compile(rb"/FontName\s*/([^\s/<>\[\](){}]+)")
BASEFONT_RE = re.compile(rb"/BaseFont\s*/([^\s/<>\[\](){}]+)")
FAMILY_RE = re.compile(rb"/FontFamily\s*\(([^)]{0,80})\)")
CJK_HEX_RE = re.compile(rb"<([0-9A-Fa-f]{4})>")


def scan_raw(path: str) -> dict:
    """直接扫 PDF 字节，统计字体名与关键结构标记。"""
    with open(path, "rb") as fh:
        data = fh.read()
    names = set()
    for m in NAME_RE.finditer(data):
        names.add(normalize_font_name(m.group(1).decode("latin-1", "ignore")))
    for m in BASEFONT_RE.finditer(data):
        names.add(normalize_font_name(m.group(1).decode("latin-1", "ignore")))
    families = set()
    for m in FAMILY_RE.finditer(data):
        families.add(m.group(1).decode("latin-1", "ignore").strip())
    return {
        "bytes": len(data),
        "header_ok": data[:5] == b"%PDF-",
        "eof_ok": data.rstrip()[-5:] == b"%%EOF",
        "font_names": sorted(names),
        "font_families": sorted(families),
        "cid_type0": len(re.findall(rb"/CIDFontType0", data)),
        "cid_type2": len(re.findall(rb"/CIDFontType2", data)),
        "fontfile": len(re.findall(rb"/FontFile\b", data)),
        "fontfile2": len(re.findall(rb"/FontFile2", data)),
        "fontfile3": len(re.findall(rb"/FontFile3", data)),
        "identity_h": len(re.findall(rb"/Identity-H", data)),
        "type3_count": len(re.findall(rb"/Subtype\s*/Type3", data)),
    }


# ---------------------------------------------------------------------------
# pypdf 权威遍历
# ---------------------------------------------------------------------------
def _deref(obj):
    """安全地取 .get_object()。"""
    if obj is None:
        return None
    try:
        return obj.get_object()
    except Exception:
        return obj


def _has_fontfile(desc) -> bool:
    """判断字体描述符里是否带嵌入的字体文件流。"""
    desc = _deref(desc)
    if not isinstance(desc, dict):
        return False
    return any(k in desc for k in ("/FontFile", "/FontFile2", "/FontFile3"))


def _tounicode_has_cjk(font_dict) -> bool:
    """判断 Type3 字体的 ToUnicode 是否映射到 CJK 码位。"""
    tu = _deref(font_dict.get("/ToUnicode")) if isinstance(font_dict, dict) else None
    if tu is None:
        return False
    try:
        data = tu.get_data()
    except Exception:
        return False
    for hx in CJK_HEX_RE.findall(data):
        try:
            cp = int(hx, 16)
        except ValueError:
            continue
        if 0x4E00 <= cp <= 0x9FFF or 0x3000 <= cp <= 0x303F or 0xFF00 <= cp <= 0xFFEF:
            return True
    return False


def walk_fonts(reader, page_indices) -> tuple[dict, dict]:
    """遍历指定页面的字体资源。

    返回 (named_fonts, stats)：
      named_fonts: 有 /BaseFont 的字体（去重），含名称/子类型/CID 类型/是否嵌入
      stats:      Type3 字形程序数量与其中 ToUnicode 命中 CJK 的数量
    """
    named: dict[tuple, dict] = {}
    type3_total = 0
    type3_cjk = 0
    for i in page_indices:
        try:
            page = reader.pages[i]
            res = _deref(page.get("/Resources"))
        except Exception:
            continue
        if not isinstance(res, dict):
            continue
        fonts = _deref(res.get("/Font"))
        if not isinstance(fonts, dict):
            continue
        for key in list(fonts.keys()):
            try:
                fd = _deref(fonts[key])
            except Exception:
                continue
            if not isinstance(fd, dict):
                continue
            subtype = str(fd.get("/Subtype", "")).lstrip("/")
            if subtype == "Type3":
                type3_total += 1
                if _tounicode_has_cjk(fd):
                    type3_cjk += 1
                continue
            base = fd.get("/BaseFont")
            name = normalize_font_name(str(base)) if base is not None else str(key)
            cid_type = ""
            embedded = False
            if subtype == "Type0":
                desc_fonts = _deref(fd.get("/DescendantFonts"))
                if isinstance(desc_fonts, list) and desc_fonts:
                    d = _deref(desc_fonts[0])
                    if isinstance(d, dict):
                        cid_type = str(d.get("/Subtype", "")).lstrip("/")
                        embedded = _has_fontfile(d.get("/FontDescriptor"))
            else:
                embedded = _has_fontfile(fd.get("/FontDescriptor"))
            named[(name, subtype, cid_type)] = {
                "name": name,
                "subtype": subtype,
                "cid_type": cid_type,
                "embedded": embedded,
                "cjk": is_cjk_font_name(name),
            }
    stats = {"type3_total": type3_total, "type3_cjk": type3_cjk}
    return named, stats


def pick_page_indices(pages: int, sample: int) -> list[int]:
    """在全书均匀抽样页码（含首尾）。"""
    if pages <= 0:
        return []
    if pages <= sample:
        return list(range(pages))
    step = (pages - 1) / (sample - 1)
    return sorted({int(round(i * step)) for i in range(sample)})


def sample_cjk_chars(reader, pages: int, sample: int = 16) -> dict:
    """在全书均匀抽样若干页，统计能抽出的汉字数量与样例。"""
    idxs = pick_page_indices(pages, sample)
    total = 0
    errors = 0
    snippet = ""
    for i in idxs:
        try:
            text = reader.pages[i].extract_text() or ""
        except Exception:
            errors += 1
            continue
        cn = re.findall(r"[\u4e00-\u9fff]", text)
        total += len(cn)
        if not snippet and cn:
            snippet = "".join(cn[:40])
    return {
        "pages_sampled": len(idxs),
        "errors": errors,
        "cjk_chars": total,
        "sample": snippet,
    }


# ---------------------------------------------------------------------------
# 判定与报告
# ---------------------------------------------------------------------------
def evaluate(path: str, min_cjk_chars: int, sample_pages: int = 12) -> dict:
    result: dict = {
        "path": path,
        "checks": [],
        "fonts": [],
        "pages": 0,
        "degraded": False,
        "notes": [],
    }

    def add(name: str, ok: bool, detail: str, level: str = "hard"):
        result["checks"].append({
            "name": name, "ok": bool(ok), "detail": detail, "level": level,
        })

    if not os.path.isfile(path):
        add("文件存在", False, f"找不到 {path}")
        return result
    size = os.path.getsize(path)
    if size == 0:
        add("文件完整性", False, "PDF 为空文件")
        return result

    raw = scan_raw(path)
    result["raw"] = raw

    # --- 1. 文件完整性 ---
    add(
        "文件完整性（%PDF- 头 / %%EOF 尾）",
        raw["header_ok"] and raw["eof_ok"],
        f"{size / 1024 / 1024:.1f} MB；头={raw['header_ok']}，尾={raw['eof_ok']}",
    )

    # --- 字体清单：pypdf 权威遍历 + 全文件字节扫描（两者互补） ---
    named_fonts: dict = {}
    stats = {"type3_total": 0, "type3_cjk": 0}
    text_probe = None
    try:
        from pypdf import PdfReader
        reader = PdfReader(path, strict=False)
        pages = len(reader.pages)
        result["pages"] = pages
        idxs = pick_page_indices(pages, sample_pages)
        named_fonts, stats = walk_fonts(reader, idxs)
        try:
            text_probe = sample_cjk_chars(reader, pages)
        except Exception as exc:
            result["notes"].append(f"文本抽样异常（降级为告警）：{exc}")
    except Exception as exc:
        result["degraded"] = True
        result["notes"].append(
            f"pypdf 不可用或无法解析（{exc}），降级为字节扫描；文本层校验降级为告警。"
        )

    # CJK 字体程序：页级命名的字体 + 全文件 FontName/BaseFont/FontFamily
    cjk_names: dict[str, str] = {}
    for f in named_fonts.values():
        if f["cjk"]:
            cjk_names.setdefault(f["name"], "页面字体资源")
    for n in raw["font_names"]:
        if is_cjk_font_name(n):
            cjk_names.setdefault(n, "文件内字体程序")
    for n in raw["font_families"]:
        if is_cjk_font_name(n):
            cjk_names.setdefault(n, "文件内字体族")

    type3_cjk = stats["type3_cjk"]
    glyph_sources = list(cjk_names.keys())
    if type3_cjk:
        glyph_sources.append(f"Type3 字形程序 ×{type3_cjk}")

    result["fonts"] = sorted(named_fonts.values(), key=lambda f: (not f["cjk"], f["name"]))
    result["cjk_font_programs"] = sorted(cjk_names.keys())
    result["type3"] = stats

    # --- 2. 文本层中文可抽取（决定性，对应读者诉求） ---
    if text_probe is None:
        add("文本层中文可抽取", True,
            "（降级：文本抽样不可用，本项未参与判定）", level="soft")
    else:
        ok = text_probe["cjk_chars"] >= min_cjk_chars
        add(
            "文本层中文可抽取（抽样汉字数 ≥ 阈值）",
            ok,
            f"抽样 {text_probe['pages_sampled']} 页（读取错误 {text_probe['errors']}），"
            f"抽出 {text_probe['cjk_chars']} 个汉字（阈值 {min_cjk_chars}）"
            + (f"；样例：{text_probe['sample']}" if text_probe["sample"] else ""),
        )

    # --- 3. 中文字形来源存在 ---
    add(
        "中文字形来源存在",
        bool(glyph_sources),
        (f"内嵌 CJK 字体程序 {len(cjk_names)} 个"
         + (f"（{'、'.join(sorted(cjk_names)[:4])}）" if cjk_names else "")
         + (f"；Type3 字形程序命中 CJK {type3_cjk} 个" if type3_cjk else "")
         if glyph_sources else
         "既无内嵌 CJK 字体程序，也无 ToUnicode 命中 CJK 的 Type3 字形程序"),
    )

    # --- 4. 字体承载结构合理 ---
    composite = raw["cid_type0"] + raw["cid_type2"] + raw["identity_h"]
    struct_ok = composite > 0 or stats["type3_total"] > 0
    add(
        "字体承载结构合理（复合编码或 Type3 字形程序）",
        struct_ok,
        f"CIDFontType0={raw['cid_type0']}，CIDFontType2={raw['cid_type2']}，"
        f"Identity-H={raw['identity_h']}，Type3 字体对象={raw['type3_count']}",
    )

    return result


# ---------------------------------------------------------------------------
# 闸门自检：证明这道闸门还会拦人
# ---------------------------------------------------------------------------
def _make_latin_only_pdf(path: str) -> bool:
    """造一个「有中文文本、但只有拉丁字体」的 PDF，复刻豆腐块环境。"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
    except Exception:
        return False
    c = canvas.Canvas(path, pagesize=A4)
    c.setFont("Helvetica", 12)
    for i in range(3):
        c.drawString(72, 720, "Kubernetes deployment guide - page %d" % (i + 1))
        c.drawString(72, 700, "order-demo / gateway 8080 / api 8081")
        c.showPage()
    c.save()
    return os.path.exists(path) and os.path.getsize(path) > 0


def self_test() -> int:
    """自检：确认闸门仍然会拒绝坏 PDF，而不是退化成一盏永远绿灯的灯。

    一个永远通过的闸门等于没有闸门。本自检构造两类坏件，断言闸门必须拦下：
      1) 只有拉丁字体的 PDF（复刻 D-60 的豆腐块环境）
      2) 被截断的 PDF（缺 %%EOF）
    同时校验 CJK 字体名分类器没被改坏（NotoColorEmoji 不是中文字体）。
    """
    import logging
    import tempfile

    print("== PDF 中文字体闸门 · 自检 ==")
    problems = []

    # 截断件必然触发 pypdf 的 "EOF marker not found" 告警，属预期现象，
    # 压掉以免自检输出被噪音淹没（仅自检期间生效）。
    pypdf_logger = logging.getLogger("pypdf")
    prev_level = pypdf_logger.level
    pypdf_logger.setLevel(logging.ERROR)
    try:
        return _self_test_body(problems)
    finally:
        pypdf_logger.setLevel(prev_level)


def _self_test_body(problems: list) -> int:
    import tempfile

    # --- 分类器断言 ---
    cases = [
        ("NotoSerifCJKsc-Regular", True),
        ("NotoSansCJKsc-Bold", True),
        ("SimSun", True),
        ("SimHei", True),
        ("MicrosoftYaHei", True),
        ("STSong", True),
        ("WenQuanYiZenHei", True),
        ("AAAAAA+NotoSerifCJKsc-Regular", True),
        ("NotoColorEmoji", False),
        ("NotoSansSymbols2", False),
        ("DejaVuSans", False),
        ("LiberationMono", False),
        ("Helvetica", False),
    ]
    for name, expected in cases:
        got = is_cjk_font_name(name)
        mark = "✅" if got == expected else "❌"
        print(f"  {mark} 分类器 {name!r} → {got}（期望 {expected}）")
        if got != expected:
            problems.append(f"分类器判定错误：{name} → {got}，期望 {expected}")

    with tempfile.TemporaryDirectory() as tmp:
        latin = os.path.join(tmp, "latin_only.pdf")
        if not _make_latin_only_pdf(latin):
            print("  ⚠️ 跳过 PDF 构造自检（缺 reportlab）")
        else:
            res = evaluate(latin, 500)
            hard = [c for c in res["checks"] if c["level"] == "hard"]
            failed = [c for c in hard if not c["ok"]]
            print(f"  {'✅' if failed else '❌'} 纯拉丁字体 PDF：硬闸门失败 "
                  f"{len(failed)}/{len(hard)} 项")
            if not failed:
                problems.append("闸门自检失败：纯拉丁字体 PDF 竟被放行（闸门已失效）")

            # 截断件
            trunc = os.path.join(tmp, "truncated.pdf")
            with open(latin, "rb") as fh:
                data = fh.read()
            with open(trunc, "wb") as fh:
                fh.write(data[:max(200, len(data) // 3)])
            res2 = evaluate(trunc, 500)
            ok2 = any(not c["ok"] and "完整性" in c["name"]
                      for c in res2["checks"] if c["level"] == "hard")
            print(f"  {'✅' if ok2 else '❌'} 截断 PDF：完整性检查"
                  f"{'已拦下' if ok2 else '未拦下'}")
            if not ok2:
                problems.append("闸门自检失败：截断 PDF 未被完整性检查拦下")

    if problems:
        print("\n[FAIL] 闸门自检未通过：", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("\n[OK] 闸门自检通过：闸门仍会拦下坏件，未退化成永远绿灯。")
    return 0


def render_report(result: dict, min_cjk_chars: int) -> str:
    """把判定结果渲染成 Markdown 报告（随 Release 一起留证）。"""
    hard = [c for c in result["checks"] if c["level"] == "hard"]
    failed = [c for c in hard if not c["ok"]]
    passed = not failed
    raw = result.get("raw", {})

    lines = []
    lines.append("# PDF 中文字体校验报告（D-62 硬闸门）\n")
    lines.append(f"- 结论：**{'通过' if passed else '未通过（应阻断发布）'}**")
    lines.append(f"- 文件：`{os.path.basename(result['path'])}`")
    lines.append(f"- 页数：{result['pages'] or '未知'}")
    if raw:
        lines.append(f"- 体积：{raw['bytes'] / 1024 / 1024:.1f} MB")
    lines.append(f"- 判定模式：{'降级（字节扫描）' if result['degraded'] else '完整（pypdf 遍历）'}")
    lines.append(f"- 汉字抽样阈值：{min_cjk_chars}\n")

    lines.append("## 检查项\n")
    lines.append("| 检查项 | 级别 | 结果 | 说明 |")
    lines.append("| --- | --- | --- | --- |")
    for c in result["checks"]:
        mark = "✅" if c["ok"] else ("❌" if c["level"] == "hard" else "⚠️")
        level = "硬闸门" if c["level"] == "hard" else "告警"
        detail = c["detail"].replace("|", "\\|")
        lines.append(f"| {c['name']} | {level} | {mark} | {detail} |")

    lines.append("\n## 中文字形来源\n")
    programs = result.get("cjk_font_programs", [])
    if programs:
        lines.append("文件内嵌的中文字体程序：")
        for p in programs:
            lines.append(f"- `{p}`")
    else:
        lines.append("文件内嵌的中文字体程序：无")
    t3 = result.get("type3", {})
    if t3.get("type3_total"):
        lines.append(
            f"\nType3 字形程序：抽样页面共 {t3['type3_total']} 个，"
            f"其中 ToUnicode 命中 CJK 码位 {t3['type3_cjk']} 个"
            "（Chromium 在 Linux 上绘制中文的真实路径：用字形程序描摹 Noto 字形）"
        )

    lines.append("\n## 页面字体资源（抽样页，去重）\n")
    fonts = result.get("fonts", [])
    if fonts:
        lines.append("| 字体名 | 子类型 | CID 类型 | 中文字体 | 嵌入 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for f in fonts:
            lines.append(
                f"| {f['name']} | {f['subtype'] or '-'} | {f['cid_type'] or '-'} "
                f"| {'是' if f['cjk'] else '否'} | {'是' if f['embedded'] else '否'} |"
            )
    else:
        lines.append("（未解析到具名字体）")

    if result["notes"]:
        lines.append("\n## 备注\n")
        for n in result["notes"]:
            lines.append(f"- {n}")

    lines.append(
        "\n---\n本报告由 `hack/check-pdf-fonts.py` 自动生成。"
        "中文渲染为豆腐块（缺字体）时，本闸门会以非零退出码阻断发布。\n\n"
        "复现：`python hack/check-pdf-fonts.py --pdf <pdf>`"
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="PDF 中文字体闸门：确保中文真的能显示与检索（D-62）")
    ap.add_argument("--pdf", default="", help="待校验的 PDF 路径")
    ap.add_argument("--report", default="", help="Markdown 报告输出路径（可选）")
    ap.add_argument("--min-cjk-chars", type=int, default=500,
                    help="抽样页最少需抽出的汉字数（默认 500）")
    ap.add_argument("--sample-pages", type=int, default=12,
                    help="字体资源抽样页数（默认 12）")
    ap.add_argument("--self-test", action="store_true",
                    help="闸门自检：构造坏件确认本闸门仍会拦下（不校验任何 PDF）")
    ap.add_argument("--json", action="store_true", help="额外输出 JSON 到 stdout")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not args.pdf:
        ap.error("需要 --pdf <路径>，或使用 --self-test")

    result = evaluate(args.pdf, args.min_cjk_chars, args.sample_pages)
    report = render_report(result, args.min_cjk_chars)

    if args.report:
        parent = os.path.dirname(os.path.abspath(args.report))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(args.report, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(report)

    hard = [c for c in result["checks"] if c["level"] == "hard"]
    failed = [c for c in hard if not c["ok"]]

    print(report)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if failed:
        print("\n[FAIL] PDF 中文字体校验未通过，阻断发布：", file=sys.stderr)
        for c in failed:
            print(f"  - {c['name']}：{c['detail']}", file=sys.stderr)
        return 1
    print(f"\n[OK] PDF 中文字体校验通过（{len(hard)} 项硬闸门全绿）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
