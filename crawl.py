#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CCTV《今日说法》节目单增量爬虫（纯标准库，无需 pip install）
=============================================================

数据源
    列表：https://api.cntv.cn/NewVideo/getVideoListByColumn?id=TOPC1451464665008914
          n=100 一页即可覆盖整月；接口的 d=YYYYMM 偶有跨月，故按 time 严格过滤。
    播放：https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/<guid>/main.m3u8?maxbr=2048
          实测与 vdn 接口返回的 hls_url 完全一致，故默认直连拼接；
          需要逐条校正时加 --resolve 或单独跑 --refresh。

用法
    python crawl.py                                  # 增量：抓最近 3 页，遇到已有日期即停
    python crawl.py --backfill                       # 全量建档：2009-08 至今（按月抓，约 2~3 分钟）
    python crawl.py --year 2026                      # 抓整年
    python crawl.py --year 2026 --month 11           # 抓单月
    python crawl.py --refresh                        # 校验已有地址，失效的重新解析
    python crawl.py --backfill --dry-run --limit 5   # 试跑：只打印，不写盘

输出 jrsf.json
    [{"name": "今日说法 2026-11-17 车顶跌落理赔之争",
      "date": "2026-11-17", "year": "2026",
      "vod": "https://...main.m3u8?maxbr=2048",
      "guid": "d0821f39332543119335d7825f6e5882",
      "pic": "https://p3.img.cctvpic.com/...jpg",
      "dur": "00:27:59", "desc": "本期节目主要内容：……"}]
    历史条目（只有 name/year/vod）原样保留，不删不改。
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date as _date

try:  # Windows 控制台默认 GBK，避免打印中文报错
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

JSON_FILE = "jrsf.json"

COLUMN_ID = "TOPC1451464665008914"
LIST_API = "https://api.cntv.cn/NewVideo/getVideoListByColumn"
VDN_API = "https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do?pid="
HLS_TPL = (
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/"
    "{guid}/main.m3u8?maxbr=2048"
)

START_YEAR, START_MONTH = 2009, 8   # 实测最早有数据的月份（2009-07 及以前为空）
PAGE_SIZE = 100                     # 接口单页上限实测 100 可用
RECENT_PAGES = 3                    # 增量模式翻页数（约 300 期，足够覆盖数月）
DESC_LIMIT = 100                    # 简介截断长度（控制 jrsf.json 体积）

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Referer": "https://tv.cctv.com/",
    "Accept": "*/*",
}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NUM_DATE_RE = re.compile(r"(\d{4})(\d{2})(\d{2})")
PREFIX_RE = re.compile(r"^《?今日说法》?\s*(?:\d{8})?\s*(.*)$")


def log(*args):
    print(*args, flush=True)


# --------------------------------------------------------------------------
# 网络
# --------------------------------------------------------------------------
def http_get(url, timeout=25, retries=3):
    """带重试的 GET，失败返回 None。"""
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception as exc:      # noqa: BLE001 - 网络异常统一重试
            last = exc
            if i < retries - 1:
                time.sleep(1.5 * (i + 1))
    log("    ! 请求失败: {} ({})".format(url, last))
    return None


def http_json(url, **kwargs):
    text = http_get(url, **kwargs)
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:                 # noqa: BLE001
        return None


# --------------------------------------------------------------------------
# 抓取
# --------------------------------------------------------------------------
def list_month(year, month):
    """取某月节目原始条目；请求失败返回 None，空月返回 []。"""
    url = "{}?id={}&n={}&p=1&sort=desc&d={:04d}{:02d}&serviceId=tvcctv".format(
        LIST_API, COLUMN_ID, PAGE_SIZE, year, month
    )
    data = http_json(url)
    if data is None:
        return None
    payload = data.get("data") or {}
    items = payload.get("list") if isinstance(payload, dict) else None
    tag = "{:04d}-{:02d}".format(year, month)
    return [x for x in (items or []) if str(x.get("time", ""))[:7] == tag]


def list_recent(pages, known):
    """从最新一页开始往前翻，遇到已有日期后停止，返回规范化条目列表。"""
    out, seen = [], set()
    for page in range(1, pages + 1):
        url = "{}?id={}&n={}&p={}&sort=desc&d=&serviceId=tvcctv".format(
            LIST_API, COLUMN_ID, PAGE_SIZE, page
        )
        data = http_json(url)
        if data is None:
            break
        payload = data.get("data") or {}
        items = payload.get("list") if isinstance(payload, dict) else None
        if not items:
            break
        stop = False
        for raw in items:
            item = to_item(raw)
            if not item or item["date"] in seen:
                continue
            seen.add(item["date"])
            out.append(item)
            if item["date"] in known:
                stop = True
        if stop:
            break
    return out


