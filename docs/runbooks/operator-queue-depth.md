# Runbook：Operator 工作队列堆积

症状：告警 `OperatorQueueDepthHigh`（warning）。`workqueue_depth` 持续 > 50，
疑似 reconcile 中存在阻塞慢调用（第 28 章反模式一）。
前置：kubectl 指向目标集群；控制器为 order-demo-operator。

## 一、定位命令
```bash
# 看队列深度（对应告警 expr：max(workqueue_depth) > 50）
kubectl -n <operator-ns> logs deploy/<operator>-controller-manager --since=15m \
  | grep -i 'workqueue' | tail -20
# 看 reconcile 时延分布，定位慢调用
kubectl -n <operator-ns> logs deploy/<operator>-controller-manager --since=15m \
  | grep -i 'reconcile.*duration' | sort -t= -k2 -n | tail -10
# 看控制器资源是否受限（CPU throttle 会让 reconcile 变慢、队列堆积）
kubectl -n <operator-ns> top pod -l app.kubernetes.io/name=<operator>
```

## 二、止血动作
- 优先排查 reconcile 内的外部调用（API/数据库/Webhook）是否变慢或超时；临时提高控制器副本数缓解积压。
- 若是自身缺陷（无退避/无限重试）：按第 28 章反模式一修复 rate limiter 与超时，再发布。
- 避免直接删 Pod 制造更多待协调项。

## 三、验证方法
- `workqueue_depth` 回落到 50 以下并稳定（`for: 15m` 解除）；
- reconcile 时延分布回到基线，无持续堆积。

## 四、升级路径
- 单 CR 坏数据引发雪崩 → 转 `docs/runbooks/operator-reconcile-errors.md`；
- 控制器整体失联 → 转 `docs/runbooks/operator-silent.md`；
- 现成 Operator 同类问题 → 查 `docs/operator-degradation-plan.md`。
