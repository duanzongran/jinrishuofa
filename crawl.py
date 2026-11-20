# -*- coding: utf-8 -*-
"""
央视剧集 + 今日说法 · 每日增量更新脚本

流程：
  1. 读 jrsf_list.json（今日说法历年数据，按年份分线路）
  2. 调央视栏目接口取最近若干期，逐期解析 m3u8 直链
  3. 按 (播出日期, 清洗后标题) 去重，只追加新节目；出现新一年（如 2027）自动新建该年
  4. 重新生成 cctv_drama.js（电视剧目录来自 tv_catalog.json + 今日说法年份卡片）
     —— 首页两个分类：电视剧 / 今日说法，一年一卡
  5. 无新增则不改文件，有新增则提交 jrsf_list.json 与 cctv_drama.js

只依赖 Python 标准库，GitHub Actions 无需安装任何包。
"""

import json
import os
import re
import sys
import time
import urllib.request

# ---------------- 配置 ----------------
DATA_FILE = os.environ.get("DATA_FILE", "jrsf_list.json")     # 今日说法数据
TV_FILE = os.environ.get("TV_FILE", "tv_catalog.json")        # 电视剧目录
OUT_JS = os.environ.get("OUT_JS", "cctv_drama.js")           # 生成的源文件
COLUMN_ID = "TOPC1451464665008914"                            # 今日说法栏目ID
PAGES = int(os.environ.get("PAGES") or 3)                     # 抓前几页（每页100条）
PAGE_SIZE = 100
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
TIMEOUT = 25

LIST_API = ("https://api.cntv.cn/NewVideo/getVideoListByColumn"
            "?id={cid}&n={n}&sort=desc&p={p}&mode=0&serviceId=tvcctv")
VDN_API = "https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do?pid={guid}"

# 播放地址压缩：两条正常可播的主机（cnTV 会随机下发 cdn20 等坏主机，必须归一化）
HOSTS = ["https://newcntv.qcloudcdn.com", "https://hls.cntv.lxdns.com"]
TPL = "/asp/hls/main/0303000a/3/default/{guid}/main.m3u8?maxbr=2048"
G32 = re.compile(r"([0-9a-f]{32})")


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


# ---------------- 文本清洗 ----------------
def clean_title(title):
    t = (title or "").strip()
    t = t.replace("《今日说法》", "").replace("[今日说法]", "")
    t = re.sub(r"^\s*\d{8}\s*", "", t)
    t = re.sub(r"^\s*今日说法\s*\d{4}\s*年\s*第\s*\d+\s*期\s*", "", t)
    t = re.sub(r"^\s*今日说法\s*", "", t)
    t = t.replace("\u3000", " ").strip()
    t = t.replace("#", "＃").replace("$", "＄")
    return t or "未命名"


def episode_name(date_str, title):
    """集名格式：2026-11.17 标题"""
    mmdd = date_str[5:].replace("-", ".")
    return f"{date_str[:4]}-{mmdd} {title}"


# ---------------- 数据读写 ----------------
def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_lines(card):
    """vod_play_from / vod_play_url -> {年份: [(集名, 地址)]}"""
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
    m = re.match(r"^(\d{4})-(\d{2})\.(\d{2})\s+(.*)$", ep_name)
    if not m:
        return (ep_name, "")
    y, mm, dd, title = m.groups()
    return (f"{y}-{mm}-{dd}", title.strip())


def dump_lines(card, lines):
    years = sorted([y for y in lines if y.isdigit()], key=int)
    card["vod_play_from"] = "$$$".join(f"{y}年" for y in years)
    card["vod_play_url"] = "$$$".join(
        "#".join(f"{n}${u}" for n, u in lines[y]) for y in years
    )
    return years, sum(len(lines[y]) for y in years)


# ---------------- 抓取 ----------------
def fetch_recent():
    out = []
    for p in range(1, PAGES + 1):
        d = http_json(LIST_API.format(cid=COLUMN_ID, n=PAGE_SIZE, p=p))
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
            out.append((t[:10], clean_title(it.get("title")), guid))
        time.sleep(0.6)
    return out


def resolve_hls(guid):
    d = http_json(VDN_API.format(guid=guid))
    return ((d or {}).get("hls_url") or "").strip()


def host_url(guid, i):
    return HOSTS[i] + TPL.replace("{guid}", guid)


