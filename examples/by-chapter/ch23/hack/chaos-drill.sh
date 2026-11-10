#!/usr/bin/env bash
set -euo pipefail
NS=order-demo-staging
EXP=chaos/experiments

kubectl apply -f "${EXP}/pod-kill.yaml"
sleep 20
echo "== 按 docs/runbooks/crashloop-backoff.md 定位 =="
kubectl -n "${NS}" get pods -l app.kubernetes.io/component=gateway -o wide
kubectl -n "${NS}" get events --sort-by=.lastTimestamp | tail -10

echo "== 止血：回到上一版产物（第 13 章） =="
kubectl -n "${NS}" rollout status deploy/gateway --timeout=120s

echo "== 清理注入对象 =="
kubectl -n chaos-testing delete -f "${EXP}/" --ignore-not-found
kubectl -n chaos-testing get podchaos,stresschaos,networkchaos

./hack/verify.sh
echo "PASS: chaos drill recovered and injection objects cleaned"
