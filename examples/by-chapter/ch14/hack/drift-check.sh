# 路径 A（推荐，生产唯一合法路径）：回退 Git 声明，再让控制器同步
git revert <晋升 PR 的 merge commit>
git push origin main
argocd app sync order-demo-prod
argocd app wait order-demo-prod --health --timeout 120s

# 路径 B（临时止血）：按 Argo CD 历史回滚，之后必须补路径 A
HISTORY_ID="$(argocd app history order-demo-prod -o json | \
  python3 -c 'import sys,json; d=json.load(sys.stdin); print(d[1]["id"])')"
argocd app rollback order-demo-prod "${HISTORY_ID}"
argocd app wait order-demo-prod --health --timeout 120s
# 立即补：把上一版 SHA 重新渲染成 PR，见 hack/render.sh prod <上一个 sha7>

# 路径 C（冻结窗口，带有效期）：临时关掉自愈，必须以 PR 形式且到期 revert
# 在 gitops/applicationset.yaml 把 selfHeal 置 false，PR 描述写明责任人与有效期（≤ 2h）
git checkout -b freeze/order-demo-prod
# ... 提交后由控制器同步；窗口结束 git revert 该 PR
