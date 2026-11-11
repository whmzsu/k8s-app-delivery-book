#!/usr/bin/env python3
"""清理正文中读者不可见的内部标记（P6 出书面 / D-43）。

四类残留：
  1. 仓库内部写作资产路径  `book/decisions.md` / `book/checklist-master.md` /
     `book/case-evolution.md` / `book/hooks.md` / `book/glossary.md` /
     `book/concept-ladder.md` —— 读者手上没有这个仓库。
  2. 强耦合对编号 `SP-NN`（21 对跨章口径约束的内部编号）。
  3. 裁决编号 `D-NN`（写作期决策记录编号）。
  4. 未决项编号 `U-NN`（写作期待定项编号）。

处理原则（不留空洞、不伤论证）：
  - 括号内只起溯源作用的编号 → 连括号一起删；括号里还有正文语义（如「见第 17 章」）→
    只删编号、保留语义。
  - 句中作主语的编号（如「SP-19 要求……」「D-01 划定边界」）→ 换成读者能懂的主体
    （「第 17 章的 requests 基线」「第 6 章的边界划定」）。
  - `book/xxx.md` → 换成书内可指向的锚点（配置契约 → 第 6 章；检查清单 → CL 编号本身；
    钩子清单 → 第 1 章；选型基线 → 本书选型基线）。

用法：
    python hack/strip-internals.py --dry-run   # 打印每条规则命中数与剩余残留，不写盘
    python hack/strip-internals.py             # 执行
    python hack/strip-internals.py --check     # 只检测残留（CI 用）
"""

from __future__ import annotations

import glob
import re
import sys

CHAPTERS = sorted(glob.glob("chapters/ch*.md"))

