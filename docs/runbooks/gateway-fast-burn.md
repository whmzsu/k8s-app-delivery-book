# Runbook：GatewayAvailabilityFastBurnPaging

症状：告警 `GatewayAvailabilityFastBurnPaging`（paging）。gateway 错误预算快燃尽，
1h 与 5m 双窗燃尽率均 `>= 14.4`，用户可感 5xx 正在快速消耗 28 天错误预算。
前置：kubectl 指向 order-demo-prod；Prometheus 地址见第 20 章 `budget-report.sh`。

## 一、定位命令
```bash
# 确认快燃尽判定成立
kubectl -n order-demo-prod get deployment/gateway -o jsonpath='{..image}{"\n"}'
./hack/budget-report.sh   # 看 SLI(28d) 与 错误预算消耗
# 看当前 5xx 比例
kubectl -n order-demo-prod logs deploy/gateway --tail=100 | grep -c ' 5[0-9][0-9] '
```

## 二、止血动作（首步，来自告警 first_action）
```bash
kubectl -n order-demo-prod rollout undo deployment/gateway   # 退回上一已知良好版本
```
观察 SLI 5 分钟，确认燃尽率回落。若 undo 后仍不恢复，按第 23 章事件响应升级。

## 三、验证方法
- `./hack/budget-report.sh` 中 `release_freeze` 仍为 0 或燃尽率明显回落；
- gateway 连续 30 次 `/healthz` 全 200；
- 5xx 比例回落到基线（见第 20 章 SLI 定义）。

## 四、升级路径
- 5 分钟未认领 → 升级至平台负责人；
- 15 分钟未恢复 → 按第 23 章启动事件响应；
- 若判定为容量/回归问题，转 `docs/runbooks/http-5xx-spike.md` 与第 17 章资源基线；
- 若预算已耗尽，转 `docs/runbooks/gateway-budget-exhausted.md`。
