#!/usr/bin/env bash
set -euo pipefail
CLUSTER=order-demo-incident
NS=order-demo-prod

if ! kind get clusters | grep -qx "${CLUSTER}"; then
  kind create cluster --name "${CLUSTER}" --config kind-config.yaml
fi

kubectl apply -f deploy/incident/order-demo-incident.yaml
kubectl -n "${NS}" rollout status deployment/gateway --timeout=30s || true

kubectl -n "${NS}" port-forward svc/gateway 8080:8080 >/dev/null 2>&1 &
PF=$!
trap 'kill "${PF}" 2>/dev/null || true' EXIT
for i in $(seq 1 15); do
  curl -fsS http://127.0.0.1:8080/healthz >/dev/null 2>&1 && break
  sleep 1
done

echo "== curl /orders =="
curl -i http://127.0.0.1:8080/orders || true

echo
echo "== 本次事故的 8 个失效点（合成案例，逐条对照全书） =="
echo "H1 [产物] :latest 被覆盖，线上跑的不是以为的产物 …… 详见第 3 章"
echo "H2 [终态] 手工 kubectl edit 改运行对象，被控制循环改回去 …… 详见第 2 章"
echo "H3 [发布] 滚动更新卡住，新 Pod 永远不 Ready …… 详见第 8 章"
echo "H4 [处置] liveness 误杀引发重启级联，现场无人能定位 …… 详见第 23 章"
echo "H5 [回滚] 想回滚却发现没有回滚方案 / schema 不兼容 …… 详见第 13 章"
echo "H6 [凭据] 密钥轮换踩坑，配置与凭据混在一起 …… 详见第 9 章"
echo "H7 [漂移] 有人手工 kubectl edit 改了生产，Git 里没有对应声明 …… 详见第 14 章"
echo "H8 [响应] 告警响了却没有 runbook，值班不知道做什么 …… 详见第 22 章"
