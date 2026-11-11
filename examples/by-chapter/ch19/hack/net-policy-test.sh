#!/usr/bin/env bash
set -euo pipefail
NS=order-demo-dev

echo "== 授权链路：app.kubernetes.io/component=api 的 Pod 访问 db:5432 应成功 =="
kubectl -n "${NS}" run net-policy-authorized --rm -i --restart=Never \
  --labels='app.kubernetes.io/name=order-demo,app.kubernetes.io/component=api' \
  --image=busybox:1.36 --command -- sh -c \
  'nc -z -w2 db 5432 && echo "api->db: ALLOWED (expected)" || echo "api->db: BLOCKED (unexpected)"'

echo "== 未授权链路：app.kubernetes.io/component=probe 的 Pod 访问 db:5432 应失败 =="
kubectl -n "${NS}" run net-policy-unauthorized --rm -i --restart=Never \
  --labels='app.kubernetes.io/name=order-demo,app.kubernetes.io/component=probe' \
  --image=busybox:1.36 --command -- sh -c \
  'nc -z -w2 db 5432 && echo "UNEXPECTED: reachable" || echo "probe->db: DENIED (expected)"'

echo "== 已生效的策略清单 =="
kubectl -n "${NS}" get networkpolicy
