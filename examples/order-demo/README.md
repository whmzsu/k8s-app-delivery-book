# `order-demo` 第 6 章基线

这是全书贯穿案例在第 6 章「先跑通：一个应用的最小完整闭环」处的**完整可运行基线**，与 `chapters/ch06.md` §6.4 逐字一致。第 7–31 章的增量配置在各章 §N.4 给出，按章叠加即可。

## 运行

```bash
cd examples/order-demo
chmod +x hack/kind-up.sh hack/verify.sh
./hack/kind-up.sh     # 起 kind、构建 SHA 标签镜像、装进集群、apply、等待 Ready
./hack/verify.sh      # curl /healthz、检查 GREETING 来自 ConfigMap、打印 image 字段
```

前置：Docker（或兼容 OCI 构建器）、`kind`、`kubectl`、`curl`、git。版本见附录 A。

## 验收

| 判据 | 期望 |
|---|---|
| `/healthz` | HTTP 200 |
| 根路径 | 含 `hello from configmap (dev)` 与 `version=git-<真实短 SHA>` |
| image 字段 | `registry.example.com/order-demo/gateway:git-<sha7>`，无 `latest` |
| 删 Pod 后 | 重跑 `verify.sh` 仍返回 200 |

回滚演练命令见 `chapters/ch06.md` §6.5；上线检查清单见附录 B。

## 配置契约（不得改动）

命名空间 `order-demo-dev`｜Service 名 `gateway`｜端口 8080｜标签 `app.kubernetes.io/name=order-demo`、`component=gateway`、`version=git-<sha7>`、`managed-by=kubectl`｜镜像标签 `git-<sha7>`。完整契约见 `book/case-evolution.md`。
