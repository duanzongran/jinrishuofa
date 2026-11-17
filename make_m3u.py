#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 jrsf.json 生成影视仓（TVBox 内核）能直接读的静态播放列表
==========================================================

为什么需要它
    TVBox / 影视仓只认 jar 蜘蛛或动态 api 接口，读不了 js 蜘蛛；
    但它们都支持「直播」通道读 m3u / txt 列表。本脚本把节目单转成：

        jrsf.m3u            全部年份，group-title 按年份分组（新 → 旧）
        jrsf.txt            TVBox 原生 txt 格式（更省体积，兼容性最好）
        jrsf_2026.m3u …     每年一个文件，低配盒子只加当年即可秒开
        jrsf_list.json      精简版点播接口样例（一年一条，期数放 vod_play_url）

    列表里只保留「分组 / 显示名 / 播放地址」，不写简介、封面、时长。

用法
    python make_m3u.py                    # 全量生成
    python make_m3u.py --recent 3         # 只导出最近 3 年
    python make_m3u.py --no-year-files    # 不生成分年文件
    python make_m3u.py --no-list          # 不生成 jrsf_list.json
    python make_m3u.py --bom              # 给老播放器加 UTF-8 BOM
"""

import argparse
import json
import os
import re
import sys

try:  # Windows 控制台默认 GBK，避免打印中文报错
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

JSON_FILE = "jrsf.json"
M3U_FILE = "jrsf.m3u"
TXT_FILE = "jrsf.txt"
YEAR_FILE_TPL = "jrsf_{}.m3u"
LIST_FILE = "jrsf_list.json"
API_FILE_TPL = "jrsf_api_{}.json"       # 每年一个独立接口文件（--api-files 时生成）
CONFIG_FILE = "config.json"

HLS_TPL = (
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/"
    "{guid}/main.m3u8?maxbr=2048"
)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NUM_DATE_RE = re.compile(r"(\d{4})(\d{2})(\d{2})")
TITLE_PREFIX_RE = re.compile(r"^《?今日说法》?\s*")


def log(*args):
    print(*args, flush=True)


# --------------------------------------------------------------------------
# 读取与归一化
# --------------------------------------------------------------------------
def load_items(path):
    if not os.path.exists(path):
        raise SystemExit("找不到 {}，请先运行 crawl.py".format(path))
    with open(path, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    if isinstance(data, dict):
        data = data.get("list") or []
    if not isinstance(data, list):
        raise SystemExit("{} 结构异常：顶层应为数组".format(path))
    return [x for x in data if isinstance(x, dict)]


def item_date(item):
    """兼容只有 name/year/vod 的老条目，规则与 crawl.py 保持一致。"""
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


def item_vod(item):
    vod = str(item.get("vod") or "").strip()
    if vod.startswith("http"):
        return vod
    guid = str(item.get("guid") or "").strip()
    return HLS_TPL.format(guid=guid) if guid else ""


def subtitle(item, date):
    """去掉「今日说法」前缀、日期等噪声，只留副标题。"""
    name = re.sub(r"\s+", " ", str(item.get("name") or "")).strip()
    name = TITLE_PREFIX_RE.sub("", name)
    if name.startswith(date):
        name = name[len(date):]
    name = re.sub(r"^\d{8}\s*", "", name)          # 老数据可能带 20261117
    return name.strip()


def display_name(item, date):
    sub = subtitle(item, date)
    return (date + " " + sub).strip() if sub else date


def prepare(items):
    """归一化成 [{date, year, title, vod}]，按日期新 → 旧，按天去重。"""
    rows, seen = [], set()
    for item in items:
        date = item_date(item)
        vod = item_vod(item)
        if not date or not vod or date in seen:
            continue
        seen.add(date)
        rows.append(
            {
                "date": date,
                "year": date[:4],
                "title": display_name(item, date),
                "vod": vod,
            }
        )
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


# --------------------------------------------------------------------------
# 生成
# --------------------------------------------------------------------------
def build_m3u(rows):
    out = ["#EXTM3U"]
    for r in rows:
        out.append('#EXTINF:-1 group-title="{}年",{}'.format(r["year"], r["title"]))
        out.append(r["vod"])
    out.append("")
    return "\n".join(out)


def build_txt(rows):
    """TVBox 原生 txt：`分组,#genre#` 换组，`名称,地址` 换台。"""
    out, cur = [], None
    for r in rows:
        if r["year"] != cur:
            cur = r["year"]
            out.append("{}年,#genre#".format(cur))
        out.append("{},{}".format(r["title"], r["vod"]))
    out.append("")
    return "\n".join(out)


def build_list(rows):
    """一年一条：class 给分类，list 里 vod_play_url 用 # 拼成选集。"""
    by_year = {}
    for r in rows:
        by_year.setdefault(r["year"], []).append(r)

    classes, items = [], []
    for year in sorted(by_year, reverse=True):
        group = sorted(by_year[year], key=lambda x: x["date"])
        parts = []
        for idx, r in enumerate(group, 1):
            sub = r["title"][len(r["date"]):].strip()
            label = "{:02d} {}".format(idx, r["date"][5:])
            if sub:
                label += " " + sub
            parts.append(label + "$" + r["vod"])
        classes.append({"type_id": year, "type_name": "{}年".format(year)})
        items.append(
            {
                "vod_id": "jrsf" + year,
                "type_id": year,
                "type_name": "{}年".format(year),
                "vod_name": "今日说法 {}年".format(year),
                "vod_remarks": "{}期".format(len(group)),
                "vod_year": year,
                "vod_play_from": "央视",
                "vod_play_url": "#".join(parts),
            }
        )
    return {
        "class": classes,
        "page": 1,
        "pagecount": 1,
        "limit": len(items),
        "total": len(items),
        "list": items,
    }


