#!/usr/bin/env bash
# 引用闸门：字段完整性、编号闭环、链接可达性、版本一致性
# 用法：./hack/check-references.sh [--links]
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== 引用登记字段与角标闭环 =="
python hack/book_tools.py check

echo "== 池外候选（pending_url，需季度复核） =="
python hack/book_tools.py pending | tee /tmp/pending_refs.txt
echo "待核验条数: $(wc -l < /tmp/pending_refs.txt)"

if [[ "${1:-}" == "--links" ]]; then
  echo "== 链接可达性（需安装 lychee 或 curl） =="
  python - <<'PY' > /tmp/refs_urls.txt
import sys, glob
sys.path.insert(0, 'hack')
import book_tools as b
for f in glob.glob('references/ch*.yaml'):
    for e in b.parse_refs(f):
        if e.get('url','').startswith('http'):
            print(e['url'])
PY
  if command -v lychee >/dev/null 2>&1; then
    lychee --no-progress /tmp/refs_urls.txt
  else
    echo "lychee 未安装，用 curl 抽样核验（UA + HTTP/1.1）"
    UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
    sort -u /tmp/refs_urls.txt | head -40 | while read -r u; do
      c=$(curl -sS -L -o /dev/null -w "%{http_code}" --http1.1 --max-time 20 -A "$UA" "$u" 2>/dev/null || echo 000)
      echo "$c $u"
    done
  fi
fi

echo "== 引用闸门：通过（链接可达性以附录 I 与 _verified.md 的复核记录为准） =="
