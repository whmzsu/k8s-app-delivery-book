#!/usr/bin/env bash
set -euo pipefail
NS=order-demo-prod
POD=db-0
PSQL=(kubectl -n "${NS}" exec "${POD}" -- psql -U postgres -d orderdemo -tAc)

ROWS="$("${PSQL[@]}" "SELECT count(*) FROM orders;")"
MISSING="$("${PSQL[@]}" "SELECT count(*) FROM orders WHERE amount_cents IS NULL;")"
DRIFT="$("${PSQL[@]}" \
  "SELECT count(*) FROM orders WHERE amount IS NOT NULL AND amount_cents <> ROUND(amount*100)::BIGINT;")"

echo "orders=${ROWS} missing_amount_cents=${MISSING} amount_mismatch=${DRIFT}"
[ "${MISSING}" = "0" ] || { echo "新列存在未回填行" >&2; exit 1; }
[ "${DRIFT}" = "0" ]  || { echo "新旧列金额不一致，禁止进入 contract" >&2; exit 1; }
echo "双写一致性校验通过。"
