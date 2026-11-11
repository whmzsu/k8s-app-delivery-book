# Runbook：双凭据共存轮换（order-demo-db-credentials）

适用：数据库口令轮换，且要求「零 5xx、镜像标签 git-<sha7> 全程不变」。
前置：凭据后端为 vault，集群内由 External Secrets Operator 同步为 Secret
`order-demo-db-credentials`；应用通过 `envFrom.secretRef` 读环境变量（见第 9 章）。
核心约束：凭据只走环境变量、镜像标签全程不变，任何一段出问题都能退回上一段。

## 一、三段式流程（每段结束都有准入验证）

**① 共存阶段**：vault 同时保留 `password` 与 `password_new`，ESO `refreshInterval: 1h`
把集群内 Secret 同步出三个键 `DB_USER` / `DB_PASSWORD` / `DB_PASSWORD_NEW`。
准入验证（必须看到三键才进 ②）：
```bash
kubectl -n order-demo-dev get secret order-demo-db-credentials -o json | jq -r '.data | keys[]'
```

**② 切流**：后端把 `api` 读取的键从 `DB_PASSWORD` 切到 `DB_PASSWORD_NEW`；
`kubectl -n order-demo-dev rollout restart deploy/api`。
准入验证（readiness 未挡流、无 5xx）：
```bash
kubectl -n order-demo-dev rollout status deploy/api --timeout=120s
./hack/rolling-5xx-test.sh   # 退出码须为 0
```

**③ 作废**：vault 删除 `password`，`password_new` 提升为 `password`；ESO 同步后
`kubectl -n order-demo-dev rollout restart deploy/api`。
准入验证（旧凭据读取记录归零、rollback 演练通过）：
```bash
kubectl -n order-demo-dev rollout status deploy/api --timeout=120s
./hack/rolling-5xx-test.sh
```

## 二、回退动作（任意一段都可退回上一段）
- ②→①：先在 vault 恢复 `password_new`，再 `kubectl -n order-demo-dev rollout restart deploy/api`，
  待 `rollout status` 通过、`rolling-5xx-test.sh` 退出码 0、确认旧凭据读取归零，才重试 ③。
- ESO 同步滞后：临时把 `refreshInterval` 改回 `1h` 并 apply，再强制同步：
  ```bash
  kubectl -n order-demo-dev annotate externalsecret order-demo-db-credentials \
    force-sync="$(date +%s)" --overwrite
  ```
  再次执行「① 准入验证」确认 `DB_PASSWORD_NEW` 出现，才允许进入 ②。
- 全程不改镜像标签：回退没有触发任何镜像重建（公理 9 / 第 9 章）。

## 三、演练通过标准（见第 9 章注入演练）
- 两次注入（vault 误删 `password_new`、ESO 同步滞后）都能在 runbook 内找到对应退回动作；
- 全程 `./hack/rolling-5xx-test.sh` 退出码 0（readiness 挡流，未对外报 5xx）；
- 镜像标签 `git-<sha7>` 前后一致；
- 每次注入从发现到恢复不超过 5 分钟（含验证命令执行）。
演练留痕随 runbook 归档，供第 23 章 Chaos Mesh 演练与第 31 章事故重演直接复用。

## 四、升级路径
- 轮换演练未通过 → 回第 9 章补齐共存窗口，禁止计划内轮换。
- 涉及 Secrets Store CSI Driver 双实现对照 → 回第 9 章 9.3.1。
- 凭据后端不可用 → 转第 9 章密钥方案选型与 vault 高可用运维。
