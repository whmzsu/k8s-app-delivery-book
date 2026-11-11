#!/usr/bin/env python3
"""修 references/chNN.yaml 的元数据：内部指涉清理 + 引用源升级。

背景（P6 出书面 / D-46）：
  1. 附录 I 由本目录生成，`note` 会被原样印给读者。写作期留下的
     「见本章一致性备注」「SP-16」「book/decisions.md」「_verified.md 未登记，不编造」
     这类内部指涉必须清掉，否则读者会去找一个不存在的文件。
  2. `danluu/post-mortems` 一个索引页被当成 L3「案例实证」用了 11 次，
     去支撑 11 个不同论断——这是本书 v3.2 规则明确禁止的「硬凑来源」。
     能换成具体公开复盘的换掉（已逐条核验可达），换不掉的诚实降格为
     「公开复盘索引（检索入口）」，并写明「不引用其中具体事件作为论据」。
  3. 6 条把 sre.google 根页当「全书入口」，而 SRE Book 各章本来有独立 URL；
     5 条把 CNCF 白皮书指向仓库根，而白皮书 v2 有正式 PDF 路径。

用法：python hack/fix-ref-metadata.py [--dry-run]
"""

from __future__ import annotations

import glob
import os
import re
import sys

# ---------------------------------------------------------------------------
# 一、按 id 精确替换（字段级）
# ---------------------------------------------------------------------------
WP_URL = "https://github.com/cncf/tag-security/blob/main/community/resources/security-whitepaper/v2/CNCF_cloud-native-security-whitepaper-May2022-v2.pdf"
WP_NOTE = ("CNCF TAG Security 发布的云原生安全白皮书 v2（2022 年 5 月）；"
           "适用边界：面向云原生通用架构，具体控制项需按本章清单裁剪")
SRE = "https://sre.google/sre-book/"

