# -*- coding: utf-8 -*-
"""
《今日说法》影视仓清单 · 每日增量更新脚本

做什么：
  1. 读 jrsf_list.json（单卡片多线路：顶部按年份切线路）
  2. 从央视接口取最近若干期节目
  3. 逐期解析出 m3u8 直链（并统一改写到国内可用的稳定 CDN + 实测校验）
  4. 按 (播出日期, 清洗后标题) 去重，只把新节目追加进去
  5. 出现新一年（如 2027）时，自动新增一条年份线路
  6. 顺手修复历史条目里不可达的 CDN 域名
  7. 更新卡片上的期数 / 年份范围，写回 jrsf_list.json

只依赖 Python 标准库，GitHub Actions 里不用装任何包。

关于 CDN 域名（重要）：
  vdn 接口返回的 hls_url 是按【请求方 IP】做 CDN 调度的。GitHub Actions 的
  机房在海外，常被调度到 hls.cntv.cdn20.com 这类节点，而该域名对普通请求整域
  return 403（连根路径 / 都是 403），放进清单就是国内播放器黑屏。
  实测同一 GUID 把域名换成 hls.cntv.lxdns.com / newcntv.qcloudcdn.com 即 200 可播，
  所以这里统一改写到白名单域名，并做一次 #EXTM3U 探活兜底。
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

# ---------------- 配置 ----------------
DATA_FILE = os.environ.get("DATA_FILE", "jrsf_list.json")   # 清单文件
COLUMN_ID = "TOPC1451464665008914"                          # 今日说法栏目ID
PAGES = int(os.environ.get("PAGES") or 2)                   # 抓前几页（每页100条）
PAGE_SIZE = 100
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
TIMEOUT = 25

# 国内稳定可播的 HLS 节点，按优先级排列（换序即可换主力节点）
PREFERRED_HOSTS = ("hls.cntv.lxdns.com", "newcntv.qcloudcdn.com")

LIST_API = ("https://api.cntv.cn/NewVideo/getVideoListByColumn"
            "?id={cid}&n={n}&sort=desc&p={p}&mode=0&serviceId=tvcctv")
VDN_API = "https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do?pid={guid}"

# 形如 https://<host>/asp/hls/main/0303000a/3/default/<guid>/main.m3u8?maxbr=2048
HLS_RE = re.compile(r"^(https?)://([^/]+)(/asp/hls/main/\S*)$")


# ---------------- 网络 ----------------
def http_json(url, retry=2):
    last = None
    for i in range(retry + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Referer": "https://tv.cctv.com/",
                "Accept": "*/*",
            })
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except Exception as e:
            last = e
            if i < retry:
                time.sleep(2)
    print(f"  [warn] 请求失败 {url[:80]} -> {last}", file=sys.stderr)
    return None


def probe_hls(url, timeout=10):
    """探活：GET 一下 master.m3u8，看是不是正经的 #EXTM3U"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Referer": "https://tv.cctv.com/",
            "Accept": "*/*",
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            head = r.read(64)
        return head.lstrip().startswith(b"#EXTM3U")
    except Exception:
        return False


def rewrite_host(url, prefer_zero=True):
    """只改域名，不做网络请求（用于批量修历史数据）"""
    m = HLS_RE.match(url or "")
    if not m:
        return url
    scheme, host, path = m.groups()
    if host in PREFERRED_HOSTS:
        return url
    return f"{scheme}://{PREFERRED_HOSTS[0]}{path}" if prefer_zero else url


def normalize_hls(url):
    """把调度返回的 CDN 域名改写到白名单，并实测哪一个真的能播"""
    m = HLS_RE.match(url or "")
    if not m:
        return url                      # 不是标准 hls 形态，原样返回
    scheme, host, path = m.groups()

    cands = [f"{scheme}://{h}{path}" for h in PREFERRED_HOSTS]
    if host not in PREFERRED_HOSTS:
        cands.append(url)               # 原地址留作兜底
    elif url not in cands:
        cands.insert(0, url)

    for c in cands:
        if probe_hls(c):
            if c != url:
                print(f"  [cdn] 改写 {host} -> {urllib.parse.urlparse(c).netloc}")
            return c

    print(f"  [warn] 所有节点探活失败，仍保留首选域名：{cands[0][:90]}", file=sys.stderr)
    return cands[0]


# ---------------- 文本清洗 ----------------
def clean_title(title):
    """剥掉《今日说法》、开头8位日期、'今日说法 2009年 第360期' 之类前缀"""
    t = (title or "").strip()
    t = t.replace("《今日说法》", "").replace("[今日说法]", "")
    t = re.sub(r"^\s*\d{8}\s*", "", t)                            # 开头 8 位日期
    t = re.sub(r"^\s*今日说法\s*\d{4}\s*年\s*第\s*\d+\s*期\s*", "", t)
    t = re.sub(r"^\s*今日说法\s*", "", t)                          # 裸前缀
    t = t.replace("\u3000", " ").strip()
    # 集名里不能出现分隔符，替换成全角
    t = t.replace("#", "＃").replace("$", "＄")
    return t or "未命名"


