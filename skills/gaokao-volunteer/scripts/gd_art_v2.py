#!/usr/bin/env python3
"""广东美术类448分志愿推荐 v2 - 含省外院校扩展"""
import json, os

student = {"composite_score": 448, "composite_rank": 16750}

# 完整两年数据（2023+2024本科批，排位10000-28000区间）
schools = [
    # (名称, 2024分, 2024位, 2023分, 2023位, 是否广东, 公办/民办, 城市, 特色)
    # === 超冲档：公办院校（排位10000-12000） ===
    ("邯郸学院", 468, 10183, None, None, False, "公办", "河北邯郸", "师范类"),
    ("内蒙古师范大学", 474, 10183, None, None, False, "公办", "内蒙古呼和浩特", "师范类211"),
    ("上饶师范学院", 468, 10185, None, None, False, "公办", "江西上饶", "师范类"),
    ("肇庆学院", 469, 10162, None, None, True, "公办", "广东肇庆", "综合类"),
    ("吉林大学", 466, 10742, 543, 777, False, "公办", "吉林长春", "985/211名校"),
    ("湖南文理学院", 463, 11532, None, None, False, "公办", "湖南常德", "综合类"),

    # === 冲刺档（均位12000-16500） ===
    ("南昌理工学院", 455, 13414, 478, 13144, False, "民办", "江西南昌", "理工+设计"),
    ("广东白云学院", 454, 13645, 478, 13358, True, "民办", "广州", "综合类"),
    ("武汉晴川学院", 466, 13657, None, None, False, "民办", "武汉", "设计类特色"),
    ("广东培正学院", 450, 14699, 478, 13367, True, "民办", "广州", "综合类"),
    ("湖北商贸学院", None, None, 474, 14346, False, "民办", "武汉", "设计类"),
    ("吉利学院", 451, 14451, 474, 14426, False, "民办", "成都", "极稳定"),
    ("武汉工程科技学院", 451, 14466, None, None, False, "民办", "武汉", "工程+设计"),
    ("广州软件学院", 448, 15343, 474, 14503, True, "民办", "广州", "IT设计特色"),
    ("广东东软学院", 449, 15049, 467, 15307, True, "民办", "佛山", "数字媒体"),
    ("四川文化艺术学院", 464, 15340, None, None, False, "民办", "绵阳", "艺术类专精"),
    ("辽宁传媒学院", 442, 16854, 479, 13115, False, "民办", "沈阳", "传媒类"),
    ("广西外国语学院", 447, 15483, None, None, False, "民办", "南宁", "外语+设计"),
    ("三亚学院", 442, 16918, 476, 13879, False, "民办", "海南三亚", "综合类"),
    ("广州商学院", 446, 15823, None, None, True, "民办", "广州", "商科+设计"),
    ("西北大学现代学院", 447, 15509, 466, 16806, False, "民办", "西安", "位次改善中"),

    # === 稳妥档（均位16500-27000） ===
    ("广州新华学院", 437, 18068, 474, 14477, True, "民办", "广州", "中大体系"),
    ("天津传媒学院", 436, 18412, None, None, False, "民办", "天津", "传媒类特色"),
    ("海口经济学院", None, None, 461, 18288, False, "民办", "海南海口", "经济+设计"),
    ("东莞城市学院", 430, 19900, 463, 17678, True, "民办", "东莞", "工科+设计"),
    ("桂林旅游学院", 433, 19204, None, None, False, "公办", "广西桂林", "旅游+设计"),
    ("广州工商学院", 431, 19648, 456, 19763, True, "民办", "广州", "极稳定"),
    ("广州华立学院", 425, 21089, 461, 18329, True, "民办", "广州", "综合类"),
    ("湛江科技学院", None, None, 456, 19893, True, "民办", "湛江", "科技类"),
    ("广州理工学院", 428, 20457, None, None, True, "民办", "广州", "理工类"),
    ("广州应用科技学院", 417, 22968, 458, 19220, True, "民办", "广州", "应用型"),
    ("华南农业大学珠江学院", None, None, 448, 22171, True, "民办", "广州", "农林+设计"),
    ("广州华商学院", 419, 22631, None, None, True, "民办", "广州", "商科类"),
    ("广东理工学院", 416, 23269, 440, 24461, True, "民办", "肇庆", "位次改善"),
    ("南宁理工学院", None, None, 461, 18326, False, "民办", "南宁", "理工类"),
    ("四川电影电视学院(中外合作)", 404, 25643, 450, 21582, False, "民办", "成都", "影视类"),
    ("广州科技职业技术大学", 397, 26823, 436, 25565, True, "民办", "广州", "职业本科"),

    # === 保底档 ===
    ("广州应用科技学院(联合培养)", 395, 27133, 456, 19853, True, "民办", "广州", "联合培养"),
    ("广东工商职业技术大学", 393, 27428, 432, 26683, True, "民办", "肇庆", "职业本科"),
    ("广东科技学院", 393, 27425, 452, 28157, True, "民办", "东莞", "稳定保底"),
    ("广州工商学院(联合培养)", 392, 27551, 433, 26436, True, "民办", "广州", "联合培养"),
]

