#!/usr/bin/env bash
set -euo pipefail
# 验证：一次变更、两集群同一 SHA、零漂移、state 远端加密。
APP_A=order-demo-prod-cluster-a
APP_B=order-demo-prod-cluster-b
CTX_A=cluster-a
CTX_B=cluster-b
NS=order-demo-prod

echo "== 1) 两个 Application 由同一 ApplicationSet 生成 =="
argocd app list -o wide | grep -E "${APP_A}|${APP_B}"

echo "== 2) 两集群 image 字段必须相同 =="
IMG_A="$(kubectl --context "${CTX_A}" -n "${NS}" get deploy gateway \
  -o jsonpath='{.spec.template.spec.containers[0].image}')"
IMG_B="$(kubectl --context "${CTX_B}" -n "${NS}" get deploy gateway \
  -o jsonpath='{.spec.template.spec.containers[0].image}')"
echo "cluster-a: ${IMG_A}"
echo "cluster-b: ${IMG_B}"
[ "${IMG_A}" = "${IMG_B}" ] || { echo "两集群产物不一致" >&2; exit 1; }
! grep -qE ':latest' <<<"${IMG_A}"

echo "== 3) 两集群均 Healthy，且 app diff 为空 =="
for APP in "${APP_A}" "${APP_B}"; do
  argocd app wait "${APP}" --health --timeout 120s
  DIFF="$(argocd app diff "${APP}")"
  [ -z "${DIFF}" ] || { echo "${APP} 存在漂移: ${DIFF}" >&2; exit 1; }
done

echo "== 4) state 无本地副本、远端加密、plan 无漂移 =="
if git ls-files '*.tfstate' | grep -q .; then
  echo "state 文件入 Git，禁止" >&2; exit 1
fi
grep -q 'encrypt = true' infra/backend.tf
terraform -chdir=infra plan -detailed-exitcode >/dev/null
echo "terraform plan 无漂移"

echo "双集群验证通过：一次变更、两集群同一 SHA、零漂移。"
