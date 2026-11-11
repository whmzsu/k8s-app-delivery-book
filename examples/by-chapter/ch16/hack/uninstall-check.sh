#!/usr/bin/env bash
set -euo pipefail
NS=order-demo-prod

echo "== 列出仍带 finalizer 的对象 =="
kubectl -n "${NS}" get all,pvc,statefulset -o json | \
  python3 -c '
import sys, json
d = json.load(sys.stdin)
for item in d["items"]:
    fs = item.get("metadata", {}).get("finalizers", [])
    if fs:
        print(item["kind"], item["metadata"]["name"], fs)
'

echo "== 卸载顺序：先删实例，等清理完成，最后删控制器 =="
echo "1) kubectl -n ${NS} delete statefulset db --wait=true"
echo "2) 确认上面的列表为空（清理钩子已执行完）"
echo "3) 才允许删除 Operator / CRD（详见第 27 章）"
echo "禁止用 --force --grace-period=0 或手工 patch 掉 finalizer 跳过清理。"
