# 今日说法 · m3u8 节目单（影视仓 / TVBox 数据源）

CCTV《今日说法》2009 年 8 月至今每一期的 **m3u8 播放地址**，由 GitHub Actions 每天自动增量更新。
同一份数据提供两种接入方式，按客户端内核选：

| 客户端内核 | 接哪个文件 | 体验 |
| --- | --- | --- |
| **TVBox / 影视仓（绝大多数版本）** | `jrsf.m3u`、`jrsf.txt`（走「直播」通道） | 按年份分组，点开即播；无封面/无搜索 |
| **FongMi 内核**（FongMi TV 等） | `jrsf.js`（走「点播」通道） | 分类、卡片、月份筛选、搜索、详情 |

> 市面上叫「影视仓」的 App 内核各不相同：`type:3` 报「**jar加载失败**」的一律是 TVBox 内核，
> 它把 js 蜘蛛当 jar 解压，永远跑不起来 —— 请用下面的 m3u 方式。

## 目录结构

```
.
├── crawl.py                     # 爬虫：抓央视栏目接口，增量写入 jrsf.json（纯标准库，无需 pip）
├── make_m3u.py                  # 转换：jrsf.json → m3u / txt / 精简版 list（纯标准库）
├── jrsf.json                    # 主数据：每期一条（约 3.2 MB，由 Actions 更新）
├── jrsf.m3u                     # 全量 m3u，group-title 按年份分组（约 0.9 MB）
├── jrsf.txt                     # 同上的 TVBox txt 格式（约 0.75 MB，加载更快）
├── jrsf_2026.m3u … 2009.m3u     # 分年 m3u，每年一个（20~60 KB，低配盒子只加当年）
├── jrsf_list.json               # 精简点播接口样例：一年一条，期数放 vod_play_url（约 0.75 MB）
├── jrsf.js                      # FongMi 内核用的点播蜘蛛（TVBox 内核不支持）
├── config.json                  # 影视仓配置：直播源版（TVBox 内核用这个）
├── config-js.json               # 影视仓配置：点播版（FongMi 内核用）
├── README.md
└── .github/workflows/crawl.yml  # 每天定时跑 crawl.py + make_m3u.py 并提交
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

### 生成播放列表（m3u / txt / 精简 list）

```bash
python make_m3u.py                            # 全量：jrsf.m3u + jrsf.txt + 18 个分年文件 + jrsf_list.json
python make_m3u.py --api-files                # 额外生成 jrsf_api_2026.json … 每年一个接口文件
python make_m3u.py --recent 3                 # 只导最近 3 年
python make_m3u.py --no-year-files --no-txt   # 只要全量 m3u
python make_m3u.py --bom                      # 给老播放器加 UTF-8 BOM
```

生成规则：

- 只写「分组 / 显示名 / 播放地址」三样；简介、封面、时长一概不写（`jrsf_list.json` 也去掉了 `vod_pic` / `vod_content` / `vod_actor`）。
- 显示名 = `日期 副标题`，去掉重复的「今日说法」前缀。
- m3u 用 `group-title="2026年"` 分组，txt 用 `2026年,#genre#` 分组，组内新 → 旧。

行为说明：

- **只追加**：按 `date` 去重，已存在的期数绝不覆盖，没有新节目就**不写文件**（Actions 也就不会产生空提交）。
- **按月抓取**：央视接口 `d=YYYYMM` 偶尔跨月返回，脚本按 `time` 字段严格过滤，且每月一页（100 条）足够覆盖全月。
- **播放地址**：默认用 `guid` 直接拼 CDN 规律地址（实测与 vdn 接口返回的 `hls_url` 完全一致），加 `--resolve` 才逐条走接口。
- 单月请求失败只告警不中断；全部失败才返回非 0。

## GitHub Actions

