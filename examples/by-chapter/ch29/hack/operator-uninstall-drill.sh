#!/usr/bin/env bash
set -euo pipefail
# 仅评估演练集群执行；禁止对生产使用。
CTX="${1:?用法: $0 <演练集群 context>}"
NS=order-demo-eval
OPERATOR_NS=cnpg-system

echo "== 0) 确认是演练集群 =="
kubectl --context "${CTX}" config current-context | grep -qi 'eval\|drill'
! kubectl --context "${CTX}" config current-context | grep -qi 'prod'

echo "== 1) 列出 CR 与 finalizer 对象 =="
kubectl --context "${CTX}" -n "${NS}" get cluster -o wide || true
kubectl --context "${CTX}" -n "${NS}" get all,pvc -o json | python3 -c '
import sys, json
d = json.load(sys.stdin)
for item in d["items"]:
    fs = item.get("metadata", {}).get("finalizers", [])
    if fs:
        print(item["kind"], item["metadata"]["name"], fs)
'

echo "== 2) 先删 CR 实例，等清理 =="
kubectl --context "${CTX}" -n "${NS}" delete cluster order-demo-eval-db --wait=true --timeout=180s || true

echo "== 3) 检查残留 =="
kubectl --context "${CTX}" -n "${NS}" get all,pvc -o json | python3 -c '
import sys, json
d = json.load(sys.stdin)
stuck = [(i["kind"], i["metadata"]["name"]) for i in d["items"] if i.get("metadata", {}).get("finalizers")]
print("带 finalizer 的残留对象:", stuck)
if stuck:
    sys.exit(1)
'
kubectl --context "${CTX}" get crd | grep -i 'postgresql.cnpg.io' || true
kubectl --context "${CTX}" -n "${OPERATOR_NS}" get deploy || true

echo "== 4) 最后卸载控制器（生产须回 Git，见第 14 章） =="
echo "helm uninstall cnpg --namespace ${OPERATOR_NS}  # 或 git revert 安装 PR + argocd app sync --prune"
echo "卸载演练通过：无残留、finalizer 清空、PVC 按策略处置。"
