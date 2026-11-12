#!/usr/bin/env bash
# 第 17 章 · 上线检查清单长命令（按 CL 编号定位；执行后对照「通过标准」列）
# 以下命令均为只读查询，不改集群状态。
# 本文件是逐条核对的命令清单（不设 set -e）：按 CL 编号执行对应行，单条失败不影响其余核对。

# CL-17-01  全工作负载有 requests
kubectl -n order-demo-dev get deploy,sts -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.template.spec.containers[*].resources.requests}{"\n"}{end}'

# CL-17-02  QoS 符合预期
kubectl -n order-demo-dev get pod -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.qosClass}{"\n"}{end}'

# CL-S-01  非 root 运行
kubectl -n order-demo-dev get deploy api -o jsonpath='{.spec.template.spec.securityContext}'
# 与镜像 USER 对照

# CL-S-02  权限最小化
kubectl -n order-demo-dev get deploy api -o jsonpath='{.spec.template.spec.automountServiceAccountToken}'
# 与 SA 绑定 Role 对照
