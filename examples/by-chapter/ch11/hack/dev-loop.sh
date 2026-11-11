#!/usr/bin/env bash
set -euo pipefail
CTX="$(kubectl config current-context)"
NS="$(yq -r '.allowed_namespace' hack/dev-loop.yaml)"

case "${CTX}" in
  kind-*) ;;
  *) echo "FAIL: 开发回路只允许指向本地 kind 集群，当前 context=${CTX}" >&2; exit 1 ;;
esac
if [ "${NS}" != "order-demo-dev" ]; then
  echo "FAIL: 开发回路只允许命名空间 order-demo-dev，当前=${NS}" >&2
  exit 1
fi
echo "dev-loop guard OK (context=${CTX}, namespace=${NS})"
exec tilt up --namespace "${NS}"
