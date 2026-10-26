#!/usr/bin/env python3
"""广东美术类448分/排位16750志愿分析 - v1.4回测校准策略"""
import json, os

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"

student = {
    "year": 2026,
    "province": "广东",
    "category": "美术与设计类",
    "cultural_score": 425,
    "art_score_est": 185,
    "composite_score": 448,
    "composite_rank": 16750,
}

# 2024年本科批投档数据
data_2024 = [
    ("西安培华学院", 460, 12112, False),
    ("北京城市学院", 459, 12407, False),
    ("上海中侨职业技术大学", 459, 12440, False),
    ("南通理工学院", 458, 12692, False),
    ("重庆城市科技学院", 457, 12819, False),
    ("南昌理工学院", 455, 13414, False),
    ("广东白云学院", 454, 13645, True),
    ("江西科技学院", 454, 13653, False),
    ("武汉晴川学院", 466, 13657, False),
    ("吉利学院", 451, 14451, False),
    ("江西应用科技学院", 452, 14256, False),
    ("武汉工程科技学院", 451, 14466, False),
    ("天津天狮学院", 450, 14672, False),
    ("广东培正学院", 450, 14699, True),
    ("广东东软学院", 449, 15049, True),
    ("四川文化艺术学院", 464, 15340, False),
    ("广州软件学院", 448, 15343, True),
    ("广西外国语学院", 447, 15483, False),
    ("广东东软学院(专业组2)", 449, 15488, True),
    ("西北大学现代学院", 447, 15509, False),
    ("广州商学院", 446, 15823, True),
    ("辽宁传媒学院", 442, 16854, False),
    ("三亚学院", 442, 16918, False),
    ("广州新华学院", 437, 18068, True),
    ("天津传媒学院", 436, 18412, False),
    ("桂林旅游学院", 433, 19204, False),
    ("广州工商学院", 431, 19648, True),
    ("东莞城市学院", 430, 19900, True),
    ("泉州信息工程学院(中外合作)", 430, 19938, False),
    ("安徽文达信息工程学院", 428, 20303, False),
    ("广州理工学院", 428, 20457, True),
    ("广州华立学院", 425, 21089, True),
    ("广西城市职业大学", 421, 22026, False),
    ("广州华商学院", 419, 22631, True),
    ("广州应用科技学院", 417, 22968, True),
    ("广东理工学院", 416, 23269, True),
    ("四川文化艺术学院(中外合作)", 414, 23646, False),
    ("四川传媒学院(中外合作)", 414, 23728, False),
    ("四川电影电视学院(中外合作)", 404, 25643, False),
    ("青岛电影学院", 401, 26185, False),
    ("广州科技职业技术大学", 397, 26823, True),
    ("广州应用科技学院(联合培养)", 395, 27133, True),
    ("广东科技学院", 393, 27425, True),
    ("广东工商职业技术大学", 393, 27428, True),
    ("广州工商学院(联合培养)", 392, 27551, True),
]

# 2023年本科批投档数据
data_2023 = [
    ("北海艺术设计学院", 482, 12021, False),
    ("宁波财经学院", 482, 12108, False),
    ("南昌交通学院", 481, 12312, False),
    ("陕西服装工程学院", 481, 12329, False),
    ("长春建筑学院", 481, 12370, False),
    ("南昌工学院", 481, 12437, False),
    ("上海立达学院", 480, 12645, False),
    ("武汉传媒学院", 480, 12765, False),
    ("武昌理工学院", 479, 12918, False),
    ("长春人文学院", 479, 12901, False),
    ("大连艺术学院", 479, 13117, False),
    ("辽宁传媒学院", 479, 13115, False),
    ("南昌理工学院", 478, 13144, False),
    ("昆明文理学院", 478, 13194, False),
    ("江苏师范大学科文学院", 478, 13283, False),
    ("广东白云学院", 478, 13358, True),
    ("广东培正学院", 478, 13367, True),
    ("三亚学院", 476, 13879, False),
    ("上海中侨职业技术学院", 475, 14213, False),
    ("湖北商贸学院", 474, 14346, False),
    ("吉利学院", 474, 14426, False),
    ("泉州信息工程学院(中外合作)", 458, 14434, False),
    ("广州新华学院", 474, 14477, True),
    ("广西城市职业大学", 474, 14520, False),
    ("广州软件学院", 474, 14503, True),
    ("广东东软学院", 467, 15307, True),
    ("广东东软学院(专业组2)", 470, 16698, True),
    ("广东东软学院(专业组3)", 463, 15552, True),
    ("浙江越秀外国语学院", 467, 16543, False),
    ("西北大学现代学院", 466, 16806, False),
    ("海口经济学院", 461, 18288, False),
    ("南宁理工学院", 461, 18326, False),
    ("广州华立学院", 461, 18329, True),
    ("东莞城市学院", 463, 17678, True),
    ("广州应用科技学院", 458, 19220, True),
    ("湛江科技学院", 456, 19893, True),
    ("广州应用科技学院(联合培养)", 456, 19853, True),
    ("广州工商学院", 456, 19763, True),
    ("华南农业大学珠江学院", 448, 22171, True),
    ("广东理工学院", 440, 24461, True),
    ("广州科技职业技术大学", 436, 25565, True),
    ("广东工商职业技术大学", 432, 26683, True),
    ("广州工商学院(联合培养)", 433, 26436, True),
    ("广东科技学院", 452, 28157, True),
    ("四川文化艺术学院(中外合作)", 454, 20509, False),
    ("四川电影电视学院(中外合作)", 450, 21582, False),
]

