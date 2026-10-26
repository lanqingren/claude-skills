#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一人电商运营助手 / SoloEcom Pilot
====================================
选品 · 定价 · 内容 · 客服 · 合规 · 数据诊断

专为一人公司(OPC)电商创业者设计的全链路运营决策助手

作者: [你的名字]
版本: 1.1.0
日期: 2026-05-23
"""

import json
import re
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


# =============================================================================
# 核心数据模型
# =============================================================================

class Platform(Enum):
    """电商平台"""
    TAOBAO = "淘宝"
    TMALL = "天猫"
    PDD = "拼多多"
    DOUYIN = "抖音"
    XIAOHONGSHU = "小红书"
    JD = "京东"


class HealthStatus(Enum):
    """健康状态"""
    GOOD = "🟢"
    WARNING = "🟡"
    DANGER = "🔴"


# =============================================================================
# 平台扣点数据（P1改进：增加类目维度）
# =============================================================================

# 默认扣点（无类目时使用）
PLATFORM_RATES = {
    Platform.TAOBAO: {"min": 0.005, "max": 0.01, "default": 0.008},
    Platform.TMALL: {"min": 0.02, "max": 0.05, "default": 0.04},
    Platform.PDD: {"min": 0.006, "max": 0.03, "default": 0.015},
    Platform.DOUYIN: {"min": 0.02, "max": 0.10, "default": 0.05},
    Platform.XIAOHONGSHU: {"min": 0.05, "max": 0.20, "default": 0.10},
    Platform.JD: {"min": 0.03, "max": 0.08, "default": 0.05},
}

# 类目级扣点表（平台×类目）
CATEGORY_COMMISSIONS = {
    # 淘宝（个人店多数类目0.6%-1%）
    (Platform.TAOBAO, "服装鞋包"): 0.005,
    (Platform.TAOBAO, "3C数码"):   0.005,
    (Platform.TAOBAO, "家居日用"): 0.005,
    (Platform.TAOBAO, "美妆个护"): 0.008,
    (Platform.TAOBAO, "食品饮料"): 0.005,
    (Platform.TAOBAO, "母婴玩具"): 0.005,
    (Platform.TAOBAO, "珠宝首饰"): 0.008,
    # 天猫
    (Platform.TMALL, "服装鞋包"): 0.05,
    (Platform.TMALL, "3C数码"):   0.03,
    (Platform.TMALL, "美妆个护"): 0.04,
    (Platform.TMALL, "家居日用"): 0.03,
    (Platform.TMALL, "食品饮料"): 0.02,
    # 抖音
    (Platform.DOUYIN, "服装鞋包"): 0.05,
    (Platform.DOUYIN, "3C数码"):   0.03,
    (Platform.DOUYIN, "食品饮料"): 0.02,
    (Platform.DOUYIN, "美妆个护"): 0.05,
    (Platform.DOUYIN, "珠宝首饰"): 0.08,
    (Platform.DOUYIN, "家居日用"): 0.03,
    # 小红书
    (Platform.XIAOHONGSHU, "服装鞋包"): 0.10,
    (Platform.XIAOHONGSHU, "美妆个护"): 0.15,
    (Platform.XIAOHONGSHU, "食品饮料"): 0.05,
    (Platform.XIAOHONGSHU, "家居日用"): 0.10,
    # 拼多多
    (Platform.PDD, "服装鞋包"): 0.01,
    (Platform.PDD, "3C数码"):   0.01,
    (Platform.PDD, "食品饮料"): 0.008,
    (Platform.PDD, "美妆个护"): 0.015,
    (Platform.PDD, "家居日用"): 0.008,
    # 京东
    (Platform.JD, "服装鞋包"): 0.08,
    (Platform.JD, "3C数码"):   0.03,
    (Platform.JD, "美妆个护"): 0.05,
    (Platform.JD, "食品饮料"): 0.03,
    (Platform.JD, "家居日用"): 0.05,
}

# 常见类目别名映射（用户输入模糊匹配）
CATEGORY_ALIASES = {
    "服装鞋包": ["服装", "鞋", "包", "服饰", "女装", "男装", "童装", "鞋子", "箱包"],
    "3C数码": ["数码", "手机", "电脑", "耳机", "充电器", "数码配件", "3c"],
    "美妆个护": ["美妆", "化妆品", "护肤品", "个护", "面膜", "口红", "洗护"],
    "食品饮料": ["食品", "饮料", "零食", "茶叶", "咖啡", "保健品"],
    "家居日用": ["家居", "日用品", "家纺", "厨具", "收纳", "清洁"],
    "母婴玩具": ["母婴", "玩具", "婴儿", "童装", "奶粉", "纸尿裤"],
    "珠宝首饰": ["珠宝", "首饰", "黄金", "银饰", "钻石", "手表"],
}


# =============================================================================
# 广告法违禁词库（P2改进：支持从JSON文件加载）
# =============================================================================

PROHIBITED_WORDS = {
    "绝对化用语": [
        "最", "最佳", "最好", "最优", "最强", "最大", "最高", "最低",
        "最便宜", "最先进", "最流行", "最受欢迎", "最安全", "第一",
        "唯一", "首个", "首选", "首款", "第一品牌", "销量第一",
        "排名第一", "顶级", "极品", "绝版", "终极",
        "全网首发", "全国首发", "世界级", "国家级", "驰名",
    ],
    "权威性误导": [
        "国家免检", "质量免检", "免检产品", "特供", "专供",
        "指定", "推荐品牌", "XX协会推荐",
    ],
    "虚假承诺": [
        "100%有效", "100%", "永久", "包治百病", "绝对有效",
        "无效退款", "零风险", "无副作用", "药到病除",
        "立竿见影", "一用就灵", "万能",
    ],
    "夸大功效": [
        "速效", "神效", "奇效", "特效", "强效", "高效",
        "彻底清除", "根除", "完全", "绝对安全",
    ],
    "伪科学": [
        "科学证明", "医学认证", "临床证明", "权威认证",
        "经XX机构认证",
    ],
    "诱导消费": [
        "马上抢", "仅剩X件", "不买后悔", "错过再等一年",
        "最后一天", "限时秒杀", "抢疯了",
    ],
    "价格违规": [
        "原价", "特价", "跳楼价", "白菜价", "亏本甩卖",
    ],
}

REPLACEMENT_SUGGESTIONS = {
    "最": "优选/人气之选",
    "第一": "领先/前列",
    "唯一": "独特/专属",
    "100%": "显著/高效",
    "永久": "持久/长效",
    "国家级": "品牌自研/匠心打造",
    "原价": "日常价（需有真实交易记录）",
}


# =============================================================================
# P1: 平台规则更新提醒
# =============================================================================

PLATFORM_RULES_UPDATES = {
    "2026-Q2": [
        {"platform": "抖音", "change": "珠宝类目佣金调整为5%-10%", "impact": "定价需重新计算扣点"},
        {"platform": "小红书", "change": "个人店限制每日发布商品数量", "impact": "新品上架节奏需调整"},
        {"platform": "拼多多", "change": "百亿补贴门槛调整，需提供近30天销量数据", "impact": "报名条件变化"},
        {"platform": "淘宝", "change": "商品标题新增违规词自动检测机制", "impact": "标题需更加注意合规"},
    ],
}


# =============================================================================
# P0: 智能选品引擎（新增）
# =============================================================================

class MarketIntel:
    """智能选品引擎 - 交互式问卷 + 内置品类知识库"""

    # 内置品类知识库
    CATEGORY_KB = {
        "蓝牙耳机": {
            "market_heat": 4, "competition": 4, "profit_margin": 4,
            "seasonality": 1, "supply_barrier": 2,
            "avg_margin_range": "35-50%",
            "min_moq": 50, "supply_cycle": "3-7天",
            "solo_friendly": "中",
            "risks": ["头部品牌集中(漫步者/小米/华为)", "价格战激烈", "同质化严重"],
            "tips": ["建议切入细分场景(运动/游戏/降噪)", "轻资产一件代发优先", "主打性价比或差异化设计"],
            "solo_risk_note": "竞争激烈但供应链成熟，适合有差异化卖点的一人公司",
        },
        "手机壳": {
            "market_heat": 5, "competition": 5, "profit_margin": 3,
            "seasonality": 1, "supply_barrier": 1,
            "avg_margin_range": "30-60%",
            "min_moq": 10, "supply_cycle": "1-3天",
            "solo_friendly": "高",
            "risks": ["同质化极严重", "价格战激烈", "新品生命周期短"],
            "tips": ["主打设计差异化(原创图案/联名)", "紧跟新机型发布节奏", "多SKU铺量策略"],
            "solo_risk_note": "供应链门槛极低，适合一人起步，但需持续出新",
        },
        "家居收纳": {
            "market_heat": 4, "competition": 2, "profit_margin": 4,
            "seasonality": 1, "supply_barrier": 2,
            "avg_margin_range": "40-60%",
            "min_moq": 30, "supply_cycle": "5-10天",
            "solo_friendly": "高",
            "risks": ["季节性促销明显(618/双11)", "物流成本占比高(大件)"],
            "tips": ["主打细分场景(厨房/桌面/衣柜)", "短视频展示使用前后对比", "组合套装提高客单价"],
            "solo_risk_note": "竞争适中利润空间好，一人公司友好度高",
        },
        "食品零食": {
            "market_heat": 5, "competition": 4, "profit_margin": 3,
            "seasonality": 2, "supply_barrier": 3,
            "avg_margin_range": "25-45%",
            "min_moq": 100, "supply_cycle": "7-15天",
            "solo_friendly": "中",
            "risks": ["食品安全合规要求高", "保质期管理压力大", "退换货率高"],
            "tips": ["选择长保质期产品", "注意食品经营许可证", "首单小批量试销"],
            "solo_risk_note": "复购率高但合规门槛高，需办理食品经营许可证",
        },
        "美妆工具": {
            "market_heat": 4, "competition": 3, "profit_margin": 5,
            "seasonality": 1, "supply_barrier": 2,
            "avg_margin_range": "50-70%",
            "min_moq": 30, "supply_cycle": "5-10天",
            "solo_friendly": "高",
            "risks": ["成分安全需关注", "包装成本占比高"],
            "tips": ["主打细分功能(修容/美甲/脱毛)", "短视频教程式营销效果好", "搭配美妆博主推广"],
            "solo_risk_note": "利润空间大供应链成熟，非常适合一人公司",
        },
        "宠物用品": {
            "market_heat": 5, "competition": 3, "profit_margin": 4,
            "seasonality": 1, "supply_barrier": 2,
            "avg_margin_range": "35-55%",
            "min_moq": 50, "supply_cycle": "5-10天",
            "solo_friendly": "高",
            "risks": ["宠物食品安全标准", "品牌忠诚度高新品牌难切入"],
            "tips": ["主打功能性产品(智能喂食器/饮水机)", "宠物主人情感消费意愿强", "内容营销效果好"],
            "solo_risk_note": "市场增长快利润好，一人公司友好",
        },
        "数码配件": {
            "market_heat": 4, "competition": 4, "profit_margin": 3,
            "seasonality": 1, "supply_barrier": 1,
            "avg_margin_range": "20-40%",
            "min_moq": 20, "supply_cycle": "3-5天",
            "solo_friendly": "高",
            "risks": ["利润率偏低", "产品质量问题多", "售后率较高"],
            "tips": ["主打差异化设计/材质", "组合套装提高客单价", "注意品控减少售后"],
            "solo_risk_note": "供应链成熟门槛低，适合起步但需注重品控",
        },
        "手工/文创": {
            "market_heat": 3, "competition": 2, "profit_margin": 5,
            "seasonality": 2, "supply_barrier": 1,
            "avg_margin_range": "50-80%",
            "min_moq": 1, "supply_cycle": "按需制作",
            "solo_friendly": "极高",
            "risks": ["产能有限难规模化", "手工品质不稳定"],
            "tips": ["主打原创设计和故事感", "小红书/抖音内容种草效果好", "限量发售制造稀缺感"],
            "solo_risk_note": "最适合一人公司的品类，零库存按需生产",
        },
    }

    # 交互式问卷
    QUESTIONNAIRE = [
        {
            "dimension": "market_heat",
            "question": "该品类您了解的月搜索热度大概是？",
            "options": {
                "A (<1万)": 1, "B (1-5万)": 2, "C (5-20万)": 3, "D (>20万)": 4
            }
        },
        {
            "dimension": "competition",
            "question": "该品类头部品牌/卖家占比大概多少？",
            "options": {
                "A (<20%)": 4, "B (20-40%)": 3, "C (40-60%)": 2, "D (>60%)": 1
            }
        },
        {
            "dimension": "profit_margin",
            "question": "您的采购成本占竞品售价的比例大概是？",
            "options": {
                "A (<30%)": 5, "B (30-50%)": 4, "C (50-70%)": 2, "D (>70%)": 1
            }
        },
        {
            "dimension": "seasonality",
            "question": "该品类的销售淡旺季明显吗？（分数越高=越稳定）",
            "options": {
                "A (全年稳定)": 5, "B (轻微波动)": 4, "C (有明显淡旺季)": 2, "D (季节性极强)": 1
            }
        },
        {
            "dimension": "supply_barrier",
            "question": "供应商最低起订量和供货周期？（分数越高=门槛越低）",
            "options": {
                "A (一件代发)": 5, "B (10-50件/3-7天)": 4, "C (50-200件/7-15天)": 2, "D (>200件/>15天)": 1
            }
        },
    ]

    @staticmethod
    def resolve_category(user_input: str) -> Optional[str]:
        """模糊匹配用户输入到标准品类名"""
        user_input = user_input.strip()
        # 先精确匹配
        for cat in MarketIntel.CATEGORY_KB:
            if cat in user_input or user_input in cat:
                return cat
        # 再别名匹配
        for standard_cat, aliases in CATEGORY_ALIASES.items():
            for alias in aliases:
                if alias in user_input:
                    return standard_cat
        return None

    def analyze_from_kb(self, category: str) -> dict:
        """从内置知识库分析品类"""
        if category not in self.CATEGORY_KB:
            return None
        kb = self.CATEGORY_KB[category]
        scores = {
            "市场容量": kb["market_heat"],
            "竞争强度": 5 - kb["competition"],  # 竞争低=分数高
            "利润空间": kb["profit_margin"],
            "季节稳定性": kb["seasonality"],
            "供应链友好度": 5 - kb["supply_barrier"] + 1,  # 门槛低=分数高
        }
        avg_score = sum(scores.values()) / len(scores)
        return {
            "category": category,
            "scores": scores,
            "avg_score": round(avg_score, 1),
            "avg_margin_range": kb["avg_margin_range"],
            "min_moq": kb["min_moq"],
            "supply_cycle": kb["supply_cycle"],
            "solo_friendly": kb["solo_friendly"],
            "risks": kb["risks"],
            "tips": kb["tips"],
            "solo_risk_note": kb["solo_risk_note"],
            "recommendation": "推荐" if avg_score >= 3.5 else "谨慎" if avg_score >= 2.5 else "回避",
        }

    def analyze_from_questionnaire(self, answers: dict) -> dict:
        """从问卷答案分析"""
        scores = {}
        for q in self.QUESTIONNAIRE:
            dim = q["dimension"]
            answer_key = answers.get(dim, "")
            for opt_text, score in q["options"].items():
                if answer_key in opt_text or opt_text.startswith(answer_key):
                    scores[dim] = score
                    break
            else:
                scores[dim] = 3  # 默认中等

        dim_names = {
            "market_heat": "市场容量",
            "competition": "竞争强度（低=好）",
            "profit_margin": "利润空间",
            "seasonality": "季节稳定性",
            "supply_barrier": "供应链友好度",
        }
        named_scores = {dim_names.get(k, k): v for k, v in scores.items()}
        avg_score = sum(scores.values()) / len(scores)

        return {
            "scores": named_scores,
            "avg_score": round(avg_score, 1),
            "recommendation": "推荐" if avg_score >= 3.5 else "谨慎" if avg_score >= 2.5 else "回避",
            "source": "questionnaire",
        }

    def generate_selection_report(self, result: dict) -> str:
        """生成选品分析报告"""
        if result is None:
            return "❌ 未找到该品类的分析数据。请尝试其他品类名称，或使用交互式问卷模式。"

        report = f"""# 选品分析报告

