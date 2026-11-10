#!/usr/bin/env bash
# 激活 GitHub Actions 复核流水线。
#
# 背景：创建 / 更新 `.github/workflows/` 下的文件需要凭据具备 workflow 权限。
# 若当前 token 是缺该 scope 的 OAuth App token，git push 会被 GitHub 拒绝，
# 此时三个 workflow 文件会留在本地待推送提交里，本脚本用新凭据完成推送并触发首次运行。
#
# 用法（token 只走环境变量，绝不写入仓库或 .git/config）：
#   GH_TOKEN=<带 workflow 权限的 PAT> ./hack/enable-workflows.sh
#   GH_TOKEN=<...> REPO=owner/repo BRANCH=main ./hack/enable-workflows.sh
#
# 生成新凭据：GitHub → Settings → Developer settings → Personal access tokens
#   classic PAT 勾选 `repo` + `workflow`；或 fine-grained PAT 给该仓库
#   「Contents: Read and write」+「Workflows: Read and write」+「Actions: Read and write」。
set -euo pipefail
cd "$(dirname "$0")/.."

: "${GH_TOKEN:?请通过环境变量 GH_TOKEN 提供带 workflow 权限的 token}"
REPO="${REPO:-whmzsu/k8s-app-delivery-book}"
BRANCH="${BRANCH:-main}"
API="https://api.github.com"

echo "== 1. 校验凭据 =="
SCOPES="$(curl -sS -D - -o /dev/null -H "Authorization: Bearer ${GH_TOKEN}" \
  "${API}/user" | tr -d '\r' | grep -i '^x-oauth-scopes:' || true)"
echo "   ${SCOPES:-（fine-grained PAT 不返回 scopes，以实际权限为准）}"
case "$SCOPES" in
  *workflow*) echo "   已含 workflow scope" ;;
  *) echo "   提示：若是 classic PAT，请确认已勾选 workflow；否则推送会被拒绝" ;;
esac

echo "== 2. 推送含 workflow 文件的提交 =="
AUTH="$(printf 'x-access-token:%s' "${GH_TOKEN}" | base64 | tr -d '\n')"
git -c "http.extraheader=Authorization: Basic ${AUTH}" push origin "${BRANCH}"
echo "   已推送 ${BRANCH}"

echo "== 3. 触发首次运行 =="
for wf in ci.yml kind-matrix.yml references.yml; do
  CODE="$(curl -sS -o /dev/null -w '%{http_code}' -X POST \
    -H "Authorization: Bearer ${GH_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "Content-Type: application/json" \
    --data-binary "{\"ref\":\"${BRANCH}\"}" \
    "${API}/repos/${REPO}/actions/workflows/${wf}/dispatches")"
  echo "   ${wf}: HTTP ${CODE}"
  [[ "$CODE" == "204" ]] || echo "   警告：${wf} 触发失败（确认 workflow 已推送且 Actions 已启用）"
done

echo
echo "== 完成 =="
echo "查看运行：https://github.com/${REPO}/actions"
echo "真集群复核约需 15–25 分钟；私有仓库会消耗 Actions 分钟额度。"
