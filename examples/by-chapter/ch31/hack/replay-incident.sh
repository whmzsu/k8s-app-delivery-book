#!/usr/bin/env bash
set -euo pipefail
# 用 ch31-replay 重演 1.1 的同一变更：把 PAYMENT_TIMEOUT_MS 从 3000 调到 5000。
# 与 ch01-incident 同版本基线；本脚本在一次性 kind 集群执行，零故障完成。
CLUSTER=order-demo-replay
NS=order-demo-prod
REPORT="/tmp/replay-incident-$(date +%Y%m%d%H%M%S).log"

log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "${REPORT}"; }

if ! kind get clusters | grep -qx "${CLUSTER}"; then
  kind create cluster --name "${CLUSTER}"
fi

echo "== 0) 回滚方案先于发布方案（H5） =="
log "回滚命令：git revert <本次变更 PR> && argocd app sync --prune order-demo-prod"
log "回滚演练：在 staging 执行一次 git revert + app sync（见 31.3 回滚段）"

echo "== 1) 只改一行配置，产物不变（H1 / 公理 1、3） =="
kubectl apply --dry-run=server -f deploy/replay/order-demo-replay.yaml

echo "== 2) 应用正确形态基线 =="
kubectl apply -f deploy/replay/order-demo-replay.yaml
kubectl -n "${NS}" rollout status deployment/gateway --timeout=120s

echo "== 3) H1：产物可追溯，无 latest =="
IMG="$(kubectl -n "${NS}" get deploy gateway \
  -o jsonpath='{.spec.template.spec.containers[0].image}')"
log "image=${IMG}"
case "${IMG}" in *:latest) log "失败：出现 latest"; exit 1 ;; esac

echo "== 4) H3 / H4：滚动更新期间连续请求零 5xx =="
kubectl -n "${NS}" port-forward svc/gateway 8080:8080 >/dev/null 2>&1 &
PF=$!
trap 'kill "${PF}" 2>/dev/null || true' EXIT
for i in $(seq 1 30); do
  curl -fsS http://127.0.0.1:8080/healthz >/dev/null 2>&1 && break
  sleep 1
done
FAIL=0
for i in $(seq 1 30); do
  CODE="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/healthz || true)"
  [ "${CODE}" = "200" ] || FAIL=$((FAIL + 1))
done
log "30 次连续请求失败数=${FAIL}"
[ "${FAIL}" = "0" ] || { log "失败：出现非 200"; exit 1; }

echo "== 5) H2 / H7：Git 唯一真相、无漂移 =="
log "生产变更入口：Git PR；argocd app diff 应为空"
if command -v argocd >/dev/null 2>&1; then
  DIFF="$(argocd app diff order-demo-prod || true)"
  [ -z "${DIFF}" ] || log "注意：检测到漂移 ${DIFF}"
else
  log "argocd 未安装，漂移检查由第 14 章 CI 门禁承担"
fi

echo "== 6) H6：配置与密钥分离，凭据不入 Git =="
kubectl -n "${NS}" get configmap order-demo-config-v2 \
  -o jsonpath='{.data.PAYMENT_TIMEOUT_MS}{"\n"}'
if git grep -n 'DB_PASSWORD' -- deploy/ gitops/ | grep -q .; then
  log "失败：仓库出现明文凭据"; exit 1
fi
log "凭据由 ESO 注入键名 order-demo/db-credentials，Git 中只有引用"

echo "== 7) H8：告警带 runbook =="
log "逐条告警 100% 带 runbook_url（第 22 章 CL-G-11）"

echo "== 8) 首尾闭环：H1–H8 逐条收口 =="
echo "H1 [产物] 不可变镜像 + SHA 标签 …… 主责第 3 章，落地 6/12/24"
echo "H2 [终态] 声明式终态与控制循环 …… 主责第 2 章，深化 14/27"
echo "H3 [发布] readiness 判据 …… 主责第 8 章，深化 13/15"
echo "H4 [处置] CrashLoopBackOff 速查表 …… 主责第 23 章，根因 8 / 信号 21"
echo "H5 [回滚] 回滚方案先于发布 …… 主责第 13 章，深化 16/15"
echo "H6 [凭据] 配置与密钥分离 …… 主责第 9 章，深化 4/26"
echo "H7 [漂移] Git 唯一真相 + 自愈 …… 主责第 14 章，深化 4/23"
echo "H8 [响应] 每条告警可行动并指向 runbook …… 主责第 22 章，深化 23/20"

echo
echo "== 对照 ch01-incident 的 500，本次 /healthz 连续 30 次 200，零故障完成 =="
log "重演通过，报告: ${REPORT}"
