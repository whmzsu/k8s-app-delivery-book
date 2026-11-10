# 案例演进与配置契约（case-evolution）

版本 `v0.1` · 2026-11-10 · 依据第九节 9.5 展开为 31 章全量版

> 这是全书最容易脱钩的地方：`order-demo` 逐章演进，任何一章改了标签、端口、命名空间或镜像命名，后面所有章节的 YAML 都会失效。**改字段先改本文件，再按 `strong-pairs.md` 列出受影响章逐一回写。**

## 一、`order-demo` 组成

| 组件 | 角色 | 工作负载 | 端口 | 依赖 |
|---|---|---|---|---|
| `gateway` | HTTP 入口、路由与鉴权 | Deployment | 8080 | `api` |
| `api` | 订单读写，对外提供 `/orders` | Deployment | 8081 | `db` |
| `worker` | 异步任务（超时关单、通知） | Deployment | 无监听端口 | `db` |
| `db` | PostgreSQL | 第 7 章起 StatefulSet；第 16 章讨论托管 / Operator | 5432 | — |

第 1 章以「事故现场最小复现环境」登场；第 6 章用一个镜像 + Deployment/Service + ConfigMap 跑通；第 7–11 章逐层加固；第 12–16 章进入自动交付；第 17–23 章治理与观测；第 24–31 章护栏与平台化。

## 二、配置契约（冻结字段）

| 字段 | 冻结值 | 生效章 | 变更影响 |
|---|---|---|---|
| 命名空间 | `order-demo-dev` / `order-demo-staging` / `order-demo-prod` | 4 起 | 全部章的 `kubectl -n`、NetworkPolicy、RBAC、ApplicationSet |
| 镜像仓库 | `registry.example.com/order-demo/<component>` | 6 起 | 6、12、14、24 |
| 镜像标签 | `git-<7位短SHA>`，禁用 `latest` | 6 起 | 3、6、12、13、14、24 |
| 公共标签 | `app.kubernetes.io/name=order-demo`、`component=<组件>`、`version=<SHA>`、`managed-by=<工具>` | 6 起 | 8、10、14、19、21 |
| Service 名 | `gateway`、`api`、`db` | 6 起 | 6–11、19、21 |
| 探针路径 | `/healthz`（liveness）、`/readyz`（readiness）、`/startup`（startup，仅 api） | 8 起 | 8、10、13、15、23 |
| 终止宽限 | `terminationGracePeriodSeconds: 30`；`preStop` 先摘流再退出 | 8 起 | 8、13、15 |
| ConfigMap | `order-demo-config`，第 9 章起 `immutable: true` | 6 起 | 9、10、14、23 |
| Secret | 不入 Git，键名 `order-demo/db-credentials`，由 ESO / CSI 注入 | 9 起 | 4、9、14、26 |
| 资源基线（api） | requests `cpu: 100m, memory: 128Mi`；limits `cpu: 500m, memory: 256Mi` | 17 起 | 17、18、23 |
| 仓库 tag | `chNN-<主题>`，见下表 | 全书 | 附录 D、README、CI |

约定：配置块一律用代码块给出**完整可应用文件**，不写省略号；版本敏感字段标注对应的附录 A 行号。

## 三、逐章增量与可验证动作

