# 已核验来源池（P2/P3 全书共用）

核验日期 2026-11-10 · 方式：HTTPS 直连返回 200（`/tmp/urlcheck_raw.txt` 原始结果）或检索核验存在
使用规则：**逐章 `references/chNN.yaml` 优先引用本池条目**；池外来源只写名称、`url: ""`、`status: pending_url`，禁止编造 URL（D-10）。附录 I 由 `references/*.yaml` 生成。

## 一、L1 规范与官方

### Kubernetes 官方文档（适用版本统一写 v1.32，小版本见附录 A）

| 标题 | URL |
|---|---|
| Controllers（控制循环） | https://kubernetes.io/docs/concepts/architecture/controller/ |
| Declarative Object Management | https://kubernetes.io/docs/concepts/overview/working-with-objects/object-management/ |
| Service | https://kubernetes.io/docs/concepts/services-networking/service/ |
| DNS for Services and Pods | https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/ |
| Secrets | https://kubernetes.io/docs/concepts/configuration/secret/ |
| Managing Resources for Containers | https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/ |
| Assigning Pods to Nodes | https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/ |
| Taints and Tolerations | https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/ |
| Pod Priority and Preemption | https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/ |
| Pod Security Standards | https://kubernetes.io/docs/concepts/security/pod-security-standards/ |
| StatefulSets | https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/ |
| Init Containers | https://kubernetes.io/docs/concepts/workloads/pods/init-containers/ |
| Operator pattern | https://kubernetes.io/docs/concepts/extend-kubernetes/operator/ |
| Configure Liveness, Readiness and Startup Probes（任务页，当前路径） | https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/ |
| Configure a Pod Disruption Budget | https://kubernetes.io/docs/tasks/run-application/configure-pdb/ |
| Configure a Security Context | https://kubernetes.io/docs/tasks/configure-pod-container/security-context/ |
| Debug Pods | https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/ |
| ValidatingAdmissionPolicy | https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/ |
| Server-Side Apply | https://kubernetes.io/docs/reference/using-api/server-side-apply/ |
| Best Practices（官方实践汇总） | https://kubernetes.io/docs/setup/best-practices/ |
| Cluster Logging Architecture | https://kubernetes.io/docs/concepts/cluster-administration/logging/ |

> **版本漂移提示**：旧路径 `.../configure-liveness-readiness-probes/` 与 `.../workloads/pods/probes/` 在本轮直连中超时，但检索核验存在。第 8 章请引用上表「任务页，当前路径」，并在 `note` 里记录旧路径与适用版本，供附录 A 版本矩阵使用。

### 其他规范与官方文档

| 标题 | 机构 | 级别 | URL |
|---|---|---|---|
| Gateway API（规范与文档站） | Kubernetes SIG Network | L1 | https://gateway-api.sigs.k8s.io/ |
| SLSA Specification v1.0 | OpenSSF / SLSA | L1 | https://slsa.dev/spec/v1.0/ |
| OpenTelemetry Specification | CNCF OTel | L1 | https://opentelemetry.io/docs/specs/otel/ |
| Prometheus Recording Rules | Prometheus | L1 | https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/ |
| Prometheus Alerting Rules | Prometheus | L1 | https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/ |
| Prometheus Instrumentation Practices | Prometheus | L1 | https://prometheus.io/docs/practices/instrumentation/ |
| NIST SP 800-190 Application Container Security Guide | NIST | L1 | https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-190.pdf |
| OpenSLO Specification | OpenSLO | L1 | https://github.com/OpenSLO/OpenSLO |
| Helm Documentation | Helm | L1 | https://helm.sh/docs/ |
| Kustomize Documentation | Kustomize | L1 | https://kustomize.io/ |
| Argo CD Documentation | Argo CD | L1 | https://argo-cd.readthedocs.io/en/stable/ |
| Kyverno Documentation | Kyverno | L1 | https://kyverno.io/docs/ |
| External Secrets Operator Docs | ESO | L1 | https://external-secrets.io/latest/ |
| kind Documentation | kind | L1 | https://kind.sigs.k8s.io/ |
| Kubebuilder Book | Kubebuilder | L1 | https://book.kubebuilder.io/ |
| Cluster API Book | Cluster API | L1 | https://cluster-api.sigs.k8s.io/ |
| conftest | Open Policy Agent | L1 | https://www.conftest.dev/ |
| Gateway API concepts（注意：`/concepts/api-overview/` 返回 404，改用站点首页下的 Concepts 导航） | Kubernetes SIG Network | L1 | https://gateway-api.sigs.k8s.io/ |
| CloudNativePG Documentation | CloudNativePG | L1 | https://cloudnative-pg.io/ |
| Strimzi Documentation | Strimzi | L1 | https://strimzi.io/ |
| Velero Documentation | Velero | L1 | https://velero.io/docs/ |
| Karpenter Documentation | Karpenter | L1 | https://karpenter.sh/ |
| KEDA Documentation | KEDA | L1 | https://keda.sh/ |
| Crossplane Documentation | Crossplane | L1 | https://crossplane.io/ |
| Backstage Documentation | Backstage | L1 | https://www.backstage.io/ |
| Chaos Mesh Documentation | Chaos Mesh | L1 | https://chaos-mesh.org/docs/ |
| Tilt Documentation | Tilt | L1 | https://tilt.dev/ |
| Sealed Secrets（GitHub 官方仓库） | Bitnami Labs | L1 | https://github.com/bitnami-labs/sealed-secrets |
| Kubernetes the Hard Way（官方教学仓库） | Kelsey Hightower | L2 | https://github.com/kelseyhightower/kubernetes-the-hard-way |
| Argo Rollouts Documentation（本轮直连超时，标 `pending_url`） | Argo | L1 | — |
| Flux Documentation（本轮直连超时，标 `pending_url`） | Flux CD | L1 | — |
| cert-manager Documentation（本轮直连超时，标 `pending_url`） | cert-manager | L1 | — |
| OpenGitOps Principles（本轮直连超时，标 `pending_url`） | GitOps WG | L1 | — |

