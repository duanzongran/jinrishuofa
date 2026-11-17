# 今日说法 · m3u8 节目单（影视仓数据源）

CCTV《今日说法》2009 年 8 月至今每一期的 **m3u8 播放地址**，由 GitHub Actions 每天自动增量更新，
影视仓（FongMi TV 内核）通过一个 QuickJS 蜘蛛读取本仓库的 `jrsf.json`，按年份分卡片展示。

## 目录结构

```
.
├── crawl.py                     # 爬虫：抓央视栏目接口，增量写入 jrsf.json（纯标准库，无需 pip）
├── jrsf.json                    # 数据：所有期数的播放地址（由 Actions 自动更新）
├── jrsf.js                      # 影视仓蜘蛛：读 jrsf.json → 年份分类 → 卡片 → m3u8
├── README.md
└── .github/workflows/crawl.yml  # 每天定时跑 crawl.py 并提交 jrsf.json
```

## 数据格式

`jrsf.json` 是数组，按日期倒序（新 → 旧），**每条一行**（体积小、git diff 只会命中新增那一行）：

```json
[
  {
    "name": "今日说法 2026-11-17 车顶跌落理赔之争",
    "date": "2026-11-17",
    "year": "2026",
    "vod": "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/d0821f39332543119335d7825f6e5882/main.m3u8?maxbr=2048",
    "guid": "d0821f39332543119335d7825f6e5882",
    "pic": "https://p3.img.cctvpic.com/fmspic/2026/11/17/d0821f39332543119335d7825f6e5882-1.jpg",
    "dur": "00:27:59",
    "desc": "本期节目主要内容：……"
  }
]
```

| 字段 | 说明 |
| --- | --- |
| `name` | 统一格式「今日说法 YYYY-MM-DD 副标题」，可检索 |
| `date` | 节目日期，**去重键**，也是影视仓里的 `vod_id` |
| `year` | 年份，影视仓按它分卡片 |
| `vod` | m3u8 直链（央视腾讯云 CDN，无需鉴权） |
| `guid` | 央视视频 ID，`vod` 可用它重新拼出来 |
| `pic` / `dur` / `desc` | 封面、时长、简介（可选，缺了不影响播放） |

> 历史旧数据（只有 `name`/`year`/`vod`）不会被改写，蜘蛛会自动从 `name` 里补出日期。

## 本地运行

需要 Python 3.8+，**不用安装任何依赖**。

```bash
# 增量：抓最近 3 页，遇到已有日期立刻停止（日常就用这个）
python crawl.py

# 全量建档：2009-08 至今，约 208 次请求、2~3 分钟
python crawl.py --backfill

# 只抓某年 / 某年某月
python crawl.py --year 2026
python crawl.py --year 2026 --month 11

# 试跑：只打印不写盘
python crawl.py --year 2026 --month 11 --dry-run --limit 3

# 校验已有地址，失效的用 vdn 接口重新解析
python crawl.py --refresh --limit 50
```

行为说明：

- **只追加**：按 `date` 去重，已存在的期数绝不覆盖，没有新节目就**不写文件**（Actions 也就不会产生空提交）。
- **按月抓取**：央视接口 `d=YYYYMM` 偶尔跨月返回，脚本按 `time` 字段严格过滤，且每月一页（100 条）足够覆盖全月。
- **播放地址**：默认用 `guid` 直接拼 CDN 规律地址（实测与 vdn 接口返回的 `hls_url` 完全一致），加 `--resolve` 才逐条走接口。
- 单月请求失败只告警不中断；全部失败才返回非 0。

## GitHub Actions

`.github/workflows/crawl.yml` 每天两次自动运行并提交 `jrsf.json`：

| 触发 | 时间 | 说明 |
| --- | --- | --- |
| `schedule` | 北京 13:00 | 央视约 12:38 上线当天节目 |
| `schedule` | 北京 22:00 | 兜底 |
| `workflow_dispatch` | 手动 | 可选 `auto / backfill / year / refresh` |

### 首次使用必做两件事

1. **开写权限**：仓库 → `Settings` → `Actions` → `General` → `Workflow permissions` → 选 **Read and write permissions** → `Save`。
   没开这步，`git push` 会报 `403`。
2. **手动跑一次**：`Actions` → 左侧 `今日说法自动增量` → 右侧 `Run workflow`：
   - 仓库里还没有 `jrsf.json` 时，选 `backfill` 建全量；
   - 之后日常留空（`auto`）即可，Actions 只会追加当天新的一期。

### 日志里会看到

```
本地已有 6243 期（最新 2026-11-16）
增量模式：抓最近 3 页
抓取 300 期，新增 1 期，合计 6244 期
已写入 jrsf.json：2009-08-01 → 2026-11-17
```

没有新节目时是 `无新节目，jrsf.json 未改动`，随后提交步骤自动跳过。

## 影视仓配置

1. 把 `jrsf.js` 里的 `OWNER` 改成你的 GitHub 用户名（`REPO` 默认 `jinrishuofa`，如仓库名不同也改）。
2. 在影视仓使用的 `config.json` 的 `sites` 里加一项：

```json
{
  "key": "jrsf",
  "name": "今日说法",
  "type": 3,
  "api": "https://raw.githubusercontent.com/你的用户名/jinrishuofa/main/jrsf.js",
  "searchable": 1,
  "quickSearch": 1,
  "filterable": 1,
  "style": {"type": "rect", "ratio": 0.75},
  "ext": {
    "data_url": "https://raw.githubusercontent.com/你的用户名/jinrishuofa/main/jrsf.json"
  }
}
```

- `api` 指向 `.js` 文件即可，影视仓的 QuickJS 内核会直接加载，**不需要打包 jar**。
- `ext.data_url` 可覆盖数据地址；国内加载慢时换成 jsDelivr：
  `https://cdn.jsdelivr.net/gh/你的用户名/jinrishuofa@main/jrsf.json`
  （脚本默认已带 raw → jsDelivr 自动回退，且实例内缓存 10 分钟）。

### 界面效果

- 首页：分类为「最新上线」+ `2026年`、`2025年` …… `2009年`（按数据自动生成）
- 分类页：每页 30 张卡片，右上角显示日期与时长；可按「月份」筛选
- 详情页：单集「正片」
- 播放：直接输出 m3u8（`parse=0`，不做解析）
- 搜索：匹配标题 / 日期 / 简介

## 常见问题

| 现象 | 排查 |
| --- | --- |
| 影视仓里点开一片空白 | 先用浏览器打开 `api` 那个 `.js` 地址，确认能下载；再打开 `data_url` 确认是 JSON 数组 |
| 有卡片但一播放就失败 | 用 `python crawl.py --refresh --limit 20` 校正地址；或直接浏览器试 `vod` 链接 |
| 某天的节目没更新 | 央视有时晚于 13:00 上线，22:00 那次会补；也可手动 `Run workflow` |
| Actions 报 403 / 无法 push | 就是上面「开写权限」那步没做 |
| 抓取整体失败 | 央视接口改版了，看 `crawl.py` 顶部注释里的两个接口地址，按新参数改 `list_month()` |
| 想从零重建数据 | 删除 `jrsf.json` 后手动跑 `backfill` |
