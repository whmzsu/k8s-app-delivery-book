# Runbook：GatewayBudgetExhausted

症状：告警 `GatewayBudgetExhausted`（ticket）。28 天错误预算耗尽，
`release_freeze == 1`，非必要发布已冻结（第 20 章冻结规则生效）。
前置：kubectl 指向 order-demo-prod；SLO 契约见 `docs/slo-contract.md`。

## 一、定位命令（首步，来自告警 first_action）
```bash
# 核对预算消耗与冻结判定
./hack/budget-report.sh   # 退出码 2 表示已冻结
# 核对例外登记：是否有有效的 EXC- 编号
grep -E '^\| EXC-' docs/slo-contract.md
```

## 二、止血动作
- 冻结范围：功能发布、依赖升级、配置重构暂停。
- 豁免范围：回滚、安全补丁、止血变更——但须登记例外（见 `docs/slo-contract.md` 第四节）。
- 任何破例发布必须走「业务负责人 + 平台负责人」双签的 EXC 流程，禁止口头放行。

## 三、验证方法
- `slo:order_demo_gateway:release_freeze == 1` 成立；
- 冻结期内 observability/ 的每次变更都能对上一条 `EXC-` 或一次季度复审（`git log --since` 可查）；
- 解除条件：剩余预算 > 0 且连续 3 个快窗口无燃尽告警。

## 四、升级路径
- 业务要求破例 → 走 `docs/slo-contract.md` 双签流程，禁止改 `objective` 或删规则；
- 冻结误触发 → 回第 20 章预算判定（clamp_min、探针排除项）；
- 跨团队影响 → 转平台负责人与技术负责人三方会。
