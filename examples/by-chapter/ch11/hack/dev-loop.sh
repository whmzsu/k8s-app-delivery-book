# 方案 A：新规则误伤（本章最常见的回滚原因）——只回退校验，不动应用
git checkout <上一 tag> -- .github/workflows/validate.yml \
                           .github/workflows/validate-manifests.yml \
                           policy/ hack/validate.sh
echo "误伤原因：<在此写明被误伤的资源与规则名，供统稿复查>"
./hack/validate.sh --static

# 方案 B：应用侧若因误判被拦，回到 Git 上一 tag 重新声明
git checkout <上一 tag> -- deploy/overlays/dev/ deploy/base/
kubectl apply -k deploy/overlays/dev
kubectl -n order-demo-dev rollout status deployment/gateway --timeout=120s

# 方案 C：版本矩阵某个 job 持续失败，先降级为两版本并登记
yq -i '.kubernetes_versions = ["1.32", "1.33"]' hack/kind-matrix.yaml
# 同步修改 .github/workflows/validate.yml 的 matrix.k8s，再跑一致性断言
./hack/validate.sh --static
