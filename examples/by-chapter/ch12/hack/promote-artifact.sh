#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "用法: $0 --from <env> --to <env> --sha <sha7>" >&2
  exit 2
}

FROM=""; TO=""; SHA=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --from) FROM="$2"; shift 2 ;;
    --to)   TO="$2";   shift 2 ;;
    --sha)  SHA="$2";  shift 2 ;;
    *) usage ;;
  esac
done

for v in "${FROM}" "${TO}" "${SHA}"; do
  [ -n "${v}" ] || usage
done
case "${TO}" in
  dev|staging|prod) ;;
  *) echo "未知目标环境: ${TO}" >&2; exit 2 ;;
esac
case "${SHA}" in
  ???????) ;;
  *) echo "SHA 必须是 7 位短 SHA: ${SHA}" >&2; exit 2 ;;
esac

COMPONENT="gateway"
REPO="registry.example.com/order-demo/${COMPONENT}"
IMAGE="${REPO}:git-${SHA}"
OVERLAY="deploy/overlays/${TO}"

# 前置一：制品必须已存在，且这一步绝不调用任何构建命令
command -v crane >/dev/null 2>&1 || { echo "缺少 crane，见附录 A" >&2; exit 1; }
DIGEST="$(crane digest "${IMAGE}")"
[ -n "${DIGEST}" ] || { echo "镜像不存在，禁止晋升: ${IMAGE}" >&2; exit 1; }
echo "制品引用: ${IMAGE}@${DIGEST}  (from=${FROM}, to=${TO}, 不重新构建)"

# 前置二：源环境与目标环境当前指向同一制品，避免把「配置差异」误当「产物升级」
FROM_TAG="$(kustomize build "deploy/overlays/${FROM}" \
  | grep -oE "image: ${REPO}:git-[0-9a-f]{7}" | head -n1 | awk -F: '{print $NF}')"
[ "${FROM_TAG}" = "git-${SHA}" ] || {
  echo "源环境 ${FROM} 当前为 ${FROM_TAG}，与待晋升 SHA 不一致" >&2; exit 1;
}

# 只改 image 的 tag，配置差异继续保留在各自 overlay 中
(
  cd "${OVERLAY}"
  kustomize edit set image "${REPO}=${IMAGE}"
)
kustomize build "${OVERLAY}" > "/tmp/rendered-${TO}.yaml"
grep -q "image: ${IMAGE}" "/tmp/rendered-${TO}.yaml"
! grep -qE 'image:.*:latest' "/tmp/rendered-${TO}.yaml"

git add "${OVERLAY}"
git commit -m "promote(order-demo): ${COMPONENT} git-${SHA} -> ${TO} [skip ci]"
echo "OK: ${TO} 已指向 ${IMAGE}，请推送后由第 14 章的控制器同步到集群。"
