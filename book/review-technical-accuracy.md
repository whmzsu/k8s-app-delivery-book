# 技术准确性评审报告（Technical Accuracy Review）

版本 `v0.2` · 2026-11-11 · 评审维度：技术事实准确性（第二遍：资源参数 / 命令 / 版本标注 / 探针端口）
基准：`book/case-evolution.md` 冻结配置契约 + `appendices/附录A-版本兼容矩阵.md` 版本基线（K8s 1.32+）+ 官方最佳实践。
审查范围：31 章初稿正文与 `examples/by-chapter/` 物料化示例。
交付对象：本评审只负责「发现 + 定位 + 给出修正 diff」，修复（含扩写）由运维专家执行。

## 一、已核查且正确的维度（非问题，记录以收窄范围）

| 维度 | 结论 |
|---|---|
| 端口口径 | gateway 8080 / api 8081 / db 5432 全书一致，无串用（ch06–31 抽查） |
| `latest` 标签 | 仅作为事故反模式与 CI runner `ubuntu-latest` 出现，所有示例镜像均为 `git-<sha7>`，无真实误用 |
| apiVersion | 全部为 1.32+ 正确版本：`apps/v1`、`v1`、`policy/v1`、`autoscaling/v2`、`networking.k8s.io/v1`、`gateway.networking.k8s.io/v1`、`external-secrets.io/v1beta1`、`kyverno.io/v1`、`postgresql.cnpg.io/v1`、`monitoring.coreos.com/v1` 等；未发现 `extensions/v1beta1`、`policy/v1beta1`、`autoscaling/v1`、`batch/v1beta1` 等废弃版本 |
| 探针路径 | `/healthz`(liveness) / `/readyz`(readiness) / `/startup`(仅 api) 与契约一致 |

## 二、确证问题清单

### TA-01 ｜ 高 ｜ ch14 ExternalSecret `target.name` 含非法字符 `/`

- **位置**：`chapters/ch14.md:449`；已蔓延至物料化示例 `examples/by-chapter/ch14/gitops/secrets/externalsecret.yaml:33`
- **问题**：`target.name: order-demo/db-credentials`。ESO 的 `spec.target.name` 即它将创建的 **Kubernetes Secret 对象名**，而 K8s Secret 名不能含 `/`（本书 ch26:205 已明确此规则，ch09/16/26 一致用连字符名 `order-demo-db-credentials`）。此清单 `kubectl apply` 会失败。
- **修正**：
  ```yaml
  # ch14.md 与示例文件
  target:
-   name: order-demo/db-credentials
+   name: order-demo-db-credentials
    creationPolicy: Owner
  ```
- **连带**：`ch14.md:462` 注释「`target.name` 即配置契约冻结的键名 `order-demo/db-credentials`」概念混淆——`target.name` 是 K8s Secret 对象名（连字符），Vault 路径在 `remoteRef.key`（见 ch09 模式）。建议改写与 ch26:205 对齐。

### TA-02 ｜ 高 ｜ ch29 CloudNativePG `bootstrap.initdb.secret.name` 含非法字符 `/`

- **位置**：`chapters/ch29.md:288`；注释在 `ch29.md:300`
- **问题**：`secret: name: order-demo/db-credentials` 同样是 K8s Secret 对象名，含 `/` 非法，应改 `order-demo-db-credentials`。与 ch16（StatefulSet 用 `order-demo-db-credentials`）、ch26 口径一致。
- **修正**：
  ```yaml
  # ch29.md
  bootstrap:
    initdb:
      secret:
-       name: order-demo/db-credentials
+       name: order-demo-db-credentials
  ```
- **连带**：`ch29.md:300` 注释「`secret.name` 沿用配置契约冻结键名 `order-demo/db-credentials`」需改为「K8s Secret 对象名用连字符 `order-demo-db-credentials`，Vault 路径仍是 `order-demo/db-credentials`」。
- **复核**：需确认 `examples/by-chapter/ch29/` 下 CNPG Cluster 物料化文件是否含同错（当前 grep 未在示例命中此名，可能未物化或已用别值；运维专家修章后重跑 `hack/materialize.py` 并核验）。

### TA-03 ｜ 中 ｜ ch18 worker Secret 名与冻结契约不一致

- **位置**：`chapters/ch18.md:321`
- **问题**：正文「此处 Secret 名取 `db-credentials` 并假设含 `connection` 键」。冻结契约（case-evolution 二节、ch09/16/26）统一为 `order-demo-db-credentials`（带 `order-demo-` 前缀）。虽 `db-credentials` 是合法 K8s 名，但与全书命名约定不符，且与本句前半「连接凭据来自契约里的 `order-demo/db-credentials`」自相矛盾（前半说用契约 Vault 路径，后半却给了一个不同的 Secret 名）。
- **修正（二选一，建议前者）**：
  1. 统一为 `order-demo-db-credentials`，与 ch09/16/26 完全相同；
  2. 若 worker 确实用独立队列凭据，显式改名（如 `order-demo-worker-queue`）并在 ch09 注入方案处登记，避免读者误以为是 db 凭据。
