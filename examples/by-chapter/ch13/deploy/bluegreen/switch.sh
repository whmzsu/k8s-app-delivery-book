#!/usr/bin/env bash
set -euo pipefail

NS=order-demo-prod
SVC=gateway
OLD=git-1a2b3c4
NEW=git-5d6e7f8
TARGET="${1:-}"

case "${TARGET}" in
  green|"${NEW}") SELECTOR="${NEW}" ;;
  blue|"${OLD}")  SELECTOR="${OLD}" ;;
  *) echo "用法: $0 green|blue（只允许切到 ${OLD} 或 ${NEW}）" >&2; exit 2 ;;
esac

# 前置：目标版本必须真的有 Ready 副本，否则拒绝切流
READY="$(kubectl -n "${NS}" get deploy \
  -l "app.kubernetes.io/component=gateway,version=${SELECTOR}" \
  -o jsonpath='{.items[*].status.readyReplicas}' | tr ' ' '\n' | awk '{s+=$1} END {print s+0}')"
[ "${READY}" -ge 4 ] || {
  echo "目标版本 ${SELECTOR} 的 Ready 副本为 ${READY}，不足 4，拒绝切流" >&2; exit 1;
}

kubectl -n "${NS}" patch svc "${SVC}" --type=merge -p \
  "{\"spec\":{\"selector\":{\"app.kubernetes.io/name\":\"order-demo\",\"app.kubernetes.io/component\":\"gateway\",\"version\":\"${SELECTOR}\"}}}"

echo "已切到 ${SELECTOR}；旧版本 Deployment 保留至观察窗口结束，切勿立即删除。"
kubectl -n "${NS}" get svc "${SVC}" -o jsonpath='{.spec.selector.version}{"\n"}'