# ---------------------------------------------------------------- 规则表
# 顺序敏感：先处理带语义的完整短语，再用兜底规则收尾。
RULES: list[tuple[str, str]] = [
    # ---- 1. 章末「依据与延伸阅读」前注里的仓库路径（31 章各一处）----
    (
        r"> 按 D-09：本列表不写裸 URL；完整链接、访问日期与归档地址见 `references/ch\d+\.yaml`，全书汇总见附录 I。正文角标与下列编号逐一对应。",
        "> 本节不写裸 URL：完整链接、访问日期与归档地址统一收在附录 I，正文角标与下列编号逐一对应。",
    ),
    # ---- 2. 检查清单「母版」说法（31 章各一处）----
    (
        r"母版编号引用见 `book/checklist-master\.md`，",
        "检查项编号全书统一（形如 `CL-08-03`），",
    ),
    (
        r"母版编号见 `book/checklist-master\.md`，",
        "检查项编号全书统一（形如 `CL-08-03`），",
    ),
    # ---- 3. book/decisions.md ----
    (r"按 `book/decisions\.md` 的 U-05 与配置契约", "按本书选型基线与配置契约"),
    (r"`book/decisions\.md` 的 U-05 与配置契约", "本书选型基线与配置契约"),
    (r"`book/decisions\.md` U-05 钉死", "本书选型基线钉死"),
    (r"`book/decisions\.md` U-05 把", "本书选型基线把"),
    (r"按 `book/decisions\.md` U-04，", "按本书选型基线，"),
    (r"`book/decisions\.md` U-05 的固定值", "本书选型基线的固定值"),
    (r"按 `book/decisions\.md` 的「唯一示例实现」原则", "按「唯一示例实现」原则"),
    (r"按 `book/decisions\.md` 的\*\*唯一示例实现\*\*", "按本书的**唯一示例实现**"),
    (r"按 `book/decisions\.md` 的单一示例实现原则", "按单一示例实现原则"),
    (r"按 `book/decisions\.md` 与第 4 章固定值", "按本书选型基线与第 4 章固定值"),
    (r"`book/decisions\.md` 已把", "本书选型基线已把"),
    (r"`book/decisions\.md` 把", "本书选型基线把"),
    (r"`book/decisions\.md`「Helm 作对外分发 Chart」的边界", "「Helm 作对外分发 Chart」的边界"),
    (r"`book/decisions\.md` 的固定值", "本书选型基线的固定值"),
    (r"按 `book/decisions\.md`：", "按本书选型基线："),
    (r"按 `book/decisions\.md`，", "按本书选型基线，"),
    (r"按 `book/decisions\.md` 的", "按本书选型基线的"),
    (r"按 `book/decisions\.md`", "按本书选型基线"),
    (r"`book/decisions\.md`", "本书选型基线"),
    # ---- 4. book/case-evolution.md ----
    (r"`book/case-evolution\.md` 配置契约", "配置契约"),
    (r"`book/case-evolution\.md` 的配置契约", "配置契约"),
    (r"`book/case-evolution\.md` 契约", "配置契约"),
    (r"`book/case-evolution\.md` 冻结字段", "配置契约的冻结字段"),
    (r"`book/case-evolution\.md` 的组成表", "配置契约的组成表"),
    (r"`book/case-evolution\.md` 第五节", "配置契约"),
    (r"`book/case-evolution\.md` 第二节", "配置契约"),
    (r"见 `book/case-evolution\.md`", "见第 6 章配置契约"),
    (r"`book/case-evolution\.md`", "配置契约"),
    # ---- 5. book/hooks.md ----
    (r"`book/hooks\.md` 及大纲章号一致", "第 1 章的钩子清单及章号一致"),
    (r"`book/hooks\.md` 第一节完全一致", "第 1 章的钩子清单完全一致"),
    (r"按 `book/hooks\.md` 9\.7", "按 9.7 的钩子分配原则"),
    (r"`book/hooks\.md` / 大纲章号", "第 1 章钩子清单 / 章号"),
    (r"`book/hooks\.md`", "第 1 章的钩子清单"),
    # ---- 6. glossary / concept-ladder ----
    (
        r"（`book/glossary\.md` 把它与 CI 里的静态扫描明确区分：静态扫描不叫准入）",
        "（本书把它与 CI 里的静态扫描明确区分：静态扫描不叫准入）",
    ),
    (r"按 `book/concept-ladder\.md`，", "按本书的概念梯度安排，"),
    # ---- 7. U-NN 未决项 ----
    (r"按 U-05 硬要求，", "按选型基线的硬要求，"),
    (r"按 U-05 定唯一入口", "按选型基线定唯一入口"),
    (r"是 U-05 固定值", "是配置契约固定值"),
    (r"为 U-05 固定值", "为配置契约固定值"),
    (r"按 U-05，", "按本书选型基线，"),
    (r"按 U-05 ", "按本书选型基线 "),
    (r"与 `book/decisions\.md` U-05 ", "与本书选型基线 "),
    # ---- 8. D-NN（除 D-09）----
    (r"（D-01）", ""),
    (r"按 D-06 裁决，", "按本书的引用取舍，"),
    (r"按 D-02，合成案例不得冒充真实事件", "按合成案例约定，不得冒充真实事件"),
    (r"按 D-02 不得冒充真实事件", "按合成案例约定不得冒充真实事件"),
    (r"按 D-06 裁决", "按本书的引用取舍"),
    (r"（D-08）", ""),
    (r"，见 D-29）", "）"),
    (r"（D-08，避免两章各选一套）", "（单一示例实现原则，避免两章各选一套）"),
    (r"D-08 单一示例实现：避免两章各选一套导致示例跑不通。", "单一示例实现：避免两章各选一套导致示例跑不通。"),
    (r"（避免两章各选一套，D-08）", "（单一示例实现，避免两章各选一套）"),
    (r"随 D-08 的单一示例实现登记一起评审", "随单一示例实现登记一起评审"),
    (r"D-01 划定边界，本章不越界", "第 6 章的边界划定，本章不越界"),
    (r"D-01 裁决把这三件事全部从第 6 章挪到本章", "这三件事被刻意从第 6 章挪出、全部归到本章"),
    (r"先把因果摆正（D-02）：", "先把因果摆正："),
    (r"> 边界声明（D-02）：", "> 边界声明："),
    # D-10：待核验链接的登记口径（11 处，句中带内部字段名）
    (
        r"标注「链接待核验」者按 D-10 在 YAML 里记 `pending_url`，不编造链接。",
        "标注「链接待核验」者不写猜测地址，核验通过后再补。",
    ),
    # D-09 的其他变体（ch29 句序不同，先兜底再统一）
    (r"> 按 D-09：本列表不写裸 URL；完整链接见附录 I，全书汇总见附录 I。", "> 本节不写裸 URL：完整链接与归档见附录 I。"),
    (r"> 按 D-09：本列表不写裸 URL；", "> 本节不写裸 URL："),
    (r"按 D-09：", ""),
    # ---- 8b. SP-NN 句中作主语（括号规则管不到的，逐条换成读者可见主体）----
    (r"口径一致性由 SP-02 约束", "口径一致性由第 1、3、20 章共同约束"),
    (r"这是 SP-01 的验收点", "这是第 6 章最小闭环的验收点"),
    (r"SP-01 在命令层面成立", "第 6 章的最小闭环在命令层面成立"),
    (r"这是 SP-01 在打包层的延续", "这是第 6 章最小闭环在打包层的延续"),
    (r"SP-12 要求的多环境前提", "多环境隔离的前提"),
    (r"这正是 SP-19 把基线设为冻结字段的原因", "这正是 requests 基线被设为冻结字段的原因"),
    (r"SP-19 的具体含义就在这里", "这条跨章约束的具体含义就在这里"),
    (r"最后一项是 SP-19 的闸门", "最后一项是 requests 基线这道闸门"),
    (r"这张表是 SP-09、SP-15 的落点", "这张表是统一指标名与流量路由两处口径的落点"),
    (r"SP-09 要求第 15、20、22、23 章逐字引用同一指标名", "第 15、20、22、23 章必须逐字引用同一指标名"),
    (r"按 SP-09 回写第 22 章规则", "按统一指标名回写第 22 章规则"),
    (r"签名步骤按 SP-18 唯一归属本章", "签名步骤唯一归属本章"),
    (r"也是 SP-21 要求的「何时不该用」", "也回应第 5 章「何时不该用」的要求"),
    (r"与第 11 章的分工见 SP-16，", "与第 11 章分工明确，"),
    (r"SP-08 要求两章口径不冲突", "第 9 章与本章口径必须一致"),
    (r"SP-08 的两章口径因此一致", "两章口径因此一致"),
    (r"这就是 SP-06「同源」在控制器上的具体形态", "这就是「同源」在控制器上的具体形态"),
    # ---- 8c. U-05 的剩余变体（顺序在 decisions.md 之后）----
    (r"的 U-05 与 `case-evolution\.md` 第五节固定值", "与配置契约固定值"),
    (r"本章 U-05 固定的", "本章配置契约固定的"),
    (r"`book/decisions\.md` 的 U-05", "本书选型基线"),
    # ---- 9. references/chNN.yaml 单章路径 ----
    (r"见 `references/ch\d+\.yaml` 的 (R-\d+-\d+) 支撑说明", r"见附录 I 的 \1 支撑说明"),
    (r"见 references/ch\d+\.yaml 的 (R-\d+-\d+) 支撑说明", r"见附录 I 的 \1 支撑说明"),
    (r"完整链接与归档在 `references/chNN\.yaml`，汇总见附录 I", "完整链接与归档见附录 I"),
    (r"本章 `references/ch\d+\.yaml` 无对应登记条目", "本章无对应登记条目"),
    (r"见 `references/ch\d+\.yaml`", "见附录 I"),
    # ---- 9b. 「母版」是写作期对检查清单母表的叫法 ----
    (r"母版", "通用项"),
    # ---- 9c. 替换后遗留的多余空格（删掉路径会留下一个空格）----
    (r"(沿用|按|见|取|正是|对应|是) (配置契约|本书选型基线|第 1 章的钩子清单)", r"\1\2"),
    (r"本书选型基线 钉死", "本书选型基线钉死"),
    (r"本书选型基线 固定值", "本书选型基线固定值"),
    (r"本书选型基线 ([取把与定的])", r"本书选型基线\1"),
    # ---- 9d. 裸文件名（原本就没带 book/ 前缀的引用）----
    (r"计数口径与 `glossary\.md` 第二节、第 3 章一致", "计数口径与第 3 章的公理表一致"),
    (r"计数口径与 `glossary\.md` 第二节一致", "计数口径与本章 3.2 的公理表一致"),
    (r"取自 `glossary\.md` 与 `concept-ladder\.md`", "取自附录 E 术语表与本书的概念梯度"),
    (r"（hooks\.md 原句）", "（第 1 章原句）"),
    (r"见 case-evolution\.md 的 tag 命名", "见附录 D 的 tag 命名"),
    (r"`case-evolution\.md` 的配置契约", "配置契约"),
    (r"沿用 `decisions\.md`", "沿用本书选型基线"),
    (r"取 `decisions\.md`：", "取本书选型基线："),
    (r"（`decisions\.md`）", "（本书选型基线）"),
    (r"与 第 1 章的钩子清单 一致", "与第 1 章的钩子清单一致"),
    (r"`decisions\.md`", "本书选型基线"),
    (r"`case-evolution\.md`", "配置契约"),
    # ---- 10. chapters/ 路径 ----
    (r"按 `chapters/ch01\.md` 1\.4 的版本基线", "按第 1 章 1.4 的版本基线"),
]


