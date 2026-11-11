# Runbook：CrashLoopBackOff（重点是先判「liveness 误杀」）

> 来源：ch23（症状速查表 CrashLoopBackOff 行、H4 误杀复盘）、ch08（探针语义）。
> 触发：`kubectl get pods` 出现 `CrashLoopBackOff`，或 5xx 与重启同时出现。

## 第一步：先判是「崩溃」还是「被误杀」（H4 判据）

```bash
kubectl -n order-demo-prod logs <pod> --previous          # 看上一世容器日志
kubectl -n order-demo-prod describe pod <pod> | grep -A3 'Liveness probe failed'
kubectl -n order-demo-prod get deploy api -o jsonpath='{.spec.template.spec.containers[0].livenessProbe.timeoutSeconds}'
```

**判为 liveness 误杀（不是真崩溃）当且仅当同时满足**：
1. `describe pod` 出现 `Liveness probe failed`，且时间戳**早于**首条 5xx；
2. `logs --previous` **无 panic、退出码 137**（是探针超时杀的，不是进程崩）；
3. `get deploy` 看到过紧的探针参数（如 `timeoutSeconds: 1`）。

反模式（ch23:145）：不带 `--previous` 读日志，看到空白就判「启动即崩」；或把 `failureThreshold` 调大当止血——那只是改了判定标准，没改事实。

## 第二步：止血动作

命中误杀 → **退回上一版探针配置**，而非调大重启次数：

```bash
kubectl -n order-demo-prod rollout undo deployment/api
```

未命中（真崩溃，有 panic 栈 / 非 137 退出码）→ 按应用日志定位崩溃原因，不要 rollback 探针。

## 第三步：防复发

- readiness 误摘会误导 HPA 扩容、liveness 重启风暴会喂脏数据给 HPA（ch08:205-207）——先修探针参数再谈扩容。
- 扩容前先确认新副本**不携带同一份坏探针**（ch23:369 退路原则）。
- 探针配置契约见 ch08；超时/阈值取值须来自压测分位数，禁止拍脑袋。

## 关联

- 容量 / QoS / 驱逐横向判读见 `docs/ops-quickref-node-and-remediation.md` A.1。
- 节点压力驱逐与 OOMKilled 的区别见该速查 A.1 二分起点。
