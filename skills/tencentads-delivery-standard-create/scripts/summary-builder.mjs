/**
 * summary-builder.mjs — 创建成功后的中文回执拼装（常规广告版）
 *
 * 设计原则（钱相关字段必出，未命中枚举用 API 原值兜底，不报错不阻塞）:
 *   - 核心字段（必出）: 账户 ID、营销单元 ID、名称、出价方式+金额+优化目标、出价场景、日预算、定向 brief
 *   - 按需追加: 总消耗限额、深度优化、一键起量、搜索词出价、搜索扩量、版位、投放时段、上线状态、素材包
 *   - 金额单位 分→元（÷100，保留 2 位小数）
 *   - 定向全空时显示"全量投放"
 *   - 输出格式: 首行标题 + 多行 Markdown 列表（每项一行，便于 Agent 原样复读）
 *
 * 仅导出 buildSummaryText；其余字典/helper 内部使用。
 */

// ─── 中文翻译字典 ───

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

// optimization_goal 翻译表（覆盖数据集中实际出现的全部 11 个枚举）
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

// smart_bid_type 翻译表
const SMART_BID_TYPE_CN = {
  SMART_BID_TYPE_CUSTOM: "手动出价",
  SMART_BID_TYPE_SYSTEMATIC: "最大转化",
};

// bid_scene 翻译表
const BID_SCENE_CN = {
  BID_SCENE_NORMAL_AVERAGE: "均值出价",
  BID_SCENE_NORMAL_MAX: "最大转化",
  BID_SCENE_UNKNOWN: null, // 未知值不展示
};

