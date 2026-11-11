# 一线速查：节点排障与存量整改

> 本文件抽取自正文相关章的排障路径与决策树，目的是让「凌晨 3 点被报警叫醒」时**按症状一次性找到可复制的命令与判读**，不用在各章之间来回翻。
> 每个小节都标注了内容来源章；更细的单症状 runbook 见 `docs/runbooks/` 下对应文件（已由正文 ch19/ch23 引用）。
> 本速查不引入任何新工具、不新增方法论，纯属「已有内容的汇一处」。

---

## A 节点 / 运行时排障

### A.1 Pod 消失或排不上：先判 Evicted 还是 Pending，再判 OOM 还是驱逐

**二分起点**（来自 ch17 图 17-1 / 表 17-6）：

```
Pod 没了 / 起不来
├─ phase=Failed + reason=Evicted
│   ├─ 事件含 MemoryPressure      → 节点内存压力驱逐；kubelet 排序：QoS 档 → 超出 requests 幅度 → priority
│   └─ 事件含 DiskPressure        → 节点磁盘（nodefs / inodes）驱逐；Guaranteed 不豁免
├─ phase=Failed + reason=OOMKilled（退出码 137）
│   → 容器内 cgroup memory.limit 触顶，与「节点驱逐」是两回事，先看事件 Reason 再动手（ch17:542-544）
└─ phase=Pending（没被驱逐，只是调度不上）
    → 调度器视角：PriorityClass 触发抢占，QoS 不参与（ch17:331-332）
```

**现场命令**（来自 ch17 / ch23）：

```bash
# 1) 事件流：确认是 Evicted / OOMKilled / Insufficient
kubectl -n order-demo-prod get events --sort-by=.lastTimestamp | tail -20

# 2) 节点资源账：确认是内存还是磁盘压力
kubectl -n order-demo-prod describe node <node> | grep -A6 Allocated
kubectl get nodes | grep -i 'pressure'        # 看有没有 MemoryPressure / DiskPressure

# 3) QoS 档核对（BestEffort 必被先驱逐，这是根因信号）
kubectl -n order-demo-prod get pod -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.qosClass}{"\n"}{end}'

# 4) 节点级驱逐演练（验证判读，非生产）
./hack/oom-drill.sh
kubectl -n order-demo-prod get events --sort-by=.lastTimestamp | grep -E 'Evicted|OOMKilled' || true
```

**三条铁律**（ch17:349-351，极易踩反）：
1. **PriorityClass 不是防驱逐开关**：节点压力驱逐第一顺位是「是否超出 requests」，第二才是优先级。想抗驱逐要抬 `requests`，不是抬 priority。
2. **PDB 只管主动（自愿）驱逐**：`drain` / Eviction API 受 PDB 约束；节点压力驱逐与容器 OOM **都不看 PDB**（ch08 / ch17）。
3. **QoS 不改变 OOM 阈值**：三档在 `memory.max` 面前平等，越线即杀。QoS 只改「节点内存不够时先杀谁」。

→ 详细单症状处置见 `docs/runbooks/pod-pending.md`（FailedScheduling）与 `docs/runbooks/crashloop-backoff.md`（liveness 误杀）。

---

### A.2 FailedScheduling：容量 / 污点 / 配额三类

**判定**（ch13:163、236-240）：

```bash
kubectl -n order-demo-prod describe pod <pod> | grep -A8 Events
# 典型输出：
#   0/3 nodes are available: 2 Insufficient cpu, 1 node(s) had untolerated taint {node.kubernetes.io/unschedulable: }
#   ... exceeded quota ...
```

| 事件关键词 | 含义 | 处置（ch13:170-174、237-240） |
|---|---|---|
| `Insufficient cpu` / `Insufficient memory` | 节点余量不够 | 扩容节点或回收余量（首选，控制器收敛式自动续跑）；或临时调大 `maxUnavailable`。**回滚本身也占 `maxSurge` 容量**，卡死时先腾容量再 `rollout undo` |
| `untolerated taint` / `unschedulable` | 节点在排水 / 维护 | 等排水结束，或先扩容补位；**不在现场改生产调度字段** |
| `exceeded quota` | 命名空间 ResourceQuota 触顶 | 查 `kubectl -n <ns> get resourcequotas`；配额上限低于 HPA 峰值会把扩容卡成 Pending（ch17:357） |

