#!/usr/bin/env bash
# 第 6 章：起 kind、构建 SHA 标签镜像、装进集群、apply、等待 Ready
# 版本基线见附录 A；用法见 chapters/ch06.md §6.4
set -euo pipefail

CLUSTER="${CLUSTER:-order-demo}"
SHA="$(git rev-parse --short=7 HEAD)"
IMAGE="registry.example.com/order-demo/gateway:git-${SHA}"

if ! kind get clusters | grep -qx "${CLUSTER}"; then
  kind create cluster --name "${CLUSTER}"
fi

docker build -f docker/Dockerfile -t "${IMAGE}" .
kind load docker-image "${IMAGE}" --name "${CLUSTER}"

# 用真实短 SHA 替换示例值，产物仍是可读的完整清单
sed "s/git-1a2b3c4/${SHA}/g" deploy/base/deployment.yaml > /tmp/order-demo-deployment.yaml

kubectl apply -f deploy/base/namespace.yaml
kubectl apply -f deploy/base/configmap.yaml
kubectl apply -f /tmp/order-demo-deployment.yaml
kubectl apply -f deploy/base/service.yaml

kubectl -n order-demo-dev rollout status deployment/gateway --timeout=120s
echo "IMAGE=${IMAGE}"
