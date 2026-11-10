#!/usr/bin/env bash
# 激活 / 重跑 GitHub Actions 复核流水线（SSH 优先）。
#
# 背景：通过 HTTPS token 创建或更新 `.github/workflows/` 下的文件要求 `workflow` scope；
# 2026-11-11 实测账户级 SSH 密钥不受该限制，三个 workflow 已随 f1cc0f6 推到 main。
# 仓库 origin 现固化为 git@github.com:whmzsu/k8s-app-delivery-book.git，推送不再需要 token。
#
# 用法（token 只走环境变量，绝不写入仓库、.git/config 或日志）：
#   bash hack/enable-workflows.sh                          # SSH 推送 + 触发提示
#   GH_TOKEN=<PAT> bash hack/enable-workflows.sh           # 额外用 API 手动触发三条流水线
#   SSH_KEY=~/.ssh/other REPO=owner/repo BRANCH=main bash hack/enable-workflows.sh
#
# 注意：SSH 只能推 git 数据；读取 Actions 运行结论 / workflow_dispatch 仍需 HTTPS API 凭据。
set -euo pipefail
cd "$(dirname "$0")/.."

REPO="${REPO:-whmzsu/k8s-app-delivery-book}"
BRANCH="${BRANCH:-main}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
SSH_URL="git@github.com:${REPO}.git"
API="https://api.github.com"

echo "== 1. 检查 SSH 密钥 =="
[[ -f "$SSH_KEY" ]] || { echo "找不到 SSH 私钥：${SSH_KEY}（可用 SSH_KEY= 指定）" >&2; exit 1; }
FINGERPRINT="$(ssh-keygen -lf "${SSH_KEY}.pub" 2>/dev/null | awk '{print $2, $NF}' || true)"
echo "   公钥指纹：${FINGERPRINT:-（未找到同名 .pub，跳过显示）}"
AUTH_OUT="$(ssh -T -o BatchMode=yes -o IdentitiesOnly=yes -i "$SSH_KEY" \
  -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 git@github.com 2>&1 || true)"
echo "   ${AUTH_OUT}"
case "$AUTH_OUT" in
  *successfully*) ;;
  *) echo "   SSH 认证未确认：请检查该公钥是否加在 GitHub 账户的 SSH keys（而非只读 deploy key）" >&2; exit 1 ;;
esac

echo "== 2. 推送（SSH 通道）=="
# 优先推 named remote：显式 URL 不会更新 origin/<branch> 跟踪引用，
# 会让 git status 误报 "ahead N"。
PUSH_TARGET="$SSH_URL"
if [[ "$(git remote get-url origin 2>/dev/null || true)" == "$SSH_URL" ]]; then
  PUSH_TARGET="origin"
fi
GIT_SSH_COMMAND="ssh -i ${SSH_KEY} -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=20" \
  git push "$PUSH_TARGET" "${BRANCH}:${BRANCH}"
echo "   已同步 ${BRANCH}（目标：${PUSH_TARGET}）"

echo "== 3. 触发 / 查看 =="
if [[ -n "${GH_TOKEN:-}" ]]; then
  for wf in ci.yml kind-matrix.yml references.yml; do
    CODE="$(curl -sS -o /dev/null -w '%{http_code}' -X POST \
      -H "Authorization: Bearer ${GH_TOKEN}" \
      -H "Accept: application/vnd.github+json" \
      -H "Content-Type: application/json" \
      --data-binary "{\"ref\":\"${BRANCH}\"}" \
      "${API}/repos/${REPO}/actions/workflows/${wf}/dispatches")"
    echo "   ${wf}: HTTP ${CODE}"
    [[ "$CODE" == "204" ]] || echo "   警告：触发失败（确认 workflow 已推送且 Actions 已启用）"
  done
else
  echo "   未提供 GH_TOKEN：push 已自动触发 ci.yml；references.yml 在引用/脚本变更时触发"
  echo "   kind-matrix.yml 请在网页端 Run workflow，或等每周一 11:23（北京时间）定时运行"
fi

echo
echo "== 完成 =="
echo "查看运行：https://github.com/${REPO}/actions"
echo "读取结论：gh auth login 后执行 gh run list --limit 5（SSH 不能调 HTTPS API）"
echo "真集群复核约需 15–25 分钟；私有仓库会消耗 Actions 分钟额度。"
