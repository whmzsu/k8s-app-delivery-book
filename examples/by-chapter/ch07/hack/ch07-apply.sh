#!/usr/bin/env bash
set -euo pipefail
NS=order-demo-dev
SHA="$(git rev-parse --short=7 HEAD)"

# 三个组件镜像沿用第 6 章的构建方式：把 docker/Dockerfile 的
# COPY cmd/gateway/main.go 改为 ARG COMPONENT + COPY cmd/${COMPONENT}/main.go，
# 再对每个组件执行一次 docker build 与 kind load docker-image（见 hack/kind-up.sh）。
for f in deploy/base/deployment-worker.yaml \
         deploy/base/deployment-api.yaml \
         deploy/base/service-api.yaml \
         deploy/base/service-db-headless.yaml \
         deploy/base/statefulset-db.yaml; do
  sed "s/git-1a2b3c4/${SHA}/g" "${f}" | kubectl -n "${NS}" apply -f -
done

kubectl -n "${NS}" rollout status deployment/worker --timeout=120s
kubectl -n "${NS}" rollout status deployment/api --timeout=120s
kubectl -n "${NS}" rollout status statefulset/db --timeout=120s
echo "applied ch07-workloads at git-${SHA}"
