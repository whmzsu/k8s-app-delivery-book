PREV="<上一个已验证的 sha7>"
# 方案 A（推荐，生产唯一合法路径）：用同一个晋升脚本回退引用，不重建
./hack/promote-artifact.sh --from dev --to staging --sha "${PREV}"
git push origin main
# 由第 14 章的控制器同步；此处不执行任何 kubectl 写命令

# 方案 B（仅本地 kind 演练）：直接把 image 指回已知良好的 SHA
kubectl -n order-demo-dev set image deployment/gateway \
  gateway="registry.example.com/order-demo/gateway:git-${PREV}"
kubectl -n order-demo-dev rollout status deployment/gateway --timeout=120s