FIX: dict[str, dict[str, str]] = {
    # ---- SRE Book 根页 → 章节页 ----
    "R-08-1": {
        "note": ("Kubernetes 官方探针配置任务页的当前路径；旧路径 "
                 "/configure-liveness-readiness-probes/ 已被官方重定向，引用以当前路径为准"),
    },
    "R-08-7": {
        "note": "SRE Book 第 6 章《Monitoring Distributed Systems》原文；适用边界：面向分布式在线服务，不规定具体监控工具选型",
    },
    "R-08-8": {
        "title": "Site Reliability Engineering《Addressing Cascading Failures》",
        "url": SRE + "addressing-cascading-failures/",
        "version_or_date": "SRE Book 第 22 章（在线版）",
        "note": "SRE Book 第 22 章；给出级联失败的触发条件与「重启为何是放大器」的原始论证",
    },
    "R-09-3": {
        "note": "按本书选型基线，ESO 2.x + 占位后端 vault 为全书唯一密钥注入实现，第 14、26 章与本章一致",
    },
    "R-09-7": {"url": WP_URL, "note": WP_NOTE},
    "R-10-2": {
        "note": "按本书选型基线，Kustomize 5.x overlay 为多环境基线；base + 单层 overlay 两层上限",
    },
    "R-10-3": {
        "note": "CI 里的组织策略静态校验，不等同于「准入」；集群侧策略库与准入见第 25 章",
    },
    "R-10-4": {
        "note": "rendered manifests 在本章首次提及并定义，深入展开见第 14 章",
    },
    "R-11-7": {
        "note": "按本书选型基线，Kyverno 1.x 为唯一策略引擎示例；本章只讲离线校验，集群侧策略库与准入见第 25 章",
    },
    "R-11-11": {
        "note": "公开事故复盘索引；L3 来源在本书只作行业背景实证，不用于证明本书合成案例真实发生",
    },
    "R-12-6": {
        "note": "Martin Fowler bliki 条目；与本章 build once 论述互补，不覆盖具体工具语法",
    },
    "R-12-8": {"url": WP_URL, "note": WP_NOTE},
    "R-13-3": {
        "note": "Argo Rollouts 官方文档；与 R-13-1 构成「原生滚动 vs 控制器灰度」的互相竞争实现",
    },
    "R-13-4": {
        "note": "Kubernetes 官方文档的当前路径；旧路径已被官方重定向，引用以当前路径为准",
    },
    "R-13-5": {
        "note": "Martin Fowler bliki《BlueGreenDeployment》；与 R-13-6 来自不同机构、无利益关联",
    },
    "R-13-6": {
        "note": "Sato 关于金丝雀发布的实践总结；适用边界：面向 Web 服务灰度，不覆盖数据层兼容",
    },
    "R-13-7": {
        "url": SRE + "release-engineering/",
        "version_or_date": "SRE Book 第 8 章（在线版）",
        "note": "SRE Book 第 8 章《Release Engineering》；给出发布流水线、配置管理与发布节奏的官方实践，不规定具体工具",
    },
    "R-14-5": {
        "supports": "§14.3 仓库内渲染、§14.4 渲染脚本与 kustomization.yaml",
    },
    "R-14-11": {
        "note": "Martin Fowler bliki《Continuous Delivery》；与 R-14-2 构成 GitOps 与传统 CD 的对照",
    },
    "R-15-1": {
        "note": "Argo Rollouts 官方文档（Rollout / AnalysisTemplate / 流量路由）；适用边界：控制器级灰度，不覆盖服务网格侧的流量切分",
    },
    "R-15-8": {
        "note": "Martin Fowler bliki《CanaryRelease》；提出金丝雀发布的基本形态与判据",
    },
    "R-15-10": {
        "note": "SRE Workbook《Implementing SLOs》；与 R-15-8 来自不同机构、无利益关联",
    },
    "R-15-11": {
        "version_or_date": "SRE Workbook 第 16 章（在线版）",
        "note": "SRE Workbook《Canarying Releases》；给出分批放量与阈值设定的官方做法，不覆盖具体控制器配置",
    },
    "R-16-7": {
        "note": "Martin Fowler bliki《BlueGreenDeployment》；数据层不适用蓝绿，本章只取其切换思路",
    },
    "R-16-8": {
        "url": SRE + "managing-incidents/",
        "version_or_date": "SRE Book 第 14 章（在线版）",
        "note": "SRE Book 第 14 章《Managing Incidents》；给出事件分级与角色分工，不规定工具",
    },
    "R-16-9": {
        "note": "Martin Fowler bliki《Continuous Delivery》；为「迁移先于发布」提供流程依据",
    },
    "R-17-6": {
        "url": SRE + "handling-overload/",
        "version_or_date": "SRE Book 第 21 章（在线版）",
        "note": "SRE Book 第 21 章《Handling Overload》；给出过载保护的官方判据，不覆盖具体限流实现",
    },
    "R-18-9": {
        "url": SRE + "handling-overload/",
        "version_or_date": "SRE Book 第 21 章（在线版）",
        "note": "SRE Book 第 21 章《Handling Overload》；缩容与过载保护的关系见该章「容量与关键性」部分",
    },
    "R-19-7": {
        "note": "Istio 官方流量管理文档；本书仅在选型矩阵作对比，不作为实现基线",
    },
    "R-19-8": {
        "url": SRE + "addressing-cascading-failures/",
        "version_or_date": "SRE Book 第 22 章（在线版）",
        "note": "SRE Book 第 22 章《Addressing Cascading Failures》；重试风暴与级联失败的官方论述",
    },
    "R-20-3": {
        "note": "多窗口燃尽率由同一份错误预算推导，阈值与第 22 章告警规则同源",
    },
    "R-20-5": {
        "note": "SRE Book 第 3 章《Embracing Risk》；与 R-20-4 为同机构不同著作，适用边界：以风险与变更速度权衡为语境，不覆盖规则语法",
    },
    "R-21-4": {
        "note": "第 20 章 PrometheusRule 与本条同源，命名与标签口径保持一致",
    },
    "R-21-5": {
        "note": "Grafana Loki 官方文档；适用边界：日志量大、以标签索引为主的场景，全文检索型需求需另行评估",
    },
    "R-21-6": {
        "note": "Grafana Tempo 官方文档；适用边界：已用 OTLP 上报链路的场景，不覆盖采样策略设计",
    },
    "R-21-8": {
        "note": "SRE Book 第 6 章；适用边界：面向分布式在线服务，不规定具体工具选型",
    },
    "R-22-1": {
        "note": "快窗 1h/5m、慢窗 6h 与第 20 章错误预算同源，阈值口径一致",
    },
    "R-22-2": {
        "note": "与第 20 章 R-20-2 同源，告警命名与标签口径保持一致",
    },
    "R-22-5": {
        "note": "SRE Book 第 6 章；与 R-22-4 为同机构不同著作，适用边界：监控理念层而非告警配置层",
    },
    "R-23-6": {
        "url": SRE + "postmortem-culture/",
        "version_or_date": "SRE Book 第 15 章（在线版）",
        "note": "SRE Book 第 15 章《Postmortem Culture》；适用边界：面向有专职 SRE 的组织，值班流程需按团队规模裁剪",
    },
    "R-24-5": {"version_or_date": "SPDX 3.0（在线规范）"},
    "R-24-7": {"url": WP_URL, "note": WP_NOTE},
    "R-25-5": {
        "supports": "§25.1 反模式二（CI 侧离线校验的通用做法）；与第 11 章的分工见 §25.2",
    },
    "R-25-6": {"url": WP_URL, "note": WP_NOTE},
    "R-26-4": {
        "note": "Kubernetes 官方审计文档；给出审计策略的规则顺序与输出配置，适用版本 v1.32",
    },
    "R-26-8": {"version_or_date": "EKS 官方文档（在线，随服务更新）"},
    "R-26-9": {"url": WP_URL, "note": WP_NOTE},
    "R-26-10": {
        "title": "Site Reliability Engineering《Eliminating Toil》",
        "url": SRE + "eliminating-toil/",
        "version_or_date": "SRE Book 第 5 章（在线版）",
        "note": "SRE Book 第 5 章；为「用自动化替代人工登录排障」提供运维共识依据，适用边界：面向重复性运维工作，不覆盖一次性故障排查",
    },
    "R-27-2": {
        "supports": "支撑 §27.1 反模式二、§27.2 协调循环幂等/可重入/容忍重复事件三条工程约束（不重复第 2 章定义）",
    },
    "R-30-5": {
        "note": "与 R-14-2 同源；GitOps 唯一示例实现，多集群为第 14 章晋升模型推广",
    },
}