def strip_sp(text: str) -> tuple[str, int]:
    """消解 SP-NN：括号内的删编号（保留括号内其它语义），空壳括号整体删除。"""
    n0 = len(re.findall(r"SP-\d+", text))

    def repl_paren(m: re.Match[str]) -> str:
        inner = m.group(1)
        # 去掉 SP-NN 及其相邻的分隔符
        inner = re.sub(r"SP-\d+", "", inner)
        inner = re.sub(r"^[\s、，,/／]+|[\s、，,/／]+$", "", inner)
        inner = re.sub(r"([、，,/／])\s*(?=[、，,/／])", "", inner)
        return f"（{inner}）" if inner else ""

    text = re.sub(r"（([^（）]*SP-\d+[^（）]*)）", repl_paren, text)
    return text, n0


def main() -> int:
    dry = "--dry-run" in sys.argv
    check = "--check" in sys.argv

    if check:
        bad = []
        for path in CHAPTERS:
            with open(path, encoding="utf-8") as fh:
                t = fh.read()
            hits = re.findall(r"SP-\d+|D-\d\d|U-0\d|book/[a-z-]+\.md", t)
            if hits:
                bad.append(f"{path}: {len(hits)} 处 {sorted(set(hits))[:6]}")
        if bad:
            print("内部标记残留：")
            for b in bad:
                print("  " + b)
            return 1
        print(f"OK：{len(CHAPTERS)} 章正文无内部标记")
        return 0

    total = 0
    per_rule = [0] * len(RULES)
    sp_total = 0
    out: dict[str, str] = {}

    for path in CHAPTERS:
        with open(path, encoding="utf-8") as fh:
            t = fh.read()
        for i, (pat, rep) in enumerate(RULES):
            t, k = re.subn(pat, rep, t)
            per_rule[i] += k
        t, k = strip_sp(t)
        sp_total += k
        out[path] = t

    for i, ((pat, rep), k) in enumerate(zip(RULES, per_rule)):
        if k:
            total += k
            print(f"  [{k:3d}] {pat[:78]}")
    print(f"  [{sp_total:3d}] SP-NN（括号消解）")
    total += sp_total

    residual = []
    for path, t in out.items():
        for m in re.finditer(r"SP-\d+|D-\d\d|U-0\d|book/[a-z-]+\.md", t):
            residual.append((path, m.group(0), t[max(0, m.start() - 40): m.end() + 40].replace("\n", " ")))

    print(f"\n规则命中 {total} 处；待人工处理残留 {len(residual)} 处")
    for path, tok, ctx in residual:
        print(f"  {path.split('/')[-1]:10s} {tok:14s} …{ctx.strip()}…")

    if dry:
        print("\n[dry-run] 未写盘")
        return 0

    for path, t in out.items():
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(t)
    print(f"\n已写回 {len(out)} 章")
    return 0


if __name__ == "__main__":
    sys.exit(main())
