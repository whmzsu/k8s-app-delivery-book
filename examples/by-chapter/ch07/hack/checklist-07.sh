#!/usr/bin/env bash
# 第 7 章 · 上线检查清单长命令（按 CL 编号定位；执行后对照「通过标准」列）
# 以下命令均为只读查询，不改集群状态。
# 本文件是逐条核对的命令清单（不设 set -e）：按 CL 编号执行对应行，单条失败不影响其余核对。

# CL-07-02  无裸 Pod
kubectl -n order-demo-dev get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.ownerReferences[0].kind}{"\n"}{end}'
