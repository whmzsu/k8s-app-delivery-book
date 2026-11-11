# Runbook：5xx 突增

症状：gateway 5xx 比例突增（对应第 22 章 `GatewayLatencyP99Symptom` 上下文与
第 23 章症状表「5xx 突增」）。用户请求开始失败。
前置：kubectl 指向 order-demo-prod；Trace/Loki 见第 21 章。

## 一、定位命令
```bash
# 看 SLI 与实时错误率
kubectl -n order-demo-prod get deployment/gateway -o jsonpath='{..image}{"\n"}'
# 取一个异常请求的 trace_id 下钻（第 21 章 exemplar）
# 到 Tempo / Loki 按 trace_id 查 api → db 耗时分布
```

## 二、止血动作（首步）
```bash
# 按第 13 章回滚方案先行：退回上一已知良好版本
kubectl -n order-demo-prod rollout undo deployment/gateway
```
- 预算耗尽时，按第 20 章冻结规则冻结非必要发布，走 `docs/slo-contract.md` 例外审批。
- 认领：按第 22 章 `docs/runbooks/gateway-fast-burn.md` 认领，不重复开第二工单。

## 三、验证方法
- 连续 30 次 `/healthz` 全 200；
- 5xx 比例回落到基线；
- 回滚后镜像为 `git-<OLD>` 且与 `docs/rollback-plan.md` 目标产物一致（第 13 章）。

## 四、升级路径
- 回滚无效 → 转第 17 章资源基线（是否 OOM/驱逐）与第 23 章事件响应；
- 需根因 → 取 trace_id 下钻 api / db / worker，按第 21 章信号链排查；
- 复盘 → `docs/postmortem-template.md`。
