#!/usr/bin/env bash
# P5 技术复核：在 kind 的 K8s 版本矩阵中验证全书清单与第 6 章运行时承诺。
#
# 两种模式（都复用「当前 kubeconfig 指向的集群」，多版本矩阵由 kind-matrix.yml 驱动）：
#   local（默认）  本机已起好 kind 集群时跑一次完整复核
#                   ./hack/check-version-matrix.sh [--strict] [--no-drill]
#   ci             复用 GitHub Actions 创建的集群，写 job summary、由 workflow 上传日志
#                   ./hack/check-version-matrix.sh --mode ci --version 1.32.2 --cluster NAME
#
# 分层闸门（与附录 A 一致）：
#   硬闸门：第 6 章基线 4 份清单、真实 apply、四判据、滚动 / 回滚 / 摘流演练
#   软报告：examples/by-chapter 的内置资源逐文档 server dry-run，失败清单上传为 artifact；
#           章节增量清单是教学片段，脱离该章 tag 的仓库状态不保证可独立应用，故按阈值放行
set -euo pipefail
cd "$(dirname "$0")/.."

MODE=local
STRICT=0
DRILL=1
VERSION=""
CLUSTER=""
SOFT_LIMIT="${SOFT_LIMIT:-12}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="$2"; shift 2 ;;
    --version) VERSION="$2"; shift 2 ;;
    --cluster) CLUSTER="$2"; shift 2 ;;
    --strict) STRICT=1; shift ;;
    --no-drill) DRILL=0; shift ;;
    *) echo "未知参数：$1（版本矩阵请由 kind-matrix.yml 驱动）" >&2; exit 2 ;;
  esac
done

BASES="examples/order-demo/deploy/base"
LOG="build/p5-server-dryrun.log"
MANIFESTS="build/manifests"
FAILED=0
mkdir -p build

need() {
  for c in "$@"; do
    if ! command -v "$c" >/dev/null 2>&1; then
      echo "缺少 $c" >&2
      if [[ "$MODE" == "ci" || "$STRICT" == "1" ]]; then exit 1; fi
      echo "SKIPPED：本地缺少工具，本次未执行任何校验（CI 模式会直接失败，不会假通过）"
      exit 0
    fi
  done
}
need python kubectl kind docker

# ---------- 生成逐文档、按 apiVersion 分类的校验输入 ----------
echo "== 清单预检：拆分内置资源 / CRD 实例 / Helm 模板 =="
python hack/validate-manifests.py --out "$MANIFESTS"
BUILTIN_COUNT="$(wc -l < "$MANIFESTS/builtin.txt")"
echo "内置资源文档：$BUILTIN_COUNT 份（清单见 $MANIFESTS/_index.tsv）"

# ---------- 预建命名空间：server dry-run 要求 namespace 已存在 ----------
echo "== 预建全书出现的命名空间（幂等） =="
python - <<'PY' > /tmp/p5-namespaces.txt
import glob, re, os
ns = set()
for f in glob.glob('build/manifests/builtin/*.yaml') + glob.glob('examples/order-demo/deploy/base/*.yaml'):
    t = open(f, encoding='utf-8').read()
    m = re.search(r'(?m)^kind:\s*Namespace\s*$', t)
    if m:
        x = re.search(r'(?m)^\s{2}name:\s*([\w.-]+)', t)
        if x: ns.add(x.group(1))
    for x in re.findall(r'(?m)^\s*namespace:\s*([\w.-]+)', t):
        ns.add(x)
print('\n'.join(sorted(ns - {'default', 'kube-system'})))
PY
while read -r ns; do
  [[ -z "$ns" ]] && continue
  kubectl create namespace "$ns" --dry-run=client -o yaml | kubectl apply -f - >/dev/null
done < /tmp/p5-namespaces.txt
echo "命名空间：$(grep -c . /tmp/p5-namespaces.txt) 个"

# ---------- 硬闸门：第 6 章基线 ----------
echo "== 硬闸门 A：第 6 章基线 server dry-run =="
: > "$LOG"
for f in "$BASES"/*.yaml; do
  if kubectl apply --dry-run=server -f "$f" >>"$LOG" 2>&1; then
    echo "  OK   $(basename "$f")"
  else
    echo "  FAIL $(basename "$f")"; FAILED=1
  fi
done

# ---------- 软报告：全书内置资源逐文档 dry-run ----------
echo "== 软报告 B：全书内置资源 server dry-run（阈值 $SOFT_LIMIT） =="
SOFT=0
while read -r f; do
  [[ -z "$f" ]] && continue
  if ! kubectl apply --dry-run=server -f "$f" >>"$LOG" 2>&1; then
    echo "  soft-FAIL $f"
    echo "SOFT-FAIL $f" >> "$LOG"
    SOFT=$((SOFT + 1))
  fi
done < "$MANIFESTS/builtin.txt"
echo "软报告失败 $SOFT / $BUILTIN_COUNT 份；明细：$LOG"
if [[ "$SOFT" -gt "$SOFT_LIMIT" ]]; then
  echo "!! 章节清单失败数超过阈值 $SOFT_LIMIT，需修书稿字段" >&2
  FAILED=1
fi
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo "### P5 清单校验（K8s ${VERSION:-local}）"
    echo "- 内置资源文档：${BUILTIN_COUNT} 份"
    echo "- server dry-run 软失败：${SOFT} 份（阈值 ${SOFT_LIMIT}）"
    echo "- CRD 实例 / Helm 模板：见 \`$MANIFESTS/_index.tsv\`，需对应控制器或渲染器，不在本闸门内"
  } >> "$GITHUB_STEP_SUMMARY"
fi

# ---------- 真实部署与运行时演练 ----------
if [[ "$DRILL" == "1" ]]; then
  echo "== 硬闸门 C：真实部署 + 四判据 + 滚动 / 回滚 / 摘流演练 =="
  (
    cd examples/order-demo
    CLUSTER="${CLUSTER:-order-demo}" bash hack/kind-up.sh
    bash hack/verify.sh
    CLUSTER="${CLUSTER:-order-demo}" bash hack/ci-drill.sh
  ) || FAILED=1
fi

echo "== P5 复核结束（mode=$MODE version=${VERSION:-local}）：FAILED=$FAILED =="
exit "$FAILED"
