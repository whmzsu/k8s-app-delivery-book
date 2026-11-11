# 策略例外登记（每次降级必须追加一行，变更进 Git）

> 本文件是「策略从 Enforce 临时降级为 Audit / warn」时的例外登记簿（第 25 章）。
> 每次全量降级都 `git commit` 进本文件（公理 5，见第 3 章），不允许出现「永久降级」。
> 字段固定为：登记日期 / 原因 / 影响 SHA / 降级策略 / 申请人 / 到期日期 / 恢复验证（CL-25-04）。
> 追加命令（见第 25 章 25.2.4）：
> ```bash
> # 按 docs/policy-exception.md 追加一行，注明原因、SHA、申请人、到期日期
> git add docs/policy-exception.md policies/order-demo-require-nonroot-audit.yaml
> git commit -m "chore(policy): audit-mode exception with expiry"
> ```

| 登记日期 | 原因 | 影响 SHA | 降级策略 | 申请人 | 到期日期 | 恢复验证 |
|---|---|---|---|---|---|---|
| 2026-11-11 | 存量全量 enforce 导致批量 Pending（示例，过期即删） | git-0000000 | require-nonroot: Enforce→Audit | <当班 SRE> | 2026-11-14 | `kyverno test policies/tests` 通过 + 恢复 Enforce 后 `fail.yaml` dry-run 仍被拒 |
