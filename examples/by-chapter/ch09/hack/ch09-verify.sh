#!/usr/bin/env bash
set -euo pipefail
NS=order-demo-dev

echo "== 1. 仓库无凭据明文（只允许键名/字段名，不允许带值）=="
if grep -RniE "(password|passwd|token|secret)[\"' ]*[:=][\"' ]*[A-Za-z0-9+/]{6,}" deploy/ docs/; then
  echo "FAIL: 发现疑似明文凭据" >&2
  exit 1
fi
echo "OK: 无带值凭据行"

echo "== 2. ConfigMap 不可变 =="
kubectl -n "${NS}" get cm order-demo-config -o jsonpath='{.immutable}{"\n"}'

echo "== 3. 凭据已注入 api 容器（只看键名，不打印值）=="
kubectl -n "${NS}" exec deploy/api -- env | grep '^DB_' | cut -d= -f1

echo "== 4. 镜像标签未因轮换改变 =="
kubectl -n "${NS}" get deploy api -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'

echo "== 5. 最小闭环仍通 =="
./hack/verify.sh
