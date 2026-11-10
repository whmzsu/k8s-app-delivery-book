# 1) 把清单改回原则基线（消除所有临时让步）
kubectl apply -f deploy/base/namespace.yaml
kubectl apply -f deploy/base/deployment.yaml
kubectl apply -f deploy/base/service.yaml
kubectl -n order-demo-dev rollout status deployment/gateway --timeout=120s

# 2) 例外到期：把登记表恢复为初始模板（删除所有 EXC- 登记行）
git checkout ch03-principles -- docs/principles-exceptions.md

# 3) 确认没有遗留例外
grep -c '^| EXC-' docs/principles-exceptions.md || true