def dump_list(data):
    """每条一行，git diff 只会命中变化的那一年。"""
    one = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))  # noqa: E731
    lines = ["{"]
    lines.append(' "class": [')
    lines.append(",\n".join("  " + one(x) for x in data["class"]))
    lines.append(" ],")
    lines.append(' "page": {},'.format(data["page"]))
    lines.append(' "pagecount": {},'.format(data["pagecount"]))
    lines.append(' "limit": {},'.format(data["limit"]))
    lines.append(' "total": {},'.format(data["total"]))
    lines.append(' "list": [')
    lines.append(",\n".join("  " + one(x) for x in data["list"]))
    lines.append(" ]")
    lines.append("}")
    return "\n".join(lines) + "\n"


def write_text(path, text, bom=False):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig" if bom else "utf-8", newline="\n") as fp:
        fp.write(text)
    os.replace(tmp, path)


def build_api_files(rows):
    """每年一个独立接口文件：list 只有 1 条，保证点进去一定是该年那 300 期。

    TVBox 的 api 蜘蛛在 detail 时只取返回 list 的第一条，所以不能把 18 年
    塞进同一个文件里，否则点哪年都播 2026 年。
    """
    by_year = {}
    for r in rows:
        by_year.setdefault(r["year"], []).append(r)
    made = []
    for year in sorted(by_year, reverse=True):
        path = API_FILE_TPL.format(year)
        write_text(path, dump_list(build_list(by_year[year])))
        made.append((path, len(by_year[year])))
    return made


# --------------------------------------------------------------------------
# 入口
# --------------------------------------------------------------------------
def build_args():
    parser = argparse.ArgumentParser(
        description="把 jrsf.json 转成影视仓可用的 m3u / txt 播放列表",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", default=JSON_FILE, help="输入文件（默认 jrsf.json）")
    parser.add_argument("--out", default=M3U_FILE, help="全量 m3u 文件名（默认 jrsf.m3u）")
    parser.add_argument("--recent", type=int, default=0, help="只导出最近 N 年（0 = 全部）")
    parser.add_argument("--no-year-files", action="store_true", help="不生成 jrsf_YYYY.m3u")
    parser.add_argument("--no-txt", action="store_true", help="不生成 jrsf.txt")
    parser.add_argument("--no-list", action="store_true", help="不生成 jrsf_list.json")
    parser.add_argument("--api-files", action="store_true",
                        help="额外生成 jrsf_api_YYYY.json（每年一个接口，type:1 多站点用）")
    parser.add_argument("--bom", action="store_true", help="输出 UTF-8 BOM（老播放器兼容）")
    return parser.parse_args()


def main():
    args = build_args()
    rows = prepare(load_items(args.json))
    if not rows:
        raise SystemExit("没有可用条目（date 或 vod 缺失）")

    if args.recent and args.recent > 0:
        cutoff = str(int(rows[0]["year"]) - args.recent + 1)
        rows = [r for r in rows if r["year"] >= cutoff]
        log("只导出 {} 年及以后：{} 期".format(cutoff, len(rows)))

    # 1) 全量 m3u
    write_text(args.out, build_m3u(rows), args.bom)
    log("已写出 {}：{} 期，{:,} 字节".format(args.out, len(rows), os.path.getsize(args.out)))

    # 2) 全量 txt
    if not args.no_txt:
        write_text(TXT_FILE, build_txt(rows), args.bom)
        log("已写出 {}：{:,} 字节".format(TXT_FILE, os.path.getsize(TXT_FILE)))

    # 3) 分年 m3u
    if not args.no_year_files:
        by_year = {}
        for r in rows:
            by_year.setdefault(r["year"], []).append(r)
        for year in sorted(by_year, reverse=True):
            path = YEAR_FILE_TPL.format(year)
            write_text(path, build_m3u(by_year[year]), args.bom)
            log("  {}：{} 期".format(path, len(by_year[year])))

    # 4) 精简版点播 list
    if not args.no_list:
        data = build_list(rows)
        write_text(LIST_FILE, dump_list(data), args.bom)
        log("已写出 {}：{} 年 / {} 条，{:,} 字节".format(
            LIST_FILE, len(data["class"]), len(data["list"]), os.path.getsize(LIST_FILE)))

    # 4.5) 分年接口文件（可选）
    if args.api_files:
        for path, n in build_api_files(rows):
            log("  {}：{} 期".format(path, n))

    # 5) 对账
    dist = "  ".join(
        "{}={}".format(y, sum(1 for r in rows if r["year"] == y))
        for y in sorted({r["year"] for r in rows}, reverse=True)
    )
    log("年份分布：{}".format(dist))
    return 0


if __name__ == "__main__":
    sys.exit(main())
