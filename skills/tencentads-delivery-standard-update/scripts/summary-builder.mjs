/**
 * summary-builder.mjs — 更新/回查后的中文回执拼装
 *
 * 适用场景：营销单元 / 智投项目通用更新（standard + smart 共用）。
 * 数据源：adgroups/get 返回的 list[0]（最新完整状态），不是 update 入参。
 *
 * 设计原则（钱相关字段必出，未命中枚举用 API 原值兜底，不报错不阻塞）:
 *   - 核心字段（必出）: 账户 ID、营销单元/项目 ID、名称、出价方式+金额+优化目标、出价场景、日预算、定向 brief
 *   - 按需追加: 智投场景、总消耗限额、深度优化、AIGC/全库智选、一键起量、版位、投放时段、状态、素材包
 *   - 金额单位 分→元（÷100，保留 2 位小数）
 *   - 定向全空时显示"全量投放"
 *   - 状态始终展示（已启用 / 已暂停 / 已删除）—— 与 create 模式不同
 *   - 输出格式: 首行标题 + 多行 Markdown 列表
 *
 * 自动判断营销单元类型：
 *   - 含 smart_delivery_platform → "项目"（智投）
 *   - 否则 → "营销单元"（常规）
 *
 * 仅导出 buildUpdateSummaryText；其余字典/helper 内部使用。
 */

// ─── 中文翻译字典（与 create 版本保持同步）───

const BID_MODE_CN = {
  BID_MODE_CPC: "CPC",
  BID_MODE_CPM: "CPM",
  BID_MODE_OCPM: "oCPM",
  BID_MODE_OCPC: "oCPC",
};

const GENDER_CN = {
  GENDER_MALE: "男",
  GENDER_FEMALE: "女",
  MALE: "男",
  FEMALE: "女",
};

const SITE_SET_CN = {
  SITE_SET_MOMENTS: "朋友圈",
  SITE_SET_WECHAT: "公众号与小程序",
  SITE_SET_WECHAT_PLUGIN: "微信插件位",
  SITE_SET_WECHAT_CHANNELS: "视频号",
  SITE_SET_CHANNELS: "视频号",
  SITE_SET_WECHAT_SEARCH: "微信搜一搜",
  SITE_SET_MINI_GAME_WECHAT: "微信小游戏",
  SITE_SET_KANDIAN: "腾讯看点",
  SITE_SET_QQ_MUSIC_GAME: "QQ音乐/游戏",
  SITE_SET_TENCENT_NEWS: "腾讯新闻",
  SITE_SET_TENCENT_VIDEO: "腾讯视频",
  SITE_SET_MOBILE_UNION: "优量汇",
  SITE_SET_QBSEARCH: "QQ浏览器搜索",
  SITE_SET_SEARCH_SCENE: "搜索场景",
};

const NETWORK_TYPE_CN = {
  WIFI: "WiFi",
  NET_2G: "2G",
  NET_3G: "3G",
  NET_4G: "4G",
  NET_5G: "5G",
};

const OPTIMIZATION_GOAL_CN = {
  OPTIMIZATIONGOAL_ECOMMERCE_ORDER: "成交",
  OPTIMIZATIONGOAL_FIRST_TWENTY_FOUR_HOUR_ECOMMERCE_ORDER: "首日成交",
  OPTIMIZATIONGOAL_NET_PROFIT_24H: "首日净收入",
  OPTIMIZATIONGOAL_APP_REGISTER: "注册",
  OPTIMIZATIONGOAL_APP_ACTIVATE: "激活",
  OPTIMIZATIONGOAL_APP_PURCHASE: "付费",
  OPTIMIZATIONGOAL_PAGE_RESERVATION: "页面预约",
  OPTIMIZATIONGOAL_PAGE_SCAN_CODE: "页面扫码",
  OPTIMIZATIONGOAL_FOLLOW: "关注",
  OPTIMIZATIONGOAL_LIKE: "点赞",
  OPTIMIZATIONGOAL_PROMOTION_READ_ARTICLE: "推广阅读文章",
};

