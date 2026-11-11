#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""书稿工具：引用登记规范化 / 全书一致性校验 / 附录 I 生成。

用法：
  python hack/book_tools.py normalize   # 统一 references/chNN.yaml 的字段与结构
  python hack/book_tools.py check       # 全书八项横扫（退出码非 0 表示有缺陷）
  python hack/book_tools.py appendix    # 由 references/*.yaml 生成附录 I
  python hack/book_tools.py pending     # 列出仍为 pending_url 的来源

规范依据：book/chapter-spec.md、book/references/_registry.yaml、书籍大纲-v3.md 第十节。
"""
import glob
import json
import os
import re
import sys
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH_DIR = os.path.join(ROOT, "chapters")
REF_DIR = os.path.join(ROOT, "references")
BOOK_NOTES = os.path.join(ROOT, "book", "chapter-notes")
FIELDS = ["id", "title", "author_or_org", "level", "url", "version_or_date",
          "accessed", "archive_url", "supports", "status"]
OPTIONAL = ["note", "license"]
HOOK_CHAPTERS = {"02", "03", "08", "09", "13", "14", "22", "23"}
CROSS_CHAPTERS = {"24", "25", "26"}
SPECIAL_CHAPTERS = {"01", "23", "31"}
URL_WHITELIST = re.compile(
    r"(127\.0\.0\.1|localhost|\.svc|example\.com|example\.org|"
    r"kubernetes\.default|chaos-mesh\.org|prometheus\.io|0\.0\.0\.0|"
    r"https?://api:|https?://db:|https?://gateway:|/api/v1|"
    # 配置端点（非引用 URL）：OIDC 签发方 / cosign 证书身份 / 云 OIDC issuer
    r"token\.actions\.githubusercontent\.com|"
    r"github\.com/[a-z0-9_.-]+/order-demo|"
    r"sigstore\.dev|"
    r"amazonaws\.com)"
)

# 第二轮复核后补登的规范入口：title 关键字 -> (url, note)
UPGRADES = {
    # 第一轮复核补登
    "OpenGitOps Principles": ("https://opengitops.dev/", "第二轮低并发复核 200"),
    "Flux": ("https://fluxcd.io/flux/", "第二轮低并发复核 200"),
    "cert-manager": ("https://cert-manager.io/docs/", "第二轮低并发复核 200"),
    "Argo Rollouts": ("https://argoproj.github.io/rollouts/", "官方规范入口；直连经代理超时，P4 复核"),
    "Borg, Omega, and Kubernetes": ("https://dl.acm.org/doi/10.1145/2898442.2898444", "ACM DL DOI 入口，已通过文献页核验"),
    "Implementing SLOs": ("https://sre.google/workbook/implementing-slos/", "Google SRE Workbook 规范入口；直连经代理超时，P4 复核"),
    "Alerting on SLOs": ("https://sre.google/workbook/alerting-on-slos/", "Google SRE Workbook 规范入口；直连经代理超时，P4 复核"),
    "Monitoring Distributed Systems": ("https://sre.google/sre-book/monitoring-distributed-systems/", "Google SRE Book 规范入口；直连经代理超时，P4 复核"),
    "Embracing Risk": ("https://sre.google/sre-book/embracing-risk/", "Google SRE Book 规范入口；直连经代理超时，P4 复核"),
    "Site Reliability Engineering": ("https://sre.google/", "Google SRE 站点入口；直连经代理超时，P4 复核"),
    # Kubernetes 官方概念 / 任务页（第三轮 UA 复核 200）
    "Network Policies": ("https://kubernetes.io/docs/concepts/services-networking/network-policies/", "Kubernetes v1.32 概念页"),
    "NetworkPolicy": ("https://kubernetes.io/docs/concepts/services-networking/network-policies/", "Kubernetes v1.32 概念页"),
    "Pod Lifecycle": ("https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/", "Kubernetes v1.32 概念页"),
    "Owners and Dependents": ("https://kubernetes.io/docs/concepts/overview/working-with-objects/owners-dependents/", "Kubernetes v1.32 概念页"),
    "Node-pressure Eviction": ("https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/", "Kubernetes v1.32 概念页"),
    "Using RBAC Authorization": ("https://kubernetes.io/docs/reference/access-authn-authz/rbac/", "Kubernetes v1.32 参考页"),
    "Pod Topology Spread Constraints": ("https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/", "Kubernetes v1.32 概念页"),
    "Namespaces": ("https://kubernetes.io/docs/tasks/administer-cluster/namespaces/", "Kubernetes v1.32 任务页"),
    "ResourceQuota": ("https://kubernetes.io/docs/concepts/policy/resource-quotas/", "Kubernetes v1.32 概念页"),
    "LimitRange": ("https://kubernetes.io/docs/concepts/policy/limit-range/", "Kubernetes v1.32 概念页"),
    "Deployments": ("https://kubernetes.io/docs/concepts/workloads/controllers/deployment/", "Kubernetes v1.32 概念页"),
    "Liveness, Readiness, and Startup Probes": ("https://kubernetes.io/docs/concepts/workloads/pods/probes/", "Kubernetes v1.32 概念页"),
    "OCI Image Spec": ("https://specs.opencontainers.org/image-spec/", "OCI Image Spec v1.1 规范站点"),
    "Version Skew Policy": ("https://kubernetes.io/docs/setup/release/version-skew-policy/", "Kubernetes 官方版本偏差策略"),
    "CRD 版本与转换": ("https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/", "Kubernetes v1.32 任务页"),
    # 工具官方文档（第三轮复核 200）
    "Envoy Gateway": ("https://gateway.envoyproxy.io/latest/", "Envoy Gateway 官方文档站"),
    "SOPS": ("https://github.com/mozilla/sops", "SOPS 官方仓库"),
    "Thanos": ("https://thanos.io/tip/thanos/getting-started.md/", "Thanos 官方文档"),
    "OpenTelemetry Collector": ("https://opentelemetry.io/docs/collector/", "OTel 官方文档"),
    "kubeconform": ("https://github.com/yannh/kubeconform", "kubeconform 官方仓库"),
    "kuttl": ("https://github.com/kudobuilder/kuttl", "kuttl 官方仓库"),
    "chart-testing": ("https://github.com/helm/chart-testing", "Helm chart-testing 官方仓库"),
    "Vertical Pod Autoscaler": ("https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler", "K8s Autoscaler 官方仓库 VPA 目录"),
    "Operator Lifecycle Manager": ("https://github.com/operator-framework/operator-lifecycle-manager", "OLM 官方仓库"),
    "Score Specification": ("https://github.com/score-spec/spec", "Score 规范官方仓库"),
    "Sigstore cosign": ("https://github.com/sigstore/cosign", "cosign 官方仓库"),
    "Alertmanager": ("https://prometheus.io/docs/alerting/latest/alertmanager/", "Prometheus 官方文档"),
    "Litmus": ("https://litmuschaos.io/", "LitmusChaos 官方文档站"),
    "Terraform State": ("https://developer.hashicorp.com/terraform/language/state", "HashiCorp 官方文档"),
    "controller-runtime": ("https://github.com/kubernetes-sigs/controller-runtime", "controller-runtime 官方仓库"),
    "SPDX": ("https://spdx.dev/specifications/", "SPDX 规范站点"),
    "IRSA": ("https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html", "AWS EKS 官方文档"),
    "Cloud Native Definition": ("https://github.com/cncf/toc/blob/main/DEFINITION.md", "CNCF TOC 云原生定义 v1.0"),
    "Cloud Native Landscape": ("https://github.com/cncf/landscape", "CNCF Landscape 官方仓库"),
    "Cloud Native Security Whitepaper": ("https://github.com/cncf/tag-security", "CNCF TAG Security 官方仓库（白皮书所在项目；具体 v2 文档链接待 P4 复核）"),
    "Team Topologies": ("https://teamtopologies.com/", "Team Topologies 官方站点"),
    "Refactoring Databases": ("https://www.amazon.com/Refactoring-Databases-Evolutionary-Database-Design/dp/0321293533", "书目条目（出版社信息页）"),
    # L3：公开复盘方法论合集（只支撑反模式方法论，不证明某次虚构事故真实发生）
    "postmortem": ("https://github.com/danluu/post-mortems", "公开 postmortem 索引；合成案例不得冒充真实事件"),
    "Postmortem": ("https://github.com/danluu/post-mortems", "公开 postmortem 索引；合成案例不得冒充真实事件"),
    "事故复盘": ("https://github.com/danluu/post-mortems", "公开 postmortem 索引；合成案例不得冒充真实事件"),
    # 第四轮复核 200
    "ConfigMaps": ("https://kubernetes.io/docs/concepts/configuration/configmap/", "Kubernetes v1.32 概念页（含 immutable 语义）"),
    "Configuration Best Practices": ("https://kubernetes.io/docs/concepts/configuration/overview/", "Kubernetes v1.32 配置最佳实践"),
    "Horizontal Pod Autoscaling": ("https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/", "Kubernetes v1.32 任务页"),
    "版本偏差策略": ("https://kubernetes.io/docs/setup/release/version-skew-policy/", "Kubernetes 官方版本偏差策略"),
    "KEP-753": ("https://github.com/kubernetes/enhancements/tree/master/keps/sig-node/753-sidecar-containers", "Kubernetes Enhancement Proposal 原文"),
    "Workflow syntax": ("https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions", "GitHub Actions 官方文档"),
    "GitLab CI/CD": ("https://docs.gitlab.com/ee/ci/", "GitLab 官方文档"),
    "Flagger": ("https://docs.flagger.app/", "Flagger 官方文档站"),
    "Istio Documentation": ("https://istio.io/latest/docs/", "Istio 官方文档站；本书仅作选型对比"),
    "TAG App Delivery": ("https://github.com/cncf/tag-app-delivery", "CNCF TAG App Delivery 官方仓库"),
    "finalizer": ("https://kubernetes.io/docs/concepts/architecture/garbage-collection/", "Kubernetes 垃圾回收 / finalizer 官方文档"),
    "级联删除": ("https://kubernetes.io/docs/concepts/architecture/garbage-collection/", "Kubernetes 垃圾回收 / finalizer 官方文档"),
    "Continuous Delivery（2010 专著）": ("https://continuousdelivery.com/", "Jez Humble / David Farley 持续交付官方站点"),
    "Humble & Farley": ("https://continuousdelivery.com/", "Jez Humble / David Farley 持续交付官方站点"),
    "项目成熟度分级": ("https://www.cncf.io/projects/", "CNCF 项目分级官方页"),
    "Canarying Releases": ("https://sre.google/workbook/canarying-releases/", "Google SRE Workbook 规范入口；直连经代理超时，P4 复核"),
}


def _clean(value):
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    return v.replace('\\"', '"').strip()


def parse_refs(path):
    text = open(path, encoding="utf-8").read()
    blocks = re.split(r"(?m)^(?=[ \t]*- id:)", text)
    entries = []
    for block in blocks:
        m = re.search(r"(?m)^[ \t]*- id:[ \t]*[\"']?(R-\d{2}-\d+)", block)
        if not m:
            continue
        d = {"id": m.group(1)}
        for k in FIELDS[1:] + OPTIONAL:
            mm = re.search(r"(?m)^[ \t]+" + k + r":[ \t]*(.*)$", block)
            if mm:
                d[k] = _clean(mm.group(1))
        for k in FIELDS[1:]:
            d.setdefault(k, "")
        entries.append(d)
    return entries


def _q(s):
    return json.dumps(s or "", ensure_ascii=False)


def normalize():
    changed = 0
    for path in sorted(glob.glob(os.path.join(REF_DIR, "ch*.yaml"))):
        n = os.path.basename(path)[2:4]
        entries = parse_refs(path)
        if not entries:
            print("!! 无法解析：", path)
            continue
        for e in entries:
            if e.get("status") == "pending_url" and not e.get("url"):
                for key, (url, note) in UPGRADES.items():
                    if key.lower() in (e.get("title") or "").lower():
                        e["url"] = url
                        e["status"] = "verified"
                        e["note"] = note
                        break
        lines = [
            "# 第 %d 章引用登记（由 hack/book_tools.py normalize 规范化）" % int(n),
            "# 编号与 chapters/ch%s.md 正文角标 [R-%s-x] 逐一闭环；字段模板见 book/references/_registry.yaml" % (n, n),
            "# 正文只出现角标，严禁裸 URL；链接池见 references/_verified.md；附录 I 由本文件生成。",
            "",
        ]
        for e in entries:
            lines.append("- id: %s" % e["id"])
            for k in FIELDS[1:]:
                lines.append("  %s: %s" % (k, _q(e.get(k, ""))))
            for k in OPTIONAL:
                if e.get(k):
                    lines.append("  %s: %s" % (k, _q(e[k])))
            lines.append("")
        out = "\n".join(lines).rstrip() + "\n"
        old = open(path, encoding="utf-8").read()
        if out != old:
            open(path, "w", encoding="utf-8", newline="\n").write(out)
            changed += 1
    print("规范化完成，改写 %d 个文件" % changed)


def chapter_ids(text, n):
    return {"R-%s-%s" % (a, b) for a, b in
            re.findall(r"\[R-(\d{2})-(\d+)\]", text) if a == n}


def check():
    problems = collections.defaultdict(list)
    chapters = sorted(glob.glob(os.path.join(CH_DIR, "ch*.md")))
    if len(chapters) != 31:
        problems["章节总数"].append(len(chapters))
    for f in chapters:
        n = os.path.basename(f)[2:4]
        t = open(f, encoding="utf-8").read()
        ref_path = os.path.join(REF_DIR, "ch%s.yaml" % n)
        if not os.path.exists(ref_path):
            problems["缺引用登记"].append(n)
            continue
        entries = parse_refs(ref_path)
        ids = {e["id"] for e in entries}
        if ids != chapter_ids(t, n):
            problems["角标未闭环"].append((n, sorted(ids ^ chapter_ids(t, n))[:5]))
        if len(ids) != len(entries):
            problems["引用 id 重复"].append(n)
        l1 = sum(1 for e in entries if e["level"] == "L1")
        l2 = sum(1 for e in entries if e["level"] == "L2")
        if l1 < 1:
            problems["L1 密度不足"].append(n)
        if l2 < 2:
            problems["L2 密度不足"].append((n, l2))
        for e in entries:
            miss = [k for k in FIELDS if not e.get(k) and k != "url" and k != "archive_url"]
            if miss:
                problems["引用字段缺失"].append((n, e["id"], miss))
            if e["status"] == "pending_url" and e["url"]:
                problems["pending_url 却有链接"].append((n, e["id"]))
            if e["status"] == "verified" and not e["url"].startswith("http"):
                problems["verified 却无链接"].append((n, e["id"]))
        # 结构
        heads = re.findall(r"(?m)^## (\d+)\.(\d)", t)
        if n in CROSS_CHAPTERS and len(heads) != 4:
            problems["横切章段数"].append((n, len(heads)))
        if n not in CROSS_CHAPTERS and n not in SPECIAL_CHAPTERS and len(heads) != 7:
            problems["主线章段数"].append((n, len(heads)))
        for marker, label in [("本书观点", "本书观点块"), ("CL-S-", "安全项"),
                              ("上线检查清单", "检查清单段"), ("依据与延伸阅读", "依据段")]:
            if marker not in t:
                problems["缺" + label].append(n)
        # P6 出书面（D-42）：写作期脚手架必须已外迁，正文不得残留
        for marker, label in [("终稿扩写清单", "扩写清单"), ("一致性备注", "一致性备注"),
                              ("初稿状态", "初稿状态行")]:
            if marker in t:
                problems["正文残留" + label].append(n)
        if not os.path.exists(os.path.join(BOOK_NOTES, f"ch{n}.md")):
            problems["缺写作笔记存档"].append(n)
        # 只有独立小标题或加粗落点才算「回到第 1 章」；「按 9.7 不硬凑…」是说明文字，不算
        hook_hit = re.search(r"(?m)^(?:\*\*回到第 1 章\*\*|#{2,3}\s*回到第 1 章)", t)
        if hook_hit and n not in HOOK_CHAPTERS and n != "31":
            problems["多余回扣"].append(n)
        if n in HOOK_CHAPTERS and not hook_hit:
            problems["钩子章缺回扣"].append(n)
        # 裸 URL（D-09 只约束正文：先去围栏代码块，配置/示例里的端点与链接不算裸 URL）
        t_prose = re.sub(r"```.*?```", "", t, flags=re.S)
        ext = [u for u in re.findall(r"https?://[^\s\"'`\)\]\|<>]+", t_prose)
               if not URL_WHITELIST.search(u)]
        if ext:
            problems["疑似裸 URL"].append((n, list(dict.fromkeys(ext))[:3]))
        # 占位词
        if re.search(r"TODO|待补|（略）|暂略", t):
            problems["占位词"].append(n)
    for k in sorted(problems):
        print("[%s] %d 处: %s" % (k, len(problems[k]), problems[k][:10]))
    total = sum(len(v) for v in problems.values())
    print("\n合计 problem = %d；%s" % (total, "通过" if total == 0 else "需修复"))
    return 1 if total else 0


def pending():
    for path in sorted(glob.glob(os.path.join(REF_DIR, "ch*.yaml"))):
        for e in parse_refs(path):
            if e["status"] == "pending_url":
                print("%s\t%s\t%s" % (os.path.basename(path), e["id"], e["title"]))


LEVEL_LABEL = {"L1": "L1 规范与官方", "L2": "L2 权威著作与共识", "L3": "L3 案例与实证"}


def appendix():
    out = ["# 附录 I　参考文献与来源登记", "",
           "> 本附录由 `references/chNN.yaml` 自动生成（`python hack/book_tools.py appendix`），不在别处手工维护第二份。",
           "> 正文只出现 `[R-XX-N]` 角标；此处给出编号、级别、标题、机构、版本、访问日期与支撑的论断位置。",
           "> 标「链接待核验」者为池外候选来源，按 D-10 不编造 URL；季度复核计划见 10.5。", ""]
    for path in sorted(glob.glob(os.path.join(REF_DIR, "ch*.yaml"))):
        n = os.path.basename(path)[2:4]
        entries = parse_refs(path)
        out += ["## 第 %d 章（%d 条）" % (int(n), len(entries)), ""]
        for e in entries:
            line = "- **%s**｜%s｜%s｜%s｜%s" % (
                e["id"], LEVEL_LABEL.get(e["level"], e["level"]), e["title"],
                e["author_or_org"], e["version_or_date"] or "—")
            out.append(line)
            out.append("  - 支撑：%s" % (e["supports"] or "—"))
            if e["url"]:
                out.append("  - 链接：%s ｜ 访问日期 %s%s" % (
                    e["url"], e["accessed"] or "—",
                    " ｜ 归档 %s" % e["archive_url"] if e["archive_url"] else ""))
            else:
                out.append("  - 链接：**待核验**（%s，访问日期 %s）" % (e["status"], e["accessed"] or "—"))
            if e.get("note"):
                out.append("  - 备注：%s" % e["note"])
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "normalize":
        normalize()
    elif cmd == "check":
        sys.exit(check())
    elif cmd == "pending":
        pending()
    elif cmd == "appendix":
        print(appendix())
    else:
        print(__doc__)
        sys.exit(2)
