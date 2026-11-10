#!/usr/bin/env bash
set -euo pipefail

PROM="${PROM:-http://prometheus.observability.svc.cluster.local:9090}"
SERVICE="${SERVICE:-gateway}"
WINDOW="${WINDOW:-28d}"

query() {
  curl -fsS --data-urlencode "query=$1" "${PROM}/api/v1/query" \
    | jq -r '.data.result[0].value[1] // "NaN"'
}

GOOD="$(query "sum(increase(order_demo_http_requests_total{service=\"${SERVICE}\",route!~\"/healthz|/readyz|/startup\",status_code!~\"5..\"}[${WINDOW}]))")"
VALID="$(query "sum(increase(order_demo_http_requests_total{service=\"${SERVICE}\",route!~\"/healthz|/readyz|/startup\"}[${WINDOW}]))")"
CONSUMED="$(query "slo:order_demo_gateway:budget_consumed_ratio_28d")"
FREEZE="$(query "slo:order_demo_gateway:release_freeze")"

awk -v g="${GOOD}" -v v="${VALID}" -v c="${CONSUMED}" 'BEGIN {
  sli = (v + 0 > 0) ? g / v : 1;
  printf "SLI(28d)=%.6f  有效请求=%.0f  成功请求=%.0f\n", sli, v, g;
  printf "错误预算消耗=%.2f%%  剩余=%.2f%%\n", c * 100, (1 - c) * 100;
}'
if [ "${FREEZE}" = "1" ]; then
  echo "判定：冻结非必要发布（走 docs/slo-contract.md 例外审批）"
  exit 2
else
  echo "判定：预算未耗尽，可按第 13 章回滚方案先行原则发布"
fi
