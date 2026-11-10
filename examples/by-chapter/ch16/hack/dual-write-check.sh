# 链 1：应用侧回滚（与第 13 章相同）
REV="$(kubectl -n order-demo-prod rollout history deployment/api | tail -n2 | head -n1 | awk '{print $1}')"
kubectl -n order-demo-prod rollout undo deployment/api --to-revision="${REV}"
kubectl -n order-demo-prod rollout status deployment/api --timeout=120s

# 链 2：schema 侧 —— 只回退到「上一个共存阶段」，禁止逆向 DROP
# 双写阶段出问题：删触发器、保留新列，应用退回 v1（v1 仍读旧列）
kubectl -n order-demo-prod exec db-0 -- psql -U postgres -d orderdemo -v ON_ERROR_STOP=1 \
  -c "DROP TRIGGER IF EXISTS orders_dual_write ON orders; DROP FUNCTION IF EXISTS orders_dual_write();"
# 已到 contract：不可逆，唯一回退是把数据从备份恢复到新集群再切流

# 链 3：数据侧 —— 从备份恢复（生产唯一合法路径仍须回到 Git，见第 14 章）
velero restore create --from-schedule order-demo-db --wait
# 或恢复到演练/新集群做验证：./hack/restore-drill.sh <context> <backup>

# 生产真相源：把 StatefulSet 与迁移脚本的回退写成 PR，由第 14 章控制器同步
git revert <迁移 PR 的 merge commit>
git push origin main
argocd app sync order-demo-prod