def verify(url, timeout=15):
    """真能播：m3u8 -> 变体 -> 首切片须是真 TS（0x47）且大于 1500 字节"""
    import urllib.parse as up
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Referer": "https://tv.cctv.com/"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "ignore")
        if "EXT-X-KEY" in body:                     # 加密切片，盒子多半解不开
            return False
        var = [l.strip() for l in body.splitlines() if l.strip() and not l.startswith("#")]
        if not var:
            return False
        vu = up.urljoin(url, var[0])
        with urllib.request.urlopen(urllib.request.Request(vu, headers={"User-Agent": UA,
                                        "Referer": "https://tv.cctv.com/"}), timeout=timeout) as r:
            vb = r.read().decode("utf-8", "ignore")
        seg = [l.strip() for l in vb.splitlines() if l.strip() and not l.startswith("#")]
        if not seg:
            return False
        su = up.urljoin(vu, seg[0])
        with urllib.request.urlopen(urllib.request.Request(su, headers={"User-Agent": UA,
                                        "Referer": "https://tv.cctv.com/"}), timeout=timeout) as r:
            head = r.read(3000)
        return len(head) > 1500 and head[0] == 0x47
    except Exception:
        return False


def pick_url(guid, hint=""):
    """拿到一个真实可播的地址：先试接口给的（若主机可信），再轮询两条正常主机"""
    cands = []
    m = G32.search(hint or "")
    if m and any((hint or "").startswith(h) for h in HOSTS):
        cands.append(hint)
    for i in range(len(HOSTS)):
        u = host_url(guid, i)
        if u not in cands:
            cands.append(u)
    for u in cands:
        if verify(u):
            return u
    return ""


# ---------------- 生成 js ----------------
def encode(url):
    """任何 cntv 主机的标准路径地址都归一化成两条正常主机的压缩形式"""
    m = G32.search(url or "")
    if not m:
        return [9, url]
    g = m.group(1)
    if "/asp/hls/main/0303000a/3/" in (url or ""):
        return [0, g]
    return [9, url]


JS_TPL = """// 央视剧集 + 今日说法 · FongMi QuickJS 源
// 首页分类：电视剧 / 今日说法，两个独立页面，卡片不混
// 本文件由 crawl.py 自动生成，请勿手改
import { Spider, page } from "catvod";

const PAGE_SIZE = 24;
const HOSTS = %s;
const TPL = "%s";
const TV = %s;
const JRSF = %s;
const ALL = TV.concat(JRSF);

function epUrl(c) {
    const h = c[0], g = c[1];
    if (h === 9 || !HOSTS[h]) return String(g);
    return HOSTS[h] + TPL.replace("{guid}", g);
}

function card(r, tid) {
    const o = { vod_id: (tid === "jrsf" ? "jrsf/" : "vod/") + r.id, vod_name: r.name, vod_remarks: r.remark, style: { type: "rect", ratio: 0.75 } };
    if (tid === "jrsf") o.vod_year = r.id.replace(/^y/, "");
    return o;
}

function detailVod(r, tid) {
    const o = card(r, tid);
    o.type_name = tid === "jrsf" ? "法治节目" : "电视剧";
    o.vod_play_from = "央视网";
    o.vod_content = r.name + "，" + r.remark + "（央视网）";
    o.vod_play_url = r.eps.map(function (e, i) {
        const nm = e[0] || (tid === "jrsf" ? "第" + (i + 1) + "期" : "第" + (i + 1) + "集");
        return nm + "$" + epUrl([e[1], e[2]]);
    }).join("#");
    return o;
}

function lookup(id) {
    const s = String(id);
    if (s.indexOf("jrsf/") === 0) {
        const r = JRSF.find(function (x) { return x.id === s.slice(5); });
        return r ? { r: r, tid: "jrsf" } : null;
    }
    const r = TV.find(function (x) { return x.id === s.replace(/^vod\\//, ""); });
    return r ? { r: r, tid: "tv" } : null;
}

export default class CctvAll extends Spider {
    homeContent(filter) {
        return { class: [{ type_id: "tv", type_name: "电视剧" }, { type_id: "jrsf", type_name: "今日说法" }] };
    }
    homeVideoContent() { return { list: TV.map(function (r) { return card(r, "tv"); }) }; }
    categoryContent(tid, pg, filter, extend) {
        const set = tid === "jrsf" ? JRSF : TV;
        const t = tid === "jrsf" ? "jrsf" : "tv";
        return page(set.map(function (r) { return card(r, t); }), pg || "1", PAGE_SIZE);
    }
    searchContent(key, quick, pg) {
        const q = String(key || "").trim().toLowerCase();
        if (!q) return page([], pg || "1", PAGE_SIZE);
        const items = ALL.filter(function (r) { return String(r.name).toLowerCase().includes(q); });
        return page(items.map(function (r) { return card(r, r.id.charAt(0) === "y" ? "jrsf" : "tv"); }), pg || "1", PAGE_SIZE);
    }
    detailContent(ids) {
        const list = [];
        for (const id of ids) {
            const x = lookup(id);
            if (x) list.push(detailVod(x.r, x.tid));
        }
        return { list: list };
    }
    playerContent(flag, id, vipFlags) {
        const url = String(id || "").trim();
        if (!/^https?:\\/\\//i.test(url)) return { parse: 0, msg: "无效播放地址" };
        return { parse: 0, jx: 0, url: url, header: "" };
    }
}
"""


