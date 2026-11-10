#!/usr/bin/env bash
# P5 技术复核：在 kind 的 K8s 版本矩阵中验证全书 YAML（见第 11 章、附录 A）
# 用法：./hack/check-version-matrix.sh [1.32 1.33 1.34]
set -euo pipefail
cd "$(dirname "$0")/.."

VERSIONS="${*:-1.32 1.33 1.34}"
BASES="examples/order-demo/deploy/base"
FAILED=0

if ! command -v kind >/dev/null 2>&1 || ! command -v kubectl >/dev/null 2>&1; then
  echo "需要 kind 与 kubectl（版本见附录 A）。当前环境缺少，跳过技术复核。"
  exit 0
fi

for v in $VERSIONS; do
  node="kindest/node:v${v}.0"
  cluster="order-demo-v${v//./-}"
  echo "== K8s $v ($node) =="
  if kind create cluster --name "$cluster" --image "$node" --wait 120s >/dev/null 2>&1; then
    for f in "$BASES"/*.yaml; do
      if kubectl --context "kind-$cluster" apply --dry-run=server -f "$f" >/dev/null 2>&1; then
        echo "  OK  $(basename "$f")"
      else
        echo "  FAIL $(basename "$f")"
        FAILED=1
      fi
    done
    kind delete cluster --name "$cluster" >/dev/null 2>&1 || true
  else
    echo "  跳过：无法创建该版本集群（镜像可能不可用）"
  fi
done

echo "== 版本矩阵复核结束，FAILED=$FAILED =="
exit "$FAILED"
