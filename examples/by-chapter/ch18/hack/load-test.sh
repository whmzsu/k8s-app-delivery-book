#!/usr/bin/env bash
set -euo pipefail
NS=order-demo-dev

kubectl -n "${NS}" apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: load-gen
  namespace: order-demo-dev
  labels:
    app.kubernetes.io/name: order-demo
    app.kubernetes.io/component: load-gen
spec:
  replicas: 3
  selector:
    matchLabels:
      app.kubernetes.io/component: load-gen
  template:
    metadata:
      labels:
        app.kubernetes.io/name: order-demo
        app.kubernetes.io/component: load-gen
    spec:
      containers:
        - name: gen
          image: busybox:1.36
          command: ["/bin/sh", "-c"]
          args:
            - |
              while true; do
                wget -q -O- http://api:8081/orders >/dev/null 2>&1 || true
              done
          resources:
            requests:
              cpu: 50m
              memory: 32Mi
            limits:
              cpu: 200m
              memory: 64Mi
YAML

echo "开始记录 HPA 序列（每 10 秒一次，共 12 次，观察窗口 120s < 缩容冷却 300s）"
for i in $(seq 1 12); do
  DESIRED=$(kubectl -n "${NS}" get hpa api-hpa -o jsonpath='{.status.desiredReplicas}' 2>/dev/null || echo "n/a")
  CPU=$(kubectl -n "${NS}" get hpa api-hpa \
    -o jsonpath='{.status.currentMetrics[0].resource.current.averageUtilization}' 2>/dev/null || echo "n/a")
  printf "%s  desired=%s  cpu=%s%%\n" "$(date +%H:%M:%S)" "${DESIRED}" "${CPU}"
  sleep 10
done

echo "== 跨可用区分布 =="
kubectl -n "${NS}" get pods -l app.kubernetes.io/component=api \
  -o jsonpath='{range .items[*]}{.spec.nodeName}{"\n"}{end}' | sort | uniq -c
echo "== 清理负载生成器（缩容冷却窗口内副本应保持不回落）=="
kubectl -n "${NS}" delete deployment load-gen --wait=false
