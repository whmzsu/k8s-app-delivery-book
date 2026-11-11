#!/usr/bin/env bash
set -euo pipefail
NS=order-demo-dev

echo "== Deployment =="
kubectl -n "${NS}" get deploy gateway \
  -o jsonpath='{.metadata.name}{" | uid="}{.metadata.uid}{"\n"}'

RS=$(kubectl -n "${NS}" get rs \
  -l app.kubernetes.io/component=gateway \
  -o jsonpath='{.items[0].metadata.name}')
echo "== ReplicaSet =="
kubectl -n "${NS}" get rs "${RS}" \
  -o jsonpath='{.metadata.name}{" | owner="}{.metadata.ownerReferences[0].name}{" | replicas="}{.status.replicas}{"\n"}'

echo "== Pods（owner 应指向上面的 ReplicaSet） =="
kubectl -n "${NS}" get pods -l app.kubernetes.io/component=gateway \
  -o custom-columns='POD:.metadata.name,OWNER:.metadata.ownerReferences[0].name,OWNER_KIND:.metadata.ownerReferences[0].kind,STATUS:.status.phase' \
  --no-headers
