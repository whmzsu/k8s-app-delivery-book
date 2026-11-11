# 30 条反模式归档（order-demo）

> 本文件全文 = 第 31 章 31.4 主表 + 31.4.1 症状/定位命令表 + 31.4.2 止血优先级表。
> 编号与「对应章」、第 1 章钩子清单逐字对齐；附录 B / 附录 I 由本表生成，不在别处维护第二份。

## 一、反模式主表（所属环节）

| 编号 | 反模式 | 所属环节 | 后果 | 对应章 |
|---|---|---|---|---|
| AP-01 | `latest` 标签覆盖产物 | 定义 | 线上跑的不是以为的、回滚无目标 | 3、6、12 |
| AP-02 | 环境参数硬编码进镜像 | 定义 | dev / prod 产物不一致，改参数要重建 | 3、6、9 |
| AP-03 | 只写 `Deployment` 就宣布完成 | 定义 | 无稳定入口、配置无法验证 | 6 |
| AP-04 | 裸 `Pod` 用于生产 | 定义 | 节点故障后服务消失 | 7 |
| AP-05 | 无 `readinessProbe` / 探针语义判错 | 定义 | 发布停在永远不健康的版本 | 8 |
| AP-06 | liveness 当心跳、误杀引发重启级联 | 响应 | `CrashLoopBackOff`，现场无人定位 | 8、23 |
| AP-07 | `ConfigMap` 原地改、无版本 | 定义 | 改动不可追溯、新旧 Pod 行为不一 | 9 |
| AP-08 | 密钥塞进 Chart / Git / 镜像 | 定义 | 凭据泄露、轮换要重建镜像 | 9、14、24 |
| AP-09 | values 爆炸、只 review 模板不 review 渲染产物 | 打包 | PR 里看不到真正会被 apply 的字节 | 10、14 |
| AP-10 | 提交前无离线校验 / 版本矩阵 | 校验 | 错误字段进集群才被发现 | 11 |
| AP-11 | 每个环境各构建一次镜像 | 打包 | 违反 build once，晋升失效 | 3、12 |
| AP-12 | 把 `kubectl edit` 当改期望状态 | 地基 | 手改被控制循环改回、反复无效 | 2、14 |
| AP-13 | 分不清「命名空间隔离」与硬隔离 | 地基 | 凭据 / 故障域没隔离 | 4、30 |
| AP-14 | Operator 万能化：一次性脚本包装成控制器 | 演进轴 | 多一套控制器与 CRD 长期负债 | 5、27 |
| AP-15 | Argo CD 3.x 与手工变更并存 | 晋升 | 两份真相，复盘指认真相源 | 14、26 |
| AP-16 | 没有回滚方案就发布 | 发布 | 想退退不回去 | 13 |
| AP-17 | 容量账没算（`maxSurge` / 节点余量） | 发布 | 高峰 Pod 不足、更新卡住 | 13、17 |
| AP-18 | 发布时执行破坏性 DDL | 发布 | 回滚后旧版全量报错 | 16 |
| AP-19 | 只做备份从不恢复 | 发布 | 真出事时备份不可用 | 16 |
| AP-20 | schema 不兼容还强行回滚 | 发布 | 数据不一致、5xx 全量 | 13、16 |
| AP-21 | requests / limits 缺失或拍脑袋 | 运行 | OOMKilled、调度抖动 | 17 |
| AP-22 | HPA 无稳定窗口、反复抖动 | 运行 | 反复扩缩，成本与稳定性双损 | 18 |
| AP-23 | `NetworkPolicy` 未默认拒绝 | 运行 | 未授权 Pod 可访问 `db` | 19、25 |
| AP-24 | 用 CPU 使用率当 SLI | 观测 | 指标业务无感、告警失真 | 20 |
| AP-25 | SLO 只写百分比，不写窗口与冻结规则 | 观测 | 错误预算形同虚设 | 20 |
| AP-26 | 告警阈值拍脑袋、无错误预算依据 | 观测 | 告警风暴或漏报 | 20、22 |
| AP-27 | 告警响了没有 runbook | 响应 | 值班不知道做什么 | 22、23 |
| AP-28 | 混沌演练 / runbook 从没跑过 | 响应 | 真故障时按文档猜 | 23 |
| AP-29 | 未签名镜像进生产 | 横切 A | 供应链不可追溯 | 24 |
| AP-30 | 特权容器 / root 运行 / SA 过权 | 横切 A | 逃逸与越权 | 6、25、26 |

读法：先按「所属环节」找到自己最常出问题的一环，再看「对应章」。AP-14、AP-15、AP-29、AP-30 是横切与演进轴的补充。

