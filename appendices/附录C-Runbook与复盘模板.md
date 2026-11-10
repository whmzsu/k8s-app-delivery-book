# 附录 C　Runbook 与复盘模板

> 与第 22 章「每条告警必须可操作并指向 runbook」、第 23 章「症状 → 定位 → 处置」配套。所有 runbook 遵守：**SSH 禁入生产**（公理 8），排障只走可观测数据与 `kubectl` 只读命令；任何写操作都要能回到 Git（公理 5）。

## C.0 Runbook 通用模板（五项必填）

```
Runbook 编号：RB-<序号>　｜　关联告警：<告警名>　｜　关联 SLO：<SLI 名称>
适用症状：<一句话，用户/调用方能感知到的现象，不是 CPU 高这类内部指标>
1. 影响面判定：受影响的服务 / 环境 / 流量比例 / 是否触及 SLO 错误预算
2. 定位路径：按顺序列出只读命令与期望输出（最多 5 步，每步写「看到什么就走哪条分支」）
3. 止血动作：按代价从小到大排序，每步给命令、预计生效时间与验证命令
4. 升级与沟通：何时叫人、叫谁、对外话术模板、状态页更新责任人
5. 收尾：回写 Git / 关闭例外登记 / 补演练记录 / 触发无责复盘的条件
```

**硬性规则**：第 3 步的第一个动作必须是**可回退**的；如果止血动作本身会改数据，必须显式写「数据侧回滚为什么不可用」并指向第 16 章。

## C.1 RB-01　Pod 长时间 Pending

| 项 | 内容 |
|---|---|
| 症状 | 发布后部分副本起不来，`kubectl get pods` 显示 `Pending`，发布卡住 |
| 定位 | ① `kubectl -n order-demo-prod describe pod <pod>` 看 Events；② `kubectl get nodes -o jsonpath` 看可分配资源；③ 检查 `topologySpreadConstraints` / 亲和 / 污点容忍；④ 检查 PVC 是否 Bound |
| 分支 | 事件出现 `FailedScheduling` + `Insufficient cpu` → 资源类；`node(s) didn't match Pod's node affinity` → 调度约束类；`volume node affinity conflict` → 存储拓扑类 |
| 止血 | ① 优先撤销本次发布的调度相关 diff（回 Git）；② 临时下调非关键工作负载副本（须登记例外）；③ 扩容节点（Karpenter/Autoscaler，见第 18 章）；**不要**直接改生产 Pod 模板 |
| 验证 | `kubectl -n order-demo-prod rollout status deployment/api --timeout=120s` 且 SLI 成功率回到目标区间 |
| 收尾 | 回见第 17、18 章检查 requests 基线与容量账，补一次发布前 CL-G-08 |

## C.2 RB-02　CrashLoopBackOff / liveness 误杀级联

| 项 | 内容 |
|---|---|
| 症状 | Pod 反复重启，错误率突增；重启计数持续增长但配置没变 |
| 定位 | ① `kubectl get pod -o jsonpath='{..restartCount}'`；② `kubectl logs <pod> --previous`；③ `kubectl describe pod` 看 `Liveness probe failed` / `OOMKilled`；④ 对比探针阈值与启动耗时（见第 8 章） |
| 分支 | 有 `Liveness probe failed` → 探针误杀；有 `OOMKilled` → 转 RB-03；日志里是配置解析错 → 转配置漂移排查 |
| 止血 | ① 回滚到上一个已知良好镜像（`git-<上一个sha7>`，见第 6、13 章）；② 若确认为探针误杀，把修正后的探针阈值走 Git 发布，**不要**在生产直接 `kubectl edit`；③ 必要时临时增大 `startupProbe.failureThreshold`（登记例外与有效期） |
| 验证 | 重启计数停止增长、`/readyz` 返回 200、5xx 比例回落 |
| 收尾 | 补第 8 章探针基线与第 21 章重启指标告警；第 23 章演练中复现一次 |

## C.3 RB-03　OOMKilled

| 项 | 内容 |
|---|---|
| 症状 | 部分请求 502/连接被重置，Pod 状态 `OOMKilled`，内存曲线呈锯齿状 |
| 定位 | ① `kubectl describe pod` 看 Last State；② 查容器内存 working set 与 limits；③ 检查近期是否改了缓存/批处理逻辑；④ 查 QoS 等级 |
| 分支 | working set 长期贴近 limits → 限额偏小；突刺型 → 流量或批量任务；两者都不是 → 查内存泄漏 |
| 止血 | ① 回滚本次变更；② 按第 17 章临时上调 memory limit（登记例外）；③ 限流或降级非关键路径 |
| 验证 | 10 分钟内无新增 `OOMKilled`，`container_memory_working_set_bytes` 与 limit 有安全余量 |
| 收尾 | 回归第 17 章 requests/limits 取舍与第 18 章 VPA 适用边界 |

## C.4 RB-04　5xx 突增

