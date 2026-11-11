#!/usr/bin/env bash
# 生成转换 webhook 的自签 CA 与服务端证书，并把 CA 注入 CRD 的 caBundle
set -euo pipefail
NS=order-demo-system
SVC=order-demo-operator-webhook
DIR=certs
CRD=maintenancewindows.ops.example.com

mkdir -p "$DIR"
openssl genrsa -out "$DIR/ca.key" 2048
openssl req -x509 -new -nodes -key "$DIR/ca.key" -days 3650 \
  -subj "/CN=order-demo-operator-webhook-ca" -out "$DIR/ca.crt"

cat > "$DIR/server.cnf" <<EOF
[req]
req_extensions = v3_req
distinguished_name = dn
prompt = no
[dn]
CN = $SVC.$NS.svc
[v3_req]
subjectAltName = @alt
extendedKeyUsage = serverAuth
keyUsage = digitalSignature, keyEncipherment
[alt]
DNS.1 = $SVC
DNS.2 = $SVC.$NS
DNS.3 = $SVC.$NS.svc
DNS.4 = $SVC.$NS.svc.cluster.local
EOF

openssl genrsa -out "$DIR/tls.key" 2048
openssl req -new -key "$DIR/tls.key" -out "$DIR/tls.csr" -config "$DIR/server.cnf"
openssl x509 -req -in "$DIR/tls.csr" -CA "$DIR/ca.crt" -CAkey "$DIR/ca.key" \
  -CAcreateserial -days 365 -extensions v3_req -extfile "$DIR/server.cnf" -out "$DIR/tls.crt"

kubectl -n "$NS" create secret tls conversion-webhook-certs \
  --cert="$DIR/tls.crt" --key="$DIR/tls.key" --dry-run=client -o yaml | kubectl apply -f -

# GNU base64；macOS 用: CA_BUNDLE=$(base64 -i "$DIR/ca.crt" | tr -d '\n')
CA_BUNDLE=$(base64 -w0 < "$DIR/ca.crt")
kubectl patch crd "$CRD" --type=merge \
  -p "{\"spec\":{\"conversion\":{\"webhook\":{\"clientConfig\":{\"caBundle\":\"${CA_BUNDLE}\"}}}}}"

kubectl get crd "$CRD" -o jsonpath='{.spec.conversion.webhook.clientConfig.caBundle}' | head -c 24
echo "  <- caBundle 前 24 字符，非空即注入成功"
