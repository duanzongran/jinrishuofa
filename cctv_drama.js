// 央视剧集 · FongMi QuickJS 源（一剧一卡）
// 接口规范：CatVodSpider / QuickJS，api 直接指向本文件地址
import { Spider, page } from "catvod";

const PAGE_SIZE = 20;

const CATALOG = [
 {
  "id": "shenfan1",
  "name": "神探狄仁杰 第一部",
  "pic": "https://p2.img.cctvpic.com/image/2009/cctvsandianshiju/2010/01/01/cctvsandianshiju_h264418000nero_aac32_20100101_1262282433929_2.jpg",
  "year": "2004",
  "area": "大陆",
  "types": [
   "悬疑",
   "古装"
  ],
  "director": "钱雁秋",
  "actor": "梁冠华,张子健,须乾",
  "content": "历史侦探悬疑剧。武则天时代，狄仁杰屡破奇案：使团惊魂、蓝衫记、滴血雄鹰……朝堂阴谋与民间奇案交织。",
  "remark": "全27集",
  "eps": [
   [
    "第1集 使团惊魂",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/fbe20fe24b2f4238395866a8a74afe21/main.m3u8?maxbr=2048"
   ],
   [
    "第2集 使团惊魂",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/e643467519b04c7d74a5ba9ee30a268a/main.m3u8?maxbr=2048"
   ],
   [
    "第3集 使团惊魂",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/dde527ffe1bf4a1ed7c4b3b3de72cd2f/main.m3u8?maxbr=2048"
   ],
   [
    "第4集 使团惊魂",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/a0306874d62d440c2d014dad2b0410a8/main.m3u8?maxbr=2048"
   ],
   [
    "第5集 使团惊魂",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/be1846372af0495061b212bcb7701a70/main.m3u8?maxbr=2048"
   ],
   [
    "第6集 使团惊魂",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/b229ccb1759346ae77b2908edb831586/main.m3u8?maxbr=2048"
   ],
   [
    "第7集 使团惊魂",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/37221768b3844f3f436615a2b484884e/main.m3u8?maxbr=2048"
   ],
   [
    "第8集 使团惊魂",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/b514544ed94c44252d2c17b115296a2e/main.m3u8?maxbr=2048"
   ],
   [
    "第9集 使团惊魂",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/0a2baf0d547840beff8bbaab57db8d38/main.m3u8?maxbr=2048"
   ],
   [
    "第10集 使团惊魂",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/2c62992c708943f888b016a08bf71236/main.m3u8?maxbr=2048"
   ],
   [
    "第11集 使团惊魂",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/74d07f311ee04cf8401a839768f57730/main.m3u8?maxbr=2048"
   ],
   [
    "第12集 使团惊魂",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/8ef652bf1f0d4ae9afdc9dadbed5e181/main.m3u8?maxbr=2048"
   ],
   [
    "第13集 使团惊魂",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/4a0733407fb9448c8d0dff87517e2e10/main.m3u8?maxbr=2048"
   ],
   [
    "第14集 蓝衫记",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/d59e70d539e2450aa116788682541dad/main.m3u8?maxbr=2048"
   ],
   [
    "第15集 蓝衫记",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/b25d512c6db04487356b65aefde654eb/main.m3u8?maxbr=2048"
   ],
   [
    "第16集 蓝衫记",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/5058f5ac903448f6fa9f6ba7e84bd84d/main.m3u8?maxbr=2048"
   ],
   [
    "第17集 蓝衫记",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/8e12fe1ec8524bc64c88588ffa90ead3/main.m3u8?maxbr=2048"
   ],
   [
    "第18集 蓝衫记",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/337c913cd2d142d2eaf8829ec0b43f18/main.m3u8?maxbr=2048"
   ],
   [
    "第19集 蓝衫记",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/5baa06ef1a5942e03710a085ba7357d3/main.m3u8?maxbr=2048"
   ],
   [
    "第20集 蓝衫记",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/37ef8c66ba374ed3a5fee4bcd43dd40c/main.m3u8?maxbr=2048"
   ],
   [
    "第21集 蓝衫记",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/aa472a432ca04605e540b18c2ad1d4e5/main.m3u8?maxbr=2048"
   ],
   [
    "第22集 蓝衫记",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/ac05fb2cbcc24158bc8c73a7ec775075/main.m3u8?maxbr=2048"
   ],
   [
    "第23集 滴血雄鹰",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/c09e73f06e94417f157ca99361b5cadb/main.m3u8?maxbr=2048"
   ],
   [
    "第24集 滴血雄鹰",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/dc93572264a941d9a4ab6d8de3789c8b/main.m3u8?maxbr=2048"
   ],
   [
    "第25集 滴血雄鹰",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/11a1fcaeaab94647282769a290946e6f/main.m3u8?maxbr=2048"
   ],
   [
    "第26集 滴血雄鹰",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/0bee9222c9c04d518c44bf96641c57ea/main.m3u8?maxbr=2048"
   ],
   [
    "第27集 滴血雄鹰",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/a7e779b0805744fe8cc8c2ba30bbad7c/main.m3u8?maxbr=2048"
   ]
  ]
 },
 {
  "id": "shexiang",
  "name": "奢香夫人",
  "pic": "https://p2.img.cctvpic.com/fmspic/2013/10/13/a3628f7699814f0e824701bf3590fa49-180.jpg",
  "year": "2011",
  "area": "大陆",
  "types": [
   "古装",
   "历史"
  ],
  "director": "陈健",
  "actor": "宁静,吕良伟,张双利,王思懿",
  "content": "明朝初年，彝族女政治家奢香夫人的传奇一生。央视网 CCTV-8 官方源。",
  "remark": "全28集",
  "eps": [
   [
    "第1集",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/a3628f7699814f0e824701bf3590fa49/main.m3u8?maxbr=2048"
   ],
   [
    "第2集",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/26cd1d29beb24ba88c3f403501ffd858/main.m3u8?maxbr=2048"
   ],
   [
    "第3集",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/2c59573d32884f69bdb8a80de24ef56c/main.m3u8?maxbr=2048"
   ],
   [
    "第4集",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/e546626c8a614332aa631baaf59b994d/main.m3u8?maxbr=2048"
   ],
   [
    "第5集",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/859d37aff958426e903dc319e962e8d3/main.m3u8?maxbr=2048"
   ],
   [
    "第6集",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/3f28fef6a6a04463abd64b2a6d466225/main.m3u8?maxbr=2048"
   ],
   [
    "第7集",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/82e293ade1ad450589859043d445971f/main.m3u8?maxbr=2048"
   ],
   [
    "第8集",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/3454ba3f4c644bbbb310ad0eee8f70e2/main.m3u8?maxbr=2048"
   ],
   [
    "第9集",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/b65a7cb434ba42fd809f9d35f85b25c2/main.m3u8?maxbr=2048"
   ],
   [
    "第10集",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/a960238e7ed54304a54236ab450a5e2a/main.m3u8?maxbr=2048"
   ],
   [
    "第11集",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/ab1a1c01caa44b6880730964f08491cd/main.m3u8?maxbr=2048"
   ],
   [
    "第12集",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/dadd89b7c52a4eabbfa74692c3510cc2/main.m3u8?maxbr=2048"
   ],
   [
    "第13集",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/80cc512598e8460c9cb02000bba867d8/main.m3u8?maxbr=2048"
   ],
   [
    "第14集",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/110905b412f845ccb08cf08ba17fbf58/main.m3u8?maxbr=2048"
   ],
   [
    "第15集",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/84900ce8afac483dad921f9b0122b14f/main.m3u8?maxbr=2048"
   ],
   [
    "第16集",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/4fa658c5058d43e69340a9e07ecaf99e/main.m3u8?maxbr=2048"
   ],
   [
    "第17集",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/ec80356433244898861f0d5046f3ce6c/main.m3u8?maxbr=2048"
   ],
   [
    "第18集",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/676b40b7d2a74c21ab3bdb00c8d5492f/main.m3u8?maxbr=2048"
   ],
   [
    "第19集",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/1f9585d030f9483dbc7728a65af2d4f4/main.m3u8?maxbr=2048"
   ],
   [
    "第20集",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/ae89ae2e94f94c238ef093cb8a53a085/main.m3u8?maxbr=2048"
   ],
   [
    "第21集",
    "https://newcntv.qcloudcdn.com/asp/hls/main/0303000a/3/default/afb873b1b73f42e0868513ba255f7bd7/main.m3u8?maxbr=2048"
   ],
   [
    "第22集",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/472cf8fa81db4eeca81819da4322cb35/main.m3u8?maxbr=2048"
   ],
   [
    "第23集",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/3aa082e425054c2685d5e99b9cd8b5ff/main.m3u8?maxbr=2048"
   ],
   [
    "第24集",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/7619a273ff7444f39ec95273fac4c71c/main.m3u8?maxbr=2048"
   ],
   [
    "第25集",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/90dad9ca5bf54a238109d66c8db10fc1/main.m3u8?maxbr=2048"
   ],
   [
    "第26集",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/2e7b43c16f064c5abb27b151ca9030fb/main.m3u8?maxbr=2048"
   ],
   [
    "第27集",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/339e34a013bd4732906937142c9f7296/main.m3u8?maxbr=2048"
   ],
   [
    "第28集(大结局)",
    "https://hls.cntv.lxdns.com/asp/hls/main/0303000a/3/default/4d2c145e6a784459b516bb6696e397b1/main.m3u8?maxbr=2048"
   ]
  ]
 }
];

