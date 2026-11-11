# 附录 A　版本兼容矩阵

> 全书正文只写主版本（如 `Helm 4.x`、`Kustomize 5.x`），**具体小版本、API 版本与破坏性变更集中在本附录**。所有示例在 kind 的 K8s 版本矩阵中验证（见第 11 章），版本差异不写进正文。每章配置块标注的「适用版本」都指向本表行号。

## A.1 基线（本书写作时锁定）

| 行 | 组件 | 基线版本 | 本书用途 | 对应章 |
|---|---|---|---|---|
| A-01 | Kubernetes | **写作基线 1.32+**；静态 schema 矩阵 1.32.0 / 1.33.0 / 1.34.0 / 1.37.0；真集群矩阵 1.32.2 / 1.34.11 / 1.37.0 | 全部 YAML 的 `apiVersion` 与字段语义 | 全书 |
| A-02 | kind | **v0.27.0**（配 1.32.2）/ **v0.33.0**（配 1.34.11、1.37.0），与 node 镜像成对锁定 | 本地集群与多版本验证 | 6、11 |
| A-03 | kubectl | 与集群版本偏差不超过 1 个次版本 | 全部命令示例 | 全书 |
| A-04 | Go 工具链 | 1.23（仅 `order-demo` 示例） | 第 6 章最小镜像构建 | 6 |
| A-05 | distroless static | `static-debian12:nonroot`（digest 锁定） | 非 root 运行镜像 | 6、24 |
| A-06 | Docker / BuildKit | 24.x+ 或兼容 OCI 构建器 | 构建与 `kind load` | 6、12 |
| A-07 | Helm | 4.x（`Chart apiVersion: v2` 不变） | 对外分发 Chart | 10、14 |
| A-08 | Kustomize | 5.x | 多环境 overlay 基线 | 4、10、14 |
| A-09 | Argo CD | 2.x | GitOps 唯一示例实现 | 14、30 |
| A-10 | Flux | 2.x | 仅选型矩阵对比 | 14 |
| A-11 | Argo Rollouts | 1.x + Gateway API traffic router 插件 | 渐进式交付 | 15 |
| A-12 | Gateway API | v1（GA 通道） | 流量入口；实现为 Envoy Gateway | 15、19、21、30 |
| A-13 | Envoy Gateway | 1.x | U-05 唯一示例实现 | 15、19 |
| A-14 | Istio | 1.x | 仅选型矩阵对比 | 19 |
| A-15 | cert-manager | 1.x | 证书自动化 | 19、29 |
| A-16 | Kyverno | 1.x | U-04 唯一示例实现（策略与验签） | 24、25 |
| A-17 | ValidatingAdmissionPolicy | K8s 1.30+ 内置 | 轻量内置对比方案 | 25 |
| A-18 | Gatekeeper | 3.x | 仅选型矩阵对比 | 25 |
| A-19 | External Secrets Operator | 0.x（API 仍在演进，升级前查 CRD 迁移） | 密钥注入 | 9、14、26 |
| A-20 | CloudNativePG | 1.x | 第 29 章 Operator 成熟度评估对象 | 16、29 |
| A-21 | Velero | 1.x | 备份恢复演练 | 16 |
| A-22 | Prometheus | 3.x | 指标与 SLO 记录规则 | 20、21、22 |
| A-23 | OpenTelemetry Collector | 0.x（contrib 与 core 分发需分开锁） | 链路/日志/指标采集 | 21 |
| A-24 | Loki / Tempo | 3.x / 2.x | 日志与链路存储 | 21 |
| A-25 | Thanos | 0.x | 长期指标（或兼容远端存储） | 21 |
| A-26 | Chaos Mesh | 2.x | 演练唯一示例实现 | 23 |
| A-27 | KEDA | 2.x | 事件驱动弹性 | 18 |
| A-28 | Karpenter | 1.x | 节点弹性 | 18 |
| A-29 | Kubebuilder | 4.x | 第 28 章 Operator 骨架（平台团队可选） | 28 |
| A-30 | Crossplane / Cluster API / Backstage / Score | 各自 1.x / 1.x / 1.x / 规范 v1 | 第 30 章平台化 | 30 |
| A-31 | Syft / Trivy / cosign | 1.x / 0.x / 2.x | SBOM / 扫描 / 签名验签 | 24 |
| A-32 | SLSA | v1.0 | 供应链等级 | 24 |
| A-33 | OpenSLO | 规范 v1 | SLO 定义 | 20 |
| A-34 | kubeconform | **v0.6.7**（`ci.yml` 的 `KUBECONFORM_VERSION` 锁定） | 三版本 schema 校验 | 11 |
| A-35 | PyYAML | **6.0.2**（`hack/requirements.txt` 锁定） | 清单逐文档拆分与结构断言 | 11 |
| A-36 | GitHub Actions runner | `ubuntu-latest`；Go **1.23**、Python **3.12** | 快车道闸门与全书装配 | 11、附录 D |
| A-37 | kind / kubectl（CI） | kind 版本与 `kindest/node` 镜像**成对锁定**（见 A-02）；kubectl 与集群 patch 版本一致，下载地址 `dl.k8s.io/release/v<k8s>/bin/linux/amd64/kubectl` | P5 真集群复核 | 11 |
| A-38 | Helm / kustomize（CI） | Helm **4.3.1**（`azure/setup-helm@v4` 的 `version` 入参显式固定——该 action 默认装「最新」，版本会随上游漂；固定值随主版本基线升级，见 D-38/D-40）；kustomize 不作独立渲染闸门，原因见 D.7 | 模板渲染与 overlay 结构报告 | 10、11 |

