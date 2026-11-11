#!/usr/bin/env bash
# A=100m/500m（契约）B=100m/100m（拉平）C=500m/500m（Guaranteed）
set -euo pipefail
NS=order-demo-dev
OUT=docs/benchmarks/ch17-cpu-limit-ab
mkdir -p "${OUT}"

kubectl -n "${NS}" scale deploy/api --replicas=2
kubectl -n "${NS}" rollout status deploy/api --timeout=180s

kubectl -n "${NS}" port-forward svc/gateway 8080:8080 >/dev/null 2>&1 &
PF=$!
trap 'kill ${PF} 2>/dev/null || true' EXIT
sleep 3
printf 'GET http://127.0.0.1:8080/orders\n' > "${OUT}/targets.txt"

bench() {   # $1=组名 $2=cpu request $3=cpu limit
  kubectl -n "${NS}" set resources deploy/api \
    --requests=cpu="$2",memory=128Mi --limits=cpu="$3",memory=256Mi
  kubectl -n "${NS}" rollout status deploy/api --timeout=180s
  sleep 60
  for R in 100 200 300 400 500; do
    vegeta attack -targets="${OUT}/targets.txt" -rate="${R}/1s" -duration=5m \
      | tee "${OUT}/$1-${R}.bin" | vegeta report -type=json > "${OUT}/$1-${R}.json"
    jq -r --arg g "$1" --arg r "$R" \
      '[$g,$r,(.latencies.p50/1e6),(.latencies.p99/1e6),(.latencies.max/1e6)]|@tsv' \
      "${OUT}/$1-${R}.json" >> "${OUT}/summary.tsv"
    POD=$(kubectl -n "${NS}" get pod -l app.kubernetes.io/component=api \
      -o jsonpath='{.items[0].metadata.name}')
    kubectl -n "${NS}" exec "${POD}" -c api -- cat /sys/fs/cgroup/cpu.stat \
      | sed "s/^/$1 $R /" >> "${OUT}/cpu-stat.log"
  done
}

bench A 100m 500m
bench B 100m 100m
bench C 500m 500m

# 复位到配置契约值，避免把演练写法留在集群里
kubectl -n "${NS}" set resources deploy/api \
  --requests=cpu=100m,memory=128Mi --limits=cpu=500m,memory=256Mi
kubectl -n "${NS}" rollout status deploy/api --timeout=180s
