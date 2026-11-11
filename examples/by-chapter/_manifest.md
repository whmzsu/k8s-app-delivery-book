# 章节配置物化清单

> 由 `hack/materialize.py` 从 `chapters/chNN.md` 的路径标注与相邻代码块生成；
> 与附录 D 的章节 tag 一一对应。章内代码块是权威副本，本目录是其可复制形态。

| 章 | 物化路径 | 行数 |
|---|---|---|
| 01 | `examples/by-chapter/ch01/deploy/incident/order-demo-incident.yaml` | 80 |
| 01 | `examples/by-chapter/ch01/hack/reproduce-incident.sh` | 33 |
| 02 | `examples/by-chapter/ch02/deploy/base/deployment.yaml` | 49 |
| 02 | `examples/by-chapter/ch02/deploy/base/namespace.yaml` | 6 |
| 02 | `examples/by-chapter/ch02/deploy/base/service.yaml` | 18 |
| 02 | `examples/by-chapter/ch02/hack/show-owner-chain.sh` | 19 |
| 03 | `examples/by-chapter/ch03/deploy/base/deployment.yaml` | 49 |
| 03 | `examples/by-chapter/ch03/observability/slo-card-minimal.yaml` | 16 |
| 04 | `examples/by-chapter/ch04/deploy/base/deployment.yaml` | 36 |
| 04 | `examples/by-chapter/ch04/deploy/base/kustomization.yaml` | 5 |
| 04 | `examples/by-chapter/ch04/deploy/base/service.yaml` | 17 |
| 04 | `examples/by-chapter/ch04/deploy/overlays/dev/kustomization.yaml` | 19 |
| 04 | `examples/by-chapter/ch04/deploy/overlays/dev/namespace.yaml` | 6 |
| 04 | `examples/by-chapter/ch04/deploy/overlays/prod/kustomization.yaml` | 19 |
| 04 | `examples/by-chapter/ch04/deploy/overlays/prod/namespace.yaml` | 6 |
| 04 | `examples/by-chapter/ch04/deploy/overlays/staging/kustomization.yaml` | 19 |
| 04 | `examples/by-chapter/ch04/deploy/overlays/staging/namespace.yaml` | 6 |
| 04 | `examples/by-chapter/ch04/gitops/bootstrap/backend.tf` | 8 |
| 04 | `examples/by-chapter/ch04/gitops/bootstrap/bootstrap-namespace.yaml` | 7 |
| 04 | `examples/by-chapter/ch04/gitops/bootstrap/kustomize/apps/applicationset.yaml` | 32 |
| 04 | `examples/by-chapter/ch04/gitops/bootstrap/main.tf` | 17 |
| 04 | `examples/by-chapter/ch04/gitops/bootstrap/providers.tf` | 18 |
| 04 | `examples/by-chapter/ch04/hack/render-diff.sh` | 19 |
| 06 | `examples/by-chapter/ch06/cmd/gateway/main.go` | 29 |
| 06 | `examples/by-chapter/ch06/deploy/base/configmap.yaml` | 9 |
| 06 | `examples/by-chapter/ch06/deploy/base/deployment.yaml` | 54 |
| 06 | `examples/by-chapter/ch06/deploy/base/namespace.yaml` | 6 |
| 06 | `examples/by-chapter/ch06/deploy/base/service.yaml` | 18 |
| 06 | `examples/by-chapter/ch06/docker/Dockerfile` | 16 |
| 06 | `examples/by-chapter/ch06/go.mod` | 3 |
| 06 | `examples/by-chapter/ch06/hack/kind-up.sh` | 24 |
| 06 | `examples/by-chapter/ch06/hack/verify.sh` | 41 |
| 07 | `examples/by-chapter/ch07/deploy/base/deployment-api.yaml` | 71 |
| 07 | `examples/by-chapter/ch07/deploy/base/deployment-worker.yaml` | 45 |
| 07 | `examples/by-chapter/ch07/deploy/base/service-api.yaml` | 18 |
| 07 | `examples/by-chapter/ch07/deploy/base/service-db-headless.yaml` | 18 |
| 07 | `examples/by-chapter/ch07/deploy/base/statefulset-db.yaml` | 61 |
| 07 | `examples/by-chapter/ch07/hack/ch07-apply.sh` | 20 |
| 08 | `examples/by-chapter/ch08/deploy/base/deployment-api.yaml` | 100 |
| 08 | `examples/by-chapter/ch08/deploy/base/deployment.yaml` | 79 |
| 08 | `examples/by-chapter/ch08/deploy/base/pdb.yaml` | 14 |
| 08 | `examples/by-chapter/ch08/hack/rolling-5xx-test.sh` | 36 |
| 09 | `examples/by-chapter/ch09/deploy/base/configmap.yaml` | 10 |
| 09 | `examples/by-chapter/ch09/deploy/base/deployment-api.yaml` | 102 |
| 09 | `examples/by-chapter/ch09/deploy/base/externalsecret.yaml` | 25 |
| 09 | `examples/by-chapter/ch09/deploy/base/secretstore.yaml` | 19 |
| 09 | `examples/by-chapter/ch09/hack/ch09-verify.sh` | 22 |
| 10 | `examples/by-chapter/ch10/deploy/base/kustomization.yaml` | 15 |
| 10 | `examples/by-chapter/ch10/deploy/charts/_order-demo-common/Chart.yaml` | 5 |
| 10 | `examples/by-chapter/ch10/deploy/charts/_order-demo-common/templates/_helpers.tpl` | 9 |
| 10 | `examples/by-chapter/ch10/deploy/charts/order-demo/Chart.yaml` | 6 |
| 10 | `examples/by-chapter/ch10/deploy/charts/order-demo/templates/configmap.yaml` | 11 |
| 10 | `examples/by-chapter/ch10/deploy/charts/order-demo/templates/deployment.yaml` | 77 |
| 10 | `examples/by-chapter/ch10/deploy/charts/order-demo/values-dev.yaml` | 2 |
| 10 | `examples/by-chapter/ch10/deploy/charts/order-demo/values-prod.yaml` | 2 |
| 10 | `examples/by-chapter/ch10/deploy/charts/order-demo/values-staging.yaml` | 2 |
| 10 | `examples/by-chapter/ch10/deploy/charts/order-demo/values.yaml` | 7 |
| 10 | `examples/by-chapter/ch10/deploy/components/defaults-deny/kustomization.yaml` | 4 |
| 10 | `examples/by-chapter/ch10/deploy/components/defaults-deny/networkpolicy-default-deny.yaml` | 12 |
| 10 | `examples/by-chapter/ch10/deploy/overlays/dev/kustomization.yaml` | 10 |
| 10 | `examples/by-chapter/ch10/deploy/overlays/prod/kustomization.yaml` | 18 |
| 10 | `examples/by-chapter/ch10/deploy/overlays/staging/kustomization.yaml` | 18 |
| 10 | `examples/by-chapter/ch10/hack/render-diff.sh` | 21 |
| 11 | `examples/by-chapter/ch11/hack/dev-loop.sh` | 15 |
| 11 | `examples/by-chapter/ch11/hack/dev-loop.yaml` | 11 |
| 11 | `examples/by-chapter/ch11/hack/kind-matrix.yaml` | 9 |
| 11 | `examples/by-chapter/ch11/hack/validate.sh` | 43 |
| 12 | `examples/by-chapter/ch12/hack/pin-actions.sh` | 37 |
| 12 | `examples/by-chapter/ch12/hack/promote-artifact.sh` | 60 |
| 13 | `examples/by-chapter/ch13/deploy/bluegreen/gateway-blue.yaml` | 53 |
| 13 | `examples/by-chapter/ch13/deploy/bluegreen/gateway-green.yaml` | 53 |
| 13 | `examples/by-chapter/ch13/deploy/bluegreen/service.yaml` | 19 |
| 13 | `examples/by-chapter/ch13/deploy/bluegreen/switch.sh` | 28 |
| 13 | `examples/by-chapter/ch13/deploy/overlays/prod/pdb.yaml` | 13 |
| 13 | `examples/by-chapter/ch13/deploy/overlays/prod/rolling-strategy.yaml` | 46 |
| 13 | `examples/by-chapter/ch13/hack/rollback-drill.sh` | 47 |
| 14 | `examples/by-chapter/ch14/deploy/overlays/prod/kustomization.yaml` | 15 |
| 14 | `examples/by-chapter/ch14/gitops/applicationset.yaml` | 56 |
| 14 | `examples/by-chapter/ch14/gitops/appproject.yaml` | 29 |
| 14 | `examples/by-chapter/ch14/gitops/rendered/prod/all.yaml` | 113 |
| 14 | `examples/by-chapter/ch14/gitops/secrets/externalsecret.yaml` | 43 |
| 14 | `examples/by-chapter/ch14/gitops/secrets/sops/.sops.yaml` | 6 |
| 14 | `examples/by-chapter/ch14/hack/drift-check.sh` | 29 |
| 14 | `examples/by-chapter/ch14/hack/render.sh` | 28 |
| 15 | `examples/by-chapter/ch15/deploy/rollouts/analysis-template.yaml` | 40 |
| 15 | `examples/by-chapter/ch15/deploy/rollouts/rollout-canary.yaml` | 86 |
| 15 | `examples/by-chapter/ch15/deploy/rollouts/rollout-replica-canary.yaml` | 79 |
| 15 | `examples/by-chapter/ch15/deploy/rollouts/traffic.yaml` | 83 |
| 15 | `examples/by-chapter/ch15/hack/inject-error-rate.sh` | 29 |
| 16 | `examples/by-chapter/ch16/deploy/base/statefulset-db.yaml` | 118 |
| 16 | `examples/by-chapter/ch16/hack/dual-write-check.sh` | 15 |
| 16 | `examples/by-chapter/ch16/hack/restore-drill.sh` | 43 |
| 16 | `examples/by-chapter/ch16/hack/uninstall-check.sh` | 20 |
| 17 | `examples/by-chapter/ch17/deploy/base/deployment-api.yaml` | 77 |
| 17 | `examples/by-chapter/ch17/deploy/base/limitrange.yaml` | 26 |
| 17 | `examples/by-chapter/ch17/deploy/base/priorityclass.yaml` | 21 |
| 17 | `examples/by-chapter/ch17/deploy/base/resourcequota.yaml` | 16 |
| 17 | `examples/by-chapter/ch17/hack/cpu-limit-bench.sh` | 42 |
| 17 | `examples/by-chapter/ch17/hack/oom-drill.sh` | 53 |
| 18 | `examples/by-chapter/ch18/deploy/base/deployment-api.yaml` | 92 |
| 18 | `examples/by-chapter/ch18/deploy/base/hpa.yaml` | 41 |
| 18 | `examples/by-chapter/ch18/deploy/base/scaledobject.yaml` | 44 |
| 18 | `examples/by-chapter/ch18/hack/cost-report.sh` | 18 |
| 18 | `examples/by-chapter/ch18/hack/kind-multi-az.sh` | 30 |
| 18 | `examples/by-chapter/ch18/hack/load-test.sh` | 56 |
| 18 | `examples/by-chapter/ch18/observability/cost-attribution.yaml` | 18 |
| 19 | `examples/by-chapter/ch19/deploy/net/backendtrafficpolicy.yaml` | 28 |
| 19 | `examples/by-chapter/ch19/deploy/net/certificate.yaml` | 28 |
| 19 | `examples/by-chapter/ch19/deploy/net/gateway.yaml` | 30 |
| 19 | `examples/by-chapter/ch19/deploy/net/httproute.yaml` | 28 |
| 19 | `examples/by-chapter/ch19/deploy/net/networkpolicy-default-deny.yaml` | 189 |
| 19 | `examples/by-chapter/ch19/hack/net-policy-test.sh` | 18 |
| 19 | `examples/by-chapter/ch19/hack/net-verify.sh` | 35 |
| 20 | `examples/by-chapter/ch20/hack/budget-report.sh` | 28 |
| 20 | `examples/by-chapter/ch20/observability/sli-recording-rules.yaml` | 80 |
| 20 | `examples/by-chapter/ch20/observability/sli-rules-test.yaml` | 35 |
| 20 | `examples/by-chapter/ch20/observability/slo.yaml` | 43 |
| 21 | `examples/by-chapter/ch21/hack/verify-signal-chain.sh` | 41 |
| 21 | `examples/by-chapter/ch21/observability/loki-tempo.yaml` | 192 |
| 21 | `examples/by-chapter/ch21/observability/otel-collector.yaml` | 231 |
| 21 | `examples/by-chapter/ch21/observability/prometheus.yaml` | 103 |
| 22 | `examples/by-chapter/ch22/hack/alert-drill.sh` | 35 |
| 22 | `examples/by-chapter/ch22/observability/alert-rules-test.yaml` | 27 |
| 22 | `examples/by-chapter/ch22/observability/alert-rules.yaml` | 91 |
| 22 | `examples/by-chapter/ch22/observability/alertmanager.yaml` | 51 |
| 23 | `examples/by-chapter/ch23/hack/chaos-drill.sh` | 20 |
| 23 | `examples/by-chapter/ch23/hack/chaos-report.sh` | 39 |
| 23 | `examples/by-chapter/ch23/hack/rollback-drill.sh` | 17 |
| 24 | `examples/by-chapter/ch24/hack/harbor-retention.json` | 38 |
| 24 | `examples/by-chapter/ch24/hack/verify-supply-chain.sh` | 103 |
| 26 | `examples/by-chapter/ch26/deploy/base/deployment.yaml` | 29 |
| 26 | `examples/by-chapter/ch26/deploy/base/serviceaccount.yaml` | 29 |
| 26 | `examples/by-chapter/ch26/hack/kind-audit.yaml` | 18 |
| 28 | `examples/by-chapter/ch28/hack/crd-rotation-drill.sh` | 81 |
| 28 | `examples/by-chapter/ch28/hack/gen-webhook-certs.sh` | 46 |
| 28 | `examples/by-chapter/ch28/observability/operator-alerts.yaml` | 43 |
| 29 | `examples/by-chapter/ch29/hack/operator-uninstall-drill.sh` | 40 |
| 29 | `examples/by-chapter/ch29/observability/operator-slo.yaml` | 43 |
| 30 | `examples/by-chapter/ch30/gitops/applicationset-multicluster.yaml` | 61 |
| 30 | `examples/by-chapter/ch30/hack/multicluster-verify.sh` | 38 |
| 31 | `examples/by-chapter/ch31/deploy/replay/order-demo-replay.yaml` | 129 |
| 31 | `examples/by-chapter/ch31/hack/replay-incident.sh` | 80 |

