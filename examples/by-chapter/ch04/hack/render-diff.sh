#!/usr/bin/env bash
set -euo pipefail

for env in dev staging prod; do
  kubectl kustomize "deploy/overlays/${env}" > "/tmp/order-demo-${env}.yaml"
done

echo "== 三环境镜像字段（必须完全相同） =="
for env in dev staging prod; do
  printf '%s: ' "${env}"
  grep 'image: registry.example.com/order-demo/gateway' "/tmp/order-demo-${env}.yaml" | sort -u | tr '\n' ' '
  echo
done

echo "== dev 与 prod 渲染 diff（应只有 namespace / replicas / GREETING / PUBLIC_URL） =="
diff -u /tmp/order-demo-dev.yaml /tmp/order-demo-prod.yaml || true

echo "== 仓库凭据明文扫描（应无命中） =="
grep -RniE 'password|token|BEGIN .*PRIVATE KEY' deploy/ gitops/ || true
