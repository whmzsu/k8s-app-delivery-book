#!/usr/bin/env python3
"""同步正文：来源替换后的依据段标题 + 行文里的描述性措辞。

`hack/fix-ref-metadata.py` 换掉了 11 处引用源的标题与机构，正文里
「依据与延伸阅读」的条目行与散落行文的描述必须跟着改，否则读者会看到
「公开的流水线配置失误复盘」指向一份 CI 服务商被攻破的报告。

用法：python hack/sync-ref-titles.py [--dry-run]
"""

from __future__ import annotations

import glob
import re
import sys

import yaml

# 换过来源的编号：依据段第 2、3 段按 yaml 重建
RETITLED = [
    "R-12-9", "R-13-9", "R-14-12", "R-15-12", "R-16-10",
    "R-22-7", "R-23-8", "R-24-9", "R-26-11", "R-29-12", "R-31-7",
    # SRE / 白皮书章节化，标题也变了
    "R-08-8", "R-13-7", "R-16-8", "R-17-6", "R-18-9", "R-19-8",
    "R-23-6", "R-26-10",
]

# 行文中的描述性措辞：换成与新来源相符的说法
PROSE = [
    ("参照公开的流水线配置失误与供应链复盘 [R-12-9]",
     "参照公开的 CI 供应链与凭据外泄复盘 [R-12-9]"),
    ("参照公开发布 / 回滚失败事故复盘 [R-13-9]",
     "参照公开的配置变更致全局中断、靠回滚恢复的复盘 [R-13-9]"),
    ("参照公开配置漂移 / 手工变更事故复盘 [R-14-12]",
     "参照公开的手工变更事故复盘 [R-14-12]；配置漂移的判定口径见 14.2 的三要素"),
    ("参照公开渐进式交付 / 自动回滚事故复盘 [R-15-12]",
     "参照公开的「未分批放量导致全局失效」复盘 [R-15-12]"),
    ("参照公开数据迁移事故复盘 [R-16-10]",
     "参照公开的数据一致性受损与恢复复盘 [R-16-10]"),
    ("失效模式的方法论参照公开复盘 [R-16-10]",
     "失效模式的方法论参照公开的恢复失效复盘 [R-16-10]"),
    ("公开的软件供应链与容器逃逸复盘反复印证",
     "公开的供应链攻击案例目录反复印证"),
    ("以上反模式的**方法论**参照公开 Operator 升级事故复盘 [R-29-12]",
     "以上反模式的**方法论**参照公开复盘索引中控制器升级类案例 [R-29-12]"),
    ("方法论参照公开 Operator 升级事故复盘 [R-29-12]",
     "方法论参照公开复盘索引中控制器升级类案例 [R-29-12]"),
]


def load_titles() -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for p in sorted(glob.glob("references/ch*.yaml")):
        for e in yaml.safe_load(open(p, encoding="utf-8")) or []:
            if e.get("id") in RETITLED:
                out[e["id"]] = (e.get("title", ""), e.get("author_or_org", ""))
    return out


def main() -> int:
    dry = "--dry-run" in sys.argv
    titles = load_titles()
    n_bullet = n_prose = 0
    for path in sorted(glob.glob("chapters/ch*.md")):
        text = open(path, encoding="utf-8").read()
        orig = text
        for rid, (title, org) in titles.items():
            pat = re.compile(rf"(?m)^(- \*\*\[{rid}\] L\d\*\*｜)([^｜]*)｜([^｜]*)｜")
            def rep(m):
                return f"{m.group(1)}{title}｜{org}｜"
            text, k = pat.subn(rep, text)
            n_bullet += k
        for old, new in PROSE:
            if old in text:
                k = text.count(old)
                text = text.replace(old, new)
                n_prose += k
        if text != orig:
            if not dry:
                open(path, "w", encoding="utf-8", newline="\n").write(text)
            print(f"  更新 {path.split('/')[-1]}")
    print(f"依据段 {n_bullet} 行 / 行文 {n_prose} 处" + ("（dry-run）" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