## 同路径多块裁决（2）

> 同一路径在一章内出现多次时，按「完整度 → 行数 → 位置」选权威副本；
> 被弃的多为回滚/处置片段，不当可复制文件。

- ch06 `hack/verify.sh`：选 L561（41 行，完整度 2），弃 L376（20 行，完整度 2）
- ch10 `deploy/charts/order-demo/Chart.yaml`：保留 L384（6 行，完整度 2），弃 L632（4 行，完整度 2）

## 跳过（13）

- ch03 `hack/verify.sh`：无 shebang，判定为命令行片段，不物化
- ch04 `deploy/overlays/<env>/kustomization.yaml`：占位路径（含 <>/模板占位），不物化
- ch04 `gitops/bootstrap/env/cluster-a.tfvars`：相邻代码块语言与文件类型不符：bash
- ch07 `hack/kind-up.sh`：相邻代码块语言与文件类型不符：yaml
- ch12 `hack/verify.sh`：无 shebang，判定为命令行片段，不物化
- ch14 `gitops/envs/<env>/config.yaml`：占位路径（含 <>/模板占位），不物化
- ch14 `gitops/rendered/<env>/all.yaml`：占位路径（含 <>/模板占位），不物化
- ch14 `gitops/rendered/<env>/all.yaml`：占位路径（含 <>/模板占位），不物化
- ch17 `hack/verify.sh`：无 shebang，判定为命令行片段，不物化
- ch21 `observability/metric-naming.md`：相邻代码块语言与文件类型不符：markdown
- ch23 `hack/verify.sh`：无 shebang，判定为命令行片段，不物化
- ch25 `deploy/base/deployment.yaml`：相邻代码块语言与文件类型不符：bash
- ch28 `go.mod`：相邻代码块语言与文件类型不符：diff