## 二、可观察症状与定位命令（31.4.1）

| 编号 | 反模式 | 可观察症状 | 定位命令 | 对应章 |
|---|---|---|---|---|
| AP-01 | `latest` 标签覆盖产物 | Pod 实际镜像与发版记录不符；仓库同标签推送历史被覆盖 | `kubectl -n order-demo-prod get deploy gateway -o jsonpath='{.spec.template.spec.containers[0].image}'`，与 `git rev-parse --short=7 HEAD` 对照 | 3、6、12 |
| AP-02 | 环境参数硬编码进镜像 | 同一镜像 dev 正常、prod 报错；改参数必须重发版 | `kubectl -n order-demo-dev exec deploy/api -- env` 与 `kubectl -n order-demo-prod exec deploy/api -- env` 比对差异 | 3、6、9 |
| AP-03 | 只写 `Deployment` 就宣布完成 | 调用方直连 Pod IP；无稳定服务入口 | `kubectl -n order-demo-prod get svc,endpoints`（缺 `gateway` 或 Endpoints 为空即中招） | 6 |
| AP-04 | 裸 `Pod` 用于生产 | 节点故障后服务消失，且 `get deploy` 查无此负载 | `kubectl -n order-demo-prod get pod -o jsonpath='{.items[*].metadata.ownerReferences[*].kind}'`（出现空值即裸 Pod） | 7 |
| AP-05 | 无 `readinessProbe` / 探针语义判错 | rollout 卡住；新 Pod `Running` 但不 `Ready` 或提前接流后 5xx | `kubectl -n order-demo-prod rollout status deployment/gateway --timeout=60s`，再 `kubectl -n order-demo-prod describe pod -l app.kubernetes.io/component=gateway` 看 Readiness 事件 | 8 |
| AP-06 | liveness 当心跳、误杀级联 | 重启计数周期性上涨；`CrashLoopBackOff` | `kubectl -n order-demo-prod get pods --sort-by='.status.containerStatuses[0].restartCount'`；对重启最多的 Pod 追加 `kubectl -n order-demo-prod logs <pod> --previous` 看被杀前日志 | 8、23 |
| AP-07 | `ConfigMap` 原地改、无版本 | 新旧 Pod 读到不同配置值；改动无审计记录 | `kubectl -n order-demo-prod get cm order-demo-config-v2 -o yaml` 加 `kubectl -n order-demo-prod rollout history deployment/gateway` | 9 |
| AP-08 | 密钥塞进 Chart / Git / 镜像 | 仓库能 grep 出凭据；镜像分层含敏感串 | `git grep -n 'PASSWORD' -- .`（应零命中；有命中即中招） | 9、14、24 |
| AP-09 | values 爆炸、不 review 渲染产物 | PR 只见模板 diff；真正被 apply 的字节无人审过 | `helm template order-demo charts/order-demo > /tmp/rendered.yaml && kubectl diff -f /tmp/rendered.yaml` | 10、14 |
| AP-10 | 提交前无离线校验 / 版本矩阵 | CI 绿灯但 apply 时才报 schema 错误 | `kubeconform -strict deploy/replay/ && conftest test deploy/replay/` | 11 |
| AP-11 | 每个环境各构建一次镜像 | 三环境镜像 SHA 不一致，晋升不可追溯 | 分别执行 `kubectl -n order-demo-dev get deploy api -o jsonpath='{..image}'` 与 staging / prod 同命令比对 | 3、12 |
| AP-12 | 把 `kubectl edit` 当改期望状态 | 手改字段几秒后被改回，反复无效 | `kubectl -n order-demo-prod get deploy gateway -w`（观察字段/副本数回弹） | 2、14 |
| AP-13 | 分不清命名空间隔离与硬隔离 | 故障与凭据跨环境蔓延；误以为命名空间即隔离边界 | `kubectl get ns --show-labels` 加 `kubectl -n order-demo-prod get secret`（凭据是否各环境独立） | 4、30 |
| AP-14 | Operator 万能化 | 自定义资源长期不收敛，控制器无人认领 | `kubectl get crd`，再对可疑 CRD `kubectl describe crd <名称>` 看 `Established` 条件与维护者 | 5、27 |
| AP-15 | GitOps 与手工变更并存 | `app diff` 长期非空；审计有手工写记录 | `argocd app diff order-demo-prod`（应为空；非空即漂移） | 14、26 |
| AP-16 | 没有回滚方案就发布 | 出事时 `rollout undo` 目标不明，无人记得上一版 | `kubectl -n order-demo-prod rollout history deployment/gateway`（对照回滚演练记录） | 13 |
| AP-17 | 容量账没算 | 滚动更新卡在 surge；Pod `Pending` 报资源不足 | `kubectl -n order-demo-prod get events --field-selector type=Warning`（找 `FailedScheduling`） | 13、17 |
| AP-18 | 发布时执行破坏性 DDL | 回滚后旧版本全量 SQL 报错 | `kubectl -n order-demo-prod logs deploy/api --since=10m`（找 SQL 列不存在类报错） | 16 |
| AP-19 | 只做备份从不恢复 | 备份 CronJob 一直成功，但从没做过恢复演练 | `kubectl -n order-demo-prod get cronjob` 加最近一次「恢复到新集群」演练记录（无记录即中招） | 16 |
| AP-20 | schema 不兼容还强行回滚 | 回滚镜像后 5xx 全量，新旧字段并存 | `kubectl -n order-demo-prod logs deploy/api --since=5m` 加 `kubectl -n order-demo-prod get deploy api -o jsonpath='{..image}'` | 13、16 |
| AP-21 | requests / limits 缺失或拍脑袋 | `OOMKilled` 频发；节点调度抖动 | `kubectl -n order-demo-prod top pod` 加 `kubectl -n order-demo-prod get pod -o jsonpath='{.items[*].status.qosClass}'`（非 `Guaranteed`/`Burstable` 基线需复盘） | 17 |
| AP-22 | HPA 无稳定窗口、反复抖动 | 副本数锯齿；HPA 事件频繁扩缩 | `kubectl -n order-demo-prod describe hpa api`（看 Events 与稳定窗口配置） | 18 |
| AP-23 | `NetworkPolicy` 未默认拒绝 | 任一 Pod 可达 `db:5432`；策略清单为空 | `kubectl -n order-demo-prod get networkpolicy`；再 `kubectl -n order-demo-prod run netprobe --rm -it --image=busybox:1.36 --restart=Never -- nc -zv db 5432` 验证可达性 | 19、25 |
| AP-24 | 用 CPU 使用率当 SLI | CPU 告警常绿，用户仍在报障 | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` | 20 |
| AP-25 | SLO 只写百分比不写窗口与冻结规则 | SLO 页只有目标数字；预算耗尽无人冻结发布 | 按第 20 章窗口查询错误率并与目标/预算比对；核对冻结规则是否成文 | 20 |
| AP-26 | 告警阈值拍脑袋、无预算依据 | 告警风暴或关键故障漏报 | `kubectl -n monitoring get prometheusrule -o yaml`，逐条问「阈值来自哪条 SLO」 | 20、22 |
| AP-27 | 告警响了没有 runbook | 告警通知里没有 runbook 链接，值班靠问人 | 检查 Alertmanager 路由与通知模板的 `annotations` 是否含 `runbook_url` | 22、23 |
| AP-28 | 混沌演练 / runbook 从没跑过 | runbook 落灰、演练记录为空，真故障按文档猜 | `./hack/replay-incident.sh` 加演练记录表（无记录即中招） | 23 |
| AP-29 | 未签名镜像进生产 | 未签名镜像被放行；供应链不可追溯 | `cosign verify --key cosign.pub registry.example.com/order-demo/api:git-1a2b3c4`（验签失败即中招） | 24 |
| AP-30 | 特权容器 / root / SA 过权 | 容器以 root 运行；SA token 全量挂载 | `kubectl -n order-demo-prod get pod -o jsonpath='{.items[*].spec.containers[*].securityContext}'` 加 `kubectl -n order-demo-prod get pod -o jsonpath='{.items[*].spec.automountServiceAccountToken}'` | 6、25、26 |

## 三、止血优先级与改错代价（31.4.2）

| 档位 | 反模式 | 共同特征 | 可后置条件 |
|---|---|---|---|
| 立即止血 | AP-01、05、06、16、20、30 | 直接制造或放大事故，或让回滚失效——不修，同类事故必然复发且更难退 | 无；任何情况下都不后置 |
| 尽快（两周～一个月） | AP-02、07、08、11、12、15、17、18、19、21、23、27、28、29 | 单点修复即消除一类隐患，彼此不依赖，可并行排期 | 仅当对应环节从未复现、且已有护栏兜底时，可延后一个季度 |
| 可后置（季度级） | AP-03、04、09、10、13、14、22、24、25、26 | 结构性改进，依赖前两档落地 | 写进季度复评；出现一次真实症状即升级为「尽快」 |

完成判据一律取 31.4.1 的定位命令输出翻转：命令从「证实中招」变成「证实排除」，才算改完。
