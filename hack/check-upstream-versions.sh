#!/usr/bin/env bash
# 上游版本核对：把「书稿口径」与「上游当前最新稳定版」并排打出来，供人工判断。
#
# 设计取舍：
#   1. 只报告、不阻断（永远 exit 0）——上游 API 会限流、会网络抖动，
#      把它做成硬闸门等于给 CI 埋一颗定时雷。版本升级是人的决策，不是脚本的。
#   2. 期望值内嵌在本表里，与附录 A.1 一一对应；改附录时同步改这里，
#      两者不一致就说明有人只改了一处。
#   3. 输出「主版本是否变化」而不是「小版本差几」——书稿只承诺主版本，
#      小版本随上游漂是正常的，见附录 A.4 第 4 条。
#
# 用法：
#   ./hack/check-upstream-versions.sh            # 需 gh 已登录（gh auth login）
#   GITHUB_TOKEN=xxx ./hack/check-upstream-versions.sh
set -uo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "需要 gh CLI（https://cli.github.com/）。跳过。" >&2
  exit 0
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "gh 未登录，先 gh auth login 或设置 GITHUB_TOKEN。跳过。" >&2
  exit 0
fi

# 仓库 | 书稿口径（主版本）| 附录 A 行号
ENTRIES=(
  "kubernetes/kubernetes|1.37|A-01"
  "kubernetes-sigs/kind|0.33|A-02"
  "helm/helm|4|A-07"
  "kubernetes-sigs/kustomize|5|A-08"
  "argoproj/argo-cd|3|A-09"
  "fluxcd/flux2|2|A-10"
  "argoproj/argo-rollouts|1|A-11"
  "kubernetes-sigs/gateway-api|1|A-12"
  "envoyproxy/gateway|1|A-13"
  "istio/istio|1|A-14"
  "cert-manager/cert-manager|1|A-15"
  "kyverno/kyverno|1|A-16"
  "open-policy-agent/gatekeeper|3|A-18"
  "external-secrets/external-secrets|2|A-19"
  "cloudnative-pg/cloudnative-pg|1|A-20"
  "vmware-tanzu/velero|1|A-21"
  "prometheus/prometheus|3|A-22"
  "open-telemetry/opentelemetry-collector|0|A-23"
  "grafana/loki|3|A-24"
  "grafana/tempo|3|A-24"
  "thanos-io/thanos|0|A-25"
  "chaos-mesh/chaos-mesh|2|A-26"
  "kedacore/keda|2|A-27"
  "kubernetes-sigs/karpenter|1|A-28"
  "kubernetes-sigs/kubebuilder|4|A-29"
  "crossplane/crossplane|2|A-30"
  "kubernetes-sigs/cluster-api|1|A-30"
  "backstage/backstage|1|A-30"
  "anchore/syft|1|A-31"
  "aquasecurity/trivy|0|A-31"
  "sigstore/cosign|3|A-31"
  "yannh/kubeconform|0|A-34"
)

printf '%-46s %-8s %-12s %-12s %s\n' "仓库" "附录" "书稿口径" "上游最新" "主版本"
printf '%s\n' "----------------------------------------------------------------------------------------------------"

# 少数仓库的 latest release 不是应用版本（ESO 发的是 helm-chart-x.y.z），单独取 v* 前缀
fetch_tag() {
  case "$1" in
    external-secrets/external-secrets)
      gh api "repos/$1/releases" --jq '[.[]|select(.tag_name|test("^v[0-9]"))][0].tag_name' 2>/dev/null ;;
    *)
      gh api "repos/$1/releases/latest" --jq .tag_name 2>/dev/null ;;
  esac
}

drift=0
for entry in "${ENTRIES[@]}"; do
  IFS='|' read -r repo pinned row <<<"$entry"
  tag="$(fetch_tag "$repo")"
  if [ -z "$tag" ]; then
    printf '%-46s %-8s %-12s %-12s %s\n' "$repo" "$row" "$pinned.x" "查询失败" "?"
    continue
  fi
  # 归一化：kustomize 的 tag 形如 kustomize/v5.8.3，istio 形如 1.32.0（无 v 前缀）
  ver="$(printf '%s' "$tag" | sed 's#.*/##; s#^v##')"
  # 主版本匹配：允许 pinned 是多段（如 kubernetes 用 1.37），只要 tag 以它开头
  case "$ver" in
    "$pinned"|"$pinned".*) flag="一致" ;;
    *) flag="** 需复核 **"; drift=$((drift + 1)) ;;
  esac
  printf '%-46s %-8s %-12s %-12s %s\n' "$repo" "$row" "${pinned}.x" "$tag" "$flag"
done

printf '%s\n' "----------------------------------------------------------------------------------------------------"
echo "主版本不一致：${drift} 项。"
echo "处理方式：主版本有变 → 按附录 A.3 逐项复核破坏性变更、改 CI 固定值与正文主版本口径、"
echo "          在 book/consistency-log.md 追加裁决；仅小版本漂移 → 只更新附录 A.1 的说明。"
exit 0
