# 附录 D　配套仓库结构与章节 tag 索引

> `order-demo` 是全书唯一贯穿案例：同一套应用从第 1 章的事故现场逐章演进到第 31 章的多集群渐进式交付。每章一个 tag，读者可 checkout 到任一章的状态并复现该章的可验证动作。tag 全量表由 `book/case-evolution.md` 第三节生成，不在别处手工维护第二份。

## D.1 仓库结构（本仓库即配套仓库）

```
.
├── 书籍大纲-v3.md              # 当前有效大纲（含 v3.1/v3.2/v3.3 全部裁决）
├── 书籍大纲-v2.md              # 历史对照版
├── book/                       # 全局资产（P0 冻结，单一真相源）
│   ├── README.md               # 资产包入口与推进状态
│   ├── glossary.md             # 统一口径 + 全书公理
│   ├── concept-ladder.md       # 概念梯度
│   ├── case-evolution.md       # 配置契约 + 31 章演进表 + 唯一示例实现固定值
│   ├── hooks.md                # H1–H8 钩子映射 + 31 章坐标标签
│   ├── checklist-master.md     # 检查清单母版
│   ├── strong-pairs.md         # 21 对跨章强耦合
│   ├── decisions.md            # U-01～U-05 裁决与 D-09～D-11
│   ├── chapter-spec.md         # 成稿规范（七段模板）
│   ├── consistency-log.md      # 裁决与每轮横扫记录
│   ├── cards/                  # P1 的 31 张章卡片 + 模板 + 索引
│   └── references/_registry.yaml
├── chapters/ch01.md … ch31.md  # 31 章成稿
├── appendices/                 # 附录 A–I
├── references/
│   ├── _verified.md            # 已核验来源池（两轮联网复核）
│   └── ch01.yaml … ch31.yaml   # 逐章引用登记（附录 I 由此生成）
├── examples/
│   ├── order-demo/             # 第 6 章基线可运行代码（见 D.4）
│   └── by-chapter/             # 各章 §N.4 代码块按章物化的可复制形态（见 D.5）
├── hack/
│   ├── book_tools.py           # 规范化 / 一致性校验 / 附录 I 生成
│   ├── materialize.py          # 物化 + --check 一致性比对
│   ├── validate-manifests.py   # 逐文档分类：内置 / CRD / 模板 / 配置
│   ├── build_book.py           # 装配全书单一 Markdown
│   ├── check-links.py          # 外链并发可达性（阈值放行）
│   ├── requirements.txt        # 依赖锁定（PyYAML 6.0.2）
│   ├── check-consistency.sh
│   ├── check-references.sh
│   ├── check-version-matrix.sh # P5：server dry-run + 真实部署 + 演练
│   └── enable-workflows.sh      # SSH 推送 + 可选手动触发流水线（无需 token）
└── .github/workflows/
    ├── ci.yml                  # 快车道：一致性 + 三版本 schema + 容器冒烟
    ├── kind-matrix.yml         # P5：真 kind 集群 × 3 版本（见 D.7）
    └── references.yml          # 背书链接复核
```

## D.2 复现方式

