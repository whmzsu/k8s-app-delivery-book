# 现成 Operator 成熟度评估表（CloudNativePG 1.x）

- 评估日期：2026-11-10
- 评估对象：CloudNativePG 1.x（PostgreSQL Operator）
- 候选对照：Strimzi 0.x / cert-manager 1.x / external-dns 0.x
- 加权规则：通过计满分、条件通过计半分、不通过计 0 分；通过线 ≥ 80%
- 结论：有条件通过 —— 允许进入受限试点，条件项（自身告警）关闭前不晋升 prod

| 评估项 | 权重 | 结论 | 证据 / 待办 | 责任人 |
|---|---|---|---|---|
| 维护活跃度 | 5 | 通过 | 发行说明、提交历史、issue 响应已归档到评估 PR | 平台组 |
| 升级策略（CRD 版本迁移） | 5 | 通过 | 官方版本兼容矩阵；升级顺序按 29.5 演练 | 平台组 |
| 备份恢复 | 5 | 通过 | 声明式 Backup / ScheduledBackup + 第 16 章恢复演练报告 | 数据 owner |
| 卸载残留 | 4 | 通过 | hack/operator-uninstall-drill.sh 输出，finalizer 清空 | 平台组 |
| 自身可观测 | 4 | 条件通过 | 控制器暴露指标；告警规则待按 observability/operator-slo.yaml 补齐 | 平台组 |
| 降级预案 | 5 | 通过 | docs/operator-degradation-plan.md 已分级、有责任人 | 平台 + DBA |
| 社区治理 | 3 | 通过 | 治理文件、贡献流程、CNCF 项目成熟度分级 | 平台组 |
| 云厂绑定 | 3 | 通过 | 存储为可移植 PVC / 对象存储抽象 | 平台组 |

## 否决项（命中任意一条即不引入）
1. CRD 只有单一版本且无迁移路径。
2. 备份无法恢复到新集群，或未做过恢复演练。
3. 卸载演练出现 finalizer 卡住且无处置方案。
4. 答不出「控制器挂了业务会不会挂」。

## 复评周期
每次控制器大版本升级前复评一次；每季度复评维护活跃度与社区治理。