| 项 | 内容 |
|---|---|
| 症状 | SLO 成功率掉出目标，错误预算快速消耗，网关 5xx 比例超阈值 |
| 定位 | ① 按 `service/version` 分组看 5xx，判断是全量还是只在新版本；② 查网关上游超时/重试与熔断（第 19 章）；③ 查依赖 `db` 连接与慢查询；④ 查最近一次发布与分析模板结果（第 15 章） |
| 分支 | 只在新版本 → 触发自动/人工回滚；全量 → 查依赖与基础设施；伴随连接拒绝 → 查 NetworkPolicy 与 EndpointSlice |
| 止血 | ① 执行第 15 章自动回滚或第 13 章人工回滚到已知良好 SHA；② 关闭非必要重试放大；③ 必要时启用降级开关（与发布解耦，见第 15 章） |
| 验证 | SLI 回到目标区间，错误预算消耗速率归零，`rollout status` 正常 |
| 收尾 | 写无责复盘；检查 Analysis 阈值是否过松（第 15 章）与告警是否可行动（第 22 章） |

## C.5 RB-05　证书过期 / TLS 握手失败

| 项 | 内容 |
|---|---|
| 症状 | 客户端报证书过期或 TLS 握手失败，网关健康检查可能仍为 200 |
| 定位 | ① `kubectl -n <ns> get certificate,secret` 看 `Ready` 与 `NotAfter`；② `openssl s_client -connect <host>:443` 看链；③ 检查 cert-manager 续期事件与 ACME 挑战；④ 检查是否有手工导入的静态证书 |
| 分支 | Certificate `Ready=False` → 续期链路；链不完整 → 分发链路；两个都正常但客户端仍报错 → 客户端信任库 |
| 止血 | ① 走 Git 修复 Certificate/Issuer 配置；② 临时切换备用证书（登记例外，写明有效期）；③ 通知调用方刷新信任链 |
| 验证 | `NotAfter` 更新、握手成功、证书有效期告警（第 22 章）恢复正常 |
| 收尾 | 复核第 19 章证书自动化与到期告警覆盖率；把「证书剩余天数」纳入第 20 章 SLI 辅助指标 |

## C.6 RB-06　配置漂移

| 项 | 内容 |
|---|---|
| 症状 | Git 里是一版、集群里是另一版；回滚后行为不一致；Argo CD 显示 OutOfSync |
| 定位 | ① `argocd app diff <app>` 或 `kubectl diff -f` 对比；② 审计日志查窗口内 `kubectl edit`/`set image`/`patch`；③ 查控制器副作用（HPA、mutating webhook、Operator）；④ 查 `managed-by` 标签与字段归属 |
| 分支 | 有人手工改 → 走 H7 处置；控制器副作用 → 明确声明与 Git 的分工；自愈误伤 → 检查 selfHeal 配置 |
| 止血 | ① 让 GitOps 控制器同步回 Git 声明（见第 14 章）；② 对确需保留的临时改动，先登记例外再补 PR；③ 关闭触发漂移的手工通道与凭据 |
| 验证 | `argocd app get <app>` 显示 Synced/Healthy，审计窗口内无新增手工变更 |
| 收尾 | 回见第 14、26 章收紧 RBAC 与审计；在附录 B 的 `CL-S-04` 记录本次结论 |

## C.7 无责复盘模板

```
复盘编号：PM-<日期>-<序号>　｜　关联事件 / Runbook：　｜　严重程度：　｜　持续时长：
一、时间线（只写事实与可验证来源：告警时间、发布记录、指标截图、操作日志）
二、影响面（受影响用户/请求比例、错误预算消耗、是否有数据侧影响）
三、失效点（逐条对照第 1 章 H1–H8 与第 31 章 AP 反模式编号，不写「某人疏忽」）
四、为什么当时没能更快发现（信号、告警、runbook、权限、演练覆盖，逐项给证据）
五、为什么不蔓延（哪些护栏真的生效了，给命令或指标证据）
六、改进项（每条写：动作 /  Owner / 验收命令 / 截止日期 / 对应章节；至少 1 条是自动化护栏，而非「加强意识」）
七、例外与公理（本次是否触发例外登记？是否暴露某条公理需要补充「例外前提」？）
```

**复盘的三条红线**：① 不追究个人，追究「为什么系统允许这个错误发生」；② 每条改进必须可执行、可验收，禁止「以后注意」；③ 复盘结论要回写到对应章节的检查清单与 runbook，否则等于没做。

## C.8 演练记录模板

```
演练编号：DR-<日期>-<序号>　｜　类型：回滚 / 故障注入 / 备份恢复 / 密钥轮换
注入方式：Chaos Mesh 实验名与参数（见第 23 章）
预期表现：哪个告警该响、哪条 runbook 该被用、SLO 消耗多少
实际表现：MTTR、误报数、未覆盖的空白点、是否触发了不该触发的自动回滚
回滚与清理：实验对象删除命令、finalizer 是否卡住（见第 27 章）
结论：通过 / 不通过 + 不通过时的整改项与复练日期
```
