#!/usr/bin/env python3
"""把 15 条 pending_url 引用核验结果写回 references/chNN.yaml。

核验口径（2026-11-11，P6 出书面 / D-45）：
  - 能定位到发布方官方入口的 → url 填真实链接、status=verified、accessed 更新；
  - 原发布方已下线（Weaveworks 停止运营、KubeCon 录播入口随年份迁移）→ status=offline，
    保留文献名称与作者，不提供易失效链接，note 写明原因与替代来源；
  - 不编造 URL：查不到就写 offline，宁缺毋滥。

D-53（2026-11-13）：R-28-7 已改由 Kubernetes《Controllers》官方文档支撑
（L1 / verified），不再是本批核验对象，故从 UPDATES 移除；保留会让重跑把新条目
覆盖回 offline。本脚本为一次性迁移工具，已执行完毕，不应重跑。

用法：python hack/verify-pending-refs.py [--dry-run]
"""

from __future__ import annotations

import glob
import os
import re
import sys

UPDATES: dict[str, dict[str, str]] = {
    "R-08-9": {
        "title": "Liveness Probes are Dangerous",
        "author_or_org": "Henning Jacobs（Zalando 首席工程师）",
        "url": "https://srcco.de/posts/kubernetes-liveness-probes-are-dangerous.html",
        "version_or_date": "2019 年发布，持续在线",
        "status": "verified",
        "note": "作者为 Zalando 首席工程师，基于其生产实践与对 Kubernetes 文档的反馈整理；适用边界：面向典型 HTTP 服务，集群成员相互探活的有状态应用需另行评估",
    },
    "R-11-10": {
        "title": "Writing Good e2e Tests for Kubernetes（SIG Testing 指南）",
        "author_or_org": "Kubernetes SIG Testing",
        "url": "https://github.com/kubernetes/community/blob/master/contributors/devel/sig-testing/writing-good-e2e-tests.md",
        "version_or_date": "当前主干版本",
        "status": "verified",
        "note": "Kubernetes 官方仓库的 e2e 测试写作指南（模式与反模式）；适用边界：只覆盖端到端层，单元与集成测试的分层判据见本章正文",
    },
    "R-14-9": {
        "title": "GitOps - Operations by Pull Request（Weaveworks 2017）",
        "author_or_org": "Weaveworks（已停止运营）",
        "url": "",
        "version_or_date": "2017 年 8 月",
        "status": "offline",
        "note": "Weaveworks 于 2024 年停止运营，原始博文所在站点已下线；本条按名称引用其历史贡献，不提供失效链接。该文提出的四原则现由 R-14-1 的 OpenGitOps 正式维护",
    },
    "R-14-10": {
        "title": "CNCF App Delivery TAG 工作组与产出索引",
        "author_or_org": "CNCF TAG App Delivery",
        "url": "https://tag-app-delivery.cncf.io/wgs/",
        "version_or_date": "持续更新",
        "status": "verified",
        "note": "TAG App Delivery 是 CNCF 应用交付领域的官方技术咨询组，其 GitOps 分工作组的正式产出即 R-14-1 的 OpenGitOps 原则；适用边界：工作组文档属方向性共识，不构成具体工具选型结论",
    },
    "R-18-10": {
        "title": "FinOps for Kubernetes：工程侧成本优化（CNCF）",
        "author_or_org": "CNCF",
        "url": "https://www.cncf.io/blog/2024/04/29/finops-for-kubernetes-engineering-cost-optimization/",
        "version_or_date": "2024 年 4 月",
        "status": "verified",
        "note": "讨论容器化环境的成本归因与优化路径；适用边界：面向云上托管 Kubernetes，自建环境的分摊口径需按组织实际调整；不含单价，仅支撑相对比例与归因方法",
    },
    "R-19-10": {
        "title": "Gateway API 增强提案（GEP）流程与设计说明",
        "author_or_org": "Kubernetes SIG Network",
        "url": "https://gateway-api.sigs.k8s.io/geps/overview/",
        "version_or_date": "持续更新，随 Gateway API 版本演进",
        "status": "verified",
        "note": "记录 Gateway API 演进中的设计取舍与角色拆分动机；适用边界：提案不是稳定规范，落地口径以 v1 通道的正式文档为准",
    },
    "R-22-6": {
        "title": "My Philosophy on Alerting",
        "author_or_org": "Rob Ewaschuk（Google SRE）",
        "url": "https://docs.google.com/document/d/199PqyG3UsyXlwieHaqbGiWVa8eMWi8zzAn0YfcApr8Q/edit",
        "version_or_date": "在线版，持续可访问",
        "status": "verified",
        "note": "被广泛引用为「告警应可行动」的共识来源；适用边界：个人实践总结，需按组织值班规模与业务形态裁剪，不宜照搬阈值",
    },
    "R-23-7": {
        "title": "Site Reliability Workbook · Incident Response",
        "author_or_org": "Google SRE",
        "url": "https://sre.google/workbook/incident-response/",
        "version_or_date": "Workbook 第 9 章",
        "status": "verified",
        "note": "给出事件响应的角色拆分（IC / Ops / Comms）与演练方法；适用边界：源自 Google 规模，小团队可合并职责但不宜省略角色本身",
    },
    "R-26-7": {
        "title": "CIS Kubernetes Benchmark",
        "author_or_org": "Center for Internet Security（CIS）",
        "url": "https://www.cisecurity.org/benchmark/kubernetes",
        "version_or_date": "Kubernetes Benchmark 2.0.x",
        "status": "verified",
        "note": "由社区共识流程维护的安全配置基线；适用边界：面向自建控制面，托管集群应按各云厂商对应的 EKS / AKS / GKE 版本裁剪",
    },
    "R-27-7": {
        "title": "Introducing Operators: Putting Operational Knowledge into Software",
        "author_or_org": "CoreOS（Brandon Philips）",
        "url": "https://ifup.org/blog/introducing-operators",
        "version_or_date": "2016 年 11 月",
        "status": "verified",
        "note": "首次提出 Operator 概念的原文，作者为 CoreOS CTO；适用边界：文中扩展机制（third party resources）已被 CRD 取代，只引用其设计动机与「无状态易、有状态难」的判断",
    },
    "R-27-8": {
        "title": "CNCF Operator 白皮书 v1.0（TAG App Delivery）",
        "author_or_org": "CNCF TAG App Delivery",
        "url": "https://tag-app-delivery.cncf.io/whitepapers/operator/",
        "version_or_date": "v1.0",
        "status": "verified",
        "note": "定义 Operator 的能力模型、设计模式与常见反模式；适用边界：面向通用 Operator，具体实现选型仍以本章 27.2 的决策树为准",
    },
    "R-28-8": {
        "title": "CNCF Operator 白皮书 v1.0（TAG App Delivery）",
        "author_or_org": "CNCF TAG App Delivery",
        "url": "https://tag-app-delivery.cncf.io/whitepapers/operator/",
        "version_or_date": "v1.0",
        "status": "verified",
        "note": "支撑「控制器静默降级」这一反模式的判定：Operator 白皮书把可观测性与状态上报列为能力项而非可选项；适用边界：白皮书给能力清单，落地强度按团队运维能力裁剪",
    },
    "R-29-8": {
        "title": "CNCF 项目成熟度分层（Graduated / Incubating / Sandbox）",
        "author_or_org": "CNCF",
        "url": "https://www.cncf.io/projects/",
        "version_or_date": "持续更新",
        "status": "verified",
        "note": "按三档成熟度列出定义与在册项目；适用边界：成熟度是准入门槛而非质量保证，同一档内项目的运维成熟度差异仍大",
    },
    "R-30-8": {
        "title": "CNCF 平台白皮书（Platforms White Paper）",
        "author_or_org": "CNCF TAG App Delivery",
        "url": "https://tag-app-delivery.cncf.io/whitepapers/platforms/",
        "version_or_date": "v1.0（2023 年发布）",
        "status": "verified",
        "note": "提出平台能力模型（黄金路径、自助服务、降低认知负荷、默认安全）与平台团队职责；适用边界：面向内部平台，团队规模与产品化程度需按实际情况裁剪",
    },
    "R-30-12": {
        "title": "CNCF 用户案例库（Case Studies）",
        "author_or_org": "CNCF",
        "url": "https://www.cncf.io/case-studies/",
        "version_or_date": "持续更新",
        "status": "verified",
        "note": "按项目与行业归档的落地案例，用于观察多集群与平台化的真实形态；适用边界：案例多为成功叙事，失败与代价需结合各章反模式自行评估",
    },
}


def patch_block(block: str, fields: dict[str, str]) -> str:
    for key, val in fields.items():
        pat = re.compile(rf'(?m)^  {key}: ".*"$')
        if pat.search(block):
            block = pat.sub(f'  {key}: "{val}"'.replace("\\", "\\\\"), block, count=1)
        else:
            block = block.rstrip("\n") + f'\n  {key}: "{val}"\n'
    return block


def main() -> int:
    dry = "--dry-run" in sys.argv
    done = 0
    for path in sorted(glob.glob("references/ch*.yaml")):
        text = open(path, encoding="utf-8").read()
        parts = re.split(r"(?m)^(?=- id: )", text)
        head, blocks = parts[0], parts[1:]
        changed = False
        for i, b in enumerate(blocks):
            m = re.match(r"- id: (\S+)", b)
            if m and m.group(1) in UPDATES:
                f = dict(UPDATES[m.group(1)])
                f["accessed"] = "2026-11-11"
                blocks[i] = patch_block(b, f)
                changed = True
                done += 1
        if changed:
            new = head + "".join(blocks)
            if not dry:
                with open(path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(new)
            print(f"  更新 {os.path.basename(path)}")
    print(f"共更新 {done} 条引用" + ("（dry-run）" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
