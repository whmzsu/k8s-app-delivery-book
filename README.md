# 一次变更的旅程：Kubernetes 应用部署与管理运维最佳实践

> 一本**决策书**，不是 K8s API 手册。面向已会 `kubectl` 的平台工程师 / SRE / 后端负责人，回答的是「什么场景选什么、为什么、踩过什么坑、怎么验证和回滚」。

本仓库既是书稿，也是全书唯一的配套示例仓库：**七篇 31 章 + 附录 A–I**，正文约 **35.2 万汉字**（含附录 38.1 万），**298 条分级引用**（L1 规范 / L2 权威著作 / L3 案例实证）。

## 下载成品

不想读 Markdown？[Releases](../../releases) 里提供三种排好版的形态，内容与仓库 Markdown 逐字一致、由同一份源装配：

| 形态 | 适合 | 文件 |
|---|---|---|
| PDF | 通读 / 打印 / 评审 | `journey-of-a-change-v1.1.0.pdf`，456 页，带页脚页码 |
| EPUB | 手机 / 电纸书 / 平板 | `journey-of-a-change-v1.1.0.epub`，可重排、带目录导航 |
| Word | 写批注 / 摘录 / 改编内训 | `journey-of-a-change-v1.1.0.docx` |

自己重新生成：`pip install -r hack/requirements.txt` 后跑 `python hack/build_dist.py --out dist/<版本>`（不需要 pandoc；PDF 走本机 Edge headless 打印，`--out` 可避开被阅读器占用的旧文件）。

## 快速开始

| 想做什么 | 去哪里 |
|---|---|
| 从头读 | [`全书目录.md`](全书目录.md) → [`chapters/ch01.md`](chapters/ch01.md) |
| 查某个决策 | [附录 G 选型决策树合集](appendices/附录G-选型决策树合集.md) |
| 查某个工具该不该上 | [附录 F 工具全景速查表](appendices/附录F-工具全景速查表.md) |
| 上线前逐条打勾 | [附录 B 上线前检查清单](appendices/附录B-上线前检查清单.md) |
| 出事了要止血 | [附录 C Runbook 与复盘模板](appendices/附录C-Runbook与复盘模板.md) |
| 跑通示例 | [`examples/order-demo/README.md`](examples/order-demo/README.md) |
| 查某条论断的出处 | [附录 I 参考文献](appendices/附录I-参考文献.md) |
| 确认版本边界 | [附录 A 版本兼容矩阵](appendices/附录A-版本兼容矩阵.md) |

## 目录结构

```
chapters/               31 章正文
appendices/             附录 A–I
examples/order-demo/    第 6 章最小完整闭环的可运行基线（唯一可直接跑的完整形态）
examples/by-chapter/    各章配置按章整理的可复制副本（与章节 tag 一一对应）
全书目录.md             阅读入口与完整目录
```

复现方式、章节 tag 全量表、示例验证到什么程度，见[附录 D](appendices/附录D-配套仓库与章节tag索引.md)。

## 三条设计红线

1. **不按工具名设章**：按交付链上的问题域设章，工具只作为候选实现；唯一例外是 Operator（第七篇），因为「要不要扩展 K8s API」本身是范式级决策。
2. **每章都要能落地**：七段模板固定为「问题与反模式 → 范式与决策树 → 工具选型 → 带版本落地配置 → 验证与回滚 → 上线检查清单 → 依据与延伸阅读」，每章必有完整配置、回滚命令、检查清单与 2–3 条安全项。
3. **背书分层，不用权威代替论证**：L1 规范官方 / L2 权威著作与共识 / L3 案例实证；「本书观点」显式标注并给论证与反例，不硬凑引用。正文只写 `[R-XX-N]` 角标，完整链接统一收在附录 I。

## 贯穿案例与配置契约

全书共用 `order-demo`（`gateway` 8080 / `api` 8081 / `worker` / `db` 5432），从第 1 章的事故现场逐章演进到第 31 章的事故重演。命名空间 `order-demo-{env}`、镜像 `registry.example.com/order-demo/<component>:git-<sha7>`、公共标签 `app.kubernetes.io/*`、探针路径这些字段在第 6 章冻结，后续章节一律引用、不再各写一套——这正是全书能逐章叠加而不互相冲突的原因。

每章一个 git tag，checkout 到任一章即可复现该章的可验证动作（见附录 D.3）。

## 示例验证到什么程度

示例配置不是「贴出来就算」，三件事在每次改动时自动做：

| 层次 | 做什么 | 覆盖范围 |
|---|---|---|
| 清单校验 | 按 `apiVersion` 分组后分别校验：内置资源走 server dry-run（K8s 1.32 / 1.33 / 1.34 / 1.37 四版本 schema），CRD 实例与 Helm 模板单独处理 | 全书 YAML |
| 真集群复核 | kind 集群 × 3 组（kind 与 node 镜像成对锁定：v0.27.0/1.32.2、v0.33.0/1.34.11、v0.33.0/1.37.0）：逐文档 dry-run、第 6 章基线真实部署、滚动零停机 / SHA 回滚 / readiness 摘流 / Pod 重建四项演练 | `examples/order-demo/` |
| 外链复核 | 引用字段与角标闭环、已登记 URL 的可达性 | 全书 298 条引用 |

**验证边界（重要）**：上述手段能证明「清单字段合法、镜像能构建、应用在 kind 里能起来且可回滚」；**不能证明**云厂商 LB / 存储 / IRSA 的真实行为、跨集群容灾、生产流量下的 HPA / KEDA 效果、长周期证书轮换，以及 Argo CD / Kyverno / Gateway API 控制器等需装 CRD 的组件在真实环境中的表现。这些必须按各章「验证与回滚」段在你自己的集群演练。**自动化校验通过 ≠ 生产可用。**

另一点容易踩坑：`examples/by-chapter/` 是逐章增量片段，后一章只给 patch，**按设计不可独立 `kustomize build`**；可独立运行与渲染的只有 `examples/order-demo/`。要用完整形态，请 checkout 对应章节 tag。

## 版本口径

正文只写主版本（`Helm 4.x`、`Kustomize 5.x`、`Argo CD 3.x`、`K8s 1.32+`），小版本、API 版本与破坏性变更集中在[附录 A](appendices/附录A-版本兼容矩阵.md)。官方文档链接按季度复核，失效链接切归档地址并在附录 I 标「已归档」。

## 许可与反馈

示例代码可直接用于你的项目；书中论断欢迎拿具体场景来反驳——「本书观点」标注处都写了适用前提与反例，如果前提不成立，结论就该改。