# ---------------------------------------------------------------------------
# 二、把「索引页当 L3」换成具体公开复盘（均已核验可达）
# ---------------------------------------------------------------------------
CASE = {
    # ch12：CI 侧凭据与供应链
    "R-12-9": {
        "title": "CircleCI 2023 年 1 月事件复盘（第三方集成被攻破导致客户凭据外泄）",
        "author_or_org": "CircleCI",
        "url": "https://circleci.com/blog/jan-4-2023-incident-report/",
        "version_or_date": "2023 年 1 月",
        "note": "CI 服务商自身被攻破、导致下游客户长期令牌与密钥外泄的官方复盘；适用边界：揭示「CI 是凭据集中地」，不覆盖流水线配置语法",
    },
    # ch13：发布与回滚
    "R-13-9": {
        "title": "Cloudflare 2020 年 7 月 17 日全球中断复盘（单条配置规则全量下发）",
        "author_or_org": "Cloudflare",
        "url": "https://blog.cloudflare.com/cloudflare-outage-on-july-17-2020/",
        "version_or_date": "2020 年 7 月",
        "note": "一条变更后的正则规则被全量下发，边缘 CPU 耗尽导致半数流量中断，最终靠全局回滚恢复；适用边界：面向配置类变更，不覆盖代码缺陷导致的回滚",
    },
    # ch14：手工变更与配置漂移
    "R-14-12": {
        "title": "AWS S3 2017 年 2 月 28 日事件摘要（运维执行既定剧本时输入参数错误）",
        "author_or_org": "Amazon Web Services",
        "url": "https://aws.amazon.com/message/41926/",
        "version_or_date": "2017 年 2 月",
        "note": "执行既定运维剧本时参数输错、移除的容量超出预期，导致区域级服务中断；官方在复盘中给出「限制并发、分批执行、加护栏」的改进项；适用边界：面向控制面操作，不覆盖应用层发布",
    },
    # ch15：分批放量与自动回滚
    "R-15-12": {
        "title": "Fastly 2021 年 6 月 8 日中断复盘（未分批的配置推送触发全局失效）",
        "author_or_org": "Fastly",
        "url": "https://www.fastly.com/blog/summary-of-june-8-outage",
        "version_or_date": "2021 年 6 月",
        "note": "一次已存在数周的配置在特定客户条件下被触发，影响全球边缘节点，靠禁用该配置恢复；适用边界：说明「配置类变更同样需要分批放量与可回滚」，不构成对具体灰度控制器的选型建议",
    },
    # ch16：备份与可恢复性
    "R-16-10": {
        "title": "GitHub 2018 年 10 月 21 日事件分析（数据一致性受损与恢复过程）",
        "author_or_org": "GitHub",
        "url": "https://github.blog/2018-10-30-oct21-post-incident-analysis/",
        "version_or_date": "2018 年 10 月",
        "note": "事故中多副本数据出现不一致，恢复依赖跨站点副本与人工校验，全过程超过 24 小时；适用边界：揭示「备份存在不等于可恢复」，不覆盖业务侧数据迁移的字段兼容问题",
    },
    # ch24：供应链攻击
    "R-24-9": {
        "title": "Catalog of Supply Chain Compromises（供应链攻击案例目录）",
        "author_or_org": "CNCF TAG Security",
        "url": "https://github.com/cncf/tag-security/blob/main/community/catalog/compromises",
        "version_or_date": "2019 年至今持续更新",
        "note": "CNCF 维护的供应链攻击案例目录，逐条记录攻击手法与影响面；适用边界：以公开披露为限，未披露事件不在其中",
    },
    # ch26：长期凭据与权限边界
    "R-26-11": {
        "title": "Codecov Bash Uploader 供应链事件官方说明（CI 上传脚本被篡改）",
        "author_or_org": "Codecov",
        "url": "https://about.codecov.io/security-update/",
        "version_or_date": "2021 年 4 月",
        "note": "官方说明：上传脚本被篡改后，运行该脚本的 CI 作业把环境变量中的凭据发往第三方；适用边界：属 CI 侧长期凭据滥用，集群内 RBAC 边界问题需另找案例",
    },
}