`.github/workflows/crawl.yml` 每天两次自动运行：抓取 → 生成 m3u / txt / list → 一起提交：

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
本地已有 5022 期（最新 2026-11-16）
增量模式：抓最近 3 页
抓取 100 期，新增 1 期，合计 5023 期
已写入 jrsf.json：2009-08-01 → 2026-11-17
已写出 jrsf.m3u：5023 期，920,065 字节
已写出 jrsf.txt：754,586 字节
  jrsf_2026.m3u：198 期
  jrsf_2025.m3u：243 期
  ……
已写出 jrsf_list.json：18 年 / 18 条，751,633 字节
年份分布：2026=198  2025=243  … 2009=97
```

没有新节目时是 `无新节目，jrsf.json 未改动`，m3u 内容也不会变，提交步骤自动跳过。

## 影视仓配置（TVBox 内核 · 点播 + 直播）

TVBox 内核**不要用 `type:3`**：它会把 `api` 指向的文件当 jar 解压，于是报「jar加载失败」。

### 方式 A：`type:1` + 静态 `jrsf_list.json`（点播列表，推荐）

`type:1` 是 TVBox 的「JSON 数据源」，由配置顶部的 `spider`（全局 jar）提供解析器，
`api` 指向一个 JSON 文件即可 —— 可以是本地路径（`/sdcard/Download/jrsf_list.json`），
也可以是网址。`jrsf_list.json` 就是按这个格式生成的：

```json
{"class":[{"type_id":"2026","type_name":"2026年"}, … 共 18 年],
 "list":[{"vod_id":"jrsf2026","vod_name":"今日说法 2026年",
          "vod_play_url":"01 11-17 副标题$https://…/main.m3u8#02 11-16 …"}]}
```

影视仓 → 设置 → 配置地址，填：

```
https://cdn.jsdelivr.net/gh/你的用户名/jinrishuofa@main/config.json
```

（仓库里的 `影视仓配置_今日说法.json` 与它内容完全一致，填哪个都行）

`config.json` 关键部分：

```json
{
  "spider": "https://gitee.com/yuxiaotian3061/tvbox/raw/master/spider.jar",
  "sites": [{
    "key": "jrsf",
    "name": "今日说法 历年(2009-2026)",
    "type": 1,
    "api": "https://cdn.jsdelivr.net/gh/你的用户名/jinrishuofa@main/jrsf_list.json",
    "headers": {"User-Agent": "Mozilla/5.0 …", "Referer": "https://tv.cctv.com/"}
  }]
}
```

- **`spider` 必须留**：删掉它，`type:1` 就没有解析器，同样会报「jar加载失败」。
- 列表里是 2009~2026 共 18 张年份卡片，点进去是该年全部期，点哪一期直接播央视 m3u8。
- 如果点开哪一年都显示 2026 年（部分内核的 detail 只取返回 `list` 的第一条），
  跑 `python make_m3u.py --api-files`，然后把 `config.json` 改成 18 个站点，
  每个站点的 `api` 指向 `jrsf_api_2026.json` … `jrsf_api_2009.json`（每个文件里只有 1 条，绝不会串年）。

### 方式 B：m3u / txt 直播源

| 想要什么 | 填这个地址（`你的用户名` 换成自己的） |
| --- | --- |
| 全部 18 年 5023 期（约 0.9 MB） | `https://cdn.jsdelivr.net/gh/你的用户名/jinrishuofa@main/jrsf.m3u` |
| 加载更快（txt 格式，约 0.75 MB） | `https://cdn.jsdelivr.net/gh/你的用户名/jinrishuofa@main/jrsf.txt` |
| 只要某一年（20~60 KB，秒开） | `https://cdn.jsdelivr.net/gh/你的用户名/jinrishuofa@main/jrsf_2026.m3u`（可换 2025、2024…） |

填在「直播源管理」里即可，`config.json` 的 `lives` 里也已经配好前两个。
加好后直播页会出现「2026年」…「2009年」共 18 个分组，点进去就是当期央视 m3u8。

