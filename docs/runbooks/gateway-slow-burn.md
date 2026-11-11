# Runbook：GatewayAvailabilitySlowBurnTicket

症状：告警 `GatewayAvailabilitySlowBurnTicket`（ticket）。存在慢性劣化，
6h 燃尽率 `>= 6`，需在工作时段排查，不半夜叫人。
前置：kubectl 指向 order-demo-prod；Grafana 占位域名见第 22 章。

## 一、定位命令（首步，来自告警 first_action）
```bash
# 拉取 6h 内按 route/status_code 分组的 SLI，定位劣化接口
kubectl -n order-demo-prod logs deploy/gateway --since=6h \
  | awk '{print $route, $status}' | sort | uniq -c | sort -rn | head
# 看慢燃尽指标
./hack/budget-report.sh
```

## 二、止血动作
- 本条为 `ticket` 级，不立即回滚；先定位劣化接口与时间点。
- 若劣化伴随明显错误，升级为 `docs/runbooks/http-5xx-spike.md` 处理。
- 若为资源/延迟劣化，转第 17 章资源基线与第 21 章 exemplar 下钻。

## 三、验证方法
- 6h 窗口内该 route 的错误率回落到基线；
- 下一次 `GatewayAvailabilitySlowBurnTicket` 不再触发（或周会复盘确认收敛）。

## 四、升级路径
- 确认为回归引入 → 按第 13 章回滚方案先行原则处理；
- 需跨团队协同 → 周会复盘，改进项登记见 `docs/postmortem-template.md` 第六节。
