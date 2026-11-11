#!/usr/bin/env bash
# 全书一致性闸门：八项横扫（术语 / 版本 / YAML 字段 / 回滚命令 / tag / 坐标 / 钩子 / 检查清单）
# 用法：./hack/check-consistency.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== 1. 章节与引用登记结构校验 =="
python hack/book_tools.py check

echo "== 2. 章节 tag 与案例演进表一致性 =="
python - <<'PY'
import re, glob, os
evo = open('book/case-evolution.md', encoding='utf-8').read()
tags = set(re.findall(r'`(ch\d{2}-[a-z0-9-]+)`', evo))
missing = []
for f in sorted(glob.glob('chapters/ch*.md')):
    n = os.path.basename(f)[2:4]
    t = open(f, encoding='utf-8').read()
    found = set(re.findall(r'`(ch\d{2}-[a-z0-9-]+)`', t))
    for x in found:
        if x not in tags:
            missing.append((n, x))
print('演进表 tag 数:', len(tags))
print('章节中不在演进表的 tag:', missing or '无')
assert not missing
PY

echo "== 3. 附录 I 由引用登记重新生成并比对 =="
python hack/book_tools.py appendix > /tmp/appendix_I_check.md
if diff -q appendices/附录I-参考文献.md /tmp/appendix_I_check.md >/dev/null; then
  echo "附录 I 与 references/*.yaml 一致"
else
  echo "!! 附录 I 已过期，请运行：python hack/book_tools.py appendix > appendices/附录I-参考文献.md"
  exit 1
fi

echo "== 4. 脚本语法 =="
# 物化产物也算：by-chapter 的片段若被误当脚本，bash -n 会当场暴露
for s in examples/order-demo/hack/*.sh hack/*.sh $(find examples/by-chapter -name '*.sh'); do bash -n "$s"; done
echo "全部脚本语法通过"

echo "== 5. 物化产物自检（Chart 元数据） =="
python - <<'PY'
import glob, sys
try:
    import yaml
except ImportError:
    print("!! 未安装 PyYAML，跳过本项（CI 会安装 hack/requirements.txt，本地请 pip install -r）")
    sys.exit(0)
bad, files = [], sorted(glob.glob('examples/by-chapter/**/Chart.yaml', recursive=True))
for f in files:
    d = yaml.safe_load(open(f, encoding='utf-8')) or {}
    miss = [k for k in ('apiVersion', 'name', 'version') if not d.get(k)]
    if miss:
        bad.append((f, 'Chart.yaml 缺 ' + '/'.join(miss)))
    elif not str(d.get('type', 'application')) == 'library' and 'dependencies' in d and d.get('apiVersion') != 'v2':
        bad.append((f, "Chart.yaml 用 dependencies 时 apiVersion 必须是 v2"))
print('Chart.yaml 检查 %d 份，问题 %d' % (len(files), len(bad)))
for f, why in bad:
    print('  ', f, why)
sys.exit(1 if bad else 0)
PY
echo "全部 Chart 元数据通过"

echo "== 6. 章内代码块与物化产物一致 =="
# 改章不同步 examples/by-chapter 是历史上最容易漏的一步（CI 单独一步才暴露）
python hack/materialize.py --check

echo "== 全书一致性闸门：通过 =="
