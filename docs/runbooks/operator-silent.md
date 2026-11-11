# Runbook：Operator 静默失效（无成功协调）

症状：告警 `OperatorNoSuccessfulReconcile`（critical）。近 10 分钟
`controller_runtime_reconcile_total{result="success"}` 增量为 0，
控制器可能已挂但业务静默降级（第 28 章反模式三）。
前置：kubectl 指向目标集群；控制器为 order-demo-operator。

## 一、定位命令
```bash
# 成功协调计数是否停滞（对应告警 expr）
kubectl -n <operator-ns> logs deploy/<operator>-controller-manager --since=10m | grep -c 'reconciled' || true
# 控制器 Pod 是否存活 / Restarting / OOMKilled
kubectl -n <operator-ns> get pod -l app.kubernetes.io/name=<operator> \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\t"}{.status.containerStatuses[0].restartCount}{"\n"}{end}'
# 数据面是否仍健康（控制器挂了业务不一定挂）
kubectl -n <tenant-ns> get <kind> <cr-name> -o jsonpath='{.status.conditions}'
```

## 二、止血动作
- 确认数据面仍在线（见第 29 章「业务会不会挂」判据）；业务在线则先观察、不盲目重启。
- 控制器 CrashLoop / OOM → 按第 17 章资源基线调整 limits，或回退到上一已知良好版本。
- 控制器不可用 > 10 分钟 → 按第 29 章降级预案 L1：副本缩到 0 冻结误动作，人工接管故障转移。

## 三、验证方法
- `controller_runtime_reconcile_total{result="success"}` 重新增长（告警 `for: 5m` 解除）；
- 关键 CR `status.conditions` 回到 `Reconciled=True`；数据面持续在线读写。

## 四、升级路径
- 现成 Operator 静默失效 → 查 `docs/operator-degradation-plan.md` 与 `docs/operator-assessment.md` 否决项；
- 自研控制器缺陷 → 按第 28 章反模式三修复后发布；
- 涉及备份/恢复能力归零 → 按第 16 章先确认最近 Completed 备份。
