# 一次变更的旅程：Kubernetes 应用部署与管理运维最佳实践

> 一本**决策书**，不是 K8s API 手册。面向已会 `kubectl` 的平台工程师 / SRE / 后端负责人，回答的是「什么场景选什么、为什么、踩过什么坑、怎么验证和回滚」。

本仓库既是书稿，也是全书唯一的配套示例仓库。当前状态：**完整初稿 v1.0**（31 章 + 附录 A–I 全部成篇），约 **15.7 万汉字**、**298 条分级引用**（其中 272 条链接已联网核验）。

## 快速开始

| 想做什么 | 去哪里 |
|---|---|
| 从头读 | [`全书目录.md`](全书目录.md) → `chapters/ch01.md` |
| 查某个决策 | [`appendices/附录G-选型决策树合集.md`](appendices/附录G-选型决策树合集.md) |
| 查工具该不该上 | [`appendices/附录F-工具全景速查表.md`](appendices/附录F-工具全景速查表.md) |
| 上线前打勾 | [`appendices/附录B-上线前检查清单.md`](appendices/附录B-上线前检查清单.md) |
| 出事了 | [`appendices/附录C-Runbook与复盘模板.md`](appendices/附录C-Runbook与复盘模板.md) |
| 跑通示例 | [`examples/order-demo/README.md`](examples/order-demo/README.md) |
| 看设计依据 | [`书籍大纲-v3.md`](书籍大纲-v3.md) 与 `book/` |

## 目录结构

```
书籍大纲-v3.md          当前有效大纲（含 v3.1 逻辑线、v3.2 背书、v3.3 推进策略）
书籍大纲-v2.md          历史对照版
book/                   P0 冻结的全局资产：术语、概念梯度、案例契约、钩子、
                        检查清单母版、强耦合对、裁决记录、成稿规范、31 张章卡片
chapters/               31 章成稿
appendices/             附录 A–I
references/             已核验来源池 + 逐章引用登记（附录 I 由此生成）
examples/order-demo/    第 6 章最小完整闭环的可运行基线
examples/by-chapter/    28 章 §N.4 代码块按章物化的可复制形态（144 个文件）
hack/                   一致性、引用、版本矩阵校验脚本与章节代码块物化工具
全书目录.md             阅读入口与完整目录
```

## 三条设计红线

1. **不按工具名设章**：按交付链上的问题域设章，工具只作为候选实现；唯一例外是 Operator（第七篇），因为「要不要扩展 K8s API」本身是范式级决策。
2. **每章都要能落地**：七段模板固定为「问题与反模式 → 范式与决策树 → 工具选型 → 带版本落地配置 → 验证与回滚 → 上线检查清单 → 依据与延伸阅读」，每章必有完整配置、回滚命令、检查清单与 2–3 条安全项。
3. **背书分层，不用权威代替论证**：L1 规范官方 / L2 权威著作与共识 / L3 案例实证；「本书观点」显式标注并给论证与反例，不硬凑引用。正文只写 `[R-XX-N]` 角标，链接统一在 `references/`。

## 贯穿案例与配置契约

全书共用 `order-demo`（`gateway` 8080 / `api` 8081 / `worker` / `db` 5432），从第 1 章的事故现场逐章演进到第 31 章的事故重演。命名空间 `order-demo-{env}`、镜像 `registry.example.com/order-demo/<component>:git-<sha7>`、公共标签 `app.kubernetes.io/*`、探针路径等字段冻结在 `book/case-evolution.md`——**改字段先改资产表，再按强耦合对回写章节**。每章一个 git tag，索引见附录 D。

## 校验

```bash
./hack/check-consistency.sh                 # 八项横扫 + tag 一致性 + 附录 I 新鲜度 + 脚本语法
./hack/check-references.sh                  # 引用字段 / 角标闭环 / 待核验清单
./hack/check-references.sh --links          # 追加链接可达性核验
./hack/check-version-matrix.sh              # P5：kind 三版本矩阵（需 kind + kubectl）
python hack/materialize.py --clean          # 重新物化各章代码块到 examples/by-chapter/
python hack/book_tools.py appendix > appendices/附录I-参考文献.md   # 重新生成附录 I
```

## 版本与复核

正文只写主版本（`Helm 3.x`、`Kustomize 5.x`、`Argo CD 2.x`），小版本、API 版本与破坏性变更集中在附录 A。官方文档链接按季度复核；失效链接切归档地址并在附录 I 标「已归档」。

## 状态与后续

| 轮次 | 状态 |
|---|---|
| P0 全局资产冻结 | 完成 |
| P1 31 张章卡片 | 完成并放行 |
| P2 样板章（第 6 章） | 完成 |
| P3 按篇成稿 31 章 | 完成（完整初稿 v1.0） |
| P4 全书统稿、附录生成 | 完成；第 1 章仍建议终稿前最后润色一次以对齐 H1–H8 |
| P5 kind 多版本矩阵技术复核 | **待在有 kind/kubectl 的环境执行**，脚本已就绪 |

终稿目标约 30–35 万字；每章末尾的「终稿扩写清单」列出了具体扩写点。当前 v1.0 的验收标准是「31 章 + 附录全部成篇、七段齐全、配置与回滚命令可执行、无空章无占位」，已满足。
