promtool check rules observability/alert-rules.yaml
promtool test rules observability/alert-rules-test.yaml
amtool check-config observability/alertmanager.yaml
kubectl -n observability create secret generic alertmanager-order-demo \
  --from-file=alertmanager.yaml=observability/alertmanager.yaml \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n observability apply -f observability/alert-rules.yaml
./hack/alert-drill.sh