# 合并两年数据
from collections import defaultdict
school_data = defaultdict(lambda: {"years": {}})
for name, score, rank, is_gd in data_2024:
    school_data[name]["is_gd"] = is_gd
    school_data[name]["years"][2024] = {"score": score, "rank": rank}
for name, score, rank, is_gd in data_2023:
    school_data[name]["is_gd"] = is_gd
    school_data[name]["years"][2023] = {"score": score, "rank": rank}

# 计算加权平均 (2024:2023 = 5:3)
results = []
for name, info in school_data.items():
    years = info["years"]
    entry = {"name": name, "is_gd": info["is_gd"]}
    if len(years) == 2:
        entry["rank_2023"] = years[2023]["rank"]
        entry["score_2023"] = years[2023]["score"]
        entry["rank_2024"] = years[2024]["rank"]
        entry["score_2024"] = years[2024]["score"]
        entry["avg_rank"] = round((years[2024]["rank"] * 5 + years[2023]["rank"] * 3) / 8)
        entry["avg_score"] = round((years[2024]["score"] * 5 + years[2023]["score"] * 3) / 8)
        entry["rank_shift"] = years[2024]["rank"] - years[2023]["rank"]
        entry["years_data"] = 2
    elif 2024 in years:
        entry["rank_2024"] = years[2024]["rank"]
        entry["score_2024"] = years[2024]["score"]
        entry["avg_rank"] = years[2024]["rank"]
        entry["avg_score"] = years[2024]["score"]
        entry["years_data"] = 1
    else:
        entry["rank_2023"] = years[2023]["rank"]
        entry["score_2023"] = years[2023]["score"]
        entry["avg_rank"] = years[2023]["rank"]
        entry["avg_score"] = years[2023]["score"]
        entry["years_data"] = 1
    results.append(entry)

results.sort(key=lambda x: x["avg_rank"])

# v1.4策略分类
student_rank = 16750
for r in results:
    diff = student_rank - r["avg_rank"]
    if 500 <= diff <= 5000:
        r["tier"] = "冲刺"
    elif -500 <= diff < 500:
        r["tier"] = "稳妥上"
    elif -10000 <= diff < -500:
        r["tier"] = "稳妥下"
    elif -25000 <= diff < -10000:
        r["tier"] = "保底"
    else:
        r["tier"] = "垫底"

# 输出
tier_emoji = {"冲刺": "🏃", "稳妥上": "⚖️", "稳妥下": "⚖️", "保底": "🛡️", "垫底": "🔒"}
tier_names = {"冲刺": "冲刺", "稳妥上": "稳妥(高位)", "稳妥下": "稳妥(低位)", "保底": "保底", "垫底": "垫底"}

for tier_key in ["冲刺", "稳妥上", "稳妥下", "保底", "垫底"]:
    tier_schools = [r for r in results if r["tier"] == tier_key]
    if not tier_schools:
        continue
    emoji = tier_emoji[tier_key]
    name = tier_names[tier_key]
    print(f"\n{'='*60}")
    print(f"{emoji} {name} ({len(tier_schools)}所)")
    print(f"{'='*60}")
    for s in tier_schools:
        gd = "🔵广东" if s["is_gd"] else "⚪外省"
        yrs = "2年" if s["years_data"] == 2 else "1年"
        warn = "⚠️" if s["years_data"] == 1 else "  "
        r23 = s.get("rank_2023", "—")
        s23 = s.get("score_2023", "—")
        r24 = s.get("rank_2024", "—")
        s24 = s.get("score_2024", "—")
        shift = f"位次{s['rank_shift']:+d}" if "rank_shift" in s else ""
        diff = student_rank - s["avg_rank"]
        print(f"  {gd} {s['name']}")
        print(f"    均分:{s['avg_score']} 均位:{s['avg_rank']} (差{diff:+d}位) [{yrs}]{warn}")
        print(f"    23年:{s23}分/{r23}位  24年:{s24}分/{r24}位  {shift}")
        print()

# 保存
output = {
    "student": student,
    "methodology": "v1.4回测校准策略, 2年加权平均(2024:2023=5:3)",
    "tiers": {},
}
for tier_key in ["冲刺", "稳妥上", "稳妥下", "保底", "垫底"]:
    output["tiers"][tier_key] = [r for r in results if r["tier"] == tier_key]

outpath = os.path.join(DATA_DIR, "gd_art_448_16750_plan.json")
with open(outpath, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n方案已保存到 {outpath}")
