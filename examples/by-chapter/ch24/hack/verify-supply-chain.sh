#!/usr/bin/env bash
set -euo pipefail
NS=order-demo-dev
REPO=registry.example.com/order-demo/gateway
SHA7="$(git rev-parse --short=7 HEAD)"
SIGNED_TAG="${REPO}:git-${SHA7}"
UNSIGNED_TAG="${REPO}:unsigned-${SHA7}"

# 0) 前置：Kyverno 1.x 已部署在命名空间 kyverno（部署方式见第 25 章，本书不写安装教程）
kubectl -n kyverno get deploy >/dev/null 2>&1 || {
  echo "缺少 Kyverno 1.x（命名空间 kyverno），请先按第 25 章部署" >&2; exit 1; }

# 1) 生成密钥对，把策略里的示例公钥换成真实公钥
if [ ! -f cosign.key ]; then
  COSIGN_PASSWORD="" cosign generate-key-pair
fi
PUB_B64="$(grep -v -- '-----' cosign.pub | tr -d '\n')"
sed "s|REPLACE_WITH_COSIGN_PUBLIC_KEY_BASE64|${PUB_B64}|" \
  policies/order-demo-verify-image-signature.yaml > /tmp/verify-policy.yaml
kubectl apply -f /tmp/verify-policy.yaml
kubectl get clusterpolicy order-demo-verify-image-signature -o jsonpath='{.spec.validationFailureAction}{"\n"}'

# 2) 未签名镜像：复用已构建镜像换标签推送，不带任何签名
docker tag "${SIGNED_TAG}" "${UNSIGNED_TAG}"
docker push "${UNSIGNED_TAG}"

# 3) 签名镜像应通过；未签名镜像应被准入拒绝
cat >/tmp/signed-deploy.yaml <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gateway-signed
  namespace: ${NS}
  labels:
    app.kubernetes.io/name: order-demo
    app.kubernetes.io/component: gateway
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: order-demo
      app.kubernetes.io/component: gateway
  template:
    metadata:
      labels:
        app.kubernetes.io/name: order-demo
        app.kubernetes.io/component: gateway
        version: git-${SHA7}
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: gateway
          image: ${SIGNED_TAG}
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8080
              protocol: TCP
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
          readinessProbe:
            httpGet:
              path: /readyz
              port: http
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
EOF
kubectl apply -f /tmp/signed-deploy.yaml
kubectl -n "${NS}" rollout status deployment/gateway-signed --timeout=120s

sed "s|image: ${SIGNED_TAG}|image: ${UNSIGNED_TAG}|; s|name: gateway-signed|name: gateway-unsigned|g" \
  /tmp/signed-deploy.yaml > /tmp/unsigned-deploy.yaml
if kubectl apply -f /tmp/unsigned-deploy.yaml > /tmp/unsigned.out 2>&1; then
  echo "FAIL：未签名镜像竟然被准入放行" >&2; exit 1
fi
grep -Eqi 'blocked|denied|failed|verification' /tmp/unsigned.out
echo "OK：未签名镜像被准入拒绝"
cat /tmp/unsigned.out

# 4) 证据可检索：签名、SBOM 制品与按 SHA 归档的报告
COSIGN_PASSWORD="" cosign verify --key cosign.pub --insecure-ignore-tlog=true "${SIGNED_TAG}"
cosign download sbom "${SIGNED_TAG}" > /tmp/downloaded-sbom.json
grep -q 'spdxVersion' /tmp/downloaded-sbom.json
crane ls "${REPO}" | grep '^sha256-' | head -n 5

# 5) 降级演练：Enforce -> Audit -> Enforce，并确认两次状态
sed 's|validationFailureAction: Enforce|validationFailureAction: Audit|' \
  /tmp/verify-policy.yaml | kubectl apply -f -
kubectl get clusterpolicy order-demo-verify-image-signature -o jsonpath='{.spec.validationFailureAction}{"\n"}'
kubectl apply -f /tmp/verify-policy.yaml
kubectl get clusterpolicy order-demo-verify-image-signature -o jsonpath='{.spec.validationFailureAction}{"\n"}'

# 6) 清理演练产物
kubectl -n "${NS}" delete deployment gateway-signed --ignore-not-found
