#!/usr/bin/env bash
# 第 30 章 · 上线检查清单长命令（按 CL 编号定位；执行后对照「通过标准」列）
# 以下命令均为只读查询，不改集群状态。
# 本文件是逐条核对的命令清单（不设 set -e）：按 CL 编号执行对应行，单条失败不影响其余核对。

# CL-30-06  同步顺序受控
kubectl -n argocd get cm argocd-cmd-params-cm -o jsonpath='{.data.applicationsetcontroller\.enable\.progressive\.syncs}'
argocd app list -o wide
