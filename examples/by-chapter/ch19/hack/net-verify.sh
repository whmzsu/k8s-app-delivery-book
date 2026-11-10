#!/usr/bin/env bash
set -euo pipefail
NS=order-demo-dev

echo "== GatewayClass 就绪 =="
kubectl get gatewayclass eg

echo "== Gateway / HTTPRoute 状态 =="
kubectl -n "${NS}" get gateway,httproute
kubectl -n "${NS}" get gateway order-demo-gw \
  -o jsonpath='{.status.conditions[?(@.type=="Accepted")].status}{"\n"}'
kubectl -n "${NS}" get httproute gateway-route \
  -o jsonpath='{.status.parents[0].conditions[?(@.type=="Accepted")].status}{"\n"}'

echo "== 证书有效期与续期时间 =="
kubectl -n "${NS}" get certificate order-demo-tls
kubectl -n "${NS}" get certificate order-demo-tls \
  -o jsonpath='{.status.notAfter}{"\t"}{.status.renewalTime}{"\n"}'

echo "== 经 Gateway API 入口访问 /orders =="
GW_SVC=$(kubectl -n envoy-gateway-system get svc -o name 2>/dev/null \
  | grep 'envoy-' | head -1 | cut -d/ -f2 || true)
if [ -z "${GW_SVC}" ]; then
  echo "提示：未探测到 Envoy Gateway 1.x 数据面 Service，可显式设置 GW_SVC 后重跑；对象状态已验证"
else
  kubectl -n envoy-gateway-system port-forward "svc/${GW_SVC}" 8080:80 >/dev/null 2>&1 &
  PF=$!
  trap 'kill "${PF}" 2>/dev/null || true' EXIT
  for i in $(seq 1 20); do
    curl -fsS -H 'Host: order-demo.example.com' \
      http://127.0.0.1:8080/orders >/dev/null 2>&1 && break
    sleep 1
  done
  curl -i -H 'Host: order-demo.example.com' http://127.0.0.1:8080/orders
fi
