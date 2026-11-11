#!/usr/bin/env bash
# hack/chaos-report.sh —— 跑一次演练并落证据；残留或未就绪即非零退出
set -euo pipefail
NS=order-demo-staging
CHAOS=chaos-testing
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="reports/chaos/${STAMP}"
mkdir -p "${OUT}"

leftovers() {
  kubectl -n "${CHAOS}" get podchaos,stresschaos,networkchaos \
    -l app.kubernetes.io/name=order-demo -o json \
    | jq '[.items[].metadata.name] | length'
}

[ "$(leftovers)" -eq 0 ] || { echo "FAIL: 演练开始前已有残留实验"; exit 1; }

T0="$(date -u +%s)"
./hack/chaos-drill.sh > "${OUT}/drill.log" 2>&1 || {
  echo "FAIL: drill 未通过，见 ${OUT}/drill.log"; exit 1; }
T1="$(date -u +%s)"

AFTER="$(leftovers)"
READY="$(kubectl -n "${NS}" get deploy gateway -o jsonpath='{.status.readyReplicas}')"
IMAGE="$(kubectl -n "${NS}" get deploy gateway \
  -o jsonpath='{.spec.template.spec.containers[0].image}')"
./hack/verify.sh > "${OUT}/verify.log" 2>&1 || true

jq -n --arg stamp "${STAMP}" --argjson after "${AFTER}" \
  --argjson seconds "$((T1 - T0))" --arg ready "${READY:-0}" --arg image "${IMAGE}" \
  '{stamp:$stamp, leftovers_after:$after, recovery_seconds:$seconds,
    gateway_ready:($ready|tonumber), image:$image}' > "${OUT}/report.json"

[ "${AFTER}" -eq 0 ] || { echo "FAIL: 残留 ${AFTER} 个实验对象"; exit 1; }
[ "${READY:-0}" -ge 1 ] || { echo "FAIL: gateway 无就绪副本"; exit 1; }

jq -r '"# 演练报告 \(.stamp)\n\n| 项 | 值 |\n|---|---|\n| 残留实验对象 | \(.leftovers_after) |\n| 恢复耗时(s) | \(.recovery_seconds) |\n| gateway 就绪副本 | \(.gateway_ready) |\n| 镜像 | \(.image) |"' \
  "${OUT}/report.json" > "${OUT}/report.md"
echo "PASS: chaos report written to ${OUT}/report.md"