| 章 | 增量 | 读者可验证的动作 | tag |
|---|---|---|---|
| 1 | 事故现场最小复现环境 | `curl` 返回 500，数出 8 个失效点 | `ch01-incident` |
| 2 | 用 OwnerReference 解释终态收敛 | `kubectl get deploy -o yaml` 找到 owner 链 | `ch02-model` |
| 3 | 镜像改打 SHA 标签 | `kubectl describe pod` 看不到 `latest` | `ch03-principles` |
| 4 | dev / staging / prod 三套 overlay 与独立凭据 | 三环境渲染结果仅配置不同、镜像相同 | `ch04-env` |
| 5 | 按团队规模选定最小工具集 | 写出本团队的工具清单与「不上什么」 | `ch05-toolmap` |
| 6 | **最小完整闭环**：一个镜像 + Deployment/Service/ConfigMap | kind 里 `curl` 通 `gateway/healthz` | `ch06-first-loop` |
| 7 | 补齐 `worker` 与 `db` 的工作负载选型 | 四类工作负载各出现一次 | `ch07-workloads` |
| 8 | 三类探针 + preStop + PDB | 滚动更新期间连续请求零 5xx | `ch08-probes` |
| 9 | 不可变 ConfigMap + 外部密钥注入 | 轮换密钥无需重建镜像 | `ch09-secrets` |
| 10 | Chart / overlay 双骨架 | `helm template` 与 overlay 渲染 diff 一致 | `ch10-helm` |
| 11 | kubeconform / conftest / kuttl + kind 版本矩阵 | 提交一个错误字段被 CI 拦下 | `ch11-validate` |
| 12 | CI 一次构建 | 推一个 commit 产出带 SHA 的镜像 | `ch12-ci` |
| 13 | 三种策略选型与回滚演练 | 执行 `kubectl rollout undo` 成功恢复 | `ch13-strategy` |
| 14 | 三环境 GitOps 晋升 | 合并 PR 后自动同步；手工改动被纠正 | `ch14-gitops` |
| 15 | 金丝雀与指标自动回滚 | 5% 流量，注入错误率后自动回退 | `ch15-canary` |
| 16 | PostgreSQL expand–contract + 备份恢复 | 演练一次备份恢复到新集群 | `ch16-stateful` |
| 17 | requests/limits 与 QoS 基线 | 触发 OOMKilled 并按 runbook 定位 | `ch17-resources` |
| 18 | HPA + topologySpread + 成本归因 | 压测触发扩容且无抖动 | `ch18-autoscale` |
| 19 | Gateway API + NetworkPolicy 默认拒绝 | 未授权 Pod 无法访问 `db` | `ch19-gateway` |
| 20 | gateway 可用性 SLO 与错误预算 | 算出本周预算消耗与是否冻结发布 | `ch20-slo` |
| 21 | OTel + Prometheus + Loki/Tempo | 一条请求能串起指标、日志、链路 | `ch21-otel` |
| 22 | 面向症状的告警与分级路由 | 触发一条带 runbook 链接的告警 | `ch22-alerts` |
| 23 | Chaos Mesh 演练 + 6 份 runbook | 注入故障后按 runbook 恢复 | `ch23-chaos` |
| 24 | SBOM / 扫描 / cosign 验签门禁 | 未签名镜像被准入拒绝 | `ch24-supply` |
| 25 | Kyverno / VAP 策略库 | 特权容器在 CI 与准入两处被拦 | `ch25-policy` |
| 26 | SA 最小化、审计、租户隔离 | 越权请求被 RBAC 拒绝并留审计 | `ch26-rbac` |
| 27 | 扩展方式五选一决策树 | 写出「本项目不写 Operator」的理由 | `ch27-crd` |
| 28 | 最小 Operator 骨架（平台团队可选） | reconcile 幂等性测试通过 | `ch28-operator` |
| 29 | CloudNativePG 成熟度评估 | 完成评估表并写出降级预案 | `ch29-cnp` |
| 30 | 双集群发布与黄金路径 | 一次变更同时发到两集群 | `ch30-multicluster` |
| 31 | 事故重演 | 同一变更零故障完成，与 `ch01-incident` 对照 | `ch31-replay` |

## 四、每章开头的固定块

每章正文开头（章首坐标标签之后）固定写：

> **此刻 `order-demo` 长什么样**：<本表对应行的一句话> ｜ **本章可验证动作**：<对应行的动作> ｜ 复现：`git checkout <tag>`。

这样读者在 31 章的增量里不会迷路，也让 P5 的技术复核有明确验收点。

## 五、唯一示例实现固定值（P2 裁决，见 `decisions.md` U-04 / U-05）

> 本表是 D-08「单一示例实现登记机制」的落地。同一示例全书只用一个实现，其余工具仅在选型矩阵中作对比。**新增字段，不改动第二节已冻结字段。**

| 项 | 固定值 | 影响章 |
|---|---|---|
| 准入策略引擎 | `kyverno` 1.x（命名空间 `kyverno`），策略命名 `order-demo-*`；VAP 作内置轻量对比，Gatekeeper 仅入矩阵 | 24、25、26 |
| 流量入口 | `GatewayClass: eg`、`Gateway` 名 `order-demo-gw`、`HTTPRoute` 名 `gateway-route` | 15、19、21、30 |
| 渐进式交付 | `argo-rollouts` + Gateway API traffic router 插件；必须同时给「按副本比例金丝雀」退化方案 | 15 |
| GitOps 引擎 | `Argo CD 2.x` 为示例，`Flux 2.x` 仅作对比 | 14、30 |
| 配置打包 | `Kustomize 5.x` overlay 为多环境基线；`Helm 3.x` 为对外分发 Chart | 10、14 |
| 密钥注入 | `External Secrets Operator` + 后端占位 `vault`，键名 `order-demo/db-credentials` | 9、14、26 |
| 可观测栈 | OTel Collector → Prometheus / Loki / Tempo；长期指标用 Thanos 或兼容远端存储 | 20、21、22 |
| 演练工具 | `Chaos Mesh` 为示例，`Litmus` 仅作对比 | 23 |
| 有状态示例 | PostgreSQL；第 16 章先用原生 StatefulSet 讲迁移范式，`CloudNativePG` 是第 29 章的评估对象 | 16、29 |
| 第 6 章 managed-by | `app.kubernetes.io/managed-by=kubectl`（第 10 章起改 `kustomize`，第 14 章起改 `argocd`） | 6、10、14 |

## 六、tag 命名变更记录

- D-04：`ch15-gitops` → `ch14-gitops`，新增 `ch15-canary`（第 14/15 章互换）
- D-05：`ch06-image` → `ch06-first-loop`（第 6 章改为最小完整闭环，供应链内容并入第 24 章）
- 附录 D 由本表生成，不在别处手工维护第二份
