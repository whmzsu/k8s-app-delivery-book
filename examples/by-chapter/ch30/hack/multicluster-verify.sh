# 链 1：应用变更回滚（一次 revert 同时作用于两个 Application）
git revert <晋升 PR 的 merge commit>
git push origin main
argocd app sync --prune order-demo-prod-cluster-a
argocd app sync --prune order-demo-prod-cluster-b
argocd app wait order-demo-prod-cluster-a --health --timeout 120s
argocd app wait order-demo-prod-cluster-b --health --timeout 120s

# 链 2：集群供应侧回退 IaC 版本，按 30.2 顺序逆向执行
#   逆向 = 先生产集群 b → 再 canary 集群 a → 最后管理集群；控制面先于节点
git revert <集群升级 PR 的 merge commit>
terraform -chdir=infra plan
terraform -chdir=infra apply

# 链 3：若只回退某一个集群的发布（不回退 Git 真相源），
#   仅允许作为有有效期、有责任人的冻结窗口，且窗口结束必须补等价 PR（见第 14 章）
