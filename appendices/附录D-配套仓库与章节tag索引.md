# 附录 D　配套仓库结构与章节 tag 索引

> `order-demo` 是全书唯一贯穿案例：同一套应用从第 1 章的事故现场逐章演进到第 31 章的多集群渐进式交付。每章一个 tag，读者可 checkout 到任一章的状态并复现该章的可验证动作。D.3 是全量 tag 表，也是唯一一份——不在别处维护第二份。

## D.1 配套仓库结构

读者真正需要的是三样东西：**一份能跑起来的基线**、**按章的配置片段**、**可复现的锚点**。仓库按这个顺序组织：

```
.
├── examples/
│   ├── order-demo/               # 第 6 章的最小完整闭环，唯一可直接运行的完整基线
│   │   ├── cmd/gateway/          # gateway 组件源码（Go）
│   │   ├── docker/               # 多阶段构建 Dockerfile
│   │   ├── deploy/base/          # namespace / configmap / deployment / service 四份清单
│   │   ├── hack/                 # kind-up.sh、verify.sh、ci-drill.sh
│   │   ├── go.mod
│   │   └── README.md             # 如何起集群、部署、验证、清理
│   └── by-chapter/               # 各章代码块按章整理的可复制副本（见 D.5）
│       ├── ch01/ … ch31/
│       └── _manifest.md          # 逐章文件清单与来源小节
├── chapters/ch01.md … ch31.md    # 全书正文
├── appendices/                   # 附录 A–I
└── .github/workflows/            # 示例配置的自动化验证（见 D.7）
```

两点说明：

- **`order-demo` 只到第 6 章为止**。它刻意保持最小：一个 `gateway` 组件、四份清单、三个脚本。后续章节的 `api`、`worker`、`db`、overlay、Policy、GitOps 清单都在 `examples/by-chapter/` 里按章给出，而不是把最终形态一次性塞进基线——否则你会失去「这一章到底加了什么」的对照。
- **本书的写作期资产不随书分发**。大纲、章卡片、跨章一致性记录、校验脚本这些是我写这本书用的东西，不会出现在你的 clone 里；它们与读者无关，删掉也不影响任何示例运行。

## D.2 复现方式

```bash
git clone <本仓库地址>
cd k8s-app-delivery-book
git checkout ch06-first-loop        # 切到任一章的 tag
less chapters/ch06.md               # 读该章正文
ls examples/by-chapter/ch06/        # 该章的配置副本

# 想直接跑起来，用第 6 章的完整基线
cd examples/order-demo
./hack/kind-up.sh                   # 起一个本地 kind 集群（需 docker）
./hack/verify.sh                    # 部署并验证（见第 6 章 §6.4–6.5）
```

> tag 是**内容快照**，不代表该章的代码只在该 tag 上存在：全书成稿与资产始终在 `main` 上，tag 用于给读者一个稳定的复现锚点，也用于附录 D 的对照练习（如 `git diff ch01-incident ch31-replay`）。

## D.3 31 章 tag 全量表

| 章 | 增量 | 可验证动作 | tag |
|---|---|---|---|
| 1 | 事故现场最小复现环境 | `curl` 返回 500，数出 8 个失效点 | `ch01-incident` |
| 2 | 用 OwnerReference 解释终态收敛 | `kubectl get deploy -o yaml` 找到 owner 链 | `ch02-model` |
| 3 | 镜像改打 SHA 标签 | `kubectl describe pod` 看不到 `latest` | `ch03-principles` |
| 4 | dev / staging / prod 三套 overlay 与独立凭据 | 三环境渲染结果仅配置不同、镜像相同 | `ch04-env` |
| 5 | 按团队规模选定最小工具集 | 写出本团队工具清单与「不上什么」 | `ch05-toolmap` |
| 6 | **最小完整闭环**：镜像 + Deployment/Service/ConfigMap | kind 里 `curl` 通 `gateway/healthz` | `ch06-first-loop` |
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
| 21 | OTel + Prometheus + Loki/Tempo | 一条请求串起指标、日志、链路 | `ch21-otel` |
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

## D.4 第 6 章基线代码

