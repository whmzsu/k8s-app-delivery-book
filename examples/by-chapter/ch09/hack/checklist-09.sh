#!/usr/bin/env bash
# 第 9 章 · 上线检查清单长命令（按 CL 编号定位；执行后对照「通过标准」列）
# 以下命令均为只读查询，不改集群状态。
# 本文件是逐条核对的命令清单（不设 set -e）：按 CL 编号执行对应行，单条失败不影响其余核对。

# CL-S-02  SA token 不挂载、ESO 用专用 SA
kubectl -n order-demo-dev get deploy api -o jsonpath='{..automountServiceAccountToken}'
# 与 secretstore.yaml 的 serviceAccountRef 对照