## 二、L2 权威人士、著作与共识

| 标题 | 作者 / 机构 | URL / 状态 |
|---|---|---|
| The Twelve-Factor App · III. Config | 12factor.net / Heroku | https://12factor.net/config |
| BlueGreenDeployment | Martin Fowler | https://martinfowler.com/bliki/BlueGreenDeployment.html |
| CanaryRelease | Danilo Sato（martinfowler.com） | https://martinfowler.com/bliki/CanaryRelease.html |
| Continuous Delivery | Martin Fowler | https://martinfowler.com/bliki/ContinuousDelivery.html |
| Feature Toggles（Feature Flags） | Pete Hodgson / Martin Fowler | https://martinfowler.com/articles/feature-toggles.html |
| The USE Method | Brendan Gregg | https://www.brendangregg.com/usemethod.html |
| The RED Method | Tom Wilkie（Grafana Labs 博文） | https://grafana.com/blog/2018/08/02/the-red-method-how-to-instrument-your-services/ |
| Site Reliability Engineering（全书入口） | Google | https://sre.google/ （检索核验存在；直连经代理超时，P4 复核） |
| SRE Book《Monitoring Distributed Systems》 | Google | https://sre.google/sre-book/monitoring-distributed-systems/ （同上） |
| SRE Book《Embracing Risk》 | Google | https://sre.google/sre-book/embracing-risk/ （同上） |
| SRE Workbook《Implementing SLOs》 | Google | https://sre.google/workbook/implementing-slos/ （已检索核验，强烈推荐第 20 章使用） |
| SRE Workbook《Alerting on SLOs》 | Google | https://sre.google/workbook/alerting-on-slos/ （检索核验存在） |
| Borg, Omega, and Kubernetes | Burns / Grant / Oppenheimer / Brewer / Wilkes，ACM Queue 14(1), 2016 | 文献条目；正式链接待补（queue.acm.org 直连超时），标 `pending_url` |
| CNCF Cloud Native Security Whitepaper v2 | CNCF TAG Security | 正式链接待补（GitHub 路径返回 503），标 `pending_url` |
| Thoughtworks Technology Radar | Thoughtworks | https://www.thoughtworks.com/radar |
| OpenSLO（规范站点） | OpenSLO | https://www.openslo.com/ |

## 三、L3 案例与实证

| 标题 | 机构 | URL |
|---|---|---|
| CNCF Annual Survey 2023 | CNCF | https://www.cncf.io/reports/cncf-annual-survey-2023/ |
| CNCF Case Studies（栏目入口，具体案例按章选） | CNCF | 名称级候选，`pending_url` |
| 公开 postmortem 合集（如 postmortems 类公开复盘） | 各机构 | 名称级候选，`pending_url`；合成案例不得冒充真实事件 |

