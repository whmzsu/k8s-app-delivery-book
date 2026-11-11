#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把字符决策树/目录树整块替换为表格（锚点定位，不做空白匹配）。

用法：python hack/charfig_to_table.py            # 执行
      python hack/charfig_to_table.py --dry-run  # 只报告命中，不写入

为什么用锚点而不是直接改文本：ASCII 图内部有大量对齐空格，靠字符串精确匹配
极易因一个空格失败；这里只要求锚点在某个 fenced 块内出现，整块替换。
"""
import re
import sys

CHAPTERS = "chapters"

# (文件, 锚点, 替换后的 Markdown)  —— 每个锚点必须只命中一个 fenced 块
BLOCKS = [
    ("ch08.md", "滚动期间连续请求 5xx 是否为 0", """| 级 | 判据（逐级放行） | 不通过 → 去处 |
|---|---|---|
| 1 | 滚动期间连续请求 5xx 是否为 0？ | 先查 readiness 是否永不失败 / preStop 是否缺失（8.4） |
| 2 | 新 Pod 是否在 startup 保护后才被 liveness 接管？ | 补 startupProbe（8.4） |
| 3 | 旧 Pod 是否在 Endpoint 摘除后才退出？ | 补 preStop 与终止宽限（8.4） |
| 4 | PDB 是否只在自愿中断时生效、未被误当兜底？ | 修正认知，容量账回第 13 章（8.2） |
| — | 四条件全成立 | 可以带着探针基线进入第 9 章 |"""),

    ("ch09.md", "这个值泄露后是否需要", """| 级 | 判据（按序自问） | 命中 → 归属 |
|---|---|---|
| 1 | 这个值泄露后是否需要「轮换 + 吊销 + 留审计」？ | **是** → 外部密钥系统（本章用 ESO + vault） |
| 2 | 这个值是否随环境变化、且改它需要重建镜像吗？ | **是** → ConfigMap（`immutable: true` + 版本后缀） |
| — | 两个都否 | 属于产物标识（如 `APP_VERSION`），随镜像标签一起变，不进 ConfigMap（第 6 章已如此处理 [R-09-9]） |"""),

    ("ch10.md", "这份配置只给同一个团队", """| 级 | 判据（按序自问） | 命中 → 选什么 |
|---|---|---|
| 1 | 这份配置只给同一个团队、发 2–3 个同源环境？ | **是** → Kustomize 5.x overlay（无模板 patch） |
| 2 | 需要打包、版本化、发给别的团队 / 外部用户？ | **是** → Helm 4.x Chart（模板 + 包管理 + release 状态） |
| 3 | 是大规模平台、需要类型检查 / 复用逻辑 / 多语言生成？ | **是** → Jsonnet / CDK8s 代码生成 |
| — | 三个都否 | 保持裸清单，不要引入任何模板层（第 6 章的做法） |"""),

    ("ch11.md", "kustomize build 能否产出渲染产物", """| 级 | 判据（逐级放行） | 不通过 → 去处 |
|---|---|---|
| 前置 | `kustomize build` 能否产出渲染产物？ | 第 10 章 render-diff（见第 10 章） |
| 1 | 第 1 层 `kubeconform -strict` 通过？ | 字段 / 类型 / schema 错误，按报错改清单 |
| 2 | 第 2 层 `conftest` 通过？ | 组织策略违规，按规则名改清单 |
| 3 | 第 3 层 `kuttl` 断言终态通过？ | 行为未收敛，查探针 / 副本数（见第 8 章） |
| 4 | 第 4 层 1.32 / 1.33 / 1.34 三个 job 全绿？ | 版本偏差，按 `matrix.k8s` 定位并锁附录 A |
| — | 四层齐备 | 可以带着这份清单进入第 12 章流水线 |"""),

    ("ch12.md", "这次变更改动了源码 / Dockerfile 吗", """| 级 | 判据（按序自问） | 命中 → 动作 |