def build_jrsf_cards(lines):
    cards = []
    for year in sorted([y for y in lines if y.isdigit()], key=int):
        eps = []
        for n, u in lines[year]:
            eps.append([n[:30], *encode(u)])
        cards.append({"id": "y" + year, "name": f"今日说法 {year}年",
                      "remark": f"{len(eps)}期", "eps": eps})
    return cards


def write_js(tv, jrsf):
    src = JS_TPL % (json.dumps(HOSTS), TPL,
                    json.dumps(tv, ensure_ascii=False, separators=(",", ":")),
                    json.dumps(jrsf, ensure_ascii=False, separators=(",", ":")))
    with open(OUT_JS, "w", encoding="utf-8") as f:
        f.write(src)
    return len(src)


# ---------------- 主流程 ----------------
def main():
    data = load_json(DATA_FILE)
    if not data:
        print(f"[fatal] 缺少 {DATA_FILE}", file=sys.stderr)
        return 1
    tv = load_json(TV_FILE, [])
    card = data["list"][0]
    lines = parse_lines(card)

    existing = set()
    for _, eps in lines.items():
        for n, _ in eps:
            existing.add(ep_key(n))

    # 1) 先修历史数据里主机不对的地址（例如 hls.cntv.cdn20.com，实测 403）
    fixed = 0
    for y, eps in lines.items():
        for i, (n, u) in enumerate(eps):
            if any(u.startswith(h) for h in HOSTS):
                continue
            m = G32.search(u or "")
            if not m:
                continue
            good = pick_url(m.group(1), u)
            if good:
                eps[i] = [n, good]
                fixed += 1
                print(f"  [修主机] {n[:26]}")
    if fixed:
        print(f"修正 {fixed} 条主机异常地址")

    recent = fetch_recent()
    print(f"接口返回 {len(recent)} 期")

    added = 0
    for date_str, title, guid in recent:
        key = (date_str, title)
        if key in existing:
            continue
        hls = pick_url(guid, resolve_hls(guid))
        if not hls:
            print(f"  [skip] 取不到可播地址：{date_str} {title}")
            continue
        year = date_str[:4]
        if year not in lines:
            lines[year] = []
            print(f"  [新年份卡片] 新增 {year} 年")
        lines[year].append([episode_name(date_str, title), hls])
        existing.add(key)
        added += 1
        print(f"  [新增] {episode_name(date_str, title)}")
        time.sleep(0.4)

    for y in lines:
        lines[y].sort(key=lambda e: ep_key(e[0]))

    years, total = dump_lines(card, lines)

    if years:
        first, last = years[0], years[-1]
        span = first if first == last else f"{first}-{last}"
        card["vod_name"] = f"今日说法 历年({span})"
        card["vod_year"] = span
        card["vod_remarks"] = f"{total}期"
        card["vod_content"] = (f"《今日说法》历年节目合集，共{total}期，"
                               f"顶部线路按年份切换，年份内按播出日期排序。央视网官方源。")

    jrsf = build_jrsf_cards(lines)
    size = write_js(tv, jrsf)

    if not added:
        print(f"✅ 没有新节目（今日说法 {total} 期 / {len(years)} 年，"
              f"js 已重建 {size} 字节）")
        return 0

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print(f"✅ 新增 {added} 期；今日说法现共 {total} 期 / {len(years)} 张年份卡，"
          f"js {size} 字节")
    return 0


if __name__ == "__main__":
    sys.exit(main())
