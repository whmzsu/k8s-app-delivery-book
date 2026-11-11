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
    ("ch20.md", "本周剩余预算 > 0", """| 级 | 判据（按序自问） | 命中 → 去处 |
|---|---|---|
| 1 | 本周剩余预算 > 0？ | **否** → 冻结非必要发布，走例外审批（20.4）。**是** → 进入第 2 级 |
| 2 | 近 1h / 5m 快燃尽 ≥ 14.4？ | **是** → 暂停发布并 paging，先止血（第 22、23 章）。**否** → 进入第 3 级 |
| 3 | 近 6h 慢燃尽 ≥ 6？ | **是** → 允许已开始的发布收尾，禁止新开，建 ticket。**否** → 进入第 4 级 |
| 4 | 本次变更是否在冻结豁免清单内？ | **是** → 放行但登记例外编号、审批人、到期时间，下次复盘核对（CL-G-10）。**否** → 正常放行，按第 13 章回滚方案先行 |"""),

    ("ch22.md", "这是一条用户可感的症状吗", """| 级 | 判据（按序自问） | 命中 → 去处 |
|---|---|---|
| 1 | 这是一条用户可感的症状吗？ | **否** → 降为 ticket / info，不 paging。**是** → 进入第 2 级 |
| 2 | 阈值由第 20 章错误预算推导了吗？ | **否** → 回第 20 章，禁止拍脑袋阈值。**是** → 进入第 3 级 |
| 3 | 带 runbook / 首步动作 / 升级路径了吗？ | **否** → 不允许合并，先补注解。**是** → 进入第 4 级 |
| 4 | 在抑制 / 静默 / 演练窗口内吗？ | **是** → 按登记放行或静默，不重复通知。**否** → 允许 paging；按分级表路由，并在周会复盘命中率 |"""),

    ("ch22.md", "├── alertmanager.yaml", """| 路径（相对仓库根） | 在门禁中的角色 |
|---|---|
| `observability/alert-rules.yaml` | 告警规则（`PrometheusRule` CR，`ruleSelector` 按 `role: alert-rules` 挂载） |
| `observability/alert-rules-test.yaml` | 规则单测输入序列（`promtool test rules` 门禁） |
| `observability/alertmanager.yaml` | 路由 / 抑制 / 静默区间（挂成 Secret，`amtool check-config` 门禁） |
| `docs/runbooks/` | runbook 索引与正文（CL-22-02 断链检查的对象） |
| `hack/alert-drill.sh` | 注入测试告警的路由演练（CI 与发布后各跑一次） |"""),

    ("ch24.md", "order-demo-dev / staging / prod 三个命名空间之一", """| 级 | 判据（按序自问） | 命中 → 结论 |
|---|---|---|
| 1 | 这个镜像会进 `order-demo-dev` / `staging` / `prod` 三个命名空间之一？ | **是**（生产证据链作用域）→ 必须走 CI 签名 + SBOM + 摘要核验；第三方镜像只接受「重新构建」或「验上游签名」两种信任根，无豁免路径。**否** → 进入第 2 级 |
| 2 | （边界内）仓库在 `registry.example.com/order-demo/` 下？ | **是** → 允许 `unsigned-` 前缀临时镜像；不带 `git-` 前缀、不进保留策略、90 天清空。**否** → 归第 25 章策略体系约束，本章不背书 |"""),

    ("ch27.md", "这个动作的终态能用原生资源表达吗", """| 级 | 判据（按序自问，命中即停） | 命中 → 用什么 |
|---|---|---|
| 1 | 这个动作的终态能用原生资源表达吗？（`Deployment` / `StatefulSet` / `CronJob` / `HPA` / `PDB`） | **是** → ① 原生资源，停 |
| 2 | 差异只是「同源清单在不同环境取不同值」？ | **是** → ② 配置打包（Helm 4.x / Kustomize 5.x），停 |
| 3 | 动作是一次性或周期性的，没有「持续比对并收敛」的需求？ | **是** → ③ CI 脚本 / CronJob，停 |
| 4 | 需求是「在对象进集群前校验或改写它」，不需要长期运行状态？ | **是** → ④ Webhook 或策略（VAP / Kyverno 1.x），停 |
| 5 | 需要持续观测 + 收敛 + 有明确领域模型，且团队能长期承担 CRD 负债（版本、备份、卸载、告警、责任人）？ | **是** → ⑤ 自定义控制器（CRD + Operator，Kubebuilder 4.x，见第 28 章） |
| — | 五级都不命中 | 写一份「本项目不写 Operator」的 ADR，回 27.3 在前四种里选一种 |"""),

    ("ch28.md", "make test（envtest）通过、幂等断言为 1", """| 级 | 判据（逐级放行） | 不通过 → 去处 |
|---|---|---|
| 1 | `make test`（envtest）通过、幂等断言为 1？ | 停在开发环境，禁止合并 |
| 2 | `status` 是否只含观测字段、`observedGeneration` 对齐？ | 回 28.2 语义修正 |
| 3 | 控制器 SA 是否最小权限、无 `cluster-admin`？ | 回 28.4 `role.yaml`（CL-S-02） |
| 4 | 三条健康告警已加载且各带 runbook？ | 补 28.4 告警规则 |
| 5 | CRD 版本迁移路径 + 升级 / 回滚演练已跑过？ | 先补演练（CL-G-07） |
| — | 五条全过 | 允许进 staging；prod 仍走第 14 章 GitOps 晋升链 |"""),

    ("ch30.md", "是否需要凭据 / 配额 / 故障域的硬隔离", """| 级 | 判据（逐级放行） | 不通过 → 去处 |
|---|---|---|
| 1 | 是否需要凭据 / 配额 / 故障域的硬隔离，或有合规审计要求？ | 停在第 4 章三套命名空间 |
| 2 | 是否有平台组能维护标准化模板与策略库？ | 先补平台能力，不复制集群 |
| 3 | 多个集群是否由同一份 IaC 模块供应、同一 GitOps 入口发布？ | 集中供应 + 一份 `ApplicationSet`，停 |
| 4 | 一次变更能否在两个集群产生同一 SHA 且可一起回退？ | 回 30.4 检查双集群生成器 |
| 5 | `state` 是否远端加密、`plan` 是否进 PR、升级顺序是否成文？ | 补护栏，不许升级生产集群 |
| — | 五条全过 | 多集群拓扑成立；黄金路径按 30.4 模板开放自助 |"""),

    ("ch30.md", "├── catalog-info.yaml", """| 路径（相对仓库根） | 内容 |
|---|---|
| `platform/golden-path/skeleton/catalog-info.yaml` | Backstage 目录实体，`owner` 取模板参数 |
| `platform/golden-path/skeleton/deploy/base/` | base 四件套：`kustomization.yaml`、`deployment.yaml`、`service.yaml`、`networkpolicy.yaml` |
| `platform/golden-path/skeleton/deploy/overlays/prod/kustomization.yaml` | prod overlay，只写与 base 不同的字段 |"""),
]

