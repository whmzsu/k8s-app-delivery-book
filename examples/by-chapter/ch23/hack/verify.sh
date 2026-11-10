
## 止血动作
1. 事件含 `Insufficient cpu/memory`：降副本回上一版 `kubectl -n order-demo-prod scale deploy/api --replicas=<上一版>`，再按第 18 章补容量。
2. 事件含 `untolerated taint` 或亲和冲突：回第 18 章核对拓扑，不在现场改生产调度字段。
3. 事件含 `unbound PVC`：查 `kubectl -n order-demo-prod get pvc`，转第 16 章，禁止删 db 的 PVC。

## 验证方法
`kubectl -n order-demo-prod rollout status deploy/api --timeout=120s` 正常结束；`./hack/verify.sh` 通过；`/readyz` 返回 200。

## 升级路径
15 分钟未恢复 → 按第 22 章 paging 升级平台负责人；涉及 db 的转第 16 章数据边界，不自行重建 StatefulSet。