# 计算加权均位
results = []
for name, s24, r24, s23, r23, is_gd, nature, city, feature in schools:
    entry = {
        "name": name, "is_gd": is_gd, "nature": nature, "city": city, "feature": feature,
        "score_2024": s24, "rank_2024": r24, "score_2023": s23, "rank_2023": r23,
    }
    if r24 and r23:
        entry["avg_rank"] = round((r24 * 5 + r23 * 3) / 8)
        entry["avg_score"] = round(((s24 or 0) * 5 + (s23 or 0) * 3) / 8) if s24 and s23 else (s24 or s23)
        entry["years"] = 2
        entry["shift"] = r24 - r23
    elif r24:
        entry["avg_rank"] = r24
        entry["avg_score"] = s24
        entry["years"] = 1
        entry["shift"] = None
    elif r23:
        entry["avg_rank"] = r23
        entry["avg_score"] = s23
        entry["years"] = 1
        entry["shift"] = None
    
    diff = student["composite_rank"] - entry["avg_rank"]
    entry["diff"] = diff
    if diff > 5000:
        entry["tier"] = "💎超冲"
    elif 500 <= diff <= 5000:
        entry["tier"] = "🏃冲刺"
    elif -500 <= diff < 500:
        entry["tier"] = "⚖️稳妥上"
    elif -10000 <= diff < -500:
        entry["tier"] = "⚖️稳妥下"
    elif -25000 <= diff < -10000:
        entry["tier"] = "🛡️保底"
    else:
        entry["tier"] = "🔒垫底"
    
    results.append(entry)

results.sort(key=lambda x: x["avg_rank"])

# === 输出推荐方案 ===
print("=" * 80)
print(f"🎨 广东2026美术类 综合分448/排位16750 志愿推荐方案 v2（含省外院校）")
print("=" * 80)

tier_names = {
    "💎超冲": "💎 超级冲刺（公办院校，录取率<15%）",
    "🏃冲刺": "🏃 冲刺档（录取率20-35%）",
    "⚖️稳妥上": "⚖️ 稳妥档-高位（录取率50-65%）",
    "⚖️稳妥下": "⚖️ 稳妥档-低位（录取率65-85%）",
    "🛡️保底": "🛡️ 保底档（录取率85-95%）",
}

for tier_key in ["💎超冲", "🏃冲刺", "⚖️稳妥上", "⚖️稳妥下", "🛡️保底"]:
    tier_schools = [r for r in results if r["tier"] == tier_key]
    if not tier_schools:
        continue
    
    print(f"\n{'─'*80}")
    print(f"{tier_names[tier_key]}  ({len(tier_schools)}所)")
    print(f"{'─'*80}")
    print(f"{'院校':<26} {'均位':>7} {'差值':>7} {'公办/民办':>8} {'城市':<10} {'年数':>4} {'波动':>8} {'特色'}")
    print(f"{'─'*80}")
    
    for s in tier_schools:
        gd = "🔵粤" if s["is_gd"] else "⚪省外"
        nat = "公办" if s["nature"] == "公办" else "民办"
        yrs = f"{s['years']}年" + ("⚠️" if s["years"] == 1 else "")
        shift = f"{s['shift']:+d}" if s["shift"] is not None else "—"
        score = s["avg_score"] or "—"
        print(f"{gd} {s['name']:<23} {s['avg_rank']:>7} {s['diff']:>+7} {nat:>8} {s['city']:<10} {yrs:>6} {shift:>8}  {s['feature']}")

# === 最终推荐15-20所清单 ===
print(f"\n{'='*80}")
print(f"📋 推荐填报清单（建议填15-20个院校专业组志愿）")
print(f"{'='*80}")

# 精选推荐
picks = {
    "💎超冲(冲公办)": [],
    "🏃冲刺": [],
    "⚖️稳妥": [],
    "🛡️保底": [],
}

for r in results:
    if r["tier"] == "💎超冲" and r["nature"] == "公办":
        picks["💎超冲(冲公办)"].append(r)
    elif r["tier"] == "🏃冲刺":
        picks["🏃冲刺"].append(r)
    elif r["tier"] in ("⚖️稳妥上", "⚖️稳妥下"):
        picks["⚖️稳妥"].append(r)
    elif r["tier"] == "🛡️保底":
        picks["🛡️保底"].append(r)

seq = 1
for category, schools_list in picks.items():
    if not schools_list:
        continue
    # 省内省外交错推荐
    gd = [s for s in schools_list if s["is_gd"]]
    og = [s for s in schools_list if not s["is_gd"]]
    
    limit = 3 if "超冲" in category else (6 if "冲刺" in category else (6 if "稳妥" in category else 3))
    selected = gd[:limit//2] + og[:limit//2]
    if len(selected) < limit:
        remaining = gd[limit//2:] + og[limit//2:]
        selected.extend(remaining[:limit - len(selected)])
    
    print(f"\n  {category}:")
    for s in selected[:limit]:
        gd_mark = "🔵粤" if s["is_gd"] else "⚪外"
        nat = "公" if s["nature"] == "公办" else "民"
        yrs = f"{s['years']}年" + ("⚠️" if s["years"] == 1 else "✅")
        print(f"    {seq:>2}. {gd_mark} [{nat}] {s['name']:<22} 均{s['avg_rank']:<6}位 ({s['diff']:+d}) {s['city']:<8} {yrs}")
        seq += 1

print(f"\n  💡 填报策略:")
print(f"     • 前3-4个志愿冲公办（录取率低但值得试）")
print(f"     • 中间8-10个志愿是主战场（民办本科，省内外搭配）")
print(f"     • 最后3个志愿必须保底（确保有本科读）")
print(f"     • 平行志愿按「最想去的排前面」，不怕浪费")
