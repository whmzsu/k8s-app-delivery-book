#!/usr/bin/env bash
set -euo pipefail

ENV="${1:?用法: $0 <dev|staging|prod> <sha7>}"
SHA="${2:?用法: $0 <dev|staging|prod> <sha7>}"
case "${ENV}" in dev|staging|prod) ;; *) echo "未知环境: ${ENV}" >&2; exit 2 ;; esac
case "${SHA}" in ???????) ;; *) echo "SHA 必须为 7 位: ${SHA}" >&2; exit 2 ;; esac

OVERLAY="deploy/overlays/${ENV}"
OUT="gitops/rendered/${ENV}/all.yaml"
mkdir -p "gitops/rendered/${ENV}"

# 只改 tag，不重建镜像；配置差异仍留在各自 overlay
(
  cd "${OVERLAY}"
  kustomize edit set image "registry.example.com/order-demo/gateway=:git-${SHA}"
)
kustomize build "${OVERLAY}" > "${OUT}"

# 渲染产物门禁：完整、可追溯、无 latest、managed-by 已切换
test -s "${OUT}"
grep -q "image: registry.example.com/order-demo/gateway:git-${SHA}" "${OUT}"
! grep -qE 'image:.*:latest' "${OUT}"
grep -q "app.kubernetes.io/managed-by: argocd" "${OUT}"
kubeconform -strict -summary "${OUT}"

echo "已生成 ${OUT}；请 review git diff 后提交 PR："
echo "  git add ${OUT} && git commit -m 'promote(order-demo): ${ENV} -> git-${SHA}'"