# 引言句改写：把「决策树」换成「判定表 / 放行表」，保持叙述自洽
SENTENCES = [
    ("ch20.md", "### 发布冻结判定决策树", "### 发布冻结判定表"),
    ("ch22.md", "**噪音治理决策树**：", "**噪音治理判定表**："),
    ("ch22.md", "决策树最后一行「在周会复盘命中率」不是口号", "判定表最后一行「在周会复盘命中率」不是口号"),
    ("ch24.md", "三类边界收敛成一棵可判定的树，新镜像接入时先过这一问：",
     "三类边界收敛成一张判定表，新镜像接入时先过这一问："),
    ("ch24.md", "树的价值在「变更评审时先问作用域」", "这张表的价值在「变更评审时先问作用域」"),
    ("ch24.md", "答案都由它在树上的位置决定", "答案都由它在表里的位置决定"),
    ("ch24.md", "树上没有的分支（比如「临时放开某次 prod 部署」）", "表里没有的位置（比如「临时放开某次 prod 部署」）"),
    ("ch27.md", "下面这棵决策树按「成本从低到高」排列", "下面这张判定表按「成本从低到高」排列"),
    ("ch28.md", "**决策树**（判断一个控制器能不能进 staging）", "**放行表**（判断一个控制器能不能进 staging）"),
    ("ch30.md", "**决策树**（判断当前该停在单集群还是升级）：", "**判定表**（判断当前该停在单集群还是升级）："),
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
