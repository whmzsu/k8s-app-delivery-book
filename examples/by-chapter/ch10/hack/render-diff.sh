#!/usr/bin/env bash
set -euo pipefail
CHART=deploy/charts/order-demo
OVERLAY=deploy/overlays/dev
NS=order-demo-dev

helm template order-demo "${CHART}" -f "${CHART}/values-dev.yaml" -n "${NS}" > /tmp/helm.yaml
kustomize build "${OVERLAY}" > /tmp/kustomize.yaml

grep -v '^# Source:' /tmp/helm.yaml > /tmp/helm.clean.yaml

# 只取两条路径共同产出的资源，统一 JSON 序列化后逐字段比较
pick() {
  yq -o=json -I=0 'select(.kind == "Deployment" and .metadata.name == "gateway" or .kind == "ConfigMap")' "$1" \
    | jq -sS 'sort_by(.kind, .metadata.name)'
}
pick /tmp/helm.clean.yaml > /tmp/helm.json
pick /tmp/kustomize.yaml > /tmp/kustomize.json

diff -u /tmp/kustomize.json /tmp/helm.json
echo "render-equivalent: OK"