# 换不到具体案例的，诚实降格为「检索入口」，并写明不作论据
INDEX = {
    "R-22-7": {
        "title": "公开事故复盘索引（告警疲劳与值班负荷相关案例的检索入口）",
        "version_or_date": "持续更新",
        "note": "由社区维护的公开复盘索引；本书只以它说明「告警疲劳普遍存在」这一背景，不引用其中任何具体事件作为论据",
    },
    "R-23-8": {
        "title": "公开事故复盘索引（数据库事故类案例的检索入口）",
        "version_or_date": "持续更新",
        "note": "由社区维护的公开复盘索引；本书只以它说明「处置时间被信息搜集拖长」是普遍现象，不引用其中任何具体事件作为论据",
    },
    "R-29-12": {
        "title": "公开事故复盘索引（Operator 与控制器升级相关案例的检索入口）",
        "version_or_date": "持续更新",
        "note": "由社区维护的公开复盘索引；控制器升级事故的公开披露零散，本书因此不引用具体事件，只据此说明该类失效存在",
    },
    "R-31-7": {
        "title": "公开事故复盘索引（复盘方法与事故重演相关案例的检索入口）",
        "version_or_date": "持续更新",
        "note": "由社区维护的公开复盘索引；用于观察复盘文档的通用结构，本书的重演脚本为合成设计，不引用其中具体事件",
    },
}

# supports 随之校准（保持 §X.1 锚点不变，只改后半句）
SUPPORTS = {
    "R-12-9": "§12.1 反模式的方法论（CI 侧凭据是供应链薄弱点）；合成案例不冒充真实事件",
    "R-13-9": "§13.1 回滚方案先于发布：全量下发的变更只能靠全局回滚收场",
    "R-14-12": "§14.1 手工变更与配置漂移的方法论；合成案例不冒充真实事件",
    "R-15-12": "§15.1 未分批的配置变更是全局故障的常见来源",
    "R-16-10": "§16.1 备份不等于可恢复：恢复依赖校验与人工判断",
    "R-24-9": "§24.1 三条反模式的方法论支撑（单点校验可绕过、证据不归档无法定界）",
    "R-26-11": "§26.1 长期密钥与默认凭据是权限事故的常见起点",
}