// configured_status 翻译表（用户期望状态）
// AD_STATUS_NORMAL = 已启用、AD_STATUS_SUSPEND = 已暂停
const CONFIGURED_STATUS_CN = {
  AD_STATUS_NORMAL: "已启用",
  AD_STATUS_SUSPEND: "已暂停",
  AD_STATUS_DELETE: "已删除",
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
  return cn.length === 2 ? null : cn.join("、"); // 两种都选 = 不限性别
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

function buildSiteSetBrief(finalBody) {
  if (finalBody.automatic_site_enabled === true) return "自动版位";
  if (!Array.isArray(finalBody.site_set) || finalBody.site_set.length === 0) return null;
  return finalBody.site_set.map((s) => translateOrFallback(s, SITE_SET_CN)).join("、");
}

function buildScheduleBrief(begin, end) {
  if (!begin) return null;
  if (!end || end === "") return `${begin} 起长期投放`;
  return `${begin} ~ ${end}`;
}

// ─── 主函数 ───

/**
 * 将营销单元的关键字段拼装成单段中文回执。
 *
 * 支持两种模式（mode）：
 *   - 'create' (默认)：创建成功后调用，输入是发给 adgroups/add 的 finalBody。
 *     首行 "...创建成功。"
 *   - 'update'：更新或回查后调用，输入是 adgroups/get 返回的 list[0]（最新完整状态）。
 *     首行 "...最新状态。"
 *
 * @param {Object} originalInput - 用户原始入参（仅用于读取 account_id / adgroup_name 兜底）
 * @param {Object} finalBody - finalBody（create 模式）或 adgroups/get 返回的 adgroup 对象（update 模式）
 * @param {number|string|null} adgroupId - API 返回的营销单元 ID
 * @param {Object} [opts]
 * @param {'create'|'update'} [opts.mode='create']
 * @returns {string} 首行标题 + 多行列表的中文回执
 */
export function buildSummaryText(originalInput, finalBody, adgroupId, opts = {}) {
  const mode = opts.mode === "update" ? "update" : "create";
  const idStr = adgroupId != null ? adgroupId : (finalBody.adgroup_id != null ? finalBody.adgroup_id : "未知");
  const name = finalBody.adgroup_name || originalInput.adgroup_name || "未命名";
  const accountStr = originalInput.account_id != null
    ? String(originalInput.account_id)
    : (finalBody.account_id != null ? String(finalBody.account_id) : null);

  // ── 出价 ──
  // 拼接逻辑：
  //   - 基本：<bid_mode> <amount> 元/<optimization_goal_cn>
  //   - 后缀：<bid_scene_cn> 或 <smart_bid_type_cn>（仅 SYSTEMATIC 时显示"最大转化"）
  //   - SYSTEMATIC 场景 bid_amount 可不传 → 直接显示"<bid_mode> 最大转化出价"
  const bidModeCn = translateOrFallback(finalBody.bid_mode, BID_MODE_CN);
  const bidAmountYuan = fenToYuan(finalBody.bid_amount);
  const optGoalCn = finalBody.optimization_goal
    ? (OPTIMIZATION_GOAL_CN[finalBody.optimization_goal] || null)
    : null;
  const bidSceneCn = finalBody.bid_scene
    ? (BID_SCENE_CN[finalBody.bid_scene] != null ? BID_SCENE_CN[finalBody.bid_scene] : null)
    : null;
  const isSystematic = finalBody.smart_bid_type === "SMART_BID_TYPE_SYSTEMATIC";

  let bidValue;
  if (bidAmountYuan != null && Number(finalBody.bid_amount) > 0) {
    bidValue = `${bidModeCn} ${bidAmountYuan} 元`;
    if (optGoalCn) bidValue += `/${optGoalCn}`;
  } else {
    bidValue = isSystematic ? `${bidModeCn} 最大转化出价` : `${bidModeCn} 自动出价`;
    if (optGoalCn) bidValue += `（按${optGoalCn}）`;
  }
  // 出价场景后缀（避免与 SYSTEMATIC 重复显示"最大转化"）
  if (bidSceneCn && !(isSystematic && bidSceneCn === "最大转化")) {
    bidValue += `（${bidSceneCn}）`;
  }

  // ── 日预算 ──
  const dailyYuan = fenToYuan(finalBody.daily_budget);
  let dailyValue;
  if (dailyYuan == null) {
    dailyValue = "未设置";
  } else if (Number(finalBody.daily_budget) === 0) {
    dailyValue = "不限";
  } else {
    dailyValue = `${dailyYuan} 元`;
  }

  // ── 定向 ──
  const targetingBrief = buildTargetingBrief(finalBody.targeting);

  // ── 按行收集（每行一条） ──
  const lines = [];
  lines.push(`- 出价：${bidValue}`);
  // 转化目标 ID（与出价配对：出价 5 元/激活，转化哪条事件）
  if (finalBody.conversion_id != null && finalBody.conversion_id !== "" && Number(finalBody.conversion_id) > 0) {
    lines.push(`- 转化目标 ID：${finalBody.conversion_id}`);
  }
  lines.push(`- 日预算：${dailyValue}`);
  lines.push(`- 定向：${targetingBrief}`);

  // 总消耗限额
  const totalYuan = fenToYuan(finalBody.total_budget);
  if (totalYuan != null && Number(finalBody.total_budget) > 0) {
    lines.push(`- 总消耗限额：${totalYuan} 元`);
  }

  // 深度优化（涉及钱）
  if (finalBody.deep_conversion_worth_rate != null) {
    lines.push(`- 深度ROI：${finalBody.deep_conversion_worth_rate}`);
  }
  if (finalBody.deep_conversion_worth_advanced_rate != null) {
    lines.push(`- 深度辅助ROI：${finalBody.deep_conversion_worth_advanced_rate}`);
  }
  const deepBidYuan = fenToYuan(finalBody.deep_conversion_behavior_bid);
  if (deepBidYuan != null && Number(finalBody.deep_conversion_behavior_bid) > 0) {
    lines.push(`- 深度出价：${deepBidYuan} 元`);
  }
  const deepAdvBidYuan = fenToYuan(finalBody.deep_conversion_behavior_advanced_bid);
  if (deepAdvBidYuan != null && Number(finalBody.deep_conversion_behavior_advanced_bid) > 0) {
    lines.push(`- 深度辅助出价：${deepAdvBidYuan} 元`);
  }

  // 一键起量预算（涉及钱）
  if (finalBody.auto_acquisition_enabled === true) {
    const autoYuan = fenToYuan(finalBody.auto_acquisition_budget);
    lines.push(autoYuan != null ? `- 一键起量预算：${autoYuan} 元` : "- 已开启一键起量");
  }

  // 搜索词出价（涉及钱）
  if (Array.isArray(finalBody.search_bidwords) && finalBody.search_bidwords.length > 0) {
    const prices = finalBody.search_bidwords
      .map((w) => Number(w?.bid_price))
      .filter((p) => !isNaN(p) && p > 0);
    if (prices.length > 0) {
      const maxPrice = (Math.max(...prices) / 100).toFixed(2);
      lines.push(`- 搜索词：${finalBody.search_bidwords.length} 个，最高出价 ${maxPrice} 元`);
    } else {
      lines.push(`- 搜索词：${finalBody.search_bidwords.length} 个`);
    }
  }

  // 搜索扩量（影响流量来源）
  if (finalBody.search_expansion_switch === "SEARCH_EXPANSION_SWITCH_OPEN") {
    lines.push("- 已开搜索扩量");
  }

  // 探索策略（仅 STEADY_EXPLORATION 才提示，AUTOMATIC 是常见默认值省略）
  if (finalBody.exploration_strategy === "STEADY_EXPLORATION") {
    lines.push("- 稳步探索");
  }

  // 自动衍生创意
  if (finalBody.auto_derived_creative_enabled === true) {
    lines.push("- 已开自动衍生创意");
  }

  // 投放版位（手动版位时）
  const siteBrief = buildSiteSetBrief(finalBody);
  if (siteBrief) lines.push(`- 版位：${siteBrief}`);

  // 投放时段
  const scheduleBrief = buildScheduleBrief(finalBody.begin_date, finalBody.end_date);
  if (scheduleBrief) lines.push(`- 投放时段：${scheduleBrief}`);

  // 状态展示
  // - create 模式：始终展示"已启用 / 已暂停 / 已删除"。SUSPEND 是默认值但仍要陈列，
  //   让用户清楚知道刚创建的单元当前是开是关，避免误以为创建即上线。
  // - update 模式：同样始终展示当前状态。
  const statusCn = finalBody.configured_status != null
    ? translateOrFallback(finalBody.configured_status, CONFIGURED_STATUS_CN)
    : null;
  if (statusCn) lines.push(`- 状态：${statusCn}`);

  // 素材包
  if (finalBody.material_package_id != null && finalBody.material_package_id !== "") {
    lines.push(`- 素材包 ID：${finalBody.material_package_id}`);
  }

  // ── 拼接首行 + 列表 ──
  const accountPrefix = accountStr ? `账户 ${accountStr} 下，` : "";
  const headSuffix = mode === "update" ? "最新状态：" : "创建成功。";
  const head = `${accountPrefix}营销单元「${name}」(ID: ${idStr}) ${headSuffix}`;
  return `${head}\n${lines.join("\n")}`;
}
