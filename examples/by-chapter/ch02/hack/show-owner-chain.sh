chmod +x hack/show-owner-chain.sh
./hack/show-owner-chain.sh

# 演示 A：改「运行对象」——删 Pod，观察控制循环收敛
kubectl -n order-demo-dev delete pod -l app.kubernetes.io/component=gateway --wait=false
sleep 3
kubectl -n order-demo-dev get pods -l app.kubernetes.io/component=gateway
./hack/show-owner-chain.sh

# 演示 B：改「声明对象」——scale 生效，再由 apply 声明覆盖回去
kubectl -n order-demo-dev scale deploy/gateway --replicas=5
kubectl -n order-demo-dev get deploy gateway -o jsonpath='{.spec.replicas}{"\n"}'
kubectl apply -f deploy/base/deployment.yaml
kubectl -n order-demo-dev get deploy gateway -o jsonpath='{.spec.replicas}{"\n"}'
