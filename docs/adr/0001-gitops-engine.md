# ADR 0001：GitOps 引擎与密钥方案

状态：已接受（2026-11-10）

## 决策
1. GitOps 引擎采用 Argo CD 3.x 为唯一示例实现；Flux 2.x 仅在选型矩阵作对比。
2. 采用仓库内渲染（rendered manifests）：PR 中 diff 的是最终清单。
3. 多环境由 ApplicationSet 的 List 生成器一次生成，晋升只改各环境渲染产物里的
   image tag，不改产物本身。
4. 密钥采用 External Secrets Operator + 后端 vault，键名 order-demo/db-credentials；
   SOPS 3.x 与 Sealed Secrets 0.x 仅作对比。
5. 生产变更一律走 Git PR；应急止血「先提交 PR、后同步」，自愈配白名单与冻结窗口。

## 理由
单一示例实现：避免两章各选一套导致示例跑不通。
rendered manifests：评审者必须能在合并前看到真正会被 apply 的字节。
密钥不入 Git：全书公理 9，且与第 9 章方案一致。

## 后果
- 正向：漂移自动纠正、晋升可 diff、回滚统一为 git revert。
- 负向：渲染产物随环境数增长；需维护 hack/render.sh 与工具版本（附录 A）。
- 约束：第 14 章起 app.kubernetes.io/managed-by 由 kustomize 改为 argocd。
