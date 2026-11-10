#!/usr/bin/env bash
set -euo pipefail
NS=order-demo-dev

# 口径见 observability/cost-attribution.yaml：仅相对比例，不含任何单价
TOTAL=$(kubectl -n "${NS}" get pods \
  -o jsonpath='{range .items[*]}{range .spec.containers[*]}{.resources.requests.cpu}{"\n"}{end}{end}' \
  | sed 's/m$//' | awk '{s += $1} END {print s + 0}')

printf "%-10s | %-16s | %s\n" "组件" "requests.cpu(m)" "相对占比(%)"
for COMP in gateway api worker db; do
  SUM=$(kubectl -n "${NS}" get pods -l app.kubernetes.io/component="${COMP}" \
    -o jsonpath='{range .items[*]}{range .spec.containers[*]}{.resources.requests.cpu}{"\n"}{end}{end}' \
    | sed 's/m$//' | awk '{s += $1} END {print s + 0}')
  PCT=$(awk -v a="${SUM}" -v b="${TOTAL}" 'BEGIN { if (b == 0) print "0.0"; else printf "%.1f", a * 100 / b }')
  printf "%-10s | %-16s | %s\n" "${COMP}" "${SUM}" "${PCT}"
done
echo "命名空间 ${NS} 合计：${TOTAL}m；报表不含具体云厂商单价"