电脑上验证：把地址丢进 PotPlayer / VLC / MX Player，能出播放列表就说明地址没问题。

> jsDelivr 对 `@main` 有约 12 小时缓存，当天新上线的一期可能延迟半天出现。
> 想立刻看到，把 `https://cdn.jsdelivr.net/gh/你的用户名/jinrishuofa@main/` 换成
> `https://raw.githubusercontent.com/你的用户名/jinrishuofa/main/`（前提是你的网络能访问 raw）。
> 改完文件后也可以访问 `https://purge.jsdelivr.net/gh/你的用户名/jinrishuofa@main/config.json` 手动刷缓存。

## 影视仓配置（FongMi 内核 · 点播体验）

FongMi 内核（FongMi TV 3.x、部分影视仓版本）支持 QuickJS 蜘蛛，用 `config-js.json`，或把下面这段加进 `sites`：

```json
{
  "key": "jrsf",
  "name": "今日说法",
  "type": 3,
  "api": "https://cdn.jsdelivr.net/gh/你的用户名/jinrishuofa@main/jrsf.js",
  "searchable": 1,
  "quickSearch": 1,
  "filterable": 1,
  "style": {"type": "rect", "ratio": 0.75},
  "ext": {"data_url": "https://cdn.jsdelivr.net/gh/你的用户名/jinrishuofa@main/jrsf.json"}
}
```

部署前把 `jrsf.js` 顶部的 `OWNER` 改成你的 GitHub 用户名（`REPO` 保持 `jinrishuofa`）。

### 界面效果（FongMi 内核）

（TVBox 内核只有直播列表，没有下面这些）

- 首页：分类为「最新上线」+ `2026年`、`2025年` …… `2009年`（按数据自动生成）
- 分类页：每页 30 张卡片，右上角显示日期与时长；可按「月份」筛选
- 详情页：单集「正片」
- 播放：直接输出 m3u8（`parse=0`，不做解析）
- 搜索：匹配标题 / 日期 / 简介

## 常见问题

| 现象 | 排查 |
| --- | --- |
| `type:3` 报「**jar加载失败**」 | 客户端是 TVBox 内核，只会把 api 当 jar 解压，不支持 js 蜘蛛 → 改用 m3u 直播源（见「影视仓配置（TVBox 内核）」） |
| 电视端提示「拉取失败」/ 配置地址加载不出来 | 电视访问不了 `raw.githubusercontent.com`，把配置地址换成 jsDelivr 那份：`https://cdn.jsdelivr.net/gh/你的用户名/jinrishuofa@main/config.json` |
| 直播列表能出来，但没有封面/简介 | m3u 是频道列表形态，本来就不带封面；要卡片和搜索得换 FongMi 内核 + `jrsf.js` |
| m3u 里没有当天最新一期 | jsDelivr 对 `@main` 有约 12 小时缓存；等半天，或改用 `raw.githubusercontent.com` 地址 |
| 直播页加载很慢 / 卡住 | 全量 m3u 有 5023 期，低配盒子改用分年文件：`jrsf_2026.m3u`、`jrsf_2025.m3u` |
| FongMi 内核里点开一片空白 | 浏览器打开 `api` 那个 `.js` 地址确认能下载；再打开 `data_url` 确认是 JSON 数组 |
| 有卡片但一播放就失败 | 用 `python crawl.py --refresh --limit 20` 校正地址；或直接浏览器试 `vod` 链接 |
| 某天的节目没更新 | 央视有时晚于 13:00 上线，22:00 那次会补；也可手动 `Run workflow` |
| Actions 报 403 / 无法 push | 就是上面「开写权限」那步没做 |
| 抓取整体失败 | 央视接口改版了，看 `crawl.py` 顶部注释里的两个接口地址，按新参数改 `list_month()` |
| 想从零重建数据 | 删除 `jrsf.json` 后手动跑 `backfill`，再跑 `python make_m3u.py` |
