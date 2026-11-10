# 路径 A：自动回滚（常态）——由 Analysis 判定失败触发，无需命令
# 以上演练已覆盖

# 路径 B：手动兜底（自动判定未及时生效时）
kubectl argo rollouts -n order-demo-prod abort gateway
kubectl argo rollouts -n order-demo-prod undo gateway
kubectl argo rollouts -n order-demo-prod status gateway --watch=false

# 路径 C：回到 Git，让真相源与集群一致（生产唯一合法路径，见第 14 章）
OLD="<上一个已验证的 sha7>"
git revert <本次晋升 PR 的 merge commit>
git push origin main
argocd app sync order-demo-prod
./hack/render.sh prod "${OLD}"