## 📊 品类：{result.get('category', '自定义品类')}

### 五维评分卡（1-5分）

| 维度 | 评分 | 说明 |
|------|------|------|
"""
        for dim, score in result.get("scores", {}).items():
            bar = "★" * score + "☆" * (5 - score)
            report += f"| {dim} | {bar} {score}/5 |\n"

        avg = result["avg_score"]
        rec = result["recommendation"]
        rec_emoji = "✅" if rec == "推荐" else "⚠️" if rec == "谨慎" else "🔴"
        report += f"""
### 综合评估

- **平均分**：{avg}/5
- **建议**：{rec_emoji} **{rec}**
- **一人公司友好度**：{result.get('solo_friendly', '未知')}
"""

        if "avg_margin_range" in result:
            report += f"- **行业毛利率区间**：{result['avg_margin_range']}\n"
            report += f"- **最低起订量**：{result['min_moq']}件\n"
            report += f"- **供货周期**：{result['supply_cycle']}\n"

        if "risks" in result:
            report += "\n### ⚠️ 风险提示\n\n"
            for risk in result["risks"]:
                report += f"- {risk}\n"

        if "tips" in result:
            report += "\n### 💡 一人公司运营建议\n\n"
            for tip in result["tips"]:
                report += f"- {tip}\n"

        if "solo_risk_note" in result:
            report += f"\n### 📦 一人公司特别提醒\n\n{result['solo_risk_note']}\n"

        # 库存风险提示（P1改进）
        report += """
