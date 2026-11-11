#!/usr/bin/env bash
# v1alpha1 → v1beta1 双写与 storage 轮转演练；只在演练集群执行，prod 必须走 Git PR（公理 5）
set -euo pipefail
CRD=maintenancewindows.ops.example.com
NS=default
API_OLD=ops.example.com/v1alpha1
API_NEW=ops.example.com/v1beta1

step() { printf '\n=== %s ===\n' "$*"; }
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
raw()  { kubectl get --raw "/apis/$1/namespaces/$NS/maintenancewindows/$2"; }

step "0 前置：webhook 必须健康，否则任何 storage 变更都会把对象读坏"
kubectl -n order-demo-system rollout status deploy/order-demo-operator-webhook --timeout=120s
[ "$(kubectl get crd "$CRD" -o jsonpath='{.spec.conversion.strategy}')" = "Webhook" ] \
  || fail "conversion.strategy 不是 Webhook"
kubectl get crd "$CRD" -o json | jq -e '.spec.versions[0].name=="v1alpha1" and .spec.versions[1].name=="v1beta1"' >/dev/null \
  || fail "版本顺序与脚本假设不符，先按实际索引改下面的 json patch"

step "1 双写验证一：旧版本创建，两个版本互为视图"
kubectl apply -f operator/config/samples/ops_v1alpha1_maintenancewindow.yaml
old_spec=$(raw "$API_OLD" idem-sample | jq -S '.spec')
new_spec=$(raw "$API_NEW" idem-sample | jq -S '.spec')
diff <(echo "$old_spec") <(echo "$new_spec") || fail "round-trip 后 spec 不一致"

step "2 双写验证二：新字段在降级视图里不许丢"
kubectl apply -f - <<'EOF'
apiVersion: ops.example.com/v1beta1
kind: MaintenanceWindow
metadata:
  name: drill-suspend
  namespace: default
spec:
  replicas: 2
  reason: "storage 轮转演练"
  suspend: true
EOF
raw "$API_OLD" drill-suspend | jq -e '.metadata.annotations["ops.example.com/converted-suspend"]=="true"' >/dev/null \
  || fail "降级视图未通过注解保留 suspend"
raw "$API_NEW" drill-suspend | jq -e '.spec.suspend==true' >/dev/null \
  || fail "round-trip 丢了 suspend（ConvertTo 未读注解）"

step "3 切 storage：一次 patch 同时改两个版本，绝不分成两次"
kubectl patch crd "$CRD" --type=json -p '[
  {"op":"replace","path":"/spec/versions/0/storage","value":false},
  {"op":"replace","path":"/spec/versions/1/storage","value":true}
]'

step "4 重写存量对象，让 etcd 真正落到 v1beta1（不重写，storedVersions 永远有两个）"
for ns in $(kubectl get "$CRD" -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\n"}{end}' | sort -u); do
  for name in $(kubectl -n "$ns" get "$CRD" -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'); do
    kubectl -n "$ns" get "$CRD" "$name" -o json \
      | jq 'del(.metadata.managedFields) | .apiVersion="ops.example.com/v1beta1"' \
      | kubectl replace -f - >/dev/null
  done
done

step "5 验证 storedVersions 只剩 v1beta1"
stored=$(kubectl get crd "$CRD" -o jsonpath='{.status.storedVersions}')
echo "storedVersions=$stored"
case "$stored" in *v1alpha1*) fail "仍有对象以 v1alpha1 落盘，补跑第 4 步" ;; esac

step "6 关旧版本 served（此刻 v1alpha1 读写 4xx，属预期）"
kubectl patch crd "$CRD" --type=json -p '[{"op":"replace","path":"/spec/versions/0/served","value":false}]'
if kubectl get --raw "/apis/$API_OLD/namespaces/$NS/maintenancewindows/drill-suspend" >/dev/null 2>&1; then
  fail "旧版本仍可读，served 未生效"
fi
raw "$API_NEW" drill-suspend | jq -r '.spec.suspend' | grep -qx true || fail "关闭 served 后新版本读数异常"

step "R 回滚：先恢复 served，再切回 storage，最后再重写一遍"
kubectl patch crd "$CRD" --type=json -p '[{"op":"replace","path":"/spec/versions/0/served","value":true}]'
kubectl patch crd "$CRD" --type=json -p '[
  {"op":"replace","path":"/spec/versions/0/storage","value":true},
  {"op":"replace","path":"/spec/versions/1/storage","value":false}
]'
for name in $(kubectl -n "$NS" get "$CRD" -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'); do
  kubectl -n "$NS" get "$CRD" "$name" -o json \
    | jq 'del(.metadata.managedFields) | .apiVersion="ops.example.com/v1alpha1"' \
    | kubectl replace -f - >/dev/null
done
echo "回滚完成，storedVersions=$(kubectl get crd "$CRD" -o jsonpath='{.status.storedVersions}')"