- **连带**：`ch18.md:321` 前半句「连接凭据来自契约里的 `order-demo/db-credentials`（由 ESO 注入、不入 Git，见第 9 章）」与后半句命名冲突，需两句口径统一。

### TA-04 ｜ 低 ｜ ch04 检查清单把 Vault 路径称为「Secret 名称」

- **位置**：`chapters/ch04.md:381`
- **问题**：`CL-04-05`「检查三环境 `Secret` 名称与注入来源（占位 `order-demo/db-credentials`）」。此处 `order-demo/db-credentials` 是 Vault 键路径（含 `/`），不是 K8s Secret 对象名；称其为「Secret 名称」与 ch26:205「K8s Secret 对象名不能含 `/`」观感冲突。
- **修正**：改为「检查三环境 Secret 对象名（`order-demo-db-credentials`）与注入来源（Vault 路径 `order-demo/db-credentials`）」，与 ch26:205 措辞对齐。

### TA-05 ｜ 中 ｜ 根因：Vault 路径与 K8s Secret 名的混淆表述

- **位置**：`ch14.md:462`、`ch29.md:300`（注释），以及契约外多处把 `order-demo/db-credentials` 直接等同于「Secret 名」。
- **问题**：这是 TA-01/TA-02 的根因——把 Vault/ESO 的**键路径**（含 `/`，如 `remoteRef.key`、CNPG 引用的后端路径）与 **K8s Secret 对象名**（连字符）混为一谈。ch26:205 已给出权威澄清句，但 ch14/29 未对齐。
- **修正**：在 ch14、ch29、ch04 的此类表述处，统一采用 ch26:205 的口径：「Vault/后端路径为 `order-demo/db-credentials`（可含 `/`），K8s Secret 对象名用连字符 `order-demo-db-credentials`」。

### TA-06 ｜ 复核后撤回 ｜ ch18:419 资源块实为 `load-gen` 压测容器，非 worker

- 初查曾怀疑 `ch18.md:421-425`（requests `cpu:50m,memory:32Mi`；limits `cpu:200m,memory:64Mi`）与 `ch17.md:56` worker 基线（`cpu:50m/300m`、`memory:64Mi/192Mi`）冲突。
- 复核 `ch18.md:408-418` 明确该容器 `name: gen`、`component: load-gen`、`image: busybox:1.36`（压测发生器），**不是 worker**。故不存在 worker 资源冲突；`busybox:1.36` 为偶然示例镜像、显式锁版本属正确做法，不计入一致性缺陷。
- 结论：撤回该疑似项，不计入确证问题。

### TA-07 ｜ 中 ｜ ch29 CNPG 集群 `spec.resources` 与 ch17 db 基线矛盾

- **位置**：`chapters/ch29.md:291-297`（`Cluster.spec.resources`，即 Postgres 实例本身）。
- **问题**：ch29 把 db 实例设为 requests `cpu:100m,memory:128Mi` / limits `cpu:500m,memory:256Mi`（Burstable）；而 `ch17.md:55` 的 db 基线为 requests==limits `cpu:250m,memory:512Mi`（**Guaranteed**，"有状态、不可丢"）。同一组件（数据库）在两章资源画像与 QoS 类别直接冲突。
- **修正（二选一，建议前者，因 ch17 是资源基线权威章）**：
  1. ch29 `spec.resources` 改为 `cpu: 250m, memory: 512Mi`（requests==limits，Guaranteed），与 ch17:55 逐字对齐；
  2. 若演练确因最小集群资源紧张需缩配，在 ch29 显式加注「本演练 db 缩配至 Burstable 的原因，已偏离 ch17 基线，生产须回 Guaranteed」，避免读者误以为 db 可随意 Burstable。
- **连带**：ch29:300 注释「`secret.name` 沿用配置契约冻结键名」同时涉及 TA-02 的 `/` 修正（见 TA-02）。

### TA-08 ｜ 中 ｜ ch13/14/15 的 `gateway` 资源与 ch17 gateway 基线不一致

- **位置**：`ch13.md:162-168`、`ch14.md:365-371`、`ch15.md:313-319` 与 `ch15.md:404-410`（三章的 `gateway` Deployment/Rollout 资源块）。
- **问题**：三章均给 `gateway` 配 requests `cpu:100m,memory:128Mi` / limits `cpu:500m,memory:256Mi`；而 `ch17.md:54` 的 gateway 基线为 requests `cpu:50m,memory:64Mi` / limits `cpu:500m,memory:128Mi`。请求与限制的内存均翻倍（64Mi→128Mi、128Mi→256Mi），CPU 请求也翻倍（50m→100m）。组件中 `name: gateway`、端口 `8080`、镜像 `.../gateway` 均正确指向 gateway，故这是**纯资源数值不一致**，非端口/命名错误。
- **说明**：冻结配置契约（`case-evolution.md:31`）仅明文锁定 **api** 基线，gateway/worker/db 基线属 ch17 自陈扩展；但 ch17 被定位为「资源基线权威章」，后续章与其数值冲突仍属内部不一致，建议统一。
- **修正**：将 ch13/14/15 的 gateway 资源块改为 ch17:54 口径（`cpu:50m,memory:64Mi` → `cpu:500m,memory:128Mi`），或在 ch13 首次出现处加注「gateway 资源采用与 ch17 不同画像的原因」。
- **连带**：ch13/14/15 的 gateway 用数值端口 `port: 8080`（ch14 同时用命名端口 `name: http` + `port: http`），本身合法，与 ch17 无关。

