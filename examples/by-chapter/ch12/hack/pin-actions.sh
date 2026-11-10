#!/usr/bin/env bash
set -euo pipefail

WORKFLOWS=(".github/workflows/build.yml" ".github/workflows/validate.yml")
# repo:tag 对照表；新增 Action 时在这里登记，而不是在工作流里写 @vX
PINS=(
  "actions/checkout:v4.2.2"
)

resolve_sha() {
  local repo="$1" tag="$2" refsha objsha
  refsha="$(gh api "repos/${repo}/git/ref/tags/${tag}" --jq '.object.sha')"
  # 附注标签需要再解一层，拿到真正指向的 commit
  objsha="$(gh api "repos/${repo}/git/tags/${refsha}" --jq '.object.sha' 2>/dev/null || true)"
  if [ -n "${objsha}" ]; then
    echo "${objsha}"
  else
    echo "${refsha}"
  fi
}

for pin in "${PINS[@]}"; do
  repo="${pin%%:*}"; tag="${pin##*:}"
  sha="$(resolve_sha "${repo}" "${tag}")"
  case "${sha}" in
    ????????????????????????????????????????) ;;
    *) echo "解析 ${repo}@${tag} 未得到 40 位 SHA: ${sha}" >&2; exit 1 ;;
  esac
  for f in "${WORKFLOWS[@]}"; do
    sed -i -E \
      "s|uses: ${repo}@[^ #]+( *#.*)?|uses: ${repo}@${sha} # ${tag}|" \
      "${f}"
  done
  echo "pinned ${repo}@${tag} -> ${sha}"
done

echo "请检查 git diff 后提交，本脚本不会自动 commit。"
