# 链 1：先删 CR 实例，检查 finalizer（见第 27 章）
kubectl --context kind-order-demo-eval -n order-demo-eval \
  delete cluster order-demo-eval-db --wait=true
kubectl --context kind-order-demo-eval -n order-demo-eval \
  get all,pvc -o json | python3 -c '
import sys, json
d = json.load(sys.stdin)
print([(i["kind"], i["metadata"]["name"]) for i in d["items"] if i.get("metadata", {}).get("finalizers")])
'

# 链 2：回退 Operator 版本（生产须回 Git，公理 5，见第 3 章）
git revert <Controller 升级 PR 的 merge commit>
git push origin main
argocd app sync cnpg-system --prune
argocd app wait cnpg-system --health --timeout 120s
# 或 Helm 安装时：helm rollback cnpg <上一 rev> --namespace cnpg-system

# 链 3：业务侧兜底 —— 从备份恢复到新集群（第 16 章）
velero restore create --from-schedule order-demo-db --wait
./hack/restore-drill.sh kind-order-demo-drill "$(velero backup get -o json | \
  python3 -c 'import sys,json; print(json.load(sys.stdin)["items"][0]["metadata"]["name"])')"