### 📦 库存风险提示

- 建议首单采购量不超过预估月销量的 **1.5 倍**，避免资金积压
- 优先选择支持**一件代发**的供应商，降低库存风险
- 季节性产品备货量建议不超过月销量的 **1 倍**
- 资金占用警戒线：库存金额不应超过月均销售额的 **50%**

---
⚠️ 各平台规则实时变动，请以您所在平台的最新商家后台为准。
💡 如需计算该品类的定价和税费，可继续使用定价引擎和财务管家 Skill。
"""
        return report


# =============================================================================
# P0: 内容工厂（新增）
# =============================================================================

class ContentFactory:
    """内容工厂 - 标题/详情页/短视频/多平台适配"""

    # 平台标题模板
    TITLE_TEMPLATES = {
        Platform.TAOBAO: [
            "{brand}{category}{material}{feature}{scene}{style}",
            "{feature}{category} {material} {scene} {suffix}",
            "{brand}官方{category} {feature} {material} {style}",
        ],
        Platform.DOUYIN: [
            "{hook}！{product}让你{benefit}",
            "别再{pain}了！{product}帮你{benefit}",
            "{scene}必备！{product} {feature} {urgency}",
        ],
        Platform.XIAOHONGSHU: [
            "{pain}党必入！{scene}下的{product}神器",
            "被{product}惊艳到了！{feature}太绝了",
            "{benefit}全靠这个{product}！{scene}必备",
        ],
        Platform.PDD: [
            "{category}{feature}{material}{price_hint}{supply}",
            "{feature}{category} {material} {price_hint} {suffix}",
            "{supply}{category} {feature} {material} {price_hint}",
        ],
    }

    # 详情页框架（FAB法则）
    DETAIL_SECTIONS = [
        ("第一屏：痛点共鸣", "描述目标用户的3个核心痛点，让买家产生'这就是我的问题'的共鸣"),
        ("第二屏：产品展示", "核心卖点 + 使用场景实拍图，直观展示产品价值"),
        ("第三屏：功能详解", "逐条展开：Feature(功能) → Advantage(优势) → Benefit(利益)"),
        ("第四屏：信任背书", "材质认证/检测报告/销量数据/真实好评截图"),
        ("第五屏：规格参数", "尺寸/材质/颜色/重量/包装清单，消除购买疑虑"),
        ("第六屏：服务承诺", "发货时效/售后政策/退换货说明，降低购买决策门槛"),
    ]

    # 短视频脚本结构
    VIDEO_SCRIPTS = {
        "15s": [
            ("[0-3s] Hook钩子", "制造悬念/抛出痛点/反常识，3秒内抓住注意力"),
            ("[3-8s] 产品登场", "快速展示产品 + 核心卖点"),
            ("[8-12s] 效果展示", "使用前后对比/用户反馈"),
            ("[12-15s] CTA行动号召", "点击链接/关注店铺"),
        ],
        "30s": [
            ("[0-3s] Hook钩子", "制造悬念/抛出痛点/反常识"),
            ("[3-10s] 痛点放大", "展示用户真实痛点场景，引发共鸣"),
            ("[10-22s] 产品登场", "展示产品 + 核心卖点演示 + 使用场景"),
            ("[22-26s] 信任背书", "效果对比/用户评价/权威认证"),
            ("[26-30s] CTA行动号召", "限时优惠 + 点击链接/关注店铺"),
        ],
        "60s": [
            ("[0-3s] Hook钩子", "制造悬念/抛出痛点/反常识"),
            ("[3-10s] 痛点放大", "展示用户真实痛点场景，引发共鸣"),
            ("[10-30s] 产品登场", "详细展示产品 + 多个核心卖点演示"),
            ("[30-42s] 使用场景", "多个使用场景展示，覆盖不同用户需求"),
            ("[42-50s] 信任背书", "效果对比/用户评价/权威认证/销量数据"),
            ("[50-55s] 限时优惠", "价格锚点 + 限时限量，制造紧迫感"),
            ("[55-60s] CTA行动号召", "点击链接/关注店铺/评论区互动"),
        ],
    }

    # 多平台风格适配规则
    PLATFORM_STYLES = {
        Platform.TAOBAO: {"tone": "信息密集", "tips": "核心关键词靠前放置（前10字权重最高），不建议全部写满30字，预留2-3字给长尾词"},
        Platform.DOUYIN: {"tone": "口语化、情绪化", "tips": "短句为主，多用感叹号，突出场景和利益点"},
        Platform.XIAOHONGSHU: {"tone": "种草风、个人体验感", "tips": "多用emoji，以第一人称视角，强调真实使用感受"},
        Platform.PDD: {"tone": "简洁、突出性价比", "tips": "堆叠核心关键词，突出价格优势"},
    }

    def generate_titles(self, product: str, features: list, platform: Platform, brand: str = "") -> list:
        """生成商品标题方案"""
        templates = self.TITLE_TEMPLATES.get(platform, self.TITLE_TEMPLATES[Platform.TAOBAO])
        feature_str = "".join(features[:3])  # 最多取3个卖点

        results = []
        for tpl in templates:
            title = tpl.format(
                brand=brand + " " if brand else "",
                category=product,
                material=features[1] if len(features) > 1 else "",
                feature=feature_str,
                scene="",
                style="",
                hook=f'别再{features[0]}了' if features else '看这里',
                benefit=f'轻松{features[0]}' if features else '解决问题',
                pain=features[0] if features else "烦恼",
                product=product,
                urgency="限时特惠",
                price_hint="超值",
                supply="厂家直发",
                suffix="热销",
            ).strip()
            # 去除多余空格
            title = re.sub(r'\s{2,}', ' ', title)
            results.append(title)

        return results

    def generate_detail_page(self, product: str, features: list, target_user: str = "年轻白领") -> str:
        """生成详情页文案框架"""
        report = f"""# {product} 详情页文案

