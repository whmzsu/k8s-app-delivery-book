#!/usr/bin/env bash
# 全书一致性闸门：九项横扫（术语 / 版本 / YAML 字段 / 回滚命令 / tag / 坐标 / 钩子 / 检查清单 / README 发版元数据）
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
python hack/book_tools.py appendix --stdout > /tmp/appendix_I_check.md
if diff -q appendices/附录I-参考文献.md /tmp/appendix_I_check.md >/dev/null; then
  echo "附录 I 与 references/*.yaml 一致"
else
  echo "!! 附录 I 已过期，请运行：python hack/book_tools.py appendix"
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

echo "== 7. 插图引用可达（Markdown 正常但成品缺图的防线） =="
# v1.1.0 的教训：mermaid 块在 Markdown 里看得见，在 PDF/EPUB/DOCX 里是裸文本，
# 六道闸门全没抓到。插图用 ![](路径) 后必须确认文件真实存在，且不是遗留的
# 不可渲染语法（mermaid / ASCII art 混入图片位）。
python - <<'PY'
import glob, os, re, sys
bad, total = [], 0
for f in sorted(glob.glob('chapters/*.md')) + sorted(glob.glob('appendices/*.md')):
    t = open(f, encoding='utf-8').read()
    for m in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', t):
        total += 1
        src = m.group(2).strip()
        if src.startswith(('http://', 'https://')):
            bad.append((f, src, '外链图不入库，构建期无法内联'))
            continue
        p = os.path.normpath(os.path.join(os.path.dirname(f), src))
        if not os.path.exists(p):
            bad.append((f, src, '文件不存在'))
        elif not src.endswith('.svg'):
            bad.append((f, src, '只接受 SVG（三形态共用矢量源）'))
print('插图引用 %d 处，问题 %d' % (total, len(bad)))
for f, src, why in bad:
    print('  ', f, '->', src, ':', why)
sys.exit(1 if bad else 0)
PY
echo "全部插图可达"
# mermaid 在成品里不可渲染：出现即说明有人写了构建管线吃不到的东西
if grep -rn '^```mermaid' chapters/ appendices/ >/dev/null 2>&1; then
  echo "!! 发现 mermaid 块：构建器不渲染它，成品会是裸文本。改用 SVG + ![]()"
  grep -rn '^```mermaid' chapters/ appendices/
  exit 1
fi

echo "== 8. 表格列口径（命令内管道必须转义） =="
# PDF 里「部分行右边多一列」的根因：表格单元格里的 shell 管道 / grep 分支 /
# PromQL 正则自带 `|`，早期解析器直接 split("|") 就把它当列分隔符。
# 这里直接复用构建器的 split_table_cells，保证「闸门口径 == 成品口径」。
python - <<'PY'
import glob, re, sys
sys.path.insert(0, 'hack')
from build_dist import split_table_cells

bad = []
files = sorted(glob.glob('chapters/ch*.md')) + sorted(glob.glob('appendices/*.md'))
for f in files:
    lines = open(f, encoding='utf-8').read().split('\n')
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith('|') and i + 1 < len(lines) and \
           re.match(r'^\s*\|[-: |]+\|\s*$', lines[i + 1]):
            ncol = len(split_table_cells(lines[i]))
            j = i + 2
            while j < len(lines) and lines[j].lstrip().startswith('|'):
                row = lines[j]
                got = len(split_table_cells(row))
                if got != ncol:
                    bad.append(f'{f}:{j+1} 逻辑列 {got} != 表头 {ncol}')
                # 反引号内的裸管道即便列数侥幸对齐，在 GitHub / GFM 下仍是坏表
                in_code = False
                for k, ch in enumerate(row):
                    if ch == '`':
                        in_code = not in_code
                    elif ch == '|' and in_code and (k == 0 or row[k-1] != '\\'):
                        bad.append(f'{f}:{j+1} 反引号内有未转义管道（应写 \\|）')
                        break
                j += 1
            i = j
        else:
            i += 1
if bad:
    print('\n'.join(bad[:40]))
    print(f'!! 共 {len(bad)} 处表格列口径问题')
    sys.exit(1)
print('全部表格列数一致、命令内管道已转义')
PY

echo "== 9. README 下载表版本与插图数（防发版漂移） =="
# 教训：README 曾停在 v1.2.0 / 460 页 / 6 张图，而成品已到 v1.4.0 / 478 页 / 14 处插图，
# 读者从仓库门面下载会拿到两代前的文件。版本号以根目录 VERSION 为唯一真相，
# 插图数直接数全书 SVG 引用；页数与文件大小不入库、不校验，故不写进 README。
python - <<'PY'
import glob, os, re, sys

bad = []
if not os.path.exists('VERSION'):
    bad.append('缺 VERSION 文件（版本号唯一真相）')
    ver = None
else:
    ver = open('VERSION', encoding='utf-8').read().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', ver):
        bad.append('VERSION 格式非法：%r（应为 X.Y.Z）' % ver)

readme = open('README.md', encoding='utf-8').read()
m = re.search(r'## 下载成品(.*?)(?=\n## )', readme, re.S)
sec = m.group(1) if m else ''
if not sec:
    bad.append('README 找不到「下载成品」段')

if ver and sec:
    names = re.findall(r'`journey-of-a-change-v[\d.]+\.(?:pdf|epub|docx)`', sec)
    if len(names) != 3:
        bad.append('下载表应有 3 个成品文件名，实测 %d 个' % len(names))
    for n in names:
        if '-v%s.' % ver not in n:
            bad.append('文件名版本与 VERSION=%s 不一致：%s' % (ver, n))
    for v in sorted(set(re.findall(r'v(\d+\.\d+\.\d+)', sec))):
        if v != ver:
            bad.append('「下载成品」段残留旧版本号 v%s' % v)

dm = re.search(r'\*\*(\d+) 处矢量插图\*\*', readme)
if not dm:
    bad.append('README 未声明「N 处矢量插图」')
else:
    declared = int(dm.group(1))
    actual = 0
    for f in glob.glob('chapters/ch*.md') + glob.glob('appendices/*.md') + ['全书目录.md']:
        actual += len(re.findall(r'!\[[^]]*\]\([^)]*\.svg\)',
                                 open(f, encoding='utf-8').read()))
    if declared != actual:
        bad.append('README 声明 %d 处插图，全书实际 %d 处' % (declared, actual))

if bad:
    print('\n'.join('  ' + b for b in bad))
    sys.exit(1)
print('下载表版本 v%s 与 VERSION 一致，插图数与全书 SVG 引用一致' % ver)
PY

echo "== 全书一致性闸门：通过 =="
