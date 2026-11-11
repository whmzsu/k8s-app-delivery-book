#!/usr/bin/env bash
set -euo pipefail

TARGET_CLUSTER="${1:?用法: $0 <新集群 context> <backup 名>}"
BACKUP="${2:?用法: $0 <新集群 context> <backup 名>}"
REPORT="docs/restore-drill-report.md"

echo "== 确认目标是演练集群，不是生产 =="
kubectl config current-context | grep -q "${TARGET_CLUSTER}"
! kubectl config current-context | grep -q 'prod'

echo "== 在演练集群创建恢复 =="
velero --kubecontext "${TARGET_CLUSTER}" restore create \
  --from-backup "${BACKUP}" \
  --namespace-mappings order-demo-prod:order-demo-restore \
  --wait

echo "== 数据一致性校验 =="
kubectl --context "${TARGET_CLUSTER}" -n order-demo-restore get statefulset db
kubectl --context "${TARGET_CLUSTER}" -n order-demo-restore wait \
  --for=condition=Ready pod/db-0 --timeout=300s
ROWS="$(kubectl --context "${TARGET_CLUSTER}" -n order-demo-restore exec db-0 -- \
  psql -U postgres -d orderdemo -tAc 'SELECT count(*) FROM orders;')"
MISSING="$(kubectl --context "${TARGET_CLUSTER}" -n order-demo-restore exec db-0 -- \
  psql -U postgres -d orderdemo -tAc 'SELECT count(*) FROM orders WHERE amount_cents IS NULL;')"
echo "restored_orders=${ROWS} missing_amount_cents=${MISSING}"
[ "${MISSING}" = "0" ] || { echo "恢复后数据不一致" >&2; exit 1; }

echo "== 写入演练报告 =="
cat > "${REPORT}" <<EOF
# 备份恢复演练报告

- 日期：$(date -u +%FT%TZ)
- 目标集群：${TARGET_CLUSTER}（演练专用，非生产）
- 备份名：${BACKUP}
- 恢复命名空间：order-demo-restore
- 恢复订单行数：${ROWS}
- 新列缺失行数：${MISSING}
- 一致性校验：通过
- 责任人：发布值班（主）／ 数据 owner（备）
- 结论：本次备份可恢复；报告归档到发布 PR
EOF
echo "演练通过，报告: ${REPORT}"