## 目标用户：{target_user}

"""
        for section_title, section_desc in self.DETAIL_SECTIONS:
            report += f"### {section_title}\n\n{section_desc}\n\n"

        # 基于用户输入的卖点生成FAB内容
        if features:
            report += "### 卖点FAB展开\n\n"
            for i, feat in enumerate(features, 1):
                report += f"""**卖点{i}：{feat}**
- **Feature（功能）**：本产品具备{feat}功能
- **Advantage（优势）**：相比同类产品，我们的{feat}更加出色
- **Benefit（利益）**：让您可以{feat}，省时省力省心

"""
        report += "---\n⚠️ 各平台规则实时变动，请以您所在平台的最新商家后台为准。\n"
        return report

    def generate_video_script(self, product: str, features: list, duration: str = "30s") -> str:
        """生成短视频脚本"""
        script_data = self.VIDEO_SCRIPTS.get(duration, self.VIDEO_SCRIPTS["30s"])

        report = f"""# {product} 短视频脚本（{duration}）

"""
        for time_slot, content in script_data:
            report += f"### {time_slot}\n{content}\n\n"

        # 基于卖点填充具体内容
        if features:
            report += "### 🎬 参考文案\n\n"
            hook = f"你还在为{features[0]}烦恼吗？"
            showcase = f"看看这款{product}，{features[0]}效果太绝了！"
            cta = f"点击下方链接，{product}限时优惠中，手慢无！"
            report += f"- **Hook**: {hook}\n"
            report += f"- **展示**: {showcase}\n"
            report += f"- **CTA**: {cta}\n"

        return report

    def adapt_content(self, content: str, target_platform: Platform) -> str:
        """多平台内容适配改写"""
        style = self.PLATFORM_STYLES.get(target_platform, {})
        tone = style.get("tone", "通用")
        tips = style.get("tips", "")

        report = f"""# 内容适配：{target_platform.value}版