```bash
git clone <本仓库地址>
cd k8s-app-delivery-book
git checkout ch06-first-loop      # 任一章 tag
cat chapters/ch06.md               # 读该章
./hack/check-consistency.sh        # 校验全书一致性（在 main 上执行）
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

`examples/order-demo/` 提供第 6 章的完整可运行基线：`go.mod`、`cmd/gateway/main.go`、`docker/Dockerfile`、`deploy/base/{namespace,configmap,deployment,service}.yaml`、`hack/kind-up.sh`、`hack/verify.sh`、`hack/ci-drill.sh`。执行方式见第 6 章 §6.4–6.5；`ci-drill.sh` 是 P5 的运行时演练（滚动零停机、SHA 回滚、readiness 摘流、Pod 重建），本地与 CI 用同一份脚本。第 7–11 章的增量配置在各章 §N.4 给出，按章叠加即可，字段严格沿用 `book/case-evolution.md` 的配置契约。

## D.5 按章物化的配置副本

`examples/by-chapter/chNN/<path>` 由 `python hack/materialize.py` 从各章 §N.4 的带路径标注代码块生成，与附录 D 的章节 tag 一一对应；清单见 `examples/by-chapter/_manifest.md`。

**为什么按章分目录**：同一路径（例如 `deploy/base/deployment.yaml`）会在多章出现，后面章节给出的往往是**增量 patch**而不是完整文件，平铺到一个目录会互相覆盖。按章物化保留了每章当时的状态，读者 checkout 对应 tag 后即可直接使用。

- 章内 §N.4 的代码块是**权威副本**；`examples/by-chapter/` 是它的可复制形态，两者冲突时以章内为准
- `examples/order-demo/` 是第 6 章的完整可运行基线，与 `examples/by-chapter/ch06/` 内容一致
- 少数章节（第 5、25、27 章）没有带路径标注的代码块，配置与命令仍完整写在章内，不需要物化
- 第 1 章的 `hack/reproduce-incident.sh` 与第 31 章的 `hack/replay-incident.sh` 是首尾对照的可执行脚本，分别位于 `examples/by-chapter/ch01/` 与 `examples/by-chapter/ch31/`

> **技术复核状态**：P5 已迁移到 GitHub Actions（`kind-matrix.yml`），无需本地安装 docker / kind / kubectl；真集群结论见仓库 Actions 记录。本地若已起好集群，仍可执行 `./hack/check-version-matrix.sh --strict` 得到同一套结论。

## D.6 tag 命名变更记录

- D-04：`ch15-gitops` → `ch14-gitops`，新增 `ch15-canary`（第 14/15 章内容互换）
- D-05：`ch06-image` → `ch06-first-loop`（第 6 章改为最小完整闭环，供应链内容并入第 24 章）
- 附录 D 由 `book/case-evolution.md` 生成，禁止在其他文件维护第二份 tag 表

## D.7 CI 持续复核与验证边界

三条 workflow 与本地脚本共用同一套口径，不另起一套校验逻辑：

| Workflow | 本地等价命令 | 触发 |
|---|---|---|
| `ci.yml` | `check-consistency.sh`、`materialize.py --check`、`validate-manifests.py`、`build_book.py`、kubeconform × 3 版本、`go vet/test/build`、`docker build/run` | push / PR / 手动 |
| `kind-matrix.yml` | `check-version-matrix.sh --mode ci --version V --cluster C` | 每周 / 基线变更 / 手动 |
| `references.yml` | `check-references.sh`、`check-links.py` | 每周 / 引用登记变更 / 手动 |

**清单分层的理由**：`validate-manifests.py` 把全书 YAML 按 `apiVersion` group 拆成逐文档文件。实测 91 个源文件拆出 131 份文档，其中内置资源 84 份、CRD 实例 37 份、Helm 模板 2 份、纯配置 8 份。只有内置资源能直接交给 kube-apiserver 的 server dry-run；CRD 实例需要先装控制器，Helm 模板要先渲染，`kind`/`Kustomization`/`Chart.yaml` 根本不是 K8s 对象。不分类就全量校验会产生大量假阳性，这在 `ci.yml` 里是硬失败来源。

**为什么 `kustomize build` 不进闸门**：`examples/by-chapter/` 是逐章增量，例如 `ch10/deploy/base/kustomization.yaml` 引用的 12 个资源分散在前面几章的目录里，按设计不可独立渲染。`ci.yml` 的 render job 只输出「引用 / 缺失」结构报告并写进 job summary，不计入闸门；可独立运行与渲染的是 `examples/order-demo/`，完整渲染请在对应章节 tag 检出仓库。

**CI 不覆盖的部分**：云厂商 LB / 存储 / IRSA 的真实行为、跨集群容灾、生产流量下的 HPA / KEDA 效果、长周期证书轮换，以及 Argo CD / Kyverno / Gateway API 控制器等需装 CRD 组件的运行时表现。这些章节的配置仍须按各章「验证与回滚」段在自有集群演练。**CI 通过 ≠ 生产可用**。
