# 租户隔离复核（每个新增租户 / 每次集群升级前执行）

- [ ] 该租户有独立 ServiceAccount，且未绑定任何 ClusterRole / cluster-admin
- [ ] 该命名空间存在默认拒绝的 NetworkPolicy，放行项按标签枚举（见第 19 章）
- [ ] 该命名空间已打 PSS `enforce` 标签，级别不低于 `baseline`（见第 25 章）
- [ ] `automountServiceAccountToken: false` 已写在所有 SA 与 Pod 模板上
- [ ] 云厂凭据走 Workload Identity / IRSA，仓库内无长期 Access Key
- [ ] 审计策略已覆盖 `secrets` 与 RBAC 对象，日志留存不少于 30 天
- [ ] 生产无 SSH 通道；排障入口为可观测栈与 runbook（见第 23 章）
- [ ] 敏感租户是否需要拆独立集群 / 独立账号，结论与第 4 章、第 30 章一致
