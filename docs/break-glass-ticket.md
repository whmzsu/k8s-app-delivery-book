# Break-glass 带外访问工单（BG-YYYYMMDD-NNN）

- 申请人 / 审批人：<不得为同一人；审批人为当班 SRE 负责人>
- 集群与范围：order-demo-prod / <具体节点或控制面组件>
- 事由：<内核级故障取证 / 云厂硬件排查；说明为什么 runbook 与可观测栈不够用>
- 触碰的公理与例外性质：公理 8 的登记例外（见第 3 章），有效期以本工单到期时间为准
- 授权对象：临时 RoleBinding `bg-<工单号>`，绑定最小 Role（如仅 `nodes/proxy` 的 `get`），不得 cluster-admin
- 生效 / 到期（UTC）：2026-11-11T10:00Z → 2026-11-11T14:00Z（最长 4 小时，到期由回收器自动删除）
- 全程留痕：K8s 审计日志 + 终端会话录制；使用期间的每次 token create 均入审计 [R-26-4]
- 收尾义务：到期后 24 小时内归档复盘，并同步更新第 25 章例外登记
- 状态：OPEN / EXPIRED / REVOKED

---

> 本工单模板与第 25 章 `docs/policy-exception.md` 的例外登记一一对应。
> 授权回收不靠人记性，靠每小时 CronJob `break-glass-reaper`：扫描带
> `order-demo.io/break-glass=true` 标签的 RoleBinding，注释里的到期时间（UTC）
> 一过即删；回收器自身不带该标签，避免被自己回收（详见第 26 章）。