|---|---|---|
| 1 | 这次变更改动了源码 / Dockerfile 吗？ | **是** → 走 build job，产出唯一 digest，记录到制品清单 |
| 2 | 只改了配置 / 文档 / 工作流文件吗？ | **是** → 不重建镜像，只更新配置清单（见第 9、14 章） |
| 3 | build job 是否只在 push 到主干时触发一次？ | **否** → 收敛触发条件，禁止每个环境各跑一遍 |
| 4 | promote 脚本里是否出现 `docker build` / `buildx`？ | **是** → 删掉，改为 `set image` 引用（12.4） |
| 5 | `uses:` 是否全部锁定到 40 位 SHA？ | **否** → 执行 `hack/pin-actions.sh` 并提交（12.4） |
| 6 | job 顺序是否为 lint → 单测 → 集成 → 构建 → 校验 → 推送？ | **否** → 按下方阶段表重排，越晚发现的错误越贵 [R-12-6] |
| — | 六条都过 | 一次构建成立，产物可进入第 13 章的发布策略选择 |"""),

    ("ch13.md", "这次发布改动了数据格式 / schema 吗", """| 级 | 判据（按序自问） | 命中 → 选什么 |
|---|---|---|
| 1 | 这次发布改动了数据格式 / schema 吗？ | **是** → 先做第 16 章 expand–contract，否则任何策略的回滚都是假回滚 |
| 2 | 有可测量的用户可感指标（错误率 / 延迟分位）吗？ | **否** → 不要选金丝雀，先补 SLI（见第 20 章） |
| 3 | 需要秒级整体回退且有双倍容量吗？ | **是** → 蓝绿（保留旧版本到观察窗口结束） |
| 4 | 需要按指标决定继续还是自动回退吗？ | **是** → 金丝雀 / 渐进式交付（详见第 15 章） |
| — | 以上都不命中 | 滚动更新（默认）：先填容量计算表，再写回滚方案，两者都通过才允许发布 |"""),
]

# 引言句改写：把「决策树」换成「判定表 / 放行表」，保持叙述自洽
SENTENCES = [
    ("ch08.md", "由这四张表可以直接得到一棵判「发布能不能算零停机」的决策树：",
     "由这四张表可以直接得到一张判「发布能不能算零停机」的放行表："),
    ("ch10.md", "决策树的第 5 分支（保持裸清单）不是弃权",
     "判定表里「保持裸清单」那一支不是弃权"),
    ("ch10.md", "由「谁在用这份配置」直接得到一棵决策树：",
     "由「谁在用这份配置」直接得到一张判定表："),
    ("ch11.md", "**一棵可判定的验证决策树**：", "**一张可判定的验证放行表**："),
    ("ch12.md", "由这四个判据得到一棵决策树。它的用途不是「设计流水线」",
     "由这四个判据得到一张判定表。它的用途不是「设计流水线」"),
    ("ch13.md", "**决策树**：", "**判定表**（先数据、再指标、最后策略）："),
]


def main(dry):
    ok, bad = 0, []
    for fname, anchor, table in BLOCKS:
        path = "%s/%s" % (CHAPTERS, fname)
        text = open(path, encoding="utf-8").read()
        hits = []
        for m in re.finditer(r"^```[^\n]*\n(.*?)^```", text, re.S | re.M):
            if anchor in m.group(1):
                hits.append(m)
        if len(hits) != 1:
            bad.append((fname, anchor, "命中 %d 个块" % len(hits)))
            continue
        m = hits[0]
        if not dry:
            text = text[:m.start()] + table + text[m.end():]
            open(path, "w", encoding="utf-8", newline="\n").write(text)
        ok += 1
    for fname, old, new in SENTENCES:
        path = "%s/%s" % (CHAPTERS, fname)
        text = open(path, encoding="utf-8").read()
        if old not in text:
            bad.append((fname, old[:20], "引言句未命中"))
            continue
        if not dry:
            open(path, "w", encoding="utf-8", newline="\n").write(text.replace(old, new, 1))
    print("块替换 %d 处；问题 %d 处" % (ok, len(bad)))
    for b in bad:
        print("  !", b)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