## 风格：{tone}
{tips}

## 适配后内容：

"""
        # 基于平台风格简单改写提示
        if target_platform == Platform.DOUYIN:
            report += f"[口语化改写] 将原文改为短句、感叹号、情绪化表达：\n\n{content}\n"
        elif target_platform == Platform.XIAOHONGSHU:
            report += f"[种草风改写] 加入emoji、第一人称体验感：\n\n{content}\n"
        elif target_platform == Platform.PDD:
            report += f"[简洁版] 突出性价比和核心关键词：\n\n{content}\n"
        else:
            report += f"[信息密集版] 补充关键词、突出功能参数：\n\n{content}\n"

        return report


# =============================================================================
# P0修复: 定价引擎（修复双重扣除bug + 增加类目参数）
# =============================================================================

class PricingEngine:
    """定价引擎"""

    @staticmethod
    def _get_platform_rate(platform: Platform, category: str = None, custom_rate: float = None) -> float:
        """获取平台扣点（支持类目和自定义覆盖）"""
        if custom_rate is not None:
            return custom_rate
        if category:
            # 模糊匹配类目
            for (plat, cat), rate in CATEGORY_COMMISSIONS.items():
                if plat == platform and (cat == category or cat in category or category in cat):
                    return rate
        return PLATFORM_RATES[platform]["default"]

    @staticmethod
    def calculate_price(
        purchase_cost: float,
        packaging_cost: float = 0,
        shipping_cost: float = 0,
        return_rate: float = 0.03,
        target_margin: float = 0.30,
        platform: Platform = Platform.TAOBAO,
        category: str = None,
        custom_rate: float = None,
        marketing_reserve: float = 0.05,
    ) -> dict:
        """
        计算建议售价

        Args:
            purchase_cost: 采购成本
            packaging_cost: 包装成本
            shipping_cost: 物流成本
            return_rate: 退换货损耗率（默认3%）
            target_margin: 目标毛利率（默认30%）
            platform: 销售平台
            category: 商品类目（可选，用于精确扣点）
            custom_rate: 自定义平台扣点（可选，覆盖所有计算）
            marketing_reserve: 营销预留比例（默认5%）
        """
        platform_rate = PricingEngine._get_platform_rate(platform, category, custom_rate)

        # 总成本（含退换货损耗）= （采购+包装+物流） × （1 + 退货率）
        base_cost = purchase_cost + packaging_cost + shipping_cost
        total_cost = base_cost * (1 + return_rate)

        # 建议售价 = 总成本 ÷ (1 - 平台扣点 - 营销预留 - 目标毛利率)
        denominator = 1 - platform_rate - marketing_reserve - target_margin
        if denominator <= 0:
            return {"error": "成本过高或利润率/扣点设置不合理，无法计算合理售价"}

        suggested_price = round(total_cost / denominator, 2)
        conservative = round(suggested_price * 0.90, 2)
        aggressive = round(suggested_price * 1.10, 2)

        # 利润模拟（P0修复：不再重复扣除退换货损耗）
        results = []
        for label, price in [("保守", conservative), ("建议", suggested_price), ("激进", aggressive)]:
            platform_fee = round(price * platform_rate, 2)
            marketing_cost = round(price * marketing_reserve, 2)
            # 毛利 = 售价 - 总成本(已含损耗) - 平台费 - 营销费
            gross_profit = round(price - total_cost - platform_fee - marketing_cost, 2)
            gross_margin = round(gross_profit / price * 100, 1) if price > 0 else 0
            results.append({
                "label": label,
                "price": price,
                "platform_fee": platform_fee,
                "marketing_cost": marketing_cost,
                "gross_profit": gross_profit,
                "gross_margin": gross_margin,
            })

        category_display = category if category else "未指定"
        return {
            "cost_breakdown": {
                "采购成本": purchase_cost,
                "包装成本": packaging_cost,
                "物流成本": shipping_cost,
                f"退换货损耗({return_rate*100:.0f}%)": round(base_cost * return_rate, 2),
                "总成本（含损耗）": round(total_cost, 2),
            },
            "platform": platform.value,
            "category": category_display,
            "platform_rate": f"{platform_rate * 100:.1f}%",
            "pricing_options": results,
        }

    @staticmethod
    def generate_pricing_report(pricing_data: dict) -> str:
        """生成定价报告"""
        if "error" in pricing_data:
            return f"❌ {pricing_data['error']}"

        report = f"""# 定价建议报告

## 💰 成本拆分

| 成本项 | 金额 |
|-------|------|
"""
        for item, amount in pricing_data["cost_breakdown"].items():
            report += f"| {item} | {amount:.2f}元 |\n"

        report += f"\n**平台**：{pricing_data['platform']} | **类目**：{pricing_data['category']} | **扣点**：{pricing_data['platform_rate']}\n"

        report += """
## 📊 三档定价方案

