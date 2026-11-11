#!/usr/bin/env bash
# P5 运行时演练：在真实 kind 集群里验证第 6/8/13 章的三个承诺
#   ① 滚动更新期间 Endpoint 始终非空（零停机的服务端判据）
#   ② 回滚能回到明确的 git SHA 标签
#   ③ readiness 失败只摘 Endpoint、不重启容器（readiness ≠ liveness）
#
# 前置：已执行 hack/kind-up.sh（gateway 已 Ready，镜像已 load 进集群）
# 用法：从 examples/order-demo/ 目录执行
#       CLUSTER=order-demo ./hack/ci-drill.sh
set -euo pipefail

NS="${NS:-order-demo-dev}"
DEPLOY="${DEPLOY:-gateway}"
CLUSTER="${CLUSTER:-order-demo}"
PF_PORT="${PF_PORT:-18080}"
BASE="http://127.0.0.1:${PF_PORT}"
FAILED=0
PF=""

step() { echo; echo "== $* =="; }
ok()   { echo "  PASS  $*"; }
fail() { echo "  FAIL  $*"; FAILED=1; }
assert_eq() {
  if [[ "$1" == "$2" ]]; then ok "$3（$1）"; else fail "$3：期望 [$2]，实际 [$1]"; fi
}

start_pf() {
  [[ -n "${PF}" ]] && kill "${PF}" 2>/dev/null || true
  kubectl -n "${NS}" port-forward "svc/${DEPLOY}" "${PF_PORT}:8080" >/tmp/ci-drill-portforward.log 2>&1 &
  PF=$!
  sleep 1
}
# port-forward 绑定的是某个具体 Pod；滚动期间该 Pod 被删除时会自动断开，
# 因此每次 HTTP 判据都允许重建一次转发（重建不算服务不可用）。
http_get() {
  local path="$1"
  if ! curl -fsS --max-time 3 "${BASE}${path}" 2>/dev/null; then
    start_pf
    curl -fsS --max-time 3 "${BASE}${path}" 2>/dev/null
  fi
}
endpoints() {
  kubectl -n "${NS}" get endpoints "${DEPLOY}" -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null || true
}
cleanup() {
  [[ -n "${PF}" ]] && kill "${PF}" 2>/dev/null || true
  kubectl -n "${NS}" delete pod readiness-demo --ignore-not-found --wait=false >/dev/null 2>&1 || true
  kubectl -n "${NS}" delete svc readiness-demo --ignore-not-found --wait=false >/dev/null 2>&1 || true
}
trap cleanup EXIT

step "0. 建立端口转发"
start_pf
for _ in $(seq 1 40); do
  curl -fsS "${BASE}/healthz" >/dev/null 2>&1 && break
  sleep 1
done
http_get /healthz >/dev/null 2>&1 && ok "入口可达" || fail "入口不可达，见 /tmp/ci-drill-portforward.log"

step "1. 四判据：配置可观察 / 产物可追溯 / 禁用 latest"
ROOT_BODY="$(http_get / || true)"
echo "  ${ROOT_BODY}"
[[ "${ROOT_BODY}" == *"version=git-"* ]] && ok "APP_VERSION 来自镜像标签" || fail "根路径未返回 git-<sha7>"
BASE_IMAGE="$(kubectl -n "${NS}" get deploy "${DEPLOY}" -o jsonpath='{.spec.template.spec.containers[0].image}')"
[[ "${BASE_IMAGE}" == *":git-"* ]] && ok "镜像标签为 SHA：${BASE_IMAGE}" || fail "镜像标签不是 git-<sha7>：${BASE_IMAGE}"
[[ "${BASE_IMAGE}" != *":latest"* ]] && ok "未使用 latest" || fail "使用了 latest"

step "2. 模拟一次发布：同一镜像打新 SHA 标签并 load（build once / promote）"
NEW_IMAGE="${BASE_IMAGE}-r2"
docker tag "${BASE_IMAGE}" "${NEW_IMAGE}"
kind load docker-image "${NEW_IMAGE}" --name "${CLUSTER}" >/dev/null
ok "已加载 ${NEW_IMAGE}"

# 后台轮询 Service 的 Endpoint：滚动期间任何时刻为空都记为一次不可用。
# 用服务端判据而非客户端 curl，避免 port-forward 自身断连造成假阳性。
GAPS=/tmp/ci-drill-gaps.txt
: > "${GAPS}"
(
  for _ in $(seq 1 90); do
    ADDR="$(kubectl -n "${NS}" get endpoints "${DEPLOY}" \
      -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null || true)"
    [[ -z "${ADDR}" ]] && echo GAP >> "${GAPS}"
    sleep 0.2
  done
) &
PROBE=$!