def to_item(raw):
    """把接口原始条目规范化；日期统一取 time 字段（老期目标题里没有日期）。"""
    if not isinstance(raw, dict):
        return None
    date = str(raw.get("time") or "")[:10]
    if not DATE_RE.match(date):
        m = NUM_DATE_RE.search(str(raw.get("title") or ""))
        if not m:
            return None
        date = "{}-{}-{}".format(*m.groups())

    title = re.sub(r"\s+", " ", str(raw.get("title") or "")).strip()
    m = PREFIX_RE.match(title)
    sub = re.sub(r"\s+", " ", m.group(1)).strip() if m else title
    name = ("今日说法 " + date + (" " + sub if sub else "")).strip()

    guid = str(raw.get("guid") or raw.get("id") or "").strip()
    desc = re.sub(r"\s+", " ", str(raw.get("brief") or "")).strip()
    if len(desc) > DESC_LIMIT:
        desc = desc[:DESC_LIMIT]

    return {
        "name": name,
        "date": date,
        "year": date[:4],
        "vod": HLS_TPL.format(guid=guid) if guid else "",
        "guid": guid,
        "pic": str(raw.get("image") or "").strip(),
        "dur": str(raw.get("length") or "").strip(),
        "desc": desc,
    }


def resolve_hls(guid):
    """通过 vdn 接口取真实 hls 地址，失败退回规律直链。"""
    if not guid:
        return ""
    data = http_json(VDN_API + urllib.parse.quote(guid), retries=2)
    if isinstance(data, dict):
        url = str(data.get("hls_url") or "").strip()
        if url.startswith("http"):
            return url
    return HLS_TPL.format(guid=guid)


# --------------------------------------------------------------------------
# 存储
# --------------------------------------------------------------------------
def item_date(item):
    d = str(item.get("date") or "")
    if DATE_RE.match(d):
        return d
    name = str(item.get("name") or "")
    m = re.search(r"\d{4}-\d{2}-\d{2}", name)
    if m:
        return m.group(0)
    m = NUM_DATE_RE.search(name)
    if m:
        return "{}-{}-{}".format(*m.groups())
    year = str(item.get("year") or "")
    return year + "-01-01" if re.match(r"^\d{4}$", year) else ""


def dedup_key(item):
    return item_date(item)


def load_items():
    if not os.path.exists(JSON_FILE):
        return []
    with open(JSON_FILE, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    if isinstance(data, dict):
        data = data.get("list") or []
    if not isinstance(data, list):
        raise SystemExit("{} 结构异常：顶层应为数组".format(JSON_FILE))
    return [x for x in data if isinstance(x, dict)]


def save_items(items):
    """每条一行输出：体积小，且 git diff 只会命中新增那一行。"""
    tmp = JSON_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fp:
        if not items:
            fp.write("[]\n")
        else:
            fp.write("[\n")
            fp.write(",\n".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) for x in items))
            fp.write("\n]\n")
    os.replace(tmp, JSON_FILE)


def merge(old, new):
    """按日期去重合并，返回 (全部条目[新→旧], 真正新增列表)。历史条目原样保留。"""
    seen, result = set(), []
    for item in old:
        key = dedup_key(item)
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        result.append(item)

    added = []
    for item in new:
        key = dedup_key(item)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
        added.append(item)

    result.sort(key=item_date, reverse=True)
    return result, added


# --------------------------------------------------------------------------
# 采集流程
# --------------------------------------------------------------------------
def collect_months(months, limit=None, resolve=False):
    """按 (year, month) 列表抓取；单月失败只告警，不中断整体。"""
    collected, failed = [], []
    for idx, (year, month) in enumerate(months, 1):
        raws = list_month(year, month)
        if raws is None:
            failed.append((year, month))
            log("  [{}/{}] {:04d}-{:02d} 请求失败，跳过".format(idx, len(months), year, month))
            continue
        items = [x for x in (to_item(r) for r in raws) if x]
        if resolve:
            for item in items:
                item["vod"] = resolve_hls(item["guid"])
                time.sleep(0.1)
        log("  [{}/{}] {:04d}-{:02d} 取得 {} 期".format(idx, len(months), year, month, len(items)))
        collected.extend(items)
        if limit and len(collected) >= limit:
            collected = collected[:limit]
            break
    return collected, failed