| 方案 | 售价 | 平台扣点 | 营销预留 | 毛利 | 毛利率 |
|------|------|---------|---------|------|-------|
"""
        for opt in pricing_data["pricing_options"]:
            report += (f"| {opt['label']} | {opt['price']:.2f}元 | "
                       f"{opt['platform_fee']:.2f}元 | {opt['marketing_cost']:.2f}元 | "
                       f"{opt['gross_profit']:.2f}元 | "
                       f"{opt['gross_margin']}% |\n")

        report += """
## ⚠️ 合规提醒

- **虚构原价**：标注"原价"必须有真实交易记录支撑（《价格法》第14条）
- **虚假折扣**：折后价不得高于近7日内最低成交价
- **价格标注**：使用"日常价""活动价"等替代"原价""特价"

## 💡 定价策略建议

- 新品上架建议使用**建议价**，观察市场反应后调整
- 如竞品价格低于建议价，可考虑**竞品跟随策略**
- 引流款可使用**保守价**，利润款使用**建议价或激进价**

## 📦 库存风险提示

- 建议首单采购量不超过预估月销量的 **1.5 倍**
- 优先选择支持**一件代发**的供应商

---
⚠️ 各平台规则实时变动，请以您所在平台的最新商家后台为准。
💡 如需计算本月的增值税和企业所得税，可调用「一人公司财务管家」Skill 进行自动计税。
"""
        return report


# =============================================================================
# 广告法合规检查器（P2改进：支持JSON文件加载）
# =============================================================================

class AdComplianceChecker:
    """广告法合规检查器"""

    def __init__(self, wordlist_path: str = None):
        if wordlist_path and os.path.exists(wordlist_path):
            with open(wordlist_path, "r", encoding="utf-8") as f:
                self.prohibited_words = json.load(f)
        else:
            self.prohibited_words = PROHIBITED_WORDS
        self.replacements = REPLACEMENT_SUGGESTIONS

    def check_text(self, text: str) -> dict:
        """检查文本中的违禁词"""
        violations = []
        cleaned = text

        for category, words in self.prohibited_words.items():
            for word in words:
                if word in text:
                    suggestion = self.replacements.get(word, "请替换为更客观的表述")
                    violations.append({
                        "word": word,
                        "category": category,
                        "suggestion": suggestion,
                    })
                    cleaned = cleaned.replace(word, f"【{word}→{suggestion}】")

        return {
            "is_compliant": len(violations) == 0,
            "violation_count": len(violations),
            "violations": violations,
            "cleaned_text": cleaned,
        }

    def generate_compliance_report(self, result: dict, original_text: str = "") -> str:
        """生成合规检查报告"""
        if result["is_compliant"]:
            return "✅ **合规检查通过**：未发现广告法违禁词。"

        report = f"""# 广告法合规检查报告

## 🚨 发现 {result['violation_count']} 处违规

