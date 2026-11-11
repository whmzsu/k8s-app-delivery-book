kubectl -n order-demo-prod get deploy gateway -o jsonpath='{..image}{"\n"}'
kubectl -n order-demo-prod get deploy gateway \
  -o jsonpath='{.status.availableReplicas}{"\n"}'
kubectl -n order-demo-prod get svc gateway -o jsonpath='{.spec.selector.version}{"\n"}'
./hack/verify.sh
kubectl -n order-demo-prod rollout history deployment/gateway