const SMART_BID_TYPE_CN = {
  SMART_BID_TYPE_CUSTOM: "手动出价",
  SMART_BID_TYPE_SYSTEMATIC: "最大转化",
};

const BID_SCENE_CN = {
  BID_SCENE_NORMAL_AVERAGE: "均值出价",
  BID_SCENE_NORMAL_MAX: "最大转化",
  BID_SCENE_UNKNOWN: null,
};

// configured_status：始终展示
const CONFIGURED_STATUS_CN = {
  AD_STATUS_NORMAL: "已启用",
  AD_STATUS_SUSPEND: "已暂停",
  AD_STATUS_DELETE: "已删除",
};

// 智投场景枚举翻译
const SMART_PLATFORM_CN = {
  SMART_DELIVERY_PLATFORM_EDITION_WECHAT_STORE_PRODUCT_OR_LIVE: "微信小店商品/直播",
  SMART_DELIVERY_PLATFORM_EDITION_WECHAT_STORE_MANAGEMENT: "微信小店全店托管",
  SMART_DELIVERY_PLATFORM_EDITION_WECHAT_STORE_LIVE: "微信小店直播",
  SMART_DELIVERY_PLATFORM_EDITION_WECHAT_STORE_PRODUCT: "微信小店商品",
  SMART_DELIVERY_PLATFORM_EDITION_WECHAT_STORE_SINGLE_PRODUCT: "短直双开",
  SMART_DELIVERY_PLATFORM_EDITION_GAME_APP: "游戏App智投",
  SMART_DELIVERY_PLATFORM_EDITION_READING_APP: "阅读App智投",
  SMART_DELIVERY_PLATFORM_EDITION_AI_APP: "AI应用智投",
  SMART_DELIVERY_PLATFORM_EDITION_ECOLOGY_LEADS: "线索留资智投",
  SMART_DELIVERY_PLATFORM_EDITION_ECOLOGY_PLAYLET: "爆剧跑量智投",
  SMART_DELIVERY_PLATFORM_EDITION_MINI_GAME_PROMOTION: "小游戏智投",
  SMART_DELIVERY_PLATFORM_EDITION_DRUG_PRODUCT: "商品/医药智投",
  SMART_DELIVERY_PLATFORM_EDITION_FICTION: "小说智投",
  SMART_DELIVERY_PLATFORM_EDITION_QYT_LIVE: "全域通-直播",
  SMART_DELIVERY_PLATFORM_EDITION_QYT_WECHAT_STORE: "全域通-直购",
};

// 一级行政区（省/直辖市/自治区/特区）整十万 ID
const PROVINCE_CN = {
  110000: "北京", 120000: "天津", 130000: "河北", 140000: "山西",
  150000: "内蒙古", 210000: "辽宁", 220000: "吉林", 230000: "黑龙江",
  310000: "上海", 320000: "江苏", 330000: "浙江", 340000: "安徽",
  350000: "福建", 360000: "江西", 370000: "山东", 410000: "河南",
  420000: "湖北", 430000: "湖南", 440000: "广东", 450000: "广西",
  460000: "海南", 500000: "重庆", 510000: "四川", 520000: "贵州",
  530000: "云南", 540000: "西藏", 610000: "陕西", 620000: "甘肃",
  630000: "青海", 640000: "宁夏", 650000: "新疆", 710000: "台湾",
  810000: "香港", 820000: "澳门",
};

// ─── 内部 helper ───

function fenToYuan(fen) {
  if (fen == null || fen === "" || isNaN(Number(fen))) return null;
  return (Number(fen) / 100).toFixed(2);
}

function translateOrFallback(value, dict) {
  return dict[value] != null ? dict[value] : String(value);
}

