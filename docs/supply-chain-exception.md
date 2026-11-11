# 供应链验签例外登记（写入 Git，带到期时间）

> 本文件是「出仓验签从 Enforce 临时降级为 Audit」时的例外登记簿。
> 每次应急降级都 `git commit` 进本文件（公理 5，见第 3 章），不允许出现「永久 Audit」。
> 每行一条记录，字段固定为 `date` / `reason` / `sha` / `expires` 四项（CL-24-04 要求）。
> 追加命令（见第 24 章 24.2.3）：
> ```bash
> printf '%s\n' "date=$(date -u +%F) reason=emergency-release sha=${SHA7} expires=$(date -u -d '+3 days' +%F)" \
>   >> docs/supply-chain-exception.md
> ```

| date | reason | sha | expires |
|---|---|---|---|
| 2026-11-11 | emergency-release（示例，过期即删） | git-0000000 | 2026-11-14 |
