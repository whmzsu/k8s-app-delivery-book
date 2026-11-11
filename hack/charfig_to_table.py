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
    ("ch08.md", "控制器决定替换 Pod", """| 步 | 谁在做 | 发生什么 | 为什么必须是这个顺序 |
|---|---|---|---|
| 1 | 控制器 | Pod 进入 `Terminating`，同时从 Service Endpoint 摘除 | 摘流先于停进程：让新请求不再被路由过来 |
| 2 | kubelet | 执行 `preStop`（本章 `preStop.sleep.seconds: 5`），进程先静默 | 专门覆盖「Endpoint 摘除与转发规则更新」之间的竞态 |
| 3 | kubelet | 发 SIGTERM，应用在 `terminationGracePeriodSeconds: 30` 内排空在途请求 | 给在途请求一个自然的完成窗口 |
| 4 | kubelet | 宽限用尽 → SIGKILL | 兜底，不再等待 |"""),

    ("ch10.md", "仓库内渲染（repo-side）", """| 维度 | 仓库内渲染（repo-side） | 集群内渲染（cluster-side） |
|---|---|---|
| 谁在渲染 | 开发者 / CI 跑 `helm template`、`kustomize build` | 控制器（如 Argo CD / Helm Operator）在集群里渲染 |
| 产物是什么 | 静态 YAML | 控制器运行时生成 |
| 是否进 Git | 进 Git / PR 附件 | 不进 Git，Git 只存模板 / overlay |
| 下游怎么用 | GitOps 控制器直接 `apply` | 控制器自行 `apply` 运行时产物 |"""),

    ("ch13.md", "rollout 卡住（UP-TO-DATE 不涨", """| Pod 现象 | 事件 / 状态 | 去处 |
|---|---|---|
| `Pending` | `FailedScheduling: Insufficient cpu / memory` | 容量不足，按 13.2.1 处置（扩容回收余量，或临时调大 `maxUnavailable`） |
| `Pending` | `FailedScheduling: node(s) had untolerated taint` | 节点在排水 / 维护，等排水结束或先扩容补位 |
| `Pending` | `FailedScheduling: exceeded quota` | 命名空间 `ResourceQuota` 用尽，见下表第 4 行（注意此时可能根本没有 Pending Pod） |
| `Pending` | `FailedScheduling: topology / anti-affinity / spread 约束` | 分布约束把可放节点排空，见下表第 5 行 |
| `ImagePullBackOff` / `ErrImagePull` | 拉取失败 | 镜像不可拉取，见下表第 1 行 |
| `Running` 但一直 `0/1 Ready` | 探针不过 | 见下表第 2 行 |"""),

    ("ch15.md", "Rollout 进入 analysis step", """| 阶段 | 触发条件 | 计数动作 | 终态 |
|---|---|---|---|
| 测量（每 `interval` 一次） | 结果满足 `successCondition` | `measurement.phase = Successful` | 成功计数 +1 |
| 测量 | 结果不满足 | `measurement.phase = Failed` | 失败计数 +1 |
| 测量 | 查询报错 / 结果为空 | `measurement.phase = Error` | 连续错误计数 +1 |
| 判定 | 失败计数 > `failureLimit` | — | `AnalysisRun = Failed` → Rollout abort（canary 归 0、`Degraded`） |
| 判定 | 连续错误 ≥ `consecutiveErrorLimit` | — | `AnalysisRun = Error` → abort |
| 判定 | 成功计数 ≥ `successLimit`，或投满 `count` 且失败数 ≤ `failureLimit` | — | `Successful` → 进入下一个 step |
| 判定 | 被 Rollout abort 或人工终止 | — | `Inconclusive` → 权重停在原地，等人裁决 |"""),

    ("ch20.md", "[0] 触发：口径偏差证据", """| 步 | 动作 | 步间闸门 |
|---|---|---|
| 0 | 触发：口径偏差证据（新路由未进排除项 / 4xx 语义被判错 / 旅程拆分 / 低流量转绝对量） | 产出查询语句 + 时间窗 + 受影响请求数，写进 PR 描述（不接受「感觉不准」） |
| 1 | 修订：同改三处声明 —— `observability/slo.yaml`、`observability/sli-recording-rules.yaml`、`docs/slo-contract.md` | 闸门 A：`promtool check rules` 退出码 0 |
| 2 | 例外审批：`EXC` 编号 + 业务负责人、平台负责人双签（§20.4） | 闸门 B：无 `EXC` 编号的 `observability/` 变更，CI 拒绝合并 |
| 3 | 回归单测：新增口径用例，同时保留旧用例做对照（用例矩阵见下） | 闸门 C：`promtool test rules` 全绿，四类用例齐全 |
| 4 | 暗跑 7 天：新旧两条记录规则并行，只有一条有判定权 | 闸门 D：两口径差异 ≤ 预算的 10% |
| 5 | 切主口径：`release_freeze` 指向新规则，旧规则标 `deprecated` 保留一个窗口 | 闸门 E：切换后首小时 `budget-report.sh` 与暗跑末值一致 |
| 6 | 归档：契约版本 +1，记录断点日期与「预算不追溯」说明 | — |"""),

    ("ch23.md", "演练报告 / 事故复盘", """| 步 | 产出 / 动作 | 通过与否的去处 |
|---|---|---|
| ① | runbook 缺口：只写可观测证据（哪个症状、哪条命令、哪次判据缺失） | 进入 ② |
| ② | 复盘改进项 `ACT-nn`：负责人 / 截止日期 / 验收方式，缺一栏不算完成 | 进入 ③ |
| ③ | 下一轮演练验证：同一实验、同一判据、同一爆炸半径 | **通过** → 关闭 `ACT`，判据写入 `CL-23-0x` 与 23.2 速查表；**未通过** → 缺口升级：runbook 问题回 23.3 补模板，权限问题转第 26 章，策略问题转第 25 章，工具能力问题回 23.4 调整实验设计 |"""),

    ("ch25.md", "开发者 ──提 PR", """| 步 | 动作 | 留痕点 |
|---|---|---|
| 1 | 开发者提 PR（改 `policies/` 或 `deploy/`）→ GitHub | — |
| 2 | `policy.yml` 触发：`kyverno test` 四条断言 + 离线校验（25.2.3） | **① CI**：check run 结果记录在 PR 页面 |
| 3 | review + merge → main | PR 评审记录 |
| 4 | Argo CD 检测到 `policies/` 变化并同步（见第 14 章） | Argo CD 同步记录 |
| 5 | sync：apply `ClusterPolicy` → Kyverno 热加载策略 | — |
| 6 | 提交工作负载（Pod 创建或滚动更新），API Server 调 Kyverno webhook | **② 准入**：同步返回 allow / deny 与 message，审计日志记录本次判定 |
| 7 | 对象进入集群（或被拒绝） | — |
| 8 | background scan 周期重扫存量资源 | **③ 审计**：违规写入命名空间级 `PolicyReport` |"""),
]

