#!/usr/bin/env bash
set -euo pipefail

APP=order-demo-dev
NS=order-demo-dev
REPORT="/tmp/drift-check-$(date +%Y%m%d%H%M%S).log"
log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "${REPORT}"; }

log "同步前基线"
argocd app diff "${APP}" | tee -a "${REPORT}"

log "手工把副本数改为 9（仅演练，生产禁止此操作）"
kubectl -n "${NS}" scale deployment/gateway --replicas=9
kubectl -n "${NS}" get deploy gateway -o jsonpath='{.spec.replicas}{"\n"}' | tee -a "${REPORT}"

log "等待自愈（最多 180s）"
for i in $(seq 1 36); do
  REPLICAS="$(kubectl -n "${NS}" get deploy gateway -o jsonpath='{.spec.replicas}')"
  [ "${REPLICAS}" = "4" ] && break
  sleep 5
done

log "自愈后副本数: $(kubectl -n "${NS}" get deploy gateway -o jsonpath='{.spec.replicas}')"
[ "$(kubectl -n "${NS}" get deploy gateway -o jsonpath='{.spec.replicas}')" = "4" ] || {
  log "失败：漂移未被纠正"; exit 1;
}
DIFF="$(argocd app diff "${APP}")"
[ -z "${DIFF}" ] || { log "失败：仍有漂移 ${DIFF}"; exit 1; }
log "漂移检测与自愈通过，报告: ${REPORT}"
