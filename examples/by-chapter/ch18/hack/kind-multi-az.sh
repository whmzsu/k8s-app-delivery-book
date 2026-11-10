#!/usr/bin/env bash
set -euo pipefail
CLUSTER="${CLUSTER:-order-demo}"

if ! kind get clusters | grep -qx "${CLUSTER}"; then
  cat > /tmp/kind-multi-az.yaml <<'YAML'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
  - role: worker
YAML
  kind create cluster --name "${CLUSTER}" --config /tmp/kind-multi-az.yaml
fi

# 给三个 worker 打上不同可用区标签，让 topologySpreadConstraints 有可分布的域
ZONES=(az-a az-b az-c)
i=0
for NODE in $(kubectl get nodes --no-headers -o custom-columns=":metadata.name" | grep worker); do
  kubectl label node "${NODE}" "topology.kubernetes.io/zone=${ZONES[$((i % 3))]}" --overwrite
  i=$((i + 1))
done
kubectl get nodes -L topology.kubernetes.io/zone

# HPA 依赖 metrics-server；安装方式锁附录 A，此处只校验就绪
if ! kubectl -n kube-system get deploy metrics-server >/dev/null 2>&1; then
  echo "提示：HPA 需要 metrics-server 0.7.x，安装方式见附录 A"
fi