`examples/order-demo/` 提供第 6 章的完整可运行基线：`go.mod`、`cmd/gateway/main.go`、`docker/Dockerfile`、`deploy/base/{namespace,configmap,deployment,service}.yaml`、`hack/{kind-up,verify,ci-drill}.sh`。执行方式见第 6 章 §6.4–6.5。

`ci-drill.sh` 是运行时演练脚本，一次跑完四件事：滚动更新零停机、SHA 标签回滚、readiness 摘流、Pod 重建。它不需要额外工具，只要集群起好了就能执行——建议你第一次照抄完配置就顺手跑一遍，用它的输出对照第 6 章的四条验证判据。

第 7–11 章的增量配置在各章 §N.4 给出，按章叠加即可，字段严格沿用第 6 章冻结的配置契约（命名空间、标签、端口、镜像命名）。

## D.5 按章整理的配置副本

`examples/by-chapter/chNN/<path>` 是从各章 §N.4 带路径标注的代码块整理出来的可复制副本，与 D.3 的章节 tag 一一对应；逐章清单见 `examples/by-chapter/_manifest.md`。

**为什么按章分目录而不是平铺**：同一路径（例如 `deploy/base/deployment.yaml`）会在多章出现，后面章节给出的往往是**增量 patch** 而不是完整文件，平铺到一个目录会互相覆盖。按章保留，等于保留了每章当时的真实状态——你 checkout 对应 tag 后可以直接用，也可以拿两章对比看出「这一章改了什么」。

- 章内 §N.4 的代码块是**权威副本**；`examples/by-chapter/` 是它的可复制形态，两者冲突时以章内为准
- `examples/order-demo/` 是第 6 章的完整可运行基线，与 `examples/by-chapter/ch06/` 内容一致
- 少数章节（第 5、25、27 章）以命令与判断为主，没有带路径标注的清单，不需要副本，配置完整写在章内
- 第 1 章的 `hack/reproduce-incident.sh` 与第 31 章的 `hack/replay-incident.sh` 是首尾对照的两个可执行脚本，分别位于 `examples/by-chapter/ch01/` 与 `examples/by-chapter/ch31/`——建议各自跑一次，体会同一事故在「不懂」和「懂」两种状态下的差别

## D.7 示例配置验到了什么程度

示例配置不是「贴出来就算」。三件事在每次改动时自动做，你也可以用它们判断某个示例能不能直接抄。

**一、清单按类型分开校验。** 全书 YAML 按 `apiVersion` 分组：内置资源（Deployment、Service、ConfigMap 等）、CRD 实例（`HTTPRoute`、`ClusterPolicy`、`Application` 等）、Helm 模板、以及非 K8s 对象（`kind` 集群配置、`Kustomization`、`Chart.yaml`）。只有内置资源能直接交给 API Server 做 server dry-run；CRD 实例要先装对应控制器，模板要先渲染。**不分类就全量校验，会产生大量假阳性**——所以示例清单是分类验的，不是一把梭。

**二、能跑的那份必须真跑。** `examples/order-demo/` 进硬闸门：四版本 schema 校验 → 真实 kind 集群部署 → `ci-drill.sh` 演练。它在 K8s 1.32.2 / 1.34.11 / 1.37.0 三个版本上各跑一遍，版本与 kind 成对锁定（见附录 A.2）。**这是本书唯一承诺「拷下去能跑」的部分。**

**三、逐章片段只做结构报告。** `examples/by-chapter/` 是逐章增量，例如 `ch10/deploy/base/kustomization.yaml` 引用的 12 个资源分散在前面几章的目录里，按设计不可独立渲染。因此它只输出「引用 / 缺失」的结构报告，**不计入阻断**——它保证的是「这一章的清单长这样」，不是「单独拿走能跑」。要用完整形态，请 checkout 对应章节 tag。

**验证覆盖不到的地方**（务必自己补）：云厂商 LB / 存储 / IRSA 的真实行为、跨集群容灾、生产流量下的 HPA / KEDA 效果、长周期证书轮换，以及 Argo CD / Kyverno / Gateway API 等需装 CRD 控制器的运行时表现。这些必须按各章「验证与回滚」段在自有集群演练。**自动化校验通过 ≠ 生产可用**，这句话在本书里出现两次，因为它最容易被误读成「示例经过了完整验证」。