## 三、移交与验证建议

1. 运维专家按 TA-01～TA-05 修章，并**重跑 `python hack/materialize.py`** 重新物化 `examples/by-chapter/`。
2. 修复后建议跑一次 `examples/by-chapter/ch14/gitops/secrets/externalsecret.yaml` 与 ch29 CNPG Cluster 的 `kubectl apply --dry-run=server`（或并入 P5 的 kind-matrix 演练），确认 `/` 问题不再出现。
3. 一致性闸门 `./hack/check-consistency.sh` 与 `check-version-matrix.sh` 对 Secret 名无硬校验，建议后续在 `strong-pairs` 或一致性脚本里加一条「K8s 对象名不得含 `/`」的横扫规则，防止回归。

## 四、审查进度与待续维度

| 维度 | 状态 | 结论 |
|---|---|---|
| 端口口径 | ✅ 已覆盖 | 干净（TA-00，第一遍） |
| `latest` 标签 | ✅ 已覆盖 | 干净 |
| apiVersion / 废弃版本 | ✅ 已覆盖 | 干净 |
| 探针路径 | ✅ 已覆盖 | 干净 |
| Secret 名称含 `/` | ✅ 已覆盖 | **TA-01~05 确证**（高/中/低） |
| 命名端口 `port: http` | ✅ 已覆盖 | 干净（ch08/09/18 均定义 `name: http`） |
| 命令正确性（kubectl/crane/argocd） | ✅ 已覆盖 | `argocd app rollback` 在 2.x 仍合法（readthedocs 2.9 文档化），本书表述正确；余无拼写/参数错误 |
| 资源参数（requests/limits 一致性） | ✅ 已覆盖 | **TA-07/TA-08 确证**（内部不一致）；TA-06 误报已撤回 |
| 正文工具版本 vs 附录 A | ✅ 已覆盖 | 干净（正文仅主版本写法，符合 A.1 L89） |
| 镜像仓库路径 / `git-<sha7>` 标签 | ✅ 已覆盖 | 干净 |
| RBAC `verbs: []` | ✅ 已覆盖 | 前序 D-29 已修复，本轮未复发 |

**待续（建议后续轮次或运维专家扩写时顺带自查）**：
- HPA `behavior`（缩容冷却/稳定窗口）、PDB `minAvailable`/`maxUnavailable` 数值与第 17 章 Quota 的算术自洽（ch13/17/18 跨章核对）。
- `kuttl` / `helm template` / `argocd app wait --health` 等命令参数的真实可用性（建议进 P5 kind-matrix 真实集群演练核验）。
- 观测指标名（Prometheus 3.x 记录规则、OTel 信号名）与第 20–22 章是否一致。
- 引用 `[R-NN-x]` 角标与 `references/chNN.yaml` 闭环（属「一致性」维度，非本评审）。
- 26 条 `pending_url` 链接复核（属独立待办，非本评审）。

## 五、第二遍已核查维度（非问题，避免重复劳动）

- **`argocd app rollback`**：Argo CD 2.9 官方仍文档化该命令（`argo-cd.readthedocs.io/en/release-2.9/.../argocd_app_rollback`）；且本书已正确表述为「临时止血，之后必须补等价 PR 否则产生新漂移」（ch14:565、ch15、ch16、ch23），**非错误**。
- **探针命名端口**：ch08:180/286、ch09:260、ch18:183 容器均定义 `name: http`，与探针 `port: http` 同源，合法。
- **正文工具版本写法**：仅用主版本（如 `Argo CD 2.x`、`Kustomize 5.x`、`cosign 2.x / Syft 1.x / Trivy 0.x`、`crane 0.x`），与附录 A 一致；未发现具体小版本违规（符合 A.1 L89「正文出现具体小版本即视为一致性缺陷」的逆向判据）。
- **探针路径分布**：liveness=`/healthz`、readiness=`/readyz`、startup=`/startup`（仅 api，见 ch08:293、ch09:268、ch18:193），全书一致。
- **端口归属**：ch13/14/15 的 `port: 8080` 均属 `gateway`（name/镜像/端口自洽），**非 api 错配**；gateway=8080 / api=8081 / db=5432 三端口全书无串用。
- **load-gen vs worker**：ch18:419-425 为 `busybox:1.36` 压测容器（`component: load-gen`），不计入 worker 基线，无需对齐 ch17 worker 值。

