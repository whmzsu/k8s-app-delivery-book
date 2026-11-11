# order-demo runbook 索引

## 一、告警层（本章 ch22-alerts，接到告警先打开对应条目）
| 告警 | severity | runbook | 首步 |
|---|---|---|---|
| GatewayAvailabilityFastBurnPaging | paging | docs/runbooks/gateway-fast-burn.md | rollout undo + 观察 SLI 5 分钟 |
| GatewayAvailabilitySlowBurnTicket | ticket | docs/runbooks/gateway-slow-burn.md | 按 route/status_code 拉 6h SLI |
| GatewayBudgetExhausted | ticket | docs/runbooks/gateway-budget-exhausted.md | 核对 budget-report.sh 与例外登记 |

## 二、症状层（见第 23 章 ch23-chaos，6 份 runbook 模板）
| 症状 | runbook |
|---|---|
| Pending | docs/runbooks/pod-pending.md |
| CrashLoopBackOff | docs/runbooks/crashloop-backoff.md |
| OOMKilled | docs/runbooks/oomkilled.md |
| 5xx 突增 | docs/runbooks/http-5xx-spike.md |
| 证书过期 | docs/runbooks/cert-expired.md |
| 配置漂移 | docs/runbooks/config-drift.md |

## 三、互链规则
- 告警层 runbook 的「定位」小节必须链接到症状层对应 runbook。
- 症状层 runbook 的「升级路径」必须回链到 alertmanager.yaml 的 paging 路由。
- 每份 runbook 含五项：症状、定位命令、止血动作、验证方法、升级路径（模板见第 23 章）。
- 索引与规则同仓、同 PR，禁止在 Alertmanager UI 里新增入口。
