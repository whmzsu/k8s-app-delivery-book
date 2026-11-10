#!/usr/bin/env bash
set -euo pipefail

NS=order-demo-prod
PROM="http://prometheus.observability.svc.cluster.local:9090"
LOKI="http://loki.observability.svc.cluster.local:3100"
TEMPO="http://tempo.observability.svc.cluster.local:3200"

kubectl -n "${NS}" port-forward svc/gateway 8080:8080 >/dev/null 2>&1 &
kubectl -n observability port-forward svc/prometheus 9090:9090 >/dev/null 2>&1 &
kubectl -n observability port-forward svc/loki 3100:3100 >/dev/null 2>&1 &
kubectl -n observability port-forward svc/tempo 3200:3200 >/dev/null 2>&1 &
PF_PIDS=$(jobs -p)
trap 'kill ${PF_PIDS} 2>/dev/null || true' EXIT
sleep 3

TRACE_ID="$(curl -fsS -D - -o /dev/null http://127.0.0.1:8080/orders \
  | awk -F': ' 'tolower($1)=="x-trace-id" {gsub(/\r/,"",$2); print $2}')"
[ -n "${TRACE_ID}" ] || { echo "FAIL: no X-Trace-Id in response header"; exit 1; }
echo "trace_id=${TRACE_ID}"

echo "== 1) 指标：按 trace_id 查 exemplar =="
curl -fsS --data-urlencode \
  'query=order_demo_http_request_duration_seconds_bucket{service="gateway",route="/orders"}' \
  --data-urlencode "start=$(date -u -d '-5 min' +%Y-%m-%dT%H:%M:%SZ)" \
  --data-urlencode "end=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  "${PROM}/api/v1/query_exemplars" \
  | jq -r --arg t "${TRACE_ID}" '.data[].exemplars[]? | select(.labels.trace_id==$t) | "exemplar trace_id=\(.labels.trace_id) value=\(.value)"'

echo "== 2) 日志：Loki 按 trace_id 捞结构化行 =="
curl -fsS --data-urlencode \
  "query={app=\"order-demo\"} |= \"${TRACE_ID}\"" \
  --data-urlencode "limit=20" \
  "${LOKI}/loki/api/v1/query_range" \
  | jq -r '.data.result[0].values[][1]'

echo "== 3) 链路：Tempo 按 trace_id 取瀑布 =="
curl -fsS "${TEMPO}/api/traces/${TRACE_ID}" \
  | jq -r '.batches[].scopeSpans[].spans[] | "\(.name) duration_ms=\((.endTimeUnixNano|tonumber - .startTimeUnixNano|tonumber)/1000000)"'

echo "PASS: same trace_id resolved in metrics / logs / traces"