function buildAgeBrief(ageArr) {
  if (!Array.isArray(ageArr) || ageArr.length === 0) return null;
  return ageArr
    .filter((a) => a && a.min != null && a.max != null)
    .map((a) => `${a.min}-${a.max}岁`)
    .join("、");
}

function buildGenderBrief(genderArr) {
  if (!Array.isArray(genderArr) || genderArr.length === 0) return null;
  const cn = genderArr.map((g) => translateOrFallback(g, GENDER_CN));
  return cn.length === 2 ? null : cn.join("、");
}

function buildGeoBrief(geo) {
  if (!geo || typeof geo !== "object") return null;
  const regions = Array.isArray(geo.regions) ? geo.regions : [];
  if (regions.length === 0) return null;
  const provinces = regions
    .map((id) => PROVINCE_CN[Number(id)])
    .filter(Boolean);
  if (provinces.length === regions.length) return provinces.join("、");
  if (provinces.length > 0) return `${provinces.join("、")} 等 ${regions.length} 个地域`;
  return `已指定 ${regions.length} 个地域`;
}

function buildOsBrief(osArr) {
  if (!Array.isArray(osArr) || osArr.length === 0) return null;
  if (osArr.length === 1 && osArr[0] === "ANDROID") return "Android";
  if (osArr.length === 1 && osArr[0] === "IOS") return "iOS";
  const androidVer = osArr.filter((o) => o.startsWith("ANDROID_VERSION_"));
  const iosVer = osArr.filter((o) => o.startsWith("IOS_VERSION_"));
  const parts = [];
  if (androidVer.length > 0) {
    const numbers = androidVer.map((o) => parseInt(o.replace("ANDROID_VERSION_", ""), 10)).filter((n) => !isNaN(n));
    if (numbers.length > 0) parts.push(`Android ${Math.min(...numbers)}+`);
  }
  if (iosVer.length > 0) {
    const numbers = iosVer.map((o) => parseInt(o.replace("IOS_VERSION_", ""), 10)).filter((n) => !isNaN(n));
    if (numbers.length > 0) parts.push(`iOS ${Math.min(...numbers)}+`);
  }
  if (parts.length > 0) return parts.join("、");
  return osArr.join("、");
}

function buildNetworkBrief(netArr) {
  if (!Array.isArray(netArr) || netArr.length === 0) return null;
  return netArr.map((n) => translateOrFallback(n, NETWORK_TYPE_CN)).join("/");
}

function buildTargetingBrief(targeting) {
  if (!targeting || typeof targeting !== "object") return "全量投放";
  const parts = [];
  const geo = buildGeoBrief(targeting.geo_location);
  if (geo) parts.push(geo);
  const age = buildAgeBrief(targeting.age);
  if (age) parts.push(age);
  const gender = buildGenderBrief(targeting.gender);
  if (gender) parts.push(gender);
  const os = buildOsBrief(targeting.user_os);
  if (os) parts.push(os);
  const net = buildNetworkBrief(targeting.network_type);
  if (net) parts.push(net);
  const extraDims = [];
  if (Array.isArray(targeting.custom_audience) && targeting.custom_audience.length > 0) extraDims.push("自定义人群");
  if (Array.isArray(targeting.excluded_custom_audience) && targeting.excluded_custom_audience.length > 0) extraDims.push("排除人群");
  if (Array.isArray(targeting.device_brand_model) && targeting.device_brand_model.length > 0) extraDims.push("设备机型");
  if (Array.isArray(targeting.education) && targeting.education.length > 0) extraDims.push("学历");
  if (Array.isArray(targeting.device_price) && targeting.device_price.length > 0) extraDims.push("设备价格");
  if (extraDims.length > 0) parts.push(`含${extraDims.join("、")}`);
  if (parts.length === 0) return "全量投放";
  // 部分定向时，明确告知"其他维度不限"，避免用户把 "男" 误读为全维度限定
  return `${parts.join("/")}（其他维度不限）`;
}

