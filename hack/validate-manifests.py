#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P5 清单预检：把全书物化 YAML 按「内置资源 / CRD 实例 / Helm 模板 / 纯配置」逐文档拆分。

为什么需要这一步：
  `examples/by-chapter/` 里的清单来自 31 章增量，混有 Helm 模板（`{{ ... }}`，不是合法 YAML）、
  Kustomization、kind Cluster 配置，以及 Argo / Prometheus / Gateway API / Kyverno 等 CRD 实例。
  把它们不加区分地丢给 kubeconform 或 `kubectl apply --dry-run=server` 会产生大量假阳性。
  本脚本按 apiVersion group 白名单拆成逐文档文件，让 CI 只对「内置资源」做严格校验。

输出（默认 build/manifests/）：
  builtin/   内置资源，逐文档一份 YAML —— kubeconform / server dry-run 的输入
  crd/       CRD 实例与工具 CRD —— 只做语法与结构断言（需装对应 CRD 才能进集群）
  template/  Helm 模板原文 —— 由 helm template 渲染后另行复验
  other/     无 kind 的配置（values.yaml、Chart.yaml、规则测试等）
  _index.tsv / builtin.txt / crd.txt / template.txt  索引与文件列表

用法：
  python hack/validate-manifests.py [--out DIR] [--no-clean]
  python hack/validate-manifests.py --out "$RUNNER_TEMP/manifests"

依赖：PyYAML 可选。存在时做真正的 YAML 解析与重排；不存在时降级为按 `---` 切分原文，
      语法与 schema 校验交由 kubeconform / kube-apiserver（它们才是权威解析器）。
"""
import argparse
import glob
import os
import re
import shutil
import sys

try:
    import yaml
except ImportError:
    yaml = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_GLOBS = [
    "examples/by-chapter/**/*.yaml",
    "examples/by-chapter/**/*.yml",
    "examples/order-demo/deploy/base/*.yaml",
]

# Kubernetes 内置 API group（不含任何第三方 CRD）
BUILTIN_GROUPS = {
    "core", "apps", "batch", "autoscaling", "policy", "networking.k8s.io",
    "rbac.authorization.k8s.io", "scheduling.k8s.io", "storage.k8s.io",
    "admissionregistration.k8s.io", "apiextensions.k8s.io",
    "coordination.k8s.io", "certificates.k8s.io", "discovery.k8s.io",
    "events.k8s.io", "node.k8s.io", "flowcontrol.apiserver.k8s.io",
    "authentication.k8s.io", "authorization.k8s.io", "resource.k8s.io",
}

DOC_SEP = re.compile(r"(?m)^---\s*$")
TEMPLATE = re.compile(r"\{\{")
CATEGORIES = ("builtin", "crd", "template", "other")


def group_of(api_version):
    if "/" in api_version:
        return api_version.split("/", 1)[0]
    return "core"  # v1


def flat_name(relpath):
    return relpath.replace("\\", "__").replace("/", "__")


def raw_docs(text):
    """无 PyYAML 时的降级：按文档分隔符切原文，不做语法判断。"""
    parts = DOC_SEP.split(text)
    return [p.strip() for p in parts if p.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "manifests"))
    ap.add_argument("--no-clean", action="store_true", help="不清空输出目录")
    args = ap.parse_args()
    out = os.path.abspath(args.out)

    if not args.no_clean and os.path.isdir(out):
        shutil.rmtree(out)
    for c in CATEGORIES:
        os.makedirs(os.path.join(out, c), exist_ok=True)

    files = sorted({p for g in SRC_GLOBS
                    for p in glob.glob(os.path.join(ROOT, g), recursive=True)})
    if not files:
        print("未找到任何 YAML，检查 examples/by-chapter 是否已物化", file=sys.stderr)
        return 2

    index, errors, counts = [], [], {c: 0 for c in CATEGORIES}
    counters = {c: 0 for c in CATEGORIES}

    for src in files:
        rel = os.path.relpath(src, ROOT).replace("\\", "/")
        text = open(src, encoding="utf-8").read()
        parsed = None
        if yaml is not None:
            try:
                parsed = [d for d in yaml.safe_load_all(text) if d is not None]
            except Exception as exc:
                if TEMPLATE.search(text):
                    cat = "template"
                else:
                    errors.append((rel, "YAML 解析失败：%s" % str(exc).splitlines()[0]))
                    continue
        else:
            if TEMPLATE.search(text):
                parsed = None
            else:
                parsed = raw_docs(text)

        if parsed is None:  # Helm 模板：整文件保留原文
            counters["template"] += 1
            name = flat_name(rel)
            dest = os.path.join(out, "template", name)
            with open(dest, "w", encoding="utf-8", newline="\n") as f:
                f.write(text.rstrip() + "\n")
            index.append(("template", rel, 0, "-", "-", dest))
            counts["template"] += 1
            continue

        for i, doc in enumerate(parsed, 1):
            if yaml is None:
                # 降级模式：doc 是原文字符串，用正则取字段
                m_api = re.search(r"(?m)^apiVersion:\s*['\"]?([^'\"\s]+)", doc)
                m_kind = re.search(r"(?m)^kind:\s*['\"]?([^'\"\s]+)", doc)
                api = m_api.group(1) if m_api else ""
                kind = m_kind.group(1) if m_kind else ""
                body = doc
                is_dict = True
            else:
                if not isinstance(doc, dict):
                    api = kind = ""
                    body = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
                    is_dict = False
                else:
                    api = str(doc.get("apiVersion") or "")
                    kind = str(doc.get("kind") or "")
                    body = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
                    is_dict = True

            if is_dict and api and kind:
                cat = "builtin" if group_of(api) in BUILTIN_GROUPS else "crd"
            else:
                cat = "other"

            counters[cat] += 1
            stem = os.path.splitext(flat_name(rel))[0]
            name = "%s-d%02d.yaml" % (stem, i)
            dest = os.path.join(out, cat, name)
            with open(dest, "w", encoding="utf-8", newline="\n") as f:
                f.write(body.rstrip() + "\n")
            index.append((cat, rel, i, api or "-", kind or "-", dest))
            counts[cat] += 1

    with open(os.path.join(out, "_index.tsv"), "w", encoding="utf-8", newline="\n") as f:
        f.write("category\tsource\tdoc\tapiVersion\tkind\toutput\n")
        for row in index:
            f.write("\t".join(str(x) for x in row[:5]) + "\t" +
                    os.path.relpath(row[5], ROOT).replace("\\", "/") + "\n")
    for c in CATEGORIES:
        with open(os.path.join(out, c + ".txt"), "w", encoding="utf-8", newline="\n") as f:
            for row in index:
                if row[0] == c:
                    f.write(os.path.relpath(row[5], ROOT).replace("\\", "/") + "\n")

    print("YAML 源文件 %d 个，拆出文档 %d 份" % (len(files), len(index)))
    print("分类：" + "  ".join("%s=%d" % (c, counts[c]) for c in CATEGORIES))
    print("解析器：%s" % ("PyYAML %s" % yaml.__version__ if yaml else "降级（按 --- 切分，语法交给 kubeconform / apiserver）"))
    print("输出：%s" % out)
    if errors:
        for rel, why in errors:
            print("  ERR %s：%s" % (rel, why), file=sys.stderr)
        print("语法错误 %d 处" % len(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