**容量账复核**（ch13:71-72、174），发布 / 扩容前必做：

```bash
kubectl describe nodes | awk '/^Name:/{n=$2} /^Allocated resources/{f=1} f{print n": "$0}'
# 逐节点 floor(单副本 requests) 后求和 ≥ 峰值 Pod 的 requests 之和，且余量不被邻居吃掉
```

---

### A.3 CoreDNS 解析失败：四跳定位 + 内外二分

**四跳链路**（ch19:473-495）：Pod → kube-dns（ClusterIP/53）→ CoreDNS Pod（OOM/重启）→ 上游 DNS。

```bash
# 第 1 跳：Pod 自己的 resolv.conf（默认 search 三域 + ndots:5）
kubectl -n order-demo-dev exec deploy/gateway -- cat /etc/resolv.conf
# 第 2 跳：kube-dns Endpoint 与 NetworkPolicy UDP/53
kubectl -n kube-system get endpoints kube-dns
# 第 3 跳：CoreDNS 自身是否 OOM / 重启循环
kubectl -n kube-system get pods -l k8s-app=kube-dns
# 第 4 跳：上游 DNS（只对外部域名失败）
kubectl run -it --rm dns-debug --image=busybox:1.36 --restart=Never -- nslookup order-demo.example.com
```

**二分判据**（ch19:495，一次对照实验收敛）：
- **内不通、外通** → 查第 1–3 跳
- **外不通、内通** → 查第 4 跳（上游 / VPC DNS）
- **全不通** → 先查第 1–2 跳

**指标判读**（ch19:506-512）：`kubectl -n kube-system port-forward` 到 9153，`coredns_dns_responses_total{rcode}` 中 `SERVFAIL` 持续增长指向第 4 跳；大量 `NXDOMAIN` 且集中在追加了 search 域后缀的名字，是 `ndots:5` 放大复发（ch19:312-313）。

→ 详细版见 `docs/runbooks/dns.md`。**注意**：默认拒绝 egress 后最先「看起来像 DNS 挂了」的，往往是 NetworkPolicy 没放通 `kube-dns:53`（ch19:308、572）。

---

### A.4 存储 / PVC：孤儿卷清理、PVC Pending、命名空间删不掉

**孤儿 PVC 清理（来自 ch07 7.1.1，DiskPressure 的常见根因）**：

```bash
# 1) 定位：DiskPressure 后，确认是哪类资源膨胀；Pod 已删但 PVC 仍 Bound
kubectl -n order-demo-prod get pvc
kubectl -n order-demo-prod get pod -l app=gw      # 为空 = 孤儿
# 2) 备份后再删（无备份严禁进下一步）
# 3) 逐个删 PVC → 4) StorageClass 为 Retain 时 PV 仍占后端，需 kubectl delete pv <name>
# 5) 校验：kubectl get nodes 无 DiskPressure
```

**PVC 一直 Pending**（ch07:615-623）：`kubectl get storageclass` 看是否有 `(default)`；无默认类则 PVC 永远 Pending。扩容先看 StorageClass `allowVolumeExpansion: true`（只能增大、不能缩小）。

**命名空间删不掉 / finalizer 卡住**（ch16:553-564）：`kubectl get namespace <ns> -o jsonpath='{.spec.finalizers}'` 仍含 `kubernetes` 说明有对象卡在删除流程，回到 L0 逐个找。**禁止对挂有 PVC 的 Pod 用 `--force --grace-period=0`**：强杀只让 kubelet 与 API Server 对卷回收状态产生分歧，留下更难清理的孤儿卷。

---

### A.5 节点失联 / NotReady：模拟与自愈

**人工模拟节点失联（ch18:777-799）**：cordon 后删 Pod（非驱逐 API，PDB 不拦截），验证 Endpoint 摘除与重排；`drain` 时驱逐受 PDB `ALLOWED DISRUPTIONS` 约束。