function buildSiteSetBrief(adgroup) {
  // 智投场景固定自动版位
  if (adgroup.smart_delivery_platform) return "自动版位";
  if (adgroup.automatic_site_enabled === true) return "自动版位";
  if (!Array.isArray(adgroup.site_set) || adgroup.site_set.length === 0) return null;
  return adgroup.site_set.map((s) => translateOrFallback(s, SITE_SET_CN)).join("、");
}

function buildScheduleBrief(begin, end) {
  if (!begin) return null;
  if (!end || end === "") return `${begin} 起长期投放`;
  return `${begin} ~ ${end}`;
}

// ─── 主函数 ───

/**
 * 将 adgroups/get 返回的最新营销单元 / 项目数据拼装成单段中文回执（用于 update 后的状态陈列）。
 *
 * @param {Object} adgroup - adgroups/get 返回的 list[0]，包含完整的最新字段
 * @param {Object} [opts]
 * @param {string|number} [opts.accountId] - 账户 ID（adgroup 没带时手动指定）
 * @param {string[]} [opts.updatedFields] - 本轮更新的字段名（用于在首行后追加"本次更新：xxx"）
 * @returns {string} 首行标题 + 多行列表的中文回执
 */
export function buildUpdateSummaryText(adgroup, opts = {}) {
  if (!adgroup || typeof adgroup !== "object") {
    return "回查未返回数据，请向用户说明并提示手动确认。";
  }

  const isSmart = !!adgroup.smart_delivery_platform;
  const entityCn = isSmart ? "项目" : "营销单元";
  const idStr = adgroup.adgroup_id != null ? adgroup.adgroup_id : "未知";
  const name = adgroup.adgroup_name || "未命名";
  const accountStr = opts.accountId != null
    ? String(opts.accountId)
    : (adgroup.account_id != null ? String(adgroup.account_id) : null);

  // ── 出价 ──
  const bidModeCn = translateOrFallback(adgroup.bid_mode, BID_MODE_CN);
  const bidAmountYuan = fenToYuan(adgroup.bid_amount);
  const optGoalCn = adgroup.optimization_goal
    ? (OPTIMIZATION_GOAL_CN[adgroup.optimization_goal] || null)
    : null;
  const bidSceneCn = adgroup.bid_scene
    ? (BID_SCENE_CN[adgroup.bid_scene] != null ? BID_SCENE_CN[adgroup.bid_scene] : null)
    : null;
  const isSystematic = adgroup.smart_bid_type === "SMART_BID_TYPE_SYSTEMATIC";

  let bidValue;
  if (bidAmountYuan != null && Number(adgroup.bid_amount) > 0) {
    bidValue = `${bidModeCn} ${bidAmountYuan} 元`;
    if (optGoalCn) bidValue += `/${optGoalCn}`;
  } else {
    bidValue = isSystematic ? `${bidModeCn} 最大转化出价` : `${bidModeCn} 自动出价`;
    if (optGoalCn) bidValue += `（按${optGoalCn}）`;
  }
  if (bidSceneCn && !(isSystematic && bidSceneCn === "最大转化")) {
    bidValue += `（${bidSceneCn}）`;
  }

  // ── 日预算 ──
  const dailyYuan = fenToYuan(adgroup.daily_budget);
  let dailyValue;
  if (dailyYuan == null) {
    dailyValue = "未设置";
  } else if (Number(adgroup.daily_budget) === 0) {
    dailyValue = "不限";
  } else {
    dailyValue = `${dailyYuan} 元`;
  }

  // ── 定向 ──
  const targetingBrief = buildTargetingBrief(adgroup.targeting);

  // ── 状态（始终展示） ──
  const statusCn = adgroup.configured_status != null
    ? translateOrFallback(adgroup.configured_status, CONFIGURED_STATUS_CN)
    : null;

  // ── 按行收集 ──
  const lines = [];
  lines.push(`- 状态：${statusCn || "未知"}`);
  lines.push(`- 出价：${bidValue}`);
  // 转化目标 ID（与出价配对）
  if (adgroup.conversion_id != null && adgroup.conversion_id !== "" && Number(adgroup.conversion_id) > 0) {
    lines.push(`- 转化目标 ID：${adgroup.conversion_id}`);
  }
  lines.push(`- 日预算：${dailyValue}`);
  lines.push(`- 定向：${targetingBrief}`);

  // 智投场景
  if (isSmart) {
    const platCn = translateOrFallback(adgroup.smart_delivery_platform, SMART_PLATFORM_CN);
    lines.push(`- 智投场景：${platCn}`);
  }

  // 总消耗限额
  const totalYuan = fenToYuan(adgroup.total_budget);
  if (totalYuan != null && Number(adgroup.total_budget) > 0) {
    lines.push(`- 总消耗限额：${totalYuan} 元`);
  }

  // 深度优化
  if (adgroup.deep_conversion_worth_rate != null && adgroup.deep_conversion_worth_rate !== 0) {
    lines.push(`- 深度ROI：${adgroup.deep_conversion_worth_rate}`);
  }
  if (adgroup.deep_conversion_worth_advanced_rate != null && adgroup.deep_conversion_worth_advanced_rate !== 0) {
    lines.push(`- 深度辅助ROI：${adgroup.deep_conversion_worth_advanced_rate}`);
  }
  const deepBidYuan = fenToYuan(adgroup.deep_conversion_behavior_bid);
  if (deepBidYuan != null && Number(adgroup.deep_conversion_behavior_bid) > 0) {
    lines.push(`- 深度出价：${deepBidYuan} 元`);
  }
  const deepAdvBidYuan = fenToYuan(adgroup.deep_conversion_behavior_advanced_bid);
  if (deepAdvBidYuan != null && Number(adgroup.deep_conversion_behavior_advanced_bid) > 0) {
    lines.push(`- 深度辅助出价：${deepAdvBidYuan} 元`);
  }

  // 一键起量（常规广告专属，但智投返回 false 时也安全省略）
  if (adgroup.auto_acquisition_enabled === true) {
    const autoYuan = fenToYuan(adgroup.auto_acquisition_budget);
    lines.push(autoYuan != null ? `- 一键起量预算：${autoYuan} 元` : "- 已开启一键起量");
  }

  // AIGC / 全库智选（智投专属）
  if (adgroup.smart_delivery_aigc_creative?.is_open === true) {
    lines.push("- AIGC创意已开启");
  }
  if (adgroup.smart_delivery_history_comp_reused_creative?.is_open === true) {
    lines.push("- 全库智选已开启");
  }

  // 自动衍生创意
  if (adgroup.auto_derived_creative_enabled === true) {
    lines.push("- 已开自动衍生创意");
  }

  // 版位（仅常规广告，智投强制自动版位仍然展示一条）
  const siteBrief = buildSiteSetBrief(adgroup);
  if (siteBrief) lines.push(`- 版位：${siteBrief}`);

  // 投放时段
  const scheduleBrief = buildScheduleBrief(adgroup.begin_date, adgroup.end_date);
  if (scheduleBrief) lines.push(`- 投放时段：${scheduleBrief}`);

  // 素材包
  if (adgroup.material_package_id != null && adgroup.material_package_id !== "") {
    lines.push(`- 素材包 ID：${adgroup.material_package_id}`);
  }

  // ── 拼接首行 + 列表 ──
  const accountPrefix = accountStr ? `账户 ${accountStr} 下，` : "";
  const updatedFieldsHint = Array.isArray(opts.updatedFields) && opts.updatedFields.length > 0
    ? `（本次更新：${opts.updatedFields.join("、")}）`
    : "";
  const head = `${accountPrefix}${entityCn}「${name}」(ID: ${idStr}) 最新状态${updatedFieldsHint}：`;
  return `${head}\n${lines.join("\n")}`;
}
