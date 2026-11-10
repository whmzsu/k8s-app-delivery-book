chmod +x hack/ch07-apply.sh
./hack/ch07-apply.sh
kubectl -n order-demo-dev get deploy,sts,pod -o wide
kubectl -n order-demo-dev get svc -o wide
kubectl -n order-demo-dev get pvc
kubectl -n order-demo-dev get pod db-0 -o jsonpath='{.metadata.name}{"\t"}{.spec.hostname}{"\n"}'
kubectl -n order-demo-dev rollout history deployment/worker
./hack/verify.sh
