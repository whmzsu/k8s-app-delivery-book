#!/usr/bin/env bash
set -euo pipefail
NS=order-demo-dev
CODES=/tmp/ch08-codes.txt
: > "${CODES}"

kubectl -n "${NS}" apply -f deploy/base/pdb.yaml

kubectl -n "${NS}" port-forward svc/gateway 8080:8080 >/dev/null 2>&1 &
PF=$!
trap 'kill "${PF}" 2>/dev/null || true' EXIT

for i in $(seq 1 30); do
  curl -fsS http://127.0.0.1:8080/healthz >/dev/null 2>&1 && break
  sleep 1
done

# 后台连续请求，逐条记录 HTTP 状态码
(
  for i in $(seq 1 300); do
    curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/ >> "${CODES}"
    sleep 0.1
  done
) &
PROBE=$!

# 触发一次滚动更新：切回同一镜像标签即可制造新旧 Pod 交替
kubectl -n "${NS}" rollout restart deployment/gateway
kubectl -n "${NS}" rollout status deployment/gateway --timeout=120s

wait "${PROBE}" || true
echo "== 状态码统计 =="
sort "${CODES}" | uniq -c
FIVE=$(grep -c '^5' "${CODES}" || true)
echo "5xx 计数: ${FIVE}"
test "${FIVE}" -eq 0
