# Runbook：证书过期

症状：TLS 证书即将/已经过期，HTTPS 握手失败或浏览器报不安全。
适用：由 cert-manager 1.x 管理的 `order-demo` 入口证书（见第 19 章入口链路）。
前置：kubectl 指向 order-demo-prod；cert-manager 已安装。

## 一、定位命令
```bash
kubectl -n order-demo-prod get certificate
kubectl -n order-demo-prod get secret <tls-secret> -o jsonpath='{.data.tls\.crt}' \
  | base64 -d | openssl x509 -noout -enddate
```

## 二、止血动作
```bash
# 触发重签：删除 secret 由 cert-manager 重建
kubectl -n order-demo-prod delete secret <tls-secret>
```
- 同时核对 `renewBefore`（提前续期窗口是否足够，避免临期才续）；
- 检查 cert-manager 与入口控制器（第 19 章）链路是否正常。

## 三、验证方法
```bash
kubectl -n order-demo-prod get certificate   # READY=True，Not After 已顺延
openssl s_client -connect <host>:443 2>/dev/null | openssl x509 -noout -enddate
```

## 四、升级路径
- 重签失败 → 查 cert-manager Issuer/ClusterIssuer 与 ACME 账户（第 19 章）；
- 入口链路异常 → 转第 19 章入口与网关排查；
- 反复临期 → 调大 `renewBefore` 并登记第 22 章告警。
