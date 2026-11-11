kustomize build deploy/overlays/dev | grep -c 'kind: NetworkPolicy'
# 期望 0：dev 未挂载
kustomize build deploy/overlays/prod | grep -c 'kind: NetworkPolicy'
# 当前期望 0（未挂载）；第 19 章落地后此命令期望 ≥1，届时纳入该章检查清单