> 「合成案例」按 10.3 需显式标注，L3 只用于支撑反模式的**方法论**，不用于证明某次虚构事故真实发生。

## 四、排除项（不得写入书稿）

内容农场与 SEO 聚合站、非官方镜像站/转载站、厂商营销落地页（作为 L1/L2 时）、未标注版本或发布日期的二手教程。本轮命中 `https://gateway-api.sigs.k8s.io/concepts/api-overview/`（404）与 CNCF 白皮书 GitHub 路径（503），均已替换为候选或标 `pending_url`。

---

## 五、第二轮复核增补（2026-11-10，UA / 低并发复核）

首轮 `000` 多为代理并发与 UA 拦截，并非页面不存在。以下链接已复核为 200，**可升级 `pending_url` 为 `verified`**：

| 标题 | 级别 | URL |
|---|---|---|
| Kubernetes Concepts Overview | L1 | https://kubernetes.io/docs/concepts/overview/ |
| Deployments | L1 | https://kubernetes.io/docs/concepts/workloads/controllers/deployment/ |
| ConfigMaps | L1 | https://kubernetes.io/docs/concepts/configuration/configmap/ |
| Configuration Best Practices / Overview | L1 | https://kubernetes.io/docs/concepts/configuration/overview/ |
| Images / ImagePullPolicy | L1 | https://kubernetes.io/docs/concepts/containers/images/ |
| Custom Resources（概念页） | L1 | https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/ |
| Owners and Dependents（OwnerReference） | L1 | https://kubernetes.io/docs/concepts/overview/working-with-objects/owners-dependents/ |
| Node-pressure Eviction | L1 | https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/ |
| Topology Spread Constraints | L1 | https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/ |
| Ingress | L1 | https://kubernetes.io/docs/concepts/services-networking/ingress/ |
| Network Policies | L1 | https://kubernetes.io/docs/concepts/services-networking/network-policies/ |
| Jobs | L1 | https://kubernetes.io/docs/concepts/workloads/controllers/job/ |
| CronJobs | L1 | https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/ |
| DaemonSets | L1 | https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/ |
| Pod Lifecycle | L1 | https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/ |
| Sidecar Containers | L1 | https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/ |
| Pod Disruptions | L1 | https://kubernetes.io/docs/concepts/workloads/pods/disruptions/ |
| Liveness, Readiness, and Startup Probes（概念页） | L1 | https://kubernetes.io/docs/concepts/workloads/pods/probes/ |
| RBAC | L1 | https://kubernetes.io/docs/reference/access-authn-authz/rbac/ |
| Service Accounts | L1 | https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/ |
| Pod v1 API Reference | L1 | https://kubernetes.io/docs/reference/kubernetes-api/workload-resources/pod-v1/ |
| Horizontal Pod Autoscaling（任务页） | L1 | https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/ |
| Namespaces（任务页） | L1 | https://kubernetes.io/docs/tasks/administer-cluster/namespaces/ |
| Resource Quotas（任务页） | L1 | https://kubernetes.io/docs/tasks/administer-cluster/manage-resources/quota-memory-cpu-namespace/ |
| CRD（任务页） | L1 | https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/ |
| Probes（旧任务页路径，仅作版本漂移记录） | L1 | https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-probes/ |
| OpenGitOps Principles | L1 | https://opengitops.dev/ |
| OpenTelemetry Docs | L1 | https://opentelemetry.io/docs/ |
| Flux Documentation | L1 | https://fluxcd.io/flux/ |
| cert-manager Documentation | L1 | https://cert-manager.io/docs/ |
| Kubebuilder（站点） | L1 | https://kubebuilder.io/ |
| Borg, Omega, and Kubernetes（ACM Queue 14(1), 2016，DOI 入口） | L2 | https://dl.acm.org/doi/10.1145/2898442.2898444 |

> 仍无法直连但已通过检索/文献核验的**规范入口**（保留 URL 并在 `note` 里说明「直连经代理超时，P4 复核」，不算编造）：Google SRE 站点各页（`https://sre.google/`、`https://sre.google/sre-book/monitoring-distributed-systems/`、`https://sre.google/sre-book/embracing-risk/`、`https://sre.google/workbook/implementing-slos/`、`https://sre.google/workbook/alerting-on-slos/`）、Argo Rollouts 文档站（`https://argoproj.github.io/rollouts/`）、Google Research 论文页、`https://queue.acm.org/detail.cfm?id=2898444`（返回 403，已改用上表 DOI 入口）。