## A.2 关键 API 版本与字段

| 资源 / 字段 | `apiVersion` | 稳定状态 | 版本注意 |
|---|---|---|---|
| Deployment / StatefulSet / DaemonSet | `apps/v1` | GA | 老教程里的 `extensions/v1beta1`、`apps/v1beta2` 均已移除 |
| Job / CronJob | `batch/v1` | GA | `batch/v1beta1` CronJob 自 1.25 起不可用 |
| PodDisruptionBudget | `policy/v1` | GA | `policy/v1beta1` 自 1.25 起不可用 |
| Ingress | `networking.k8s.io/v1` | GA | 本书只在第 19 章作演进对比，新增入口一律用 Gateway API |
| Gateway / HTTPRoute | `gateway.networking.k8s.io/v1` | GA（v1 通道） | 实现必须声明支持 v1；实验性通道字段不得进生产清单 |
| NetworkPolicy | `networking.k8s.io/v1` | GA | 默认拒绝行为依赖 CNI 实现，见第 19 章验证命令 |
| HorizontalPodAutoscaler | `autoscaling/v2` | GA | `autoscaling/v2beta2` 已移除 |
| ValidatingAdmissionPolicy | `admissionregistration.k8s.io/v1` | GA（1.30+） | 低版本集群不可用，见第 25 章降级路径 |
| CRD | `apiextensions.k8s.io/v1` | GA | 必须带 schema 与版本迁移路径，见第 27、28 章 |
| Service / ConfigMap / Secret / Namespace | `v1` | GA | — |
| EndpointSlice | `discovery.k8s.io/v1` | GA | readiness 摘流的实际作用对象，见第 8 章 |
| Pod `sidecarContainers`（原生 sidecar） | `v1` | GA（1.29+） | 低版本须退回 initContainer 模式，见第 7 章 |

## A.3 已知破坏性变更与复核触发点

