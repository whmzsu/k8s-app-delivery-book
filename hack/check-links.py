#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""权威来源链接可达性复核（背书体系 10.5 的季度复核自动化）。

从 references/ch*.yaml 抽取所有已登记 URL，去重后并发核验，输出 TSV 报告。
外链会因反爬、临时维护、区域限制返回 4xx/5xx，因此这是「监控型」检查：
失败率超过阈值才判失败，且失败清单总是写进 job summary 与 artifact。

用法：python hack/check-links.py [--max-fail-rate 0.08] [--workers 6] [--report build/link-report.tsv]
"""
import argparse
import concurrent.futures
import glob
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import book_tools  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def _curl(url, timeout):
    try:
        r = subprocess.run(
            ["curl", "-sS", "-L", "-o", "/dev/null", "-w", "%{http_code}",
             "--http1.1", "--max-time", str(timeout), "-A", UA, url],
            capture_output=True, text=True, timeout=timeout + 10)
        return (r.stdout or "000").strip().splitlines()[-1]
    except Exception:
        return "000"


def probe(url):
    """先探一次，`000` 与 5xx 再试一次。

    这是监控型检查，最怕把本机代理抖动或 TLS 握手的偶发失败当成
    「链接已死」——一份误报率高的报告没人会看，等于没做（实测
    `keda.sh` 首次 000、重试立即 200）。4xx 不重试：403/404 是确定性
    结论，重试只是浪费对方配额。
    """
    code = _curl(url, 25)
    if code == "000" or code.startswith("5"):
        print("  retry %s（首次 %s）" % (url, code))
        code = _curl(url, 40)
    return url, code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-fail-rate", type=float, default=0.08)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0, help="仅核验前 N 条（本地抽样用，CI 不设）")
    ap.add_argument("--report", default=os.path.join(ROOT, "build", "link-report.tsv"))
    args = ap.parse_args()

    urls, pending = set(), 0
    for f in sorted(glob.glob(os.path.join(ROOT, "references", "ch*.yaml"))):
        for e in book_tools.parse_refs(f):
            if e.get("url", "").startswith("http"):
                urls.add(e["url"])
            if e.get("status") == "pending_url":
                pending += 1
    urls = sorted(urls)
    total = len(urls)
    if args.limit:
        urls = urls[:args.limit]
    print("已登记 URL %d 条（去重），待核验候选 %d 条，本次核验 %d 条" % (
        total, pending, len(urls)))

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for url, code in pool.map(probe, urls):
            ok = code.startswith(("2", "3"))
            results.append((url, code, "OK" if ok else "FAIL"))

    failed = [r for r in results if r[2] == "FAIL"]
    rate = len(failed) / len(results) if results else 0.0
    os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
    with open(args.report, "w", encoding="utf-8", newline="\n") as f:
        f.write("status\tcode\turl\n")
        for url, code, st in results:
            f.write("%s\t%s\t%s\n" % (st, code, url))

    print("可达 %d / 失败 %d / 失败率 %.1f%%（阈值 %.1f%%）" % (
        len(results) - len(failed), len(failed), rate * 100, args.max_fail_rate * 100))
    for url, code, _ in failed[:20]:
        print("  FAIL %s %s" % (code, url))

    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("\n### 背书链接复核\n\n")
            f.write("- 已登记 URL：%d 条；待核验候选（pending_url）：%d 条\n" % (len(results), pending))
            f.write("- 失败：%d 条（失败率 %.1f%%，阈值 %.1f%%）\n\n" % (
                len(failed), rate * 100, args.max_fail_rate * 100))
            for url, code, _ in failed[:30]:
                f.write("- `%s` %s\n" % (code, url))

    return 1 if rate > args.max_fail_rate else 0


if __name__ == "__main__":
    raise SystemExit(main())
