# Runbook：CoreDNS 解析失败

> 来源：ch19（§19.2.4 DNS 解析完整链路、CL-19-05）。
> 触发：Pod 内 `Temporary failure in name resolution` / DNS 超时；Service 短名偶发命中不了。

## 四跳链路与二分判据

```
Pod → kube-dns(ClusterIP:53) → CoreDNS Pod(OOM/重启) → 上游 DNS(VPC DNS)
```
- **内不通、外通** → 查第 1–3 跳
- **外不通、内通** → 查第 4 跳（上游 / VPC DNS）
- **全不通** → 先查第 1–2 跳

## 逐步定位命令

```bash
# 第 1 跳：Pod 自己的 resolv.conf（默认 search 三域 + ndots:5）
kubectl -n order-demo-dev exec deploy/gateway -- cat /etc/resolv.conf
#   通过标准：search 三域 + options ndots:5；不符先查 dnsPolicy/dnsConfig

# 第 2 跳：kube-dns Endpoint 是否存在、NetworkPolicy 是否放通 UDP/53
kubectl -n kube-system get endpoints kube-dns

# 第 3 跳：CoreDNS 是否 OOM / 重启循环
kubectl -n kube-system get pods -l k8s-app=kube-dns

# 第 4 跳：外部域名对照（内通外不通时）
kubectl run -it --rm dns-debug --image=busybox:1.36 --restart=Never -- nslookup order-demo.example.com
```

## 指标判读（ch19:506-512）

```bash
POD=$(kubectl -n kube-system get pods -l k8s-app=kube-dns -o name | head -1 | cut -d/ -f2)
kubectl -n kube-system port-forward "${POD}" 9153:9153 >/dev/null 2>&1 &
PF=$!; sleep 1
curl -s 127.0.0.1:9153/metrics | grep -E '^coredns_(dns_responses_total|forward_requests_total)'
kill "${PF}" 2>/dev/null || true
```
- `SERVFAIL` 持续增长 → 第 4 跳上游问题；
- 大量 `NXDOMAIN` 且集中在追加了 search 域后缀的名字 → `ndots:5` 放大复发（ch19:312-313）。

## 易踩的反模式

- 默认拒绝 egress 后最先「看起来像 DNS 挂了」的，往往是 NetworkPolicy 没放通 `kube-dns:53`（ch19:308、572）。先放通 `allow-dns` 再看。
- 不要为「DNS 有点慢」直接改 `dnsPolicy: Default`——那会绕过 `cluster.local` 解析，Service 短名全部失效（ch19:516）。

## 关联

- 横向判读与内外二分见 `docs/ops-quickref-node-and-remediation.md` A.3。
