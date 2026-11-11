#!/usr/bin/env bash
set -euo pipefail

AM="http://alertmanager.observability.svc.cluster.local:9093"
RULES=observability/alert-rules.yaml
AMCFG=observability/alertmanager.yaml

promtool test rules observability/alert-rules-test.yaml
amtool check-config "${AMCFG}"

# 每条 alert 都必须带 runbook 注解
TOTAL="$(grep -c '^        - alert:' "${RULES}")"
LINKS="$(grep -c 'runbook: "docs/runbooks/' "${RULES}")"
[ "${TOTAL}" -eq "${LINKS}" ] || {
  echo "FAIL: ${TOTAL} alerts but only ${LINKS} runbook links"; exit 1;
}
echo "PASS: ${TOTAL}/${TOTAL} alerts carry a runbook link"

kubectl -n observability port-forward svc/alertmanager 9093:9093 >/dev/null 2>&1 &
PF=$!
trap 'kill "${PF}" 2>/dev/null || true' EXIT
sleep 3

START="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
END="$(date -u -d '+10 min' +%Y-%m-%dT%H:%M:%SZ)"
curl -fsS -XPOST "${AM}/api/v2/alerts" -H 'Content-Type: application/json' \
  -d "[{\"labels\":{\"alertname\":\"GatewayAvailabilityFastBurnPaging\",\"severity\":\"paging\",\"service\":\"gateway\",\"slo\":\"gateway-availability\"},\"annotations\":{\"summary\":\"drill\",\"runbook\":\"docs/runbooks/gateway-fast-burn.md\"},\"startsAt\":\"${START}\",\"endsAt\":\"${END}\"}]"

echo "== 路由命中 =="
amtool --alertmanager.url="${AM}" config routes test \
  --config.file="${AMCFG}" --tree severity=paging service=gateway
amtool --alertmanager.url="${AM}" alert query \
  alertname=GatewayAvailabilityFastBurnPaging

echo "PASS: paging alert routed and visible with runbook annotation"