| 违禁词 | 违规类别 | 替换建议 |
|-------|---------|---------|
"""
        for v in result["violations"]:
            report += f"| {v['word']} | {v['category']} | {v['suggestion']} |\n"

        report += "\n## 📝 修改后版本\n\n" + result["cleaned_text"]
        report += '\n\n## 📚 法律依据\n\n- 《广告法》第9条：广告不得使用\u201c国家级\u201d\u201c最高级\u201d\u201c最佳\u201d等用语\n- 《广告法》第11条：广告使用数据、统计资料等应当真实、准确\n- 《广告法》第28条：虚假广告认定标准\n'
        return report


# =============================================================================
# P1改进: 智能客服引擎（增加多轮追问预案 + 平台规则提醒）
# =============================================================================

class ServiceBot:
    """智能客服引擎"""

    PRE_SALE_TEMPLATES = {
        "尺寸规格": {
            "strategy": "引导提供信息 → 精准推荐",
            "template": "亲，为了给您推荐最合适的尺码/规格，方便告诉我您的{info_needed}吗？这样我可以给您最精准的建议~",
        },
        "真假正品": {
            "strategy": "品牌授权链 + 正品承诺",
            "template": "我们是{brand}官方授权店铺，每件商品都有防伪码，您可以拨打{brand_phone}验证真伪。支持假一赔十，请放心购买！",
        },
        "优惠砍价": {
            "strategy": "阶梯优惠话术",
            "round_1": "目前活动价已经是优惠价啦~ 不过满{threshold}元可以减{discount}元，还可以叠加会员{member_discount}折哦，非常划算！",
            "round_2": "亲，我理解您的心情~ 这个价格我们真的已经到底了，不过可以给您赠送{gift}作为心意，您看可以吗？",
            "round_3": "实在抱歉无法再低了，这个品质在这个价位性价比已经很高了。建议您先拍下体验，满意再回购，老客还有专属优惠哦~",
        },
        "发货物流": {
            "strategy": "时效承诺 + 查询引导",
            "template": "下单后{hours}小时内发货，一般{days}天左右到达。您可以在订单详情页实时查看物流信息，有任何问题随时联系客服~",
        },
        "退换货": {
            "strategy": "七日无理由退货说明",
            "template": "支持七日无理由退货哦！收到商品7天内不影响二次销售都可以退换。如有质量问题，运费由我们承担，请放心购买~",
        },
    }

    AFTER_SALE_DECISION_TREE = {
        "质量问题": {
            "steps": [
                "诚恳道歉，安抚情绪",
                "引导举证（拍照/视频展示问题）",
                "根据严重程度选择方案：轻微→补偿(优惠券/部分退款)；影响使用→补发/换货；严重→全额退款",
            ],
            "legal_note": "《消费者权益保护法》第24条：经营者提供的商品不符合质量要求的，消费者可退货、换货或修理。"
        },
        "物流问题": {
            "steps": [
                "查询物流状态",
                "未发货→催促发货+赔偿方案",
                "运输延误→联系快递催件+预计到达时间",
                "丢件/破损→联系快递索赔+补发或退款",
            ],
        },
        "不满意不喜欢": {
            "steps": [
                "引导七日无理由退货",
                "确认商品完好（未使用/未拆封/不影响二次销售）",
                "说明退货流程和运费承担",
            ],
            "legal_note": "《消费者权益保护法》第25条：通过网络方式购买的商品，消费者有权自收到商品之日起七日内退货。"
        },
        "差评处理": {
            "steps": [
                "分析差评原因（产品/服务/物流/恶意）",
                "产品问题→认领+改进方案+补偿",
                "服务问题→道歉+改进承诺",
                "物流问题→解释+改进",
                "恶意差评→客观回复+平台申诉+证据保全",
            ],
        },
    }

    BAD_REVIEW_TEMPLATES = {
        "产品质量": "非常抱歉给您带来不好的体验！我们已反馈给品控部门，问题已定位在{cause}，已改进。为表歉意，为您申请了{compensation}，希望您再给我们一次机会。",
        "物流问题": "很抱歉物流让您久等了！经查您的包裹因{cause}导致延误，我们已联系快递加强管理。下次下单我们会优先为您选择更快的物流方式。",
        "不合理差评": "感谢您的反馈。关于您提到的问题，实际情况是{fact}。我们已主动联系您沟通解决方案，如有疑问欢迎随时联系客服。",
    }

    def get_pre_sale_response(self, scenario: str, round_num: int = 1, **kwargs) -> str:
        """获取售前回复（支持多轮）"""
        if scenario not in self.PRE_SALE_TEMPLATES:
            return f"暂无该场景的预设话术，建议参考通用回复模板。"

        template_data = self.PRE_SALE_TEMPLATES[scenario]
        strategy = template_data["strategy"]

        # 多轮追问支持（目前仅砍价场景有多轮）
        if round_num == 1 and "template" in template_data:
            text = template_data["template"].format(**kwargs)
        elif f"round_{round_num}" in template_data:
            text = template_data[f"round_{round_num}"].format(**kwargs)
        else:
            text = template_data.get("round_3", template_data.get("template", "")).format(**kwargs)

        return f"**策略**：{strategy}\n**第{round_num}轮回复**：\n\n{text}"

    def get_after_sale_guide(self, issue_type: str) -> str:
        """获取售后处理指引"""
        if issue_type in self.AFTER_SALE_DECISION_TREE:
            tree = self.AFTER_SALE_DECISION_TREE[issue_type]
            guide = f"## {issue_type}处理指引\n\n"
            for i, step in enumerate(tree["steps"], 1):
                guide += f"{i}. {step}\n"
            if "legal_note" in tree:
                guide += f"\n**法律依据**：{tree['legal_note']}\n"
            return guide
        return "暂无该类型的处理指引。"

    @staticmethod
    def get_platform_rules_summary() -> str:
        """获取近期平台规则变更摘要"""
        report = "# 近期电商平台规则变更摘要\n\n"
        for period, rules in PLATFORM_RULES_UPDATES.items():
            report += f"## {period}\n\n"
            for rule in rules:
                report += f"- **{rule['platform']}**：{rule['change']}\n  - 影响：{rule['impact']}\n\n"
        report += "---\n⚠️ 以上为近期主要变更摘要，具体规则请以各平台官方公告为准。\n"
        return report


# =============================================================================
# P0修复: 运营数据诊断引擎（修复数值比较逻辑）
# =============================================================================

class AnalyticsDashboard:
    """运营数据诊断引擎"""

    # 数值型判断规则（P0修复：用数值比较替代字符串包含）
    METRIC_RULES = {
        "转化率": {
            "formula": "成交UV ÷ 浏览UV",
            "unit": "%",
            "mode": "gt_healthy",  # 值越大越好
            "healthy": 3.0,
            "warning": 2.0,
            "danger": 1.0,
            "danger_op": "lt",
            "warning_op": "lt",
            "optimization": "优化标题关键词、主图质量、价格竞争力",
        },
        "客单价": {
            "formula": "销售额 ÷ 订单数",
            "unit": "元",
            "mode": "absolute",  # 绝对值判断需结合业务
            "healthy": None,
            "warning": None,
            "danger": None,
            "optimization": "搭配销售、满减活动、提高高客单商品占比",
        },
        "退款率": {
            "formula": "退款订单 ÷ 总订单",
            "unit": "%",
            "mode": "lt_healthy",  # 值越小越好
            "healthy": 5.0,
            "warning": 8.0,
            "danger": 10.0,
            "danger_op": "gt",
            "warning_op": "gt",
            "optimization": "检查产品质量、描述准确性、包装防护",
        },
        "复购率": {
            "formula": "复购客户 ÷ 总客户",
            "unit": "%",
            "mode": "gt_healthy",
            "healthy": 15.0,
            "warning": 8.0,
            "danger": 5.0,
            "danger_op": "lt",
            "warning_op": "lt",
            "optimization": "建立会员体系、老客专属优惠、定期触达",
        },
        "ROI": {
            "formula": "销售额 ÷ 推广费用",
            "unit": "",
            "mode": "gt_healthy",
            "healthy": 3.0,
            "warning": 2.0,
            "danger": 1.5,
            "danger_op": "lt",
            "warning_op": "lt",
            "optimization": "优化投放人群/素材/时段，暂停低效渠道",
        },
        "好评率": {
            "formula": "好评数 ÷ 总评价数",
            "unit": "%",
            "mode": "gt_healthy",
            "healthy": 95.0,
            "warning": 92.0,
            "danger": 90.0,
            "danger_op": "lt",
            "warning_op": "lt",
            "optimization": "售后主动回访、差评跟进改进、好评引导",
        },
        "客服响应时间": {
            "formula": "平均首次回复时长",
            "unit": "秒",
            "mode": "lt_healthy",  # 值越小越好
            "healthy": 30.0,
            "warning": 120.0,
            "danger": 180.0,
            "danger_op": "gt",
            "warning_op": "gt",
            "optimization": "设置自动回复、快捷话术、客服机器人",
        },
        "DSR评分": {
            "formula": "平台动态评分",
            "unit": "",
            "mode": "gt_healthy",
            "healthy": 4.7,
            "warning": 4.6,
            "danger": 4.5,
            "danger_op": "lt",
            "warning_op": "lt",
            "optimization": "从描述相符/服务态度/物流速度三维度逐一排查改进",
        },
    }

    @staticmethod
    def _parse_value(value, unit: str = "") -> float:
        """统一解析指标值为浮点数"""
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip()
        # 去除常见单位
        for u in ["%", "秒", "元", "分"]:
            s = s.replace(u, "")
        s = s.strip()
        try:
            return float(s)
        except ValueError:
            return 0.0

    def diagnose(self, metrics_input: dict) -> str:
        """诊断运营数据"""
        report = f"""# 运营数据诊断报告

