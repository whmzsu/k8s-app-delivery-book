# Runbook：OOMKilled 定位

适用：容器被重启 / 退出码 137 / 事件出现 OOMKilled。
前置：kubectl 已指向目标集群，命名空间 order-demo-{env}。

## 一、先分清两种「被杀」
- 容器内 OOM：cgroup memory limit 触顶，内核杀容器内进程；事件 Reason=OOMKilled，退出码 137。
- 节点压力驱逐：节点内存/磁盘不足，kubelet 驱逐整个 Pod；事件 Reason=Evicted，Pod phase=Failed。
两者命令不同、处置不同，先看事件 Reason 再动手。

## 二、三步定位
1. 看状态与上次终止原因：
   kubectl -n order-demo-dev describe pod <pod> | sed -n '/Last State/,+8p'
   kubectl -n order-demo-dev get pod <pod> -o jsonpath='{.status.containerStatuses[*].lastState.terminated.reason}{"\n"}'
2. 看事件时间线（区分 OOMKilled / Evicted / 探针误杀）：
   kubectl -n order-demo-dev get events --sort-by=.lastTimestamp | grep <pod>
3. 看 limit 与实际工作集口径：
   kubectl -n order-demo-dev get pod <pod> -o jsonpath='{range .spec.containers[*]}{.name}{"\t"}{.resources.limits.memory}{"\n"}{end}'
   kubectl -n order-demo-dev top pod <pod> --containers
   注意：limit 是容器级，Pod 内 sidecar、临时卷、page cache 都会计入工作集；
   「曲线峰值没到 limit」不等于没超限，要以 container_memory_working_set_bytes 为准（见第 21 章）。

## 三、处置
- 单次偶发：确认是冷启动/批量任务尖峰 → 按 17.2 用分位数重设基线，留突发余量。
- 持续发生：不要只调大 limit；先查泄漏，再决定是否扩容或改缓存策略。
- 节点级 Evicted：查 PriorityClass 与 QoS，确认是否 BestEffort 被优先驱逐。

## 四、回升验证
kubectl -n order-demo-dev rollout status deployment/api --timeout=120s
kubectl -n order-demo-dev get pod -l app.kubernetes.io/component=api \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.qosClass}{"\t"}{.status.containerStatuses[0].restartCount}{"\n"}{end}'
通过标准：无新增 OOMKilled 事件，restartCount 不再增长，/healthz 返回 200。
演练复现：./hack/oom-drill.sh（第 23 章速查表复用本 runbook）。

## 五、升级路径
- 单次偶发、回滚后稳定 → 记入本周变更，无需升级。
- 持续 OOM 且涉及容量扩容 → 转第 17 章资源基线与 LimitRange/ResourceQuota 调整。
- 节点级大规模 Evicted → 转第 25 章节点压力与 QoS 排查，必要时扩节点池。
