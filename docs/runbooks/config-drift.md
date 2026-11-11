# Runbook：配置漂移

症状：集群实际状态与 Git 声明不一致（第 14 章"漂移"：集群里的值和 Git 里写的不一样）。
最常见触发：有人在 prod 手工 `kubectl edit` 改了副本数、镜像或 ConfigMap。
前置：Argo CD 3.x 已接入 order-demo（见第 14 章）；kubectl 指向 order-demo-prod。

## 一、定位命令
```bash
argocd app diff order-demo
kubectl -n order-demo-prod get cm order-demo-config -o yaml   # 与 Git 对照
```

## 二、止血动作（首步）
```bash
# 由 Git 唯一真相收敛，不手工 kubectl edit 改回去
argocd app sync order-demo
```
- 漂移自动纠正：selfHeal 开启时 Argo CD 会自行把集群拉回 Git 声明（第 14 章）。

## 三、验证方法
```bash
argocd app diff order-demo   # 输出为空，无漂移
kubectl -n order-demo-prod get deploy -o jsonpath='{..image}'   # 与 Git 声明一致
```

## 四、升级路径
- 漂移频繁 → 收紧 RBAC（第 26 章），禁止人手改生产；
- 误改需应急 → 按第 26 章 break-glass 流程，且必须回写 Git（公理 5）；
- 跨团队 → 转第 14 章 AppProject / RBAC 边界。
