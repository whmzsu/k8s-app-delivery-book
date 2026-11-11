#!/usr/bin/env bash
set -euo pipefail

NS=order-demo-prod
ROLLOUT=gateway
REPORT="/tmp/canary-drill-$(date +%Y%m%d%H%M%S).log"
log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "${REPORT}"; }

log "注入前状态"
kubectl argo rollouts -n "${NS}" get rollout "${ROLLOUT}" | tee -a "${REPORT}"

# 给 canary Pod 模板注入 20% 错误率（仅演练镜像支持该开关）
kubectl -n "${NS}" patch rollout "${ROLLOUT}" --type=json -p \
  '[{"op":"add","path":"/spec/template/spec/containers/0/env","value":[{"name":"INJECT_ERROR_RATE","value":"0.20"}]}]'
log "已注入 INJECT_ERROR_RATE=0.20，等待 Analysis 判定失败并自动回退"

for i in $(seq 1 60); do
  PHASE="$(kubectl -n "${NS}" get rollout "${ROLLOUT}" -o jsonpath='{.status.phase}')"
  WEIGHT="$(kubectl -n "${NS}" get httproute gateway-route \
    -o jsonpath='{.spec.rules[0].backendRefs[1].weight}')"
  log "phase=${PHASE} canaryWeight=${WEIGHT}"
  if [ "${PHASE}" = "Degraded" ] || [ "${WEIGHT}" = "0" ]; then
    log "检测到自动回退，报告: ${REPORT}"
    exit 0
  fi
  sleep 5
done

log "失败：300s 内未观察到自动回退"; exit 1
