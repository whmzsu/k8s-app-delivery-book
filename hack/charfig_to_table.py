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
    ("ch14.md", "这次生产变更，Git 里是否有一个对应的 commit", """| 级 | 判据（逐级放行） | 不通过 → 结论 |
|---|---|---|
| 1 | 这次生产变更，Git 里是否有一个对应的 commit？ | 不是 GitOps，回到 14.5 应急流程 |
| 2 | 控制器是否周期性比对 Git 与集群（非仅 Webhook 触发一次）？ | 只是「Git 触发的部署」，不算 GitOps |
| 3 | 有人在 prod 手工改一个字段，是否会被纠正或标记 `OutOfSync`？ | 缺漂移纠正，H7 风险仍在 |
| 4 | PR 里能否直接 diff 出「最终提交给集群的那份清单」？ | 选 14.3 的仓库内渲染模式 |
| — | 四问全过 | GitOps 成立；此时方可进入第 15 章讨论流量怎么灰度 |"""),

    ("ch15.md", "是否有可查询的用户可感指标", """| 级 | 判据（按序自问） | 命中 → 去处 |
|---|---|---|
| 1 | 是否有可查询的用户可感指标（错误率 / 延迟分位）？ | **否** → 不要开自动判定，退回按副本比例手动分批；先补第 21 章可观测栈。**是** → 进入第 2 级 |
| 2 | 需要精确按请求比例（如精确 5%）或按 header 定向切流吗？ | **是** → Gateway API + Envoy Gateway traffic router 插件路径（15.4）；**否** → 按副本比例金丝雀退化方案（不依赖流量插件，15.4）。两条路都进第 3 级 |
| 3 | 阈值、冷却、人工门禁是否按业务风险设定并演练过自动回滚？ | **是** → 渐进式交付成立，发布由指标决定是否继续；**否** → 禁止开启自动回滚，只保留指标观测 |"""),

    ("ch16.md", "这次发布改动了数据格式吗", """| 级 | 判据（按序自问） | 命中 → 去处 |
|---|---|---|
| 1 | 这次发布改动了数据格式吗？ | **否** → 回第 13 章，按容量与回退速度选策略。**是** → 进入第 2 级 |
| 2 | 是否包含破坏性 DDL（DROP / 改类型 / 拆分）？ | **是** → 禁止随发布执行，改走 expand–contract 四阶段。**否**（纯加列 / 加索引）→ 进入第 3 级 |
| 3 | ①②③ 每一步是否都验证了新旧版本可共存？ | **否** → 停在 expand，不许往下。**是** → 进入第 4 级 |
| 4 | 观察窗口结束、旧列零写入、本次备份已完成？ | **否** → 不做 contract，保留共存状态。**是** → 才允许执行 `V4__contract.sql`；此后应用侧回滚不再覆盖这一变更 |"""),

    ("ch17.md", "这个 Pod 的每个容器都写了 requests", """| 级 | 判据（按序自问） | 命中 → 去哪 |
|---|---|---|
| 1 | 这个 Pod 的每个容器都写了 `requests`？ | **否** → 补 `requests`；命名空间加 `LimitRange` 兜底（17.4）。**是** → 进入第 2 级 |
| 2 | 组件是在线、对尾延迟敏感？ | **是** → 只保留 CPU `requests`，放宽 / 去掉 CPU limit（本书观点）。**否**（离线 / 批处理）→ 进入第 3 级 |
| 3 | 内存是否需要硬上限？ | **是** → 设 memory limit，并按 17.5 的 OOM 演练验证。**否** → 进入第 4 级 |
| 4 | 是否要拿到 Guaranteed？ | **是** → 所有容器所有资源 `requests == limits`（代价：调度容量）。**否** → Burstable，用 `PriorityClass` 区分在线 / 离线驱逐顺序（17.4） |
| — | 无论落到哪一支 | 用分位数压测曲线复核，把 P99 与 limit 之间留出突发余量 |"""),

    ("ch18.md", "副本是否跨", """| 级 | 判据（按序自问） | 命中 → 动哪一层 |
|---|---|---|
| 1 | 副本是否跨 ≥ 2 个可用区？ | **否** → `topologySpreadConstraints`（18.4），先解决「稳」。**是** → 进入第 2 级 |
| 2 | 扩缩信号来自「Pod 负载」还是「外部队列」？ | **队列 / 事件** → KEDA 2.x `ScaledObject`（18.4）。**Pod 负载** → 进入第 3 级 |
| 3 | 是否需要长期把 `requests` 调准？ | **是** → VPA 1.x，用 `Off` / `Initial`，不与 HPA 同改 CPU。**否** → HPA（`autoscaling/v2` + `behavior` 冷却窗口） |
| 4 | 扩容后节点够不够？ | **否** → Karpenter 1.x / Cluster Autoscaler 1.x（节点层）。**是** → 进入第 5 级 |
| 5 | 有没有按组件 / 环境的成本归因？ | **否** → 先建归因口径，再谈任何「省钱」动作（本书观点）。**是** → 联动第 20 章错误预算决定能否缩容 |"""),

    ("ch19.md", "需要东西向 mTLS / 细粒度流量策略 / 统一遥测", """| 级 | 判据（按序自问） | 命中 → 结论 |
|---|---|---|
| 1 | 需要东西向 mTLS / 细粒度流量策略 / 统一遥测？ | **否** → 不上网格：Gateway API + NetworkPolicy 已够。**是** → 进入第 2 级 |
| 2 | 团队能承担数据面运维成本（注入、升级、资源、排障）？ | **否** → 不上网格：先用 Gateway API 超时 / 重试 + NetworkPolicy。**是** → 进入第 3 级 |
| 3 | 入口实现是否已统一且不与网格冲突？ | **否** → 先按选型基线定唯一入口（eg），再评估。**是** → 上网格；但重试 / 超时仍只在一层配置，不叠三层 |"""),
]

# 引言句改写：把「决策树」换成「判定表 / 放行表」，保持叙述自洽
SENTENCES = [
    ("ch14.md", "**决策树**——用来判断一个团队", "**判定表**——用来判断一个团队"),
    ("ch15.md", "**决策树**：", "**判定表**（先确认有没有判据，再选切流方式，最后确认门禁）："),
    ("ch16.md", "**决策树**：", "**判定表**（数据格式先行：改不动数据就别谈策略）："),
    ("ch17.md", "**决策树**（判断一个工作负载的资源该怎么填）：", "**判定表**（一个工作负载的资源该怎么填）："),
    ("ch18.md", "**决策树**（判断该动哪一层）：", "**判定表**（该动哪一层）："),
    ("ch19.md", "**「该不该上网格」决策树**：", "**「该不该上网格」判定表**："),
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
