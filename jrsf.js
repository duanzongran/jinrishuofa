// 今日说法 · 影视仓（FongMi TV QuickJS 内核）蜘蛛
// ---------------------------------------------------------------------------
// 只负责「读 jrsf.json + 按年份出卡片」，不做任何网页解析。
// 数据由仓库里的 GitHub Actions 每日更新（见 .github/workflows/crawl.yml）。
//
// 部署三步：
//   1) 把本文件与 jrsf.json 一起放在仓库根目录；
//   2) 改下面 OWNER / REPO 两行；
//   3) 在影视仓的 config.json 里加站点：
//      {
//        "key": "jrsf",
//        "name": "今日说法",
//        "type": 3,
//        "api": "https://raw.githubusercontent.com/<用户名>/<仓库>/main/jrsf.js",
//        "searchable": 1, "quickSearch": 1, "filterable": 1,
//        "style": {"type": "rect", "ratio": 0.75},
//        "ext": {"data_url": "https://raw.githubusercontent.com/<用户名>/<仓库>/main/jrsf.json"}
//      }
// ---------------------------------------------------------------------------

import {Spider} from "catvod";

const OWNER = "duanzongran";      // TODO: 你的 GitHub 用户名
const REPO = "jinrishuofa";     // TODO: 仓库名
const BRANCH = "main";

const DATA_URL = `https://raw.githubusercontent.com/${OWNER}/${REPO}/${BRANCH}/jrsf.json`;
const DATA_URL_BAK = `https://cdn.jsdelivr.net/gh/${OWNER}/${REPO}@${BRANCH}/jrsf.json`;
const HLS_TPL = (guid) => `https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/${guid}/main.m3u8?maxbr=2048`;

const PAGE_SIZE = 30;
const CACHE_TTL = 10 * 60 * 1000;   // 实例内缓存 10 分钟，避免每次点卡片都拉 json
const LATEST_TID = "latest";
const MONTH_KEY = "month";

export default class Jrsf extends Spider {
    // ext 是 config 里的 ext 对象，App 以字符串传入
    init(extend) {
        let ext = {};
        try {
            ext = extend ? (typeof extend === "string" ? JSON.parse(extend) : extend) : {};
        } catch (e) {
            ext = {};
        }
        this.dataUrl = ext.data_url || DATA_URL;
        this.bakUrl = ext.bak_url || DATA_URL_BAK;
        this._cache = null;
        this._at = 0;
    }

    // ---------------- 数据层 ----------------
    async load(force) {
        const now = Date.now();
        if (!force && this._cache && now - this._at < CACHE_TTL) return this._cache;
        let raw = null;
        try {
            raw = await this.net.json(this.dataUrl);
        } catch (e) {
            raw = null;
        }
        if (!raw) {
            try {
                raw = await this.net.json(this.bakUrl);
            } catch (e) {
                raw = null;
            }
        }
        const list = this.normalize(raw);
        if (list.length) {
            this._cache = list;
            this._at = now;
            return list;
        }
        return this._cache || [];
    }

