#!/usr/bin/env bash
set -euo pipefail
NS=order-demo-staging
PREV="$(kubectl -n "${NS}" get deploy gateway \
  -o jsonpath='{.spec.template.spec.containers[0].image}')"

kubectl -n "${NS}" set image deployment/gateway \
  gateway=registry.example.com/order-demo/gateway:git-0000000
kubectl -n "${NS}" rollout status deployment/gateway --timeout=60s || true

kubectl -n "${NS}" set image deployment/gateway gateway="${PREV}"
kubectl -n "${NS}" rollout status deployment/gateway --timeout=120s
./hack/verify.sh

[ "$(kubectl -n "${NS}" get deploy gateway \
  -o jsonpath='{.spec.template.spec.containers[0].image}')" = "${PREV}" ] \
  && echo "PASS: rollback drill restored ${PREV}"
