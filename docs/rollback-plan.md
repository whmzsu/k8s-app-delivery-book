# 发布回滚方案（模板 · order-demo gateway）

| 要素 | 本次取值 |
|---|---|
| 触发条件 | 发布窗口内 gateway 5xx 比例连续 3 分钟 > 1%，或 /healthz 连续 5 次非 200 |
| 目标产物 | `registry.example.com/order-demo/gateway:git-1a2b3c4`（上一个已知良好 SHA） |
| 执行命令 | 滚动：`kubectl -n order-demo-prod rollout undo deployment/gateway --to-revision=${REV}`；蓝绿：`./deploy/bluegreen/switch.sh blue`；生产唯一合法路径为把等价改动提交 Git 后由 Argo CD 3.x 同步（见第 14 章） |
| 完成时限 | 决策后 5 分钟内流量 100% 回到稳定版，rollout status 超时上限 120s |
| 验证方式 | `kubectl -n order-demo-prod get deploy -o jsonpath='{..image}'` 为旧 SHA；连续 30 次 `/healthz` 全 200；5xx 比例回落到基线 |
| 责任人 | 发布值班（主）／ 服务 owner（备），姓名与联系方式随每次发布 PR 更新 |
| 演练记录 | `hack/rollback-drill.sh` 的输出归档到本次发布 PR 附件，未附记录禁止发布 |

## 数据边界
本次发布不涉及 schema 变更；若涉及，本方案作废，须先完成第 16 章 expand–contract
的共存验证，并在此处写明「旧版本可在新 schema 上服务」的证据来源。