def episode_name(year, date_str, title):
    """集名格式：2026-11.17 标题"""
    mmdd = date_str[5:].replace("-", ".")   # 11.17
    return f"{year}-{mmdd} {title}"


# ---------------- 清单读写 ----------------
def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_lines(card):
    """把 vod_play_from / vod_play_url 拆成 {年份: [(集名, 地址)]}"""
    froms = (card.get("vod_play_from") or "").split("$$$")
    urls = (card.get("vod_play_url") or "").split("$$$")
    lines = {}
    for name, seg in zip(froms, urls):
        year = re.sub(r"\D", "", name) or name
        eps = []
        for item in (seg.split("#") if seg else []):
            if "$" not in item:
                continue
            ep_name, _, ep_url = item.partition("$")
            if ep_name and ep_url:
                eps.append([ep_name, ep_url])
        lines[year] = eps
    return lines


def ep_key(ep_name):
    """从集名 '2026-11.17 标题' 还原去重键 (日期, 标题)"""
    m = re.match(r"^(\d{4})-(\d{2})\.(\d{2})\s+(.*)$", ep_name)
    if not m:
        return (ep_name, "")
    y, mm, dd, title = m.groups()
    return (f"{y}-{mm}-{dd}", title.strip())


def dump_lines(card, lines):
    """按年份升序写回卡片"""
    years = sorted([y for y in lines if y.isdigit()], key=int)
    card["vod_play_from"] = "$$$".join(f"{y}年" for y in years)
    card["vod_play_url"] = "$$$".join(
        "#".join(f"{n}${u}" for n, u in lines[y]) for y in years
    )
    total = sum(len(lines[y]) for y in years)
    return years, total


def heal_lines(lines):
    """批量修复历史条目里非白名单的 CDN 域名，返回改动条数"""
    fixed = 0
    for year, eps in lines.items():
        for i, (name, url) in enumerate(eps):
            new = rewrite_host(url)
            if new != url:
                print(f"  [heal] {name} {urllib.parse.urlparse(url).netloc} -> "
                      f"{urllib.parse.urlparse(new).netloc}")
                eps[i][1] = new
                fixed += 1
    return fixed


# ---------------- 抓取 ----------------
def fetch_recent():
    """返回 [(year, date_str, title, guid)]，按时间倒序"""
    out = []
    for p in range(1, PAGES + 1):
        url = LIST_API.format(cid=COLUMN_ID, n=PAGE_SIZE, p=p)
        d = http_json(url)
        if not d:
            continue
        lst = ((d.get("data") or {}).get("list")) or []
        if not lst:
            break
        for it in lst:
            t = (it.get("time") or "").strip()
            guid = (it.get("guid") or "").strip()
            if not t or not guid:
                continue
            date_str = t[:10]
            year = date_str[:4]
            out.append((year, date_str, clean_title(it.get("title")), guid))
        time.sleep(0.6)
    return out


def resolve_hls(guid):
    """guid -> m3u8 直链（已做 CDN 改写 + 探活）"""
    d = http_json(VDN_API.format(guid=guid))
    if not d:
        return ""
    u = (d.get("hls_url") or "").strip()
    if not u:
        return ""
    return normalize_hls(u)


# ---------------- 主流程 ----------------
def main():
    data = load_data()
    card = data["list"][0]
    lines = parse_lines(card)

    # 先把历史条目里不可达的 CDN 域名修掉
    healed = heal_lines(lines)

    # 已有去重键
    existing = set()
    for year, eps in lines.items():
        for n, _ in eps:
            existing.add(ep_key(n))

    recent = fetch_recent()
    print(f"接口返回 {len(recent)} 条")

    added = 0
    for year, date_str, title, guid in recent:
        key = (date_str, title)
        if key in existing:
            continue
        hls = resolve_hls(guid)
        if not hls:
            print(f"  [skip] 取不到播放地址：{date_str} {title}")
            continue
        name = episode_name(year, date_str, title)
        if year not in lines:                      # ← 新的一年自动加线路
            lines[year] = []
            print(f"  [新线路] 新增 {year}年")
        lines[year].append([name, hls])
        existing.add(key)
        added += 1
        print(f"  [新增] {name}")
        time.sleep(0.4)

    # 年份内按日期升序（旧→新）
    for y in lines:
        lines[y].sort(key=lambda e: ep_key(e[0]))

    years, total = dump_lines(card, lines)

    # 卡片元信息同步
    if years:
        first, last = years[0], years[-1]
        span = first if first == last else f"{first}-{last}"
        card["vod_name"] = f"今日说法 历年({span})"
        card["vod_year"] = span
        card["vod_remarks"] = f"{total}期"
        card["vod_content"] = (
            f"《今日说法》历年节目合集，共{total}期，"
            f"顶部线路按年份切换，年份内按播出日期排序。央视网官方源。"
        )

    if not added and not healed:
        print("✅ 没有新节目，文件不改动")
        return 0

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print(f"✅ 本次新增 {added} 期、修复 {healed} 条域名，"
          f"现共 {total} 期，年份：{years[0]}–{years[-1]}（{len(years)}条线路）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