    // 兼容两种格式：[{...}] 或 {"list":[{...}]}
    normalize(raw) {
        const arr = Array.isArray(raw) ? raw : raw && Array.isArray(raw.list) ? raw.list : [];
        const map = {};
        for (let i = 0; i < arr.length; i++) {
            const it = arr[i];
            if (!it || typeof it !== "object") continue;
            const date = this.pickDate(it);
            if (!date) continue;
            const guid = String(it.guid || "");
            map[date] = {
                id: date,
                date: date,
                year: date.slice(0, 4),
                name: String(it.name || "").trim() || `今日说法 ${date}`,
                vod: String(it.vod || (guid ? HLS_TPL(guid) : "")),
                guid: guid,
                pic: String(it.pic || ""),
                dur: String(it.dur || ""),
                desc: String(it.desc || ""),
            };
        }
        const out = [];
        for (const k in map) out.push(map[k]);
        out.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0)); // 新 → 旧
        return out;
    }

    // 老数据可能只有 name/year/vod，没有 date
    pickDate(it) {
        const d = String(it.date || "");
        if (/^\d{4}-\d{2}-\d{2}$/.test(d)) return d;
        const name = String(it.name || "");
        const m = name.match(/(\d{4})-(\d{1,2})-(\d{1,2})/) || name.match(/(\d{4})(\d{2})(\d{2})/);
        if (m) return `${m[1]}-${m[2]}-${m[3]}`;
        const y = String(it.year || "");
        return /^\d{4}$/.test(y) ? `${y}-01-01` : "";
    }

    years(list) {
        const set = {};
        for (const it of list) set[it.year] = 1;
        return Object.keys(set).sort().reverse();
    }

    find(list, key) {
        if (!key) return null;
        const clean = String(key).split("@")[0];
        for (const it of list) if (it.id === clean) return it;
        return null;
    }

    months() {
        const out = [{n: "全部月份", v: ""}];
        for (let i = 1; i <= 12; i++) {
            const s = (i < 10 ? "0" : "") + i;
            out.push({n: `${i}月`, v: s});
        }
        return out;
    }

    card(it) {
        return {
            vod_id: it.id,
            vod_name: it.name,
            vod_pic: it.pic,
            vod_remarks: it.dur ? `${it.date.slice(5)} ${it.dur.slice(0, 5)}` : it.date.slice(5),
            vod_year: it.year,
            vod_tag: "file",
            style: {type: "rect", ratio: 0.75},
            action: "detail",
        };
    }

    // ---------------- 蜘蛛入口 ----------------
    async homeContent(filter) {
        const list = await this.load();
        const years = this.years(list);
        const classes = [{type_id: LATEST_TID, type_name: "最新上线"}];
        for (const y of years) classes.push({type_id: y, type_name: `${y}年`});
        const filters = {};
        for (const y of years) filters[y] = [{key: MONTH_KEY, name: "月份", init: "", value: this.months()}];
        return {
            class: classes,
            filters: filters,
            list: list.slice(0, PAGE_SIZE).map((it) => this.card(it)),
        };
    }

    async homeVideoContent() {
        const list = await this.load();
        return {list: list.slice(0, 12).map((it) => this.card(it))};
    }

    async categoryContent(tid, pg, filter, extend) {
        const list = await this.load();
        const p = parseInt(pg, 10) || 1;
        let items = tid === LATEST_TID ? list.slice() : list.filter((it) => it.year === tid);
        const month = extend && extend[MONTH_KEY] ? String(extend[MONTH_KEY]) : "";
        if (month) items = items.filter((it) => it.date.slice(5, 7) === month);
        const start = (p - 1) * PAGE_SIZE;
        return {
            list: items.slice(start, start + PAGE_SIZE).map((it) => this.card(it)),
            page: p,
            pagecount: Math.max(1, Math.ceil(items.length / PAGE_SIZE)),
            limit: PAGE_SIZE,
            total: items.length,
        };
    }

    async detailContent(ids) {
        const id = Array.isArray(ids) ? String(ids[0] || "") : String(ids || "");
        const it = this.find(await this.load(), id);
        if (!it) return {list: []};
        return {
            list: [
                {
                    vod_id: it.id,
                    vod_name: it.name,
                    vod_pic: it.pic,
                    vod_year: it.year,
                    vod_area: "中国大陆",
                    vod_remarks: it.dur ? `${it.date} ${it.dur}` : it.date,
                    vod_content: it.desc || `${it.name}（央视《今日说法》${it.date}）`,
                    vod_play_from: "央视",
                    vod_play_url: `正片$${it.id}`,
                    style: {type: "rect", ratio: 0.75},
                },
            ],
        };
    }

    async playerContent(flag, id, vipFlags) {
        const it = this.find(await this.load(), id);
        if (!it) return {parse: 0, jx: 0, msg: "找不到该期节目，请稍后重试"};
        const url = it.vod || (it.guid ? HLS_TPL(it.guid) : "");
        if (!url) return {parse: 0, jx: 0, msg: "该期缺少播放地址"};
        return {parse: 0, jx: 0, url: url, header: {}};
    }

    async searchContent(key, quick, pg = "1") {
        const kw = String(key || "").trim();
        const all = kw ? await this.load() : [];
        const hit = kw
            ? all.filter(
                  (it) =>
                      it.name.indexOf(kw) >= 0 ||
                      it.date.indexOf(kw) >= 0 ||
                      (it.desc && it.desc.indexOf(kw) >= 0)
              )
            : [];
        const p = parseInt(pg, 10) || 1;
        const start = (p - 1) * PAGE_SIZE;
        return {
            list: hit.slice(start, start + PAGE_SIZE).map((it) => this.card(it)),
            page: p,
            pagecount: Math.max(1, Math.ceil(hit.length / PAGE_SIZE)),
            limit: PAGE_SIZE,
            total: hit.length,
        };
    }
}
