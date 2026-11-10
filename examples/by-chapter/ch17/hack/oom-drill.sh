#!/usr/bin/env bash
set -euo pipefail
NS=order-demo-dev

# 用一个独立演练 Pod 触发内存超限，不改动 api 的冻结基线
kubectl -n "${NS}" apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: oom-drill
  namespace: order-demo-dev
  labels:
    app.kubernetes.io/name: order-demo
    app.kubernetes.io/component: oom-drill
spec:
  restartPolicy: Never
  containers:
    - name: allocator
      image: python:3.12-slim
      command: ["python", "-c"]
      args:
        - |
          import time
          blocks = []
          while True:
              blocks.append(bytearray(16 * 1024 * 1024))
              time.sleep(0.2)
      resources:
        requests:
          cpu: 50m
          memory: 32Mi
        limits:
          cpu: 200m
          memory: 64Mi
YAML

# 轮询等待 OOMKilled（restartPolicy=Never，终止原因落在 state 或 lastState）
for i in $(seq 1 60); do
  REASON=$(kubectl -n "${NS}" get pod oom-drill \
    -o jsonpath='{.status.containerStatuses[0].state.terminated.reason}{.status.containerStatuses[0].lastState.terminated.reason}' 2>/dev/null || true)
  if [ "${REASON}" = "OOMKilled" ]; then
    echo "OOMKilled 已触发（第 ${i} 次轮询）"
    break
  fi
  sleep 2
done

echo "== describe 关键段 =="
kubectl -n "${NS}" describe pod oom-drill | sed -n '/Last State/,+8p'
echo "== 事件时间线 =="
kubectl -n "${NS}" get events --field-selector involvedObject.name=oom-drill --sort-by=.lastTimestamp
echo "== 按 runbook 三步定位完成；清理演练对象 =="
kubectl -n "${NS}" delete pod oom-drill --wait=false
