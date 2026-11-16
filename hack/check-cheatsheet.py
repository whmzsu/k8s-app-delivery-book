#!/usr/bin/env python3
"""速查图 SVG 静态校验（附录 J.9 第 3 步的前两步）。

三项检查：
  1. XML 合法、viewBox 为 A4 竖版 1240×1680；
  2. 文本宽度估算无左右边界溢出（CJK=1em / ASCII=0.55em / 等宽=0.62em）；
  3. 版式必备字段：页眉章号、页脚 VERSION、页脚「速查附件 · 不进正文插图计数」。

注意：本工具只做静态检查，Edge/Chromium 实渲染目视确认仍需人工执行（J.9 第 3 步）。
"""
import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "{http://www.w3.org/2000/svg}"
RIGHT_MARGIN = 1225   # 画布 1240，右侧留 15px 安全边
LEFT_MARGIN = 10


def est_width(text: str, font_size: float, mono: bool) -> float:
    """保守估算文本宽度：CJK 全角按 1em，等宽 ASCII 0.62em，其余 ASCII 0.55em。"""
    w = 0.0
    for ch in text:
        if ord(ch) > 0x2e80:
            w += font_size
        elif mono:
            w += font_size * 0.62
        else:
            w += font_size * 0.55
    return w


def check(path: Path, version: str) -> int:
    problems = []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        print(f"[FAIL] {path.name}: XML 解析失败: {exc}")
        return 1

    vb = root.get("viewBox", "")
    if vb != "0 0 1240 1680":
        problems.append(f"viewBox 应为 0 0 1240 1680，实际 {vb!r}")

    texts = root.findall(f".//{NS}text")
    overflow = []
    for node in texts:
        raw = "".join(node.itertext()).strip()
        if not raw:
            continue
        x = float(node.get("x", 0))
        fs = float(node.get("font-size", 12))
        mono = "monospace" in (node.get("font-family") or "")
        w = est_width(raw, fs, mono)
        anchor = node.get("text-anchor")
        if anchor == "end":
            if x - w < LEFT_MARGIN:
                overflow.append((raw[:48], round(x - w, 1), "LEFT"))
        elif x + w > RIGHT_MARGIN:
            overflow.append((raw[:48], round(x + w, 1), "RIGHT"))
    if overflow:
        problems.append(f"文本溢出 {len(overflow)} 处：" + "; ".join(
            f"[{t}] x_end={e} {d}" for t, e, d in overflow[:5]))

    raw_text = path.read_text(encoding="utf-8")
    for needle in (f"v{version}", "速查附件", "不进正文插图计数"):
        if needle not in raw_text:
            problems.append(f"缺少必备字段 {needle!r}（页眉/页脚或 VERSION 未同步）")
    if not re.search(r"第\s*\d+\s*章", raw_text):
        problems.append("页眉缺少章号")

    if problems:
        print(f"[FAIL] {path.name}")
        for p in problems:
            print("   - " + p)
        return 1
    print(f"[PASS] {path.name}: XML OK · {len(texts)} text 节点 0 溢出 · viewBox/版本/页脚齐全")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="速查图 SVG 静态校验（J.9）")
    ap.add_argument("svg", nargs="+", help="待校验的 SVG 路径")
    ap.add_argument("--version", default="", help="期望版本号（默认读根目录 VERSION）")
    args = ap.parse_args()

    version = args.version or Path(__file__).resolve().parent.parent.joinpath(
        "VERSION").read_text(encoding="utf-8").strip()
    bad = sum(check(Path(p), version) for p in args.svg)
    print(f"\n结果：{len(args.svg) - bad}/{len(args.svg)} 通过 · 期望版本 v{version}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
