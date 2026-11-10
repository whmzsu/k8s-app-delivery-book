#!/usr/bin/env bash
set -euo pipefail

NS=order-demo-staging
DEPLOY=gateway
STABLE="$(kubectl -n "${NS}" get deploy "${DEPLOY}" \
  -o jsonpath='{.spec.template.spec.containers[0].image}')"
CANDIDATE="registry.example.com/order-demo/gateway:git-0000000"
REPORT="/tmp/rollback-drill-$(date +%Y%m%d%H%M%S).log"

log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "${REPORT}"; }

log "稳定版本: ${STABLE}"

# 制造一个「新版本」并等待它就绪，让 ReplicaSet 历史里有可退的修订
kubectl -n "${NS}" set image "deployment/${DEPLOY}" gateway="${CANDIDATE}"
kubectl -n "${NS}" rollout status "deployment/${DEPLOY}" --timeout=120s || true
log "已发布候选版本: ${CANDIDATE}"

REV="$(kubectl -n "${NS}" rollout history "deployment/${DEPLOY}" \
  | tail -n2 | head -n1 | awk '{print $1}')"
log "待回退修订号: ${REV}"

# 路径 A：按历史修订回退（演练用）
START=$(date +%s)
kubectl -n "${NS}" rollout undo "deployment/${DEPLOY}" --to-revision="${REV}"
kubectl -n "${NS}" rollout status "deployment/${DEPLOY}" --timeout=120s
log "路径 A 完成，耗时 $(( $(date +%s) - START ))s"

# 路径 B：明确 SHA 回退（推荐用于明确目标产物）
kubectl -n "${NS}" set image "deployment/${DEPLOY}" gateway="${STABLE}"
kubectl -n "${NS}" rollout status "deployment/${DEPLOY}" --timeout=120s
log "路径 B 完成，目标产物: ${STABLE}"

# 验证
IMAGE="$(kubectl -n "${NS}" get deploy "${DEPLOY}" \
  -o jsonpath='{.spec.template.spec.containers[0].image}')"
[ "${IMAGE}" = "${STABLE}" ] || { log "失败：image 未回到稳定版本"; exit 1; }
kubectl -n "${NS}" port-forward "svc/${DEPLOY}" 18080:8080 >/dev/null 2>&1 &
PF=$!
trap 'kill "${PF}" 2>/dev/null || true' EXIT
for i in $(seq 1 30); do
  curl -fsS http://127.0.0.1:18080/healthz >/dev/null 2>&1 && break
  sleep 1
done
curl -fsS http://127.0.0.1:18080/healthz | tee -a "${REPORT}"
log "演练通过，报告: ${REPORT}"