# 引言句改写：把「决策树」换成「判定表 / 放行表」，保持叙述自洽
SENTENCES = [
    ("ch08.md", "**下线时序**（Pod 被删除或滚动更新替换时，四步严格有序）[R-08-4][R-08-6]：",
     "**下线时序**（Pod 被删除或滚动更新替换时，四步严格有序，顺序换一步就会漏请求）[R-08-4][R-08-6]："),
    ("ch10.md", "> **双模式对照：仓库内渲染 vs 集群内渲染**（为第 14 章 GitOps 埋伏笔）",
     "> **双模式对照：仓库内渲染 vs 集群内渲染**（为第 14 章 GitOps 埋伏笔）"),
    ("ch13.md", "分歧点在 Pod 的 STATUS 与 Events：", "分歧点在 Pod 的 STATUS 与 Events："),
    ("ch15.md", "**AnalysisRun 的生命周期**。每个带 `analysis` 的 step 都会创建一个 `AnalysisRun` 对象——它不是「一段逻辑」，而是能在集群里 `get` 到的资源，由 Rollout 控制器按 step 创建并持有：",
     "**AnalysisRun 的生命周期**。每个带 `analysis` 的 step 都会创建一个 `AnalysisRun` 对象——它不是「一段逻辑」，而是能在集群里 `get` 到的资源，由 Rollout 控制器按 step 创建并持有。它只有四步：测量、计数、判定、交回 Rollout："),
    ("ch23.md", "**闭环流程（三步一分支，缺任一步都算断链）**", "**闭环流程（三步一分支，缺任一步都算断链）**"),
    ("ch25.md", "文字时序如下（①②③为留痕点）：", "下面按步拆开（①②③ 为留痕点）："),
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