| 触发条件 | 受影响章 | 必须复核的内容 |
|---|---|---|
| K8s 次版本升级（含 1.32 → 1.33/1.34） | 全书 | `apiVersion`、探针默认行为、`terminationGracePeriodSeconds` 与 sidecar 终止顺序、PDB 语义 |
| Gateway API 通道升级 | 15、19、21、30 | `GatewayClass`/`HTTPRoute` 字段、traffic router 插件兼容性 |
| Argo CD / Argo Rollouts 大版本 | 14、15 | ApplicationSet 生成器、插件 API、Analysis 指标名 |
| ESO / CloudNativePG CRD 升级 | 9、16、29 | CRD schema 迁移、`conversion webhook`、备份兼容性 |
| Prometheus 3.x 与 OTel Collector 升级 | 20、21、22 | 记录规则语法、指标重命名、采样配置 |
| Kyverno / cosign 升级 | 24、25 | 策略 schema、验签规则、镜像签名格式 |
| Helm 3.x → 4.x | 10、14、30 | **chart 不用重写**：`apiVersion: v2` 原样可用，Helm 4 就地接管 Helm 3 的 release 记录。要改的是**围绕它的自动化**：`--atomic`→`--rollback-on-failure`、`--force`→`--force-replace`（旧名仍可用但告警）；`--post-renderer` 只接受插件名、不再接受脚本路径；`helm registry login` 只接受裸域名（不带 `https://`）；`--wait` 改用 kstatus 判断就绪，**RBAC 需要 `watch` 动词**，否则 `install/upgrade --wait` 立即失败；新装的 release 默认 server-side apply（既有 release 沿用原 apply 方式） |
| 官方文档路径迁移 | 8 及引用章 | 探针任务页等官方路径已多次迁移，见 `references/_verified.md` 版本漂移提示 |

## A.4 复核节奏与执行方式（P5 已迁移到 GitHub Actions）

| 频率 | 由谁执行 | 命令 / workflow | 产出 |
|---|---|---|---|
| 每次 push / PR | `ci.yml` | `check-consistency.sh`、`materialize.py --check`、`validate-manifests.py`、kubeconform × 4 版本、Go/Docker 冒烟、Helm 渲染 | job summary + 全书 Markdown artifact |
| 每周一 / 示例基线变更 / 手动 | `kind-matrix.yml` | `check-version-matrix.sh --mode ci` × K8s 1.32.2（kind v0.27.0）/ 1.34.11、1.37.0（kind v0.33.0） | server dry-run 日志、集群事件、演练结论 |
| 每周一 / 引用登记变更 / 手动 | `references.yml` | `check-references.sh`、`check-links.py` | 外链报告 TSV、失败清单 |
| 每季度 | 人工 | 复核 `references/*.yaml`、`pending_url` 逐条补正式入口 | 失效链接切 `archive_url` 并在附录 I 标「已归档」 |

1. **K8s 大版本发布后**：改 `ci.yml` 的 `matrix.k8s`、`kind-matrix.yml` 的 `matrix.include`（k8s / kind / role 三项与 dispatch 的 `single_version` 选项），按 A.3 表逐项复核，把结果写回本附录。`kindest/node` 镜像 tag 由 `kind-matrix.yml` 预检步骤强制校验，不存在会直接失败，**不会静默跳过**。
2. **为什么静态矩阵与真集群矩阵不同**：kubeconform 的 JSON schema 覆盖任意版本，可以完整验证书稿声称的 1.32 / 1.33 / 1.34 窗口并延伸到当前稳定版；而 kind 对旧 K8s 有支持窗口——v0.33.0 只提供 1.34.11 及以上的 node 镜像，1.32 基线必须用 v0.27.0（其 release notes 明确列出 `kindest/node:v1.32.2`）。因此真集群矩阵按「kind 版本 + node 镜像成对锁定」，用 1.32.2 覆盖最低基线、1.34.11 覆盖书稿上界、1.37.0 覆盖当前稳定版。**这是 P5 复核发现的真实版本漂移**：原稿写的 `1.32.0 / 1.33.0 / 1.34.0` 与当前 kind 支持窗口已错位，正文因只写主版本而不受影响。
3. **清单校验分两层**：`examples/order-demo/deploy/base/` 是硬闸门（strict schema + 真实 apply + 演练）；`examples/by-chapter/` 的逐章增量片段按「软报告」处理，失败清单上传 artifact 并设阈值 `SOFT_LIMIT`，超过阈值才失败——因为它脱离对应章节 tag 的仓库状态本就不保证可独立应用。
4. **任何工具小版本变更**：只改本附录、CI 环境变量与配置文件，不改正文；正文出现具体小版本即视为一致性缺陷。
5. **版权与引用**：只引用与摘要，不整段转载；图表自行重绘并注明数据来源。
6. **CI 不能覆盖的部分**（云厂商 LB/存储/IRSA、跨集群容灾、生产流量下的弹性、长周期证书轮换、需装 CRD 的控制器行为）仍须读者按各章「验证与回滚」段在自有集群演练，不得把 CI 通过等同于生产可用。
