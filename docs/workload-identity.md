# Workload Identity / IRSA 接入 diff（order-demo）

> 本文件是「机器身份」接入的可复制 diff（对应第 26 章 §26.2.3）。
> 白话：让 Pod 用 Kubernetes ServiceAccount 身份去云厂 IdP 换一张短期令牌，
> SDK 自动刷新，配置里不再出现长期 Access Key（公理 9，见第 3 章）。
> 下面以 AWS IRSA 为唯一示例，GCP Workload Identity 的等价 annotation 写在注释里。
> 账号 ID `arn:aws:iam::123456789012:role/...` 为示例，实际值由 IaC 注入（第 30 章），不写明文凭据。

## 最小接入 diff

```yaml
# policies/rbac/order-demo-workload-identity.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: api
  namespace: order-demo-prod
  annotations:
    # AWS IRSA：让该 SA 可换发 order-demo-api 角色
    eks.amazonaws.com/role-arn: "arn:aws:iam::123456789012:role/order-demo-api"
    # GCP Workload Identity 改用下面一行，并把 GSA 绑定到该 KSA：
    # iam.gke.io/gcp-service-account: "order-demo-api@example-project.iam.gserviceaccount.com"
  labels:
    app.kubernetes.io/name: order-demo
    # 配合 tenant-isolation-checklist：automountServiceAccountToken 在 Pod 模板置 false，
    # token 只经 projected 卷发出（见第 26 章 §26.2.2）。
```

## 四段信任链（任何一环配错都表现为 403，按此逐项验证）

1. **集群 Issuer**：托管集群控制面内置 OIDC 签发者，为 Pod 的 projected SA token 签名，公开 `/.well-known/openid-configuration` 与 JWKS。issuer 形如 `https://oidc.eks.cn-north-1.amazonaws.com/id/EXAMPLE...`（示例 ID，实际由集群 IaC 产出）。
2. **云侧 IdP 注册**：在 IAM 把 issuer URL 与根 CA 指纹注册为 OIDC identity provider——云厂从此「认识」这个集群。
3. **IAM Role 信任策略**：用 `Condition` 把 `sub` 钉死为 `system:serviceaccount:order-demo-prod:api`、`aud` 钉死为 `sts.amazonaws.com`。`sub` 同时含命名空间与 SA 名，是防冒用关键。
4. **换发临时凭据**：Pod 内 SDK 用挂载 token 调 `AssumeRoleWithWebIdentity`，换到带 TTL 的临时 AK/SK/session token（TTL 可缩到 15 分钟），到期自动换发；集群里全程无长期 Access Key [R-26-1][R-26-9]。

## 验证命令

```bash
# SA annotation 已正确（信任策略的 sub 来源）
kubectl -n order-demo-prod get sa api -o yaml | grep 'eks.amazonaws.com/role-arn'
# 拆开 token 的 JWT payload，把 sub / aud 与 IAM Condition 逐字比对
kubectl -n order-demo-prod create token api --duration=1h | cut -d. -f2 | base64 -d 2>/dev/null
# 吊销演练（演示用合成步骤）：改信任策略挡「新发」，等 TTL 过期即了结「存量」
```

## 凭据生命周期对照（判据见 §26.2.3）

| 凭据类型 | 签发方 | 过期机制 | 吊销方式 |
|---|---|---|---|
| legacy token Secret | API Server | **永不过期** | 删除 Secret + 轮换集群签名密钥（按永久泄露处置） |
| bound projected token（推荐） | API Server | `expirationSeconds`（600s–1d），kubelet 自动换发 | 删挂载它的 Pod 即失效 |
| OIDC 联邦换发的云凭据（IRSA） | 云厂 STS | TTL（可收至 15 分钟） | 改信任策略 + 等 TTL 过期 + 收敛 Role 权限边界 |

> 审计留痕两侧都看：云侧每次 `AssumeRoleWithWebIdentity`（成功与被拒）有云厂审计；
> 集群侧 `kubectl create token` 对应 `serviceaccounts/token` 的 create，审计策略列为 RequestResponse。