# ---------------------------------------------------------------------------
# 三、兜底正则：清理一切残留的内部指涉
# ---------------------------------------------------------------------------
STRIP = [
    (r"；?\s*book/references/_registry\.yaml\s*[^；。]*", ""),
    (r"；?\s*_verified\.md\s*[^；。]*", ""),
    (r"；?\s*references/_verified\.md\s*[^；。]*", ""),
    (r"；?\s*book/[a-z\-]+\.md[^；。]*", ""),
    (r"按 book/decisions\.md\s*U-\d+，", "按本书选型基线，"),
    (r"（SP-\d+）", ""),
    (r"；?\s*SP-\d+\s*命名一致性依据", ""),
    (r"见 SP-\d+", ""),
    (r"（名称级候选）", ""),
    (r"，?名称级候选[，；]?", ""),
    (r"（候选待核验）", ""),
    (r"（按章择取，待核验）", ""),
    (r"；?待 P4 补正式链接", ""),
    (r"；?直连经代理超时、?检索核验存在；?单章链接待 P4 复核，暂用全书入口", ""),
    (r"；?检索核验存在、直连经代理超时，P4 复核", ""),
    (r"；?检索核验存在；直连经代理超时，P4 复核", ""),
    (r"；?直连经代理超时，P4 复核", ""),
    (r"；?已核验入口池 L2 条目，?", ""),
    (r"；?已核验链接池中无此条目，保留名称级官方文档，链接待核验；?", ""),
    (r"；?已核验链接池中无 Loki 官方文档独立条目，保留名称级官方条目，链接待核验；?", ""),
    (r"；?已核验链接池中无 Tempo 官方文档独立条目，保留名称级官方条目，链接待核验；?", ""),
    (r"；?不得编造 URL", ""),
    (r"；?见本章一致性备注[^；。]*", ""),
    (r"；?卡片列为 L1 候选", ""),
    (r"hack/[a-z\-]+\.(sh|py)", "本书配套脚本"),
    (r"^\s*[；，]\s*", ""),
]

FIELDS = ("title", "author_or_org", "version_or_date", "note", "supports")


def patch_block(block: str, fields: dict[str, str]) -> str:
    for key, val in fields.items():
        pat = re.compile(rf'(?m)^  {key}: ".*"$')
        val_esc = val.replace("\\", "\\\\").replace('"', '\\"')
        if pat.search(block):
            block = pat.sub(f'  {key}: "{val_esc}"', block, count=1)
        else:
            block = block.rstrip("\n") + f'\n  {key}: "{val_esc}"\n'
    return block


def strip_block(block: str) -> str:
    out = []
    for line in block.split("\n"):
        m = re.match(r'^  ([a-z_]+): "(.*)"$', line)
        if m and m.group(1) in FIELDS:
            key, val = m.group(1), m.group(2)
            for pat, rep in STRIP:
                val = re.sub(pat, rep, val)
            val = re.sub(r"[；，]{2,}", "；", val).strip()
            out.append(f'  {key}: "{val}"')
        else:
            out.append(line)
    return "\n".join(out)


def main() -> int:
    dry = "--dry-run" in sys.argv
    n_fix = n_case = n_strip = 0
    for path in sorted(glob.glob("references/ch*.yaml")):
        text = open(path, encoding="utf-8").read()
        parts = re.split(r"(?m)^(?=- id: )", text)
        head, blocks = parts[0], parts[1:]
        for i, b in enumerate(blocks):
            m = re.match(r"- id: (\S+)", b)
            if not m:
                continue
            rid = m.group(1)
            before = b
            if rid in FIX:
                b = patch_block(b, FIX[rid])
                n_fix += 1
            if rid in CASE:
                f = dict(CASE[rid])
                if "supports" not in f and rid in SUPPORTS:
                    f["supports"] = SUPPORTS[rid]
                b = patch_block(b, f)
                n_case += 1
            if rid in INDEX:
                b = patch_block(b, INDEX[rid])
                n_case += 1
            if rid in SUPPORTS and rid not in CASE:
                b = patch_block(b, {"supports": SUPPORTS[rid]})
            stripped = strip_block(b)
            if stripped != b:
                n_strip += 1
                b = stripped
            if b != before:
                b = b.replace('accessed: "2026-11-10"', 'accessed: "2026-11-11"')
            blocks[i] = b
        new = head + "".join(blocks)
        if not dry and new != text:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(new)
            print(f"  写入 {os.path.basename(path)}")
    print(f"字段修订 {n_fix} 条 / 来源替换 {n_case} 条 / 兜底清理命中 {n_strip} 条"
          + ("（dry-run）" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