step "3. 滚动更新（maxSurge=1 / maxUnavailable=0）"
kubectl -n "${NS}" set image "deployment/${DEPLOY}" "${DEPLOY}=${NEW_IMAGE}" >/dev/null
if timeout 180 kubectl -n "${NS}" rollout status "deployment/${DEPLOY}" --timeout=170s >/dev/null 2>&1; then
  ok "rollout 完成"
else
  fail "rollout 超时"
fi
sleep 2
kill "${PROBE}" 2>/dev/null || true
wait "${PROBE}" 2>/dev/null || true
GAPN="$(grep -c '^GAP$' "${GAPS}" || true)"
assert_eq "${GAPN}" "0" "滚动期间 Endpoint 为空的次数"
NOW_IMAGE="$(kubectl -n "${NS}" get deploy "${DEPLOY}" -o jsonpath='{.spec.template.spec.containers[0].image}')"
assert_eq "${NOW_IMAGE}" "${NEW_IMAGE}" "当前镜像标签"
http_get /healthz >/dev/null 2>&1 && ok "发布后 /healthz 仍为 200" || fail "发布后入口不可用"

step "4. 回滚：rollout undo 必须回到明确的 SHA"
kubectl -n "${NS}" rollout undo "deployment/${DEPLOY}" >/dev/null
if timeout 180 kubectl -n "${NS}" rollout status "deployment/${DEPLOY}" --timeout=170s >/dev/null 2>&1; then
  ok "回滚 rollout 完成"
else
  fail "回滚超时"
fi
BACK_IMAGE="$(kubectl -n "${NS}" get deploy "${DEPLOY}" -o jsonpath='{.spec.template.spec.containers[0].image}')"
assert_eq "${BACK_IMAGE}" "${BASE_IMAGE}" "回滚后的镜像标签"

step "5. readiness 摘流：探针失败只摘 Endpoint，不重启容器"
# 用独立 Pod + Service 演示，避免给主 Deployment 加失败探针导致滚动卡死
kubectl -n "${NS}" apply -f - <<EOF >/dev/null
apiVersion: v1
kind: Pod
metadata:
  name: readiness-demo
  namespace: ${NS}
  labels:
    app: readiness-demo
spec:
  automountServiceAccountToken: false
  containers:
    - name: gateway
      image: ${BASE_IMAGE}
      imagePullPolicy: IfNotPresent
      ports:
        - containerPort: 8080
      readinessProbe:
        httpGet:
          path: /healthz
          port: 9090
        periodSeconds: 1
        failureThreshold: 2
---
apiVersion: v1
kind: Service
metadata:
  name: readiness-demo
  namespace: ${NS}
spec:
  selector:
    app: readiness-demo
  ports:
    - port: 8080
      targetPort: 8080
EOF
sleep 8
DEMO_ADDR="$(kubectl -n "${NS}" get endpoints readiness-demo -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null || true)"
[[ -z "${DEMO_ADDR}" ]] && ok "失败探针的 Pod 未进入 Endpoint" || fail "Endpoint 仍有地址：${DEMO_ADDR}"
DEMO_RESTARTS="$(kubectl -n "${NS}" get pod readiness-demo \
  -o jsonpath='{.status.containerStatuses[0].restartCount}' 2>/dev/null || echo unknown)"
assert_eq "${DEMO_RESTARTS}" "0" "readiness-demo 容器重启次数"
DEMO_READY="$(kubectl -n "${NS}" get pod readiness-demo \
  -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo unknown)"
assert_eq "${DEMO_READY}" "False" "readiness-demo 的 Ready 条件"
kubectl -n "${NS}" delete pod readiness-demo svc readiness-demo --ignore-not-found --wait=false >/dev/null 2>&1 || true

step "6. Pod 重建后服务仍可用"
# 不用 --wait=false：旧 Pod 仍在优雅终止时 rollout status 会瞬间假 PASS，
# 随后 healthz 打到 Terminating 的 Pod 上（1.34 腿实测，D-31）。等删除完成后
# 再等替换 Pod Ready，判据才是确定的。
kubectl -n "${NS}" delete pod -l app.kubernetes.io/component=gateway >/dev/null 2>&1
if timeout 180 kubectl -n "${NS}" rollout status "deployment/${DEPLOY}" --timeout=170s >/dev/null 2>&1; then
  ok "重建后全部 Ready"
else
  fail "重建后未 Ready"
fi
http_get /healthz >/dev/null 2>&1 && ok "重建后 /healthz 仍为 200" || fail "重建后入口不可用"

echo
echo "== P5 运行时演练结束：FAILED=${FAILED} =="
exit "${FAILED}"
