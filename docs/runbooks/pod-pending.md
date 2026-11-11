# Runbook：Pod 长期处于 Pending

> 来源：ch13（§13.2.1 处置 / §13.4 决策树）、ch23（症状速查表 Pod-Pending 行）、ch17（资源语义）。
> 触发：告警「Pod 未就绪」或 `kubectl get pods` 出现 `Pending` 超过预期。先止血、再判因、不在现场改生产调度字段。

## 第一步：取事件，定性是哪一类

```bash
kubectl -n order-demo-prod describe pod <pod> | grep -A8 Events
kubectl -n order-demo-prod get events --sort-by=.lastTimestamp | tail -20
```

典型事件与判定：

| 事件关键词 | 判定 | 处置 |
|---|---|---|
| `0/N nodes are available: M Insufficient cpu` | 节点可分配余量不足 | 扩容节点或回收余量（首选，控制器收敛式自动续跑）；临时调大 `maxUnavailable` |
| `... Insufficient memory` | 同上，内存维度 | 同上 |
| `node(s) had untolerated taint {node.kubernetes.io/unschedulable: }` | 节点在排水 / 维护 | 等排水结束或先扩容补位；**不在现场改生产调度字段** |
| `exceeded quota` | 命名空间 ResourceQuota 触顶 | `kubectl -n <ns> get resourcequotas`；配额上限低于 HPA 峰值会把扩容卡成 Pending（ch17:357） |

## 第二步：容量账复核（发布 / 扩容前必做）

```bash
kubectl describe nodes | awk '/^Name:/{n=$2} /^Allocated resources/{f=1} f{print n": "$0}'
# 逐节点 floor(单副本 requests) 后求和 ≥ 峰值 Pod 的 requests 之和
```

注意：余量随时被邻居吃掉，发布 PR 必须附当天的 `kubectl top nodes` 或 `describe node` 的 `Allocated resources` 段（ch13:174、CL-13-02）。

## 第三步：若此时必须回退

回退本身也是一次滚动，同样占 `maxSurge` 容量；卡死状态下 `rollout undo` 会卡在同一个 `FailedScheduling` 上。**先执行扩容 / 回收余量把容量腾出来，再走回滚路径**（ch13:172）。

## 关联

- 若为 PVC 未绑定导致的 Pending，转 ch16（PVC Pending / StorageClass 无 default），禁止删 db 的 PVC（ch23:217）。
- 容量 / QoS / 驱逐的横向判读见 `docs/ops-quickref-node-and-remediation.md` A.1、A.2。
