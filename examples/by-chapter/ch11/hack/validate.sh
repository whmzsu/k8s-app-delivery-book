#!/usr/bin/env bash
set -euo pipefail
MODE="${1:---static}"
NS=order-demo-dev
RENDER=/tmp/rendered.yaml

# 矩阵一致性断言：workflow 的 matrix.k8s 必须与数据源逐项一致
MATRIX=$(yq -r '.kubernetes_versions | join(",")' hack/kind-matrix.yaml)
WORKFLOW=$(grep -A6 'matrix:' .github/workflows/validate.yml \
  | grep -oE '"1\.[0-9]+"' | tr -d '"' | paste -sd, -)
if [ "${MATRIX}" != "${WORKFLOW}" ]; then
  echo "FAIL: kind-matrix.yaml (${MATRIX}) 与 workflow matrix (${WORKFLOW}) 不一致" >&2
  exit 1
fi

kustomize build deploy/overlays/dev > "${RENDER}"

echo "== 第 1 层 · 语法/结构（kubeconform）=="
kubeconform -strict -summary "${RENDER}"

echo "== 第 2 层 · 组织策略（conftest）=="
conftest test "${RENDER}" -p policy/

if [ "${MODE}" = "--static" ]; then
  echo "static layers OK"
  exit 0
fi

echo "== 第 3 层 · 声明式行为测试（kuttl）=="
kubectl kuttl test --config tests/kuttl/kuttl-test.yaml

echo "== 第 4 层 · 真实集群冒烟 =="
kubectl apply -k deploy/overlays/dev
kubectl -n "${NS}" rollout status deployment/gateway --timeout=120s
kubectl -n "${NS}" port-forward svc/gateway 8080:8080 >/dev/null 2>&1 &
PF=$!
trap 'kill "${PF}" 2>/dev/null || true' EXIT
for i in $(seq 1 30); do
  curl -fsS http://127.0.0.1:8080/healthz >/dev/null 2>&1 && break
  sleep 1
done
curl -fsS http://127.0.0.1:8080/healthz
echo "cluster smoke OK (k8s ${K8S_VERSION:-local})"
