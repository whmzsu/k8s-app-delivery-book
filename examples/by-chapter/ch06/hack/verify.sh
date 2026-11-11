#!/usr/bin/env bash
set -uo pipefail   # 不用 -e：让所有断言跑完再汇总，一次性给出完整失败清单
NS=order-demo-dev
SHA="$(git rev-parse --short=7 HEAD)"
IMAGE="registry.example.com/order-demo/gateway:git-${SHA}"
FAIL=0
mark() { if [ "$1" -eq 0 ]; then echo "PASS $2"; else echo "FAIL $2"; FAIL=1; fi; }

kubectl -n "${NS}" port-forward svc/gateway 8080:8080 >/dev/null 2>&1 &
PF=$!
trap 'kill "${PF}" 2>/dev/null || true' EXIT

for i in $(seq 1 30); do
  curl -fsS http://127.0.0.1:8080/healthz >/dev/null 2>&1 && break
  sleep 1
done

# A1：/healthz 可达且正文为 ok
HZ="$(curl -fsS http://127.0.0.1:8080/healthz || true)"
mark $? "A1 /healthz 200"
[ "${HZ}" = "ok" ]; mark $? "A1b /healthz 正文为 ok"

# A2：根路径非 5xx（6.1.1 的教训：配置值炸在请求路径上，探针看不见）
curl -fsS http://127.0.0.1:8080/ >/dev/null 2>&1
mark $? "A2 根路径非 5xx"

# A3：响应含 ConfigMap 的 GREETING，证明注入生效而非镜像默认值
ROOT="$(curl -fsS http://127.0.0.1:8080/ || true)"
echo "${ROOT}" | grep -q "hello from configmap (dev)"; mark $? "A3 GREETING 来自 ConfigMap"

# A4：version、镜像标签、git SHA 三方一致（产物可追溯）
echo "${ROOT}" | grep -q "version=git-${SHA}"; mark $? "A4a 响应 version=git-<sha>"
DEPLOY_IMAGE="$(kubectl -n "${NS}" get deploy gateway \
  -o jsonpath='{.spec.template.spec.containers[0].image}')"
[ "${DEPLOY_IMAGE}" = "${IMAGE}" ]; mark $? "A4b Deployment 镜像=本次构建"

# A5：两副本全部就绪（Pod 起来，而不是只看构建成功——见 6.4.2 构建期/运行期之分）
READY="$(kubectl -n "${NS}" get deploy gateway -o jsonpath='{.status.readyReplicas}')"
[ "${READY}" = "2" ]; mark $? "A5 readyReplicas=2"

exit "${FAIL}"