诊断时间：{datetime.now().strftime('%Y年%m月%d日')}

## 📊 指标概览

| 指标 | 当前值 | 健康值 | 状态 | 优化建议 |
|------|-------|-------|------|---------|
"""
        todo_items = []

        for metric_name, value in metrics_input.items():
            if metric_name not in self.METRIC_RULES:
                continue

            rule = self.METRIC_RULES[metric_name]
            current = str(value)
            numeric_value = self._parse_value(value, rule["unit"])

            # 数值比较判断
            status = HealthStatus.GOOD
            is_warning = False
            is_danger = False

            if rule["mode"] == "gt_healthy":
                # 值越大越好：danger < warning < healthy
                if rule.get("danger_op") == "lt" and numeric_value <= rule["danger"]:
                    is_danger = True
                elif rule.get("warning_op") == "lt" and numeric_value <= rule["warning"]:
                    is_warning = True
            elif rule["mode"] == "lt_healthy":
                # 值越小越好：danger > warning > healthy
                if rule.get("danger_op") == "gt" and numeric_value >= rule["danger"]:
                    is_danger = True
                elif rule.get("warning_op") == "gt" and numeric_value >= rule["warning"]:
                    is_warning = True
            elif rule["mode"] == "absolute":
                # 客单价等绝对值指标，默认健康
                status = HealthStatus.GOOD

            if is_danger:
                status = HealthStatus.DANGER
                todo_items.append(f"- 🔴 {metric_name}异常（当前{current}），建议：{rule['optimization']}")
            elif is_warning:
                status = HealthStatus.WARNING
                todo_items.append(f"- 🟡 {metric_name}需关注（当前{current}），建议：{rule['optimization']}")

            healthy_display = rule["healthy"]
            if healthy_display is not None:
                if rule["mode"] == "gt_healthy":
                    healthy_display = f"≥{rule['healthy']}{rule['unit']}"
                elif rule["mode"] == "lt_healthy":
                    healthy_display = f"≤{rule['healthy']}{rule['unit']}"
                else:
                    healthy_display = "视品类而定"
            else:
                healthy_display = "视品类而定"

            report += f"| {metric_name} | {current} | {healthy_display} | {status.value} | {rule['optimization']} |\n"

        if todo_items:
            report += "\n## 📋 今日待办\n\n"
            for item in todo_items:
                report += f"{item}\n"
        else:
            report += "\n## ✅ 整体运营健康\n\n各项指标均在正常范围内，继续保持！"

        report += "\n---\n💡 如需计算本月的增值税和企业所得税，可调用「一人公司财务管家」Skill 进行自动计税。\n"
        return report


# =============================================================================
# 主程序入口
# =============================================================================

def main():
    """演示模式"""
    print("=" * 60)
    print("一人电商运营助手 / SoloEcom Pilot v1.1.0")
    print("=" * 60)
    print()
    print("🛒 核心功能模块：")
    print("  1. 智能选品 - 市场分析，一人公司适配度评估")
    print("  2. 定价引擎 - 科学定价，合规检查")
    print("  3. 内容工厂 - 标题/详情页/短视频/多平台适配")
    print("  4. 智能客服 - 售前话术 + 售后决策树")
    print("  5. 合规检查 - 广告法/价格法/消保法扫雷")
    print("  6. 数据诊断 - 核心指标健康检查")
    print()
    print("💡 使用示例：")
    print('  - 选品："我想卖蓝牙耳机，帮我分析一下市场"')
    print('  - 定价："成本50元，在淘宝卖服装，目标利润30%"')
    print('  - 内容："帮我写一个蓝牙耳机的淘宝标题"')
    print('  - 合规："帮我检查这个标题有没有违规词"')
    print('  - 客服："客户说产品质量有问题要退款，怎么处理"')
    print('  - 诊断："转化率1.2%，退款率8%，帮我分析一下"')

    # ===== 演示1: 选品分析 =====
    print("\n" + "=" * 60)
    print("【演示1】智能选品 - 知识库查询")
    print("=" * 60)
    intel = MarketIntel()
    result = intel.analyze_from_kb("蓝牙耳机")
    print(intel.generate_selection_report(result))

    # ===== 演示2: 内容工厂 =====
    print("\n" + "=" * 60)
    print("【演示2】内容工厂 - 标题生成")
    print("=" * 60)
    factory = ContentFactory()
    titles = factory.generate_titles("蓝牙耳机", ["降噪", "长续航", "防水"], Platform.TAOBAO)
    print("淘宝标题方案：")
    for i, t in enumerate(titles, 1):
        print(f"  {i}. {t}")

    # ===== 演示3: 定价计算（已修复bug） =====
    print("\n" + "=" * 60)
    print("【演示3】定价引擎 - 含类目扣点")
    print("=" * 60)
    engine = PricingEngine()
    result = engine.calculate_price(
        purchase_cost=50, packaging_cost=3, shipping_cost=5,
        platform=Platform.TAOBAO, category="3C数码",
    )
    print(engine.generate_pricing_report(result))

    # ===== 演示4: 违禁词检测 =====
    print("\n" + "=" * 60)
    print("【演示4】广告法合规检查（故意包含多个违禁词用于演示检测功能）")
    print("=" * 60)
    checker = AdComplianceChecker()
    test_text = "全网销量第一！100%有效，最先进的降噪技术，国家级认证，原价299元，现在仅售99元！"
    check_result = checker.check_text(test_text)
    print(checker.generate_compliance_report(check_result, test_text))

    # ===== 演示5: 数据诊断（已修复数值比较） =====
    print("\n" + "=" * 60)
    print("【演示5】运营数据诊断")
    print("=" * 60)
    dashboard = AnalyticsDashboard()
    print(dashboard.diagnose({"转化率": "1.2%", "退款率": "8%", "ROI": "1.2", "好评率": "92%"}))


if __name__ == "__main__":
    main()
