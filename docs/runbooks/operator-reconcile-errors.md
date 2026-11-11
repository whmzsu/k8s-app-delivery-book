# Runbook：Operator reconcile 持续报错

症状：告警 `OperatorReconcileErrors`（warning）。近 10 分钟 `controller_runtime_reconcile_errors_total`
速率 > 0，控制器可能无法收敛 CR（第 28 章指标表反模式一）。
前置：kubectl 指向目标集群；控制器为 order-demo-operator（第 28 章教学/平台场景）。

## 一、定位命令
```bash
# 看协调错误率（对应告警 expr）
kubectl -n <operator-ns> get --raw \
  /apis/custom.metrics.k8s.io/v1beta1/namespaces/<operator-ns>/pods/*/controller_runtime_reconcile_errors_total 2>/dev/null \
  || echo "（指标经 Prometheus 查询）"
# 看控制器日志，定位具体 CR / 字段
kubectl -n <operator-ns> logs deploy/<operator>-controller-manager --since=10m | tail -50
# 看 CR 状态条件
kubectl -n <tenant-ns> get <kind> <cr-name> -o yaml | sed -n '/status:/,/conditions:/p'
```

## 二、止血动作
- 先确认是否为「单 CR 坏数据」导致全量 reconcile 报错：隔离该 CR（删/暂停）观察错误率是否回落。
- 若为控制器缺陷：按第 28 章反模式一，检查 reconcile 中是否有阻塞慢调用（转 `operator-queue-depth.md`）。
- 升级引入：回退控制器版本 `helm rollback <release> <rev>` 或 `git revert` 升级 PR + `argocd app sync --prune`。

## 三、验证方法
- `controller_runtime_reconcile_errors_total` 速率回到 0 并持续 10 分钟（告警 `for: 10m` 解除）；
- 对应 CR `status.conditions` 出现 `Established=True` / `Reconciled=True`。

## 四、升级路径
- 数据面不受影响仍健康 → 按第 29 章降级预案 L0 观察，修复控制器；
- 控制器不可用 > 10 分钟 → 转 `docs/runbooks/operator-silent.md`（L1 降级）；
- 涉及现成 Operator → 查 `docs/operator-degradation-plan.md`。
