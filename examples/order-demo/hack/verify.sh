#!/usr/bin/env bash
# 第 6 章：四判据验证（入口 / 配置可观察 / 产物可追溯 / 可回退的前置证据）
set -euo pipefail
NS=order-demo-dev

kubectl -n "${NS}" port-forward svc/gateway 8080:8080 >/dev/null 2>&1 &
PF=$!
trap 'kill "${PF}" 2>/dev/null || true' EXIT

for i in $(seq 1 30); do
  curl -fsS http://127.0.0.1:8080/healthz >/dev/null 2>&1 && break
  sleep 1
done

echo "== /healthz =="
curl -i http://127.0.0.1:8080/healthz
echo "== 根路径（GREETING 应来自 ConfigMap，version 应为 git-<sha7>） =="
curl -fsS http://127.0.0.1:8080/
echo "== 镜像标签 =="
kubectl -n "${NS}" get deploy gateway \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
