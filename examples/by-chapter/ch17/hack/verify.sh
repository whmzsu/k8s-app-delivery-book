NS=order-demo-dev
PREV_TAG=ch16-stateful

# 方案 A：本地 kind / staging 演练用命令式回退（先删配额，再回退 Pod 模板）
kubectl -n "${NS}" delete -f deploy/base/resourcequota.yaml
kubectl -n "${NS}" delete -f deploy/base/limitrange.yaml
kubectl -n "${NS}" delete -f deploy/base/priorityclass.yaml
git show "${PREV_TAG}":deploy/base/deployment-api.yaml | kubectl -n "${NS}" apply -f -
kubectl -n "${NS}" rollout status deployment/api --timeout=120s

# 方案 B：生产正式路径（Git 唯一真相，见第 14 章，不手工改集群）
git diff "${PREV_TAG}"..HEAD -- deploy/base/deployment-api.yaml \
  deploy/base/limitrange.yaml deploy/base/resourcequota.yaml \
  deploy/base/priorityclass.yaml > /tmp/ch17-rollback.patch
git apply -R /tmp/ch17-rollback.patch
git add deploy/base/ docs/runbooks/ hack/oom-drill.sh
git commit -m "revert: 回退第 17 章资源字段至 ch16 基线"
git push origin main
# 由 Argo CD 2.x 收敛后核对（见第 14 章），不在生产手工 kubectl