function findRecord(id) {
    return CATALOG.find((r) => r.id === String(id).replace(/^vod\//, ""));
}

function card(r, styleType) {
    return {
        vod_id: "vod/" + r.id,
        vod_name: r.name,
        vod_pic: r.pic,
        vod_remarks: r.remark,
        vod_year: r.year,
        vod_area: r.area,
        style: { type: styleType || "rect", ratio: 0.75 },
    };
}

function detailVod(r) {
    const item = card(r, "rect");
    Object.assign(item, {
        type_name: (r.types || []).join("/"),
        vod_director: r.director,
        vod_actor: r.actor,
        vod_content: r.content,
        vod_play_from: "央视网",
        vod_play_url: r.eps.map((e) => e[0] + "$" + e[1]).join("#"),
    });
    return item;
}

export default class CctvDrama extends Spider {
    homeContent(filter) {
        return {
            class: [
                { type_id: "all", type_name: "全部" },
                { type_id: "shenfan1", type_name: "神探狄仁杰 第一部" },
                { type_id: "shexiang", type_name: "奢香夫人" },
            ],
        };
    }

    homeVideoContent() {
        return { list: CATALOG.map((r) => card(r, "rect")) };
    }

    categoryContent(tid, pg, filter, extend) {
        let items;
        if (tid === "all" || !tid) items = CATALOG;
        else items = CATALOG.filter((r) => r.id === tid);
        return page(items.map((r) => card(r, "rect")), pg || "1", PAGE_SIZE);
    }

    searchContent(key, quick, pg) {
        const q = String(key || "").trim().toLowerCase();
        if (!q) return page([], pg || "1", PAGE_SIZE);
        const items = CATALOG.filter((r) =>
            [r.name, r.director, r.actor, (r.types || []).join(" ")]
                .some((v) => String(v || "").toLowerCase().includes(q))
        );
        return page(items.map((r) => card(r, "rect")), pg || "1", PAGE_SIZE);
    }

    detailContent(ids) {
        const list = [];
        for (const id of ids) {
            const r = findRecord(id);
            if (r) list.push(detailVod(r));
        }
        return { list };
    }

    playerContent(flag, id, vipFlags) {
        const url = String(id || "").trim();
        if (!/^https?:\/\//i.test(url)) return { parse: 0, msg: "无效播放地址" };
        return { parse: 0, jx: 0, url, header: "" };
    }
}