```bash
AZC_NODE=$(kubectl get nodes -l topology.kubernetes.io/zone=az-c -o jsonpath='{.items[0].metadata.name}')
kubectl cordon "${AZC_NODE}"
kubectl -n order-demo-dev get pods --field-selector "spec.nodeName=${AZC_NODE}" -o name | xargs kubectl -n order-demo-dev delete
# 复核：kubectl get nodes -L topology.kubernetes.io/zone；端点数随删除同步减少
```

**自愈演练（ch30:253）**：注入一个 `NotReady` 节点，15 分钟内被 MachineHealthCheck 自动替换；自愈演练没通过不算交付完成。升级就绪判据：`/readyz?verbose` 全 ok、DaemonSet `numberReady == desiredNumberScheduled`、`Pending Pod = 0`、`NotReady 节点 = 0`（ch30:108）。

---

## B 存量集群渐进整改

> 核心认知（ch25:37）：合规策略**不追溯已在运行的 Pod**——enforce 只拦「新建」，所以「全量 enforce 让存量集体起不来」是真实翻车案例。整改必须分阶段、先 Audit 后 Enforce，且每步可回退。

### B.1 策略合规（Kyverno / PSS）分阶段（ch25 阶段 1–3）

1. **阶段 1 · Audit 先行**：只为记录不拦截，先看清存量违规面，绝不一步 enforce。
2. **阶段 2 · 恢复容量**：旧 Pod 尚在的只需确认扩容通道恢复；旧 Pod 已删、新 Pod 起不来的立即重建（ch25:71-72）。
3. **阶段 3 · 收敛违规面**：Kyverno background scan 恢复后从 PolicyReport 导出违规清单，按命名空间分派修复——典型修复只是给存量工作负载补几行 `securityContext`（ch25:80）。

**排障第一问（ch25:756）**：Kyverno 崩溃式不可用时，HPA 扩容 / 滚动更新 / DaemonSet 回补全部停在 Pod 创建——症状与「策略拒绝」相同，但根因是「引擎死了」。区分两者是排障第一步。

### B.2 资源基线最小接入顺序（ch17:353）

顺序**不可反**：先 `LimitRange`（兜底）→ 再给各 Deployment 写 `resources`（契约值）→ 再 `ResourceQuota`（总量）→ 最后 `PriorityClass` 并在 Pod 模板加 `priorityClassName`。
- 先上 Quota 会让还没填 resources 的存量 Pod 触发准入统计异常；
- 先上 PriorityClass 而不填 requests，抢占行为建立在错误的 QoS 上。

### B.3 CRD / Operator 存量迁移（ch27 / ch28）

- 双版本 CRD 并存 + 转换 webhook 就绪后，再切 `storage`（ch28:42-47）；反过来做，存量对象读出来会被新 schema 拒绝，等于不可回退的数据事故。
- 升级 PR 合并**之前**，回滚三步命令（切回旧 `storage` → 恢复旧 `served: true` → 下线 webhook）就必须写在 PR 描述里（公理 6「回滚方案先于发布方案」在控制器层的形态，ch28:1576）。
- 存量对象重写是独立一步，不能和切 storage 合并（ch28:1452、1497）。

---

## 速查索引

| 症状 | 本速查 | 单症状 runbook | 来源章 |
|---|---|---|---|
| Pod Evicted / OOMKilled | A.1 | — | ch17 |
| Pod Pending（容量/污点/配额） | A.2 | `docs/runbooks/pod-pending.md` | ch13、ch23 |
| CrashLoopBackOff（liveness 误杀） | A.1 | `docs/runbooks/crashloop-backoff.md` | ch08、ch23 |
| DNS 解析失败 | A.3 | `docs/runbooks/dns.md` | ch19 |
| 孤儿 PVC / DiskPressure | A.4 | — | ch07、ch16 |
| 节点 NotReady / 失联 | A.5 | — | ch18、ch30 |
| 全量策略 enforce 翻车 | B.1 | — | ch25 |
| 资源基线补齐 | B.2 | — | ch17 |
| CRD 存量迁移 | B.3 | — | ch27、ch28 |