def month_range(start_year, start_month, end_year, end_month):
    months, y, m = [], start_year, start_month
    while (y, m) <= (end_year, end_month):
        months.append((y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return months


def url_alive(url, timeout=15):
    """HEAD 探测，2xx/3xx 视为可用。"""
    try:
        req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except Exception:                 # noqa: BLE001
        return False


def refresh_links(items, limit=None, dry_run=False):
    """校验已有 vod，失效的用 vdn 接口重新解析（正常的地址不做改动）。"""
    targets = items[:limit] if limit else items
    checked = changed = 0
    for item in targets:
        checked += 1
        vod = str(item.get("vod") or "")
        if vod.startswith("http") and url_alive(vod):
            continue
        guid = str(item.get("guid") or "").strip()
        if not guid:
            log("  ! {} 无 guid 且地址失效，只能人工处理".format(item_date(item)))
            continue
        url = resolve_hls(guid)
        if url and url != vod:
            item["vod"] = url
            changed += 1
            log("  [{}] {} 已修复".format(checked, item_date(item)))
    log("检查 {} 期，修复 {} 期{}".format(checked, changed, "（试跑未写盘）" if dry_run else ""))
    return changed


def build_args():
    parser = argparse.ArgumentParser(
        description="CCTV《今日说法》节目单增量爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--backfill", action="store_true", help="全量建档：从 2009-08 抓到当前月")
    parser.add_argument("--year", type=int, help="抓指定年份")
    parser.add_argument("--month", type=int, help="配合 --year 抓单月")
    parser.add_argument("--refresh", action="store_true", help="校验已有地址，失效的重新解析")
    parser.add_argument("--resolve", action="store_true", help="抓取时逐条调用 vdn 校正 vod（慢）")
    parser.add_argument("--pages", type=int, default=RECENT_PAGES, help="增量模式翻页数（默认 3）")
    parser.add_argument("--limit", type=int, help="最多处理多少期（调试用）")
    parser.add_argument("--dry-run", action="store_true", help="只打印，不写 jrsf.json")
    return parser.parse_args()


def main():
    args = build_args()
    today = _date.today()

    if args.year and (args.year < 1990 or args.year > today.year + 1):
        raise SystemExit("--year 取值异常：{}".format(args.year))
    if args.month and (args.month < 1 or args.month > 12):
        raise SystemExit("--month 取值异常：{}".format(args.month))

    try:
        old_items = load_items()
    except SystemExit:
        raise
    except Exception as exc:          # noqa: BLE001
        raise SystemExit("读取 {} 失败：{}".format(JSON_FILE, exc))

    known = {k for k in (dedup_key(x) for x in old_items) if k}
    log("本地已有 {} 期（最新 {}）".format(
        len(old_items), item_date(old_items[0]) if old_items else "无"))

    # 1) 校正已有链接
    if args.refresh:
        changed = refresh_links(old_items, args.limit, args.dry_run)
        if changed and not args.dry_run:
            save_items(old_items)
            log("已写回 {}".format(JSON_FILE))
        elif not changed:
            log("无需修改，{} 保持不变".format(JSON_FILE))
        return 0

    # 2) 抓取
    backfill_months = month_range(START_YEAR, START_MONTH, today.year, today.month)
    if args.year:
        months = [(args.year, args.month)] if args.month else month_range(args.year, 1, args.year, 12)
        log("指定年份抓取：{} 个月".format(len(months)))
        new_items, failed = collect_months(months, args.limit, args.resolve)
    elif args.backfill or not old_items:
        if not args.backfill:
            log("本地无数据，自动切换为全量建档……")
        log("全量建档：{:04d}-{:02d} → {:04d}-{:02d}，共 {} 个月".format(
            START_YEAR, START_MONTH, today.year, today.month, len(backfill_months)))
        new_items, failed = collect_months(backfill_months, args.limit, args.resolve)
    else:
        log("增量模式：抓最近 {} 页".format(args.pages))
        new_items, failed = list_recent(args.pages, known), []

    if not new_items:
        log("没有取到任何节目{}".format("（部分月份失败，见上）" if failed else ""))
        return 2 if failed else 0

    merged, added = merge(old_items, new_items)
    log("抓取 {} 期，新增 {} 期，合计 {} 期".format(len(new_items), len(added), len(merged)))

    if args.dry_run:
        preview = added[: args.limit or 5] or new_items[: args.limit or 5] or merged[:5]
        log("试跑模式，不写盘。示例：")
        log(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0

    if not added:
        log("无新节目，{} 未改动".format(JSON_FILE))
        return 0

    save_items(merged)
    log("已写入 {}：{} → {}".format(JSON_FILE, item_date(merged[-1]), item_date(merged[0])))
    if failed:
        log("注意：{} 个月份抓取失败：{}".format(
            len(failed), ", ".join("{:04d}-{:02d}".format(y, m) for y, m in failed[:12])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
