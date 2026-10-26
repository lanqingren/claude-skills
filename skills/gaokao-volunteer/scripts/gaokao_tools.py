"""
高考志愿填报助手 - 工具脚本

功能：
1. 位次查询（基于一分一段表）
2. 院校录取数据匹配
3. 冲稳保方案生成
4. 选科-专业对照查询
5. 院校对比

使用方式：
    python gaokao_tools.py score_to_rank --province 河南 --year 2025 --score 550 --category 理科
    python gaokao_tools.py recommend --province 河南 --year 2025 --rank 25000 --category 物理类
    python gaokao_tools.py major_query --subjects 物理 化学 生物
    python gaokao_tools.py compare --schools "华中科技大学" "电子科技大学"
"""

import argparse
import json
import os
import sys
from itertools import permutations
from pathlib import Path

# 数据缓存目录
DATA_DIR = Path(os.environ.get("GAOKAO_DATA_DIR", r"D:\GitHub\hermescn\data\gaokao-data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ========== 选科-专业对照表 ==========

SUBJECT_MAJOR_MAP = {
    "物化生": {
        "coverage": "~96%",
        "majors": [
            "计算机科学与技术", "软件工程", "电子信息工程", "通信工程",
            "临床医学", "口腔医学", "药学", "生物医学工程",
            "机械工程", "土木工程", "建筑学", "材料科学与工程",
            "化学工程与工艺", "环境工程", "食品科学与工程",
            "数学与应用数学", "物理学", "化学", "生物科学",
            "人工智能", "数据科学与大数据技术", "机器人工程",
        ],
        "restricted": ["几乎无限制（极少专业要求政治/地理）"],
    },
    "物化政": {
        "coverage": "~95%",
        "majors": [
            "计算机科学与技术", "软件工程", "电子信息工程",
            "临床医学", "口腔医学", "药学",
            "机械工程", "土木工程", "材料科学与工程",
            "法学", "公安学", "政治学",
            "人工智能", "数据科学与大数据技术",
        ],
        "restricted": ["部分医学专业要求生物"],
    },
    "物化地": {
        "coverage": "~94%",
        "majors": [
            "计算机科学与技术", "软件工程", "电子信息工程",
            "地质学", "地理信息科学", "测绘工程",
            "机械工程", "土木工程", "材料科学与工程",
            "人工智能", "数据科学与大数据技术",
        ],
        "restricted": ["部分农学/医学要求生物"],
    },
    "物生政": {
        "coverage": "~87%",
        "majors": [
            "计算机科学与技术", "软件工程", "电子信息工程",
            "生物科学", "生物技术", "生态学",
            "法学", "公安学", "政治学",
            "教育学", "心理学",
        ],
        "restricted": ["大部分工科要求化学", "临床医学要求化学"],
    },
    "物生地": {
        "coverage": "~87%",
        "majors": [
            "计算机科学与技术", "软件工程",
            "生物科学", "生物技术", "生态学",
            "地质学", "地理信息科学",
            "教育学", "心理学",
        ],
        "restricted": ["化工材料要求化学", "大部分医学要求化学"],
    },
    "物政地": {
        "coverage": "~80%",
        "majors": [
            "计算机科学与技术", "软件工程",
            "法学", "公安学", "政治学",
            "教育学", "新闻传播学",
            "经济学", "管理学",
        ],
        "restricted": ["理工农医大部分要求化学"],
    },
    "史政地": {
        "coverage": "~50%",
        "majors": [
            "法学", "汉语言文学", "新闻传播学",
            "历史学", "哲学", "社会学",
            "经济学", "管理学", "金融学",
            "教育学", "外语类",
        ],
        "restricted": ["理工农医基本不可报"],
    },
    "史政生": {
        "coverage": "~52%",
        "majors": [
            "法学", "汉语言文学", "新闻传播学",
            "历史学", "哲学",
            "经济学", "管理学",
            "教育学", "护理学",
            "外语类",
        ],
        "restricted": ["理工农医基本不可报"],
    },
    "史化政": {
        "coverage": "~52%",
        "majors": [
            "法学", "汉语言文学", "新闻传播学",
            "历史学", "哲学",
            "经济学", "管理学",
            "护理学", "药学类（部分）",
            "外语类",
        ],
        "restricted": ["大部分工科受限", "临床医学不可报"],
    },
    "史化地": {
        "coverage": "~51%",
        "majors": [
            "法学", "汉语言文学", "新闻传播学",
            "历史学", "哲学",
            "经济学", "管理学",
            "护理学", "药学类（部分）",
            "外语类",
        ],
        "restricted": ["大部分工科受限"],
    },
    "史化生": {
        "coverage": "~52%",
        "majors": [
            "法学", "汉语言文学", "新闻传播学",
            "历史学", "哲学",
            "经济学", "管理学",
            "护理学", "药学类",
            "生物科学（部分）",
            "外语类",
        ],
        "restricted": ["大部分工科受限"],
    },
    "史生地": {
        "coverage": "~50%",
        "majors": [
            "法学", "汉语言文学", "新闻传播学",
            "历史学", "哲学",
            "经济学", "管理学",
            "护理学", "生态学（部分）",
            "外语类",
        ],
        "restricted": ["理工农医基本不可报"],
    },
}


# ========== 工具函数 ==========

def load_score_distribution(province: str, year: int, category: str):
    """加载一分一段表数据"""
    filename = f"{province}_{year}_{category}_score_dist.json"
    filepath = DATA_DIR / filename
    if not filepath.exists():
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_school_admission(province: str, year: int, school: str):
    """加载院校录取数据"""
    filename = f"{province}_{year}_{school}_admission.json"
    filepath = DATA_DIR / filename
    if not filepath.exists():
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def score_to_rank(score_dist: list, score: int) -> dict:
    """
    根据一分一段表查询位次
    score_dist 格式: [{"score": 650, "count": 120, "cumulative": 500}, ...]
    """
    for i, entry in enumerate(score_dist):
        if entry["score"] == score:
            return {
                "score": score,
                "rank": entry["cumulative"],
                "rank_range": f"{entry['cumulative'] - entry['count'] + 1} ~ {entry['cumulative']}",
                "same_score_count": entry["count"],
            }
        if entry["score"] < score:
            # 插值估算
            if i == 0:
                return {"score": score, "rank": 1, "note": "高于表中最高分，位次在前"}
            prev = score_dist[i - 1]
            ratio = (prev["score"] - score) / (prev["score"] - entry["score"])
            estimated_rank = int(prev["cumulative"] - ratio * (prev["cumulative"] - entry["cumulative"]))
            return {
                "score": score,
                "rank": estimated_rank,
                "note": "插值估算，非精确值",
            }
    return {"score": score, "rank": score_dist[-1]["cumulative"], "note": "低于表中最低分"}


def rank_to_score(score_dist: list, rank: int) -> dict:
    """根据位次反查分数"""
    for entry in score_dist:
        if entry["cumulative"] >= rank:
            return {
                "score": entry["score"],
                "rank": rank,
                "note": f"位次{rank}约对应{entry['score']}分",
            }
    return None


# ========== 偏好筛选（v1.2） ==========

# 城市别名 → 具体城市列表
CITY_ALIASES = {
    "珠三角": ["广州", "深圳", "珠海", "佛山", "东莞", "中山", "惠州", "江门", "肇庆"],
    "大湾区": ["广州", "深圳", "珠海", "佛山", "东莞", "中山", "惠州", "江门", "肇庆", "香港", "澳门"],
    "长三角": ["上海", "南京", "苏州", "无锡", "杭州", "宁波", "嘉兴", "绍兴", "常州", "南通"],
    "一线城市": ["北京", "上海", "广州", "深圳"],
    "京津冀": ["北京", "天津", "石家庄", "保定", "廊坊", "唐山"],
    "川渝": ["成都", "重庆", "绵阳"],
    "沿海城市": ["大连", "青岛", "上海", "宁波", "厦门", "深圳", "珠海", "烟台", "威海"],
    # 省份别名
    "广东": ["广州", "深圳", "珠海", "佛山", "东莞", "中山", "惠州", "江门", "肇庆", "汕头", "湛江", "茂名", "揭阳", "梅州", "潮州", "河源", "清远", "韶关", "云浮", "阳江", "汕尾"],
    "广西": ["南宁", "柳州", "桂林", "梧州", "北海", "防城港", "钦州", "贵港", "玉林", "百色", "贺州", "河池", "来宾", "崇左"],
    "湖南": ["长沙", "株洲", "湘潭", "衡阳", "邵阳", "岳阳", "常德", "张家界", "益阳", "郴州", "永州", "怀化", "娄底", "湘西"],
    "湖北": ["武汉", "黄石", "十堰", "宜昌", "襄阳", "鄂州", "荆门", "孝感", "荆州", "黄冈", "咸宁", "随州", "恩施"],
    "江西": ["南昌", "景德镇", "萍乡", "九江", "新余", "鹰潭", "赣州", "吉安", "宜春", "抚州", "上饶"],
    "福建": ["福州", "厦门", "莆田", "三明", "泉州", "漳州", "南平", "龙岩", "宁德"],
}

# 专业关键词 → 匹配范围
MAJOR_KEYWORDS = {
    "计算机": ["计算机科学与技术", "软件工程", "人工智能", "数据科学", "网络工程", "物联网", "信息安全", "大数据"],
    "金融": ["金融学", "金融工程", "投资学", "金融科技", "保险学", "经济与金融"],
    "设计": ["视觉传达设计", "环境设计", "产品设计", "数字媒体艺术", "艺术设计", "服装与服饰设计", "工艺美术"],
    "法学": ["法学", "知识产权", "监狱学", "信用风险管理与法律防控"],
    "师范": ["师范", "教育"],
    "医学": ["临床医学", "口腔医学", "麻醉学", "医学影像学", "预防医学", "中医学", "针灸推拿"],
    "电气": ["电气工程", "自动化", "智能电网"],
    "土木": ["土木工程", "建筑学", "城乡规划", "工程造价", "给排水"],
    "会计": ["会计学", "财务管理", "审计学"],
    "外语": ["英语", "日语", "韩语", "法语", "德语", "西班牙语", "商务英语", "翻译"],
}

# 学校类型关键词
SCHOOL_TYPE_KEYWORDS = {
    "985": {"tags": ["985"], "match": "include"},
    "211": {"tags": ["985", "211"], "match": "include"},
    "双一流": {"tags": ["985", "211", "双一流"], "match": "include"},
    "公办": {"tags": ["民办", "独立学院"], "match": "exclude"},
    "民办": {"tags": ["民办"], "match": "include"},
    "独立学院": {"tags": ["独立学院"], "match": "include"},
    "师范": {"tags": ["师范"], "match": "keyword"},
    "医科": {"tags": ["医科", "医学", "医药"], "match": "keyword"},
    "理工": {"tags": ["理工", "科技", "工业", "工程"], "match": "keyword"},
    "政法": {"tags": ["政法", "法律"], "match": "keyword"},
    "财经": {"tags": ["财经", "经济", "贸易", "金融"], "match": "keyword"},
    "农业": {"tags": ["农业", "农林"], "match": "keyword"},
}


def expand_cities(city_inputs: list) -> list:
    """展开城市别名为具体城市列表"""
    result = set()
    for city in city_inputs:
        city = city.strip()
        if city in CITY_ALIASES:
            result.update(CITY_ALIASES[city])
        else:
            result.add(city)
    return list(result)


def expand_majors(major_inputs: list) -> list:
    """展开专业关键词为匹配范围"""
    result = set()
    for major in major_inputs:
        major = major.strip()
        if major in MAJOR_KEYWORDS:
            result.update(MAJOR_KEYWORDS[major])
        else:
            result.add(major)
    return list(result)


def apply_preferences(admission_data: list, prefs: dict) -> list:
    """
    对录取数据应用偏好筛选
    prefs 格式: {
        "cities": ["广州", "深圳"],          # 心仪城市（正向）
        "school_types": ["公办"],             # 学校类型（正向）
        "schools": ["深圳大学"],               # 指定学校（正向）
        "majors": ["计算机"],                 # 心仪专业（正向）
        "exclude": {
            "cities": ["北方"],               # 排除城市
            "school_types": ["民办"],          # 排除学校类型
            "majors": ["护理"]                # 排除专业
        }
    }
    任意字段为 null/空 = 不筛选该维度
    """
    result = admission_data
    notes = []

    # 1. 城市筛选（正向）
    if prefs.get("cities"):
        city_list = expand_cities(prefs["cities"])
        before = len(result)
        result = [s for s in result if any(
            c in s.get("city", "") or c in s.get("province", "")
            for c in city_list
        )]
        notes.append(f"城市筛选 {prefs['cities']} → {city_list}：{before}→{len(result)}")

    # 2. 学校类型筛选（正向）
    if prefs.get("school_types"):
        for st in prefs["school_types"]:
            st_lower = st.strip()
            if st_lower in SCHOOL_TYPE_KEYWORDS:
                rule = SCHOOL_TYPE_KEYWORDS[st_lower]
                if rule["match"] == "exclude":
                    result = [s for s in result if not any(
                        t in s.get("school_type", s.get("school", ""))
                        for t in rule["tags"]
                    )]
                elif rule["match"] == "include":
                    result = [s for s in result if any(
                        t in s.get("school_type", s.get("school", ""))
                        for t in rule["tags"]
                    )]
                elif rule["match"] == "keyword":
                    result = [s for s in result if any(
                        t in s.get("school", "")
                        for t in rule["tags"]
                    )]

    # 3. 指定学校筛选（正向，模糊匹配）
    if prefs.get("schools"):
        target_schools = prefs["schools"]
        result = [s for s in result if any(
            ts in s.get("school", "")
            for ts in target_schools
        )]

    # 4. 专业筛选（正向，模糊匹配）
    if prefs.get("majors"):
        major_list = expand_majors(prefs["majors"])
        result = [s for s in result if any(
            m in s.get("major", "")
            for m in major_list
        )]

    # 5. 排除项（反向）
    exclude = prefs.get("exclude", {})
    if exclude:
        # 排除城市
        if exclude.get("cities"):
            exc_cities = expand_cities(exclude["cities"])
            result = [s for s in result if not any(
                c in s.get("city", "") or c in s.get("province", "")
                for c in exc_cities
            )]
        # 排除学校类型
        if exclude.get("school_types"):
            for st in exclude["school_types"]:
                st_lower = st.strip()
                if st_lower in SCHOOL_TYPE_KEYWORDS:
                    rule = SCHOOL_TYPE_KEYWORDS[st_lower]
                    if rule["match"] == "include":
                        # 排除民办 = 移除含"民办"标签的
                        result = [s for s in result if not any(
                            t in s.get("school_type", s.get("school", ""))
                            for t in rule["tags"] if rule["match"] == "include"
                        )]
                else:
                    result = [s for s in result if st_lower not in s.get("school", "")]
        # 排除专业
        if exclude.get("majors"):
            exc_majors = expand_majors(exclude["majors"])
            result = [s for s in result if not any(
                m in s.get("major", "")
                for m in exc_majors
            )]

    return result


def generate_recommendation(admission_data: list, user_rank: int,
                            rush_ratio=0.3, stable_ratio=0.4, safe_ratio=0.3,
                            preferences=None):
    """
    生成冲稳保方案
    admission_data 格式: [{"school": "XX大学", "major": "计算机", "min_rank_2025": 5000, "min_rank_2024": 4800, "min_rank_2023": 5200}, ...]
    preferences 格式: {"cities": [...], "school_types": [...], "schools": [...], "majors": [...], "exclude": {...}}
    """
    # v1.2: 应用偏好筛选
    if preferences:
        admission_data = apply_preferences(admission_data, preferences)

    total = len(admission_data)
    rush_count = max(1, int(total * rush_ratio))
    stable_count = max(1, int(total * total * stable_ratio))
    safe_count = max(1, total - rush_count - stable_count)

    # 按最近一年位次排序
    sorted_data = sorted(admission_data, key=lambda x: x.get("min_rank_2025", x.get("min_rank_2024", 999999)))

    rush = []
    stable = []
    safe = []

    for item in sorted_data:
        rank_2025 = item.get("min_rank_2025", item.get("min_rank_2024", 999999))
        diff = rank_2025 - user_rank

        entry = {
            "school": item["school"],
            "major": item.get("major", ""),
            "min_rank": rank_2025,
            "diff": diff,
            "probability": _calc_probability(diff),
        }

        if diff < -user_rank * 0.1:  # 录取位次远高于用户 → 冲
            rush.append(entry)
        elif abs(diff) <= user_rank * 0.1:  # 位次相当 → 稳
            stable.append(entry)
        else:  # 录取位次低于用户 → 保
            safe.append(entry)

    return {
        "user_rank": user_rank,
        "rush": rush[:rush_count],
        "stable": stable[:stable_count],
        "safe": safe[:safe_count],
    }


def _calc_probability(rank_diff: int) -> str:
    """根据位次差估算录取概率"""
    if rank_diff < -5000:
        return "40-50%（冲刺）"
    elif rank_diff < 0:
        return "50-65%（有机会）"
    elif rank_diff < 3000:
        return "70-85%（较稳）"
    elif rank_diff < 8000:
        return "85-95%（稳妥）"
    else:
        return "95%+（保底）"


def query_major(subjects: list) -> dict:
    """选科-专业查询"""
    abbreviations = {
        "物理": "物", "化学": "化", "生物": "生",
        "历史": "史", "地理": "地", "政治": "政",
    }
    short_key = "".join(abbreviations.get(s, s[0]) for s in subjects)
    if short_key in SUBJECT_MAJOR_MAP:
        return {"subjects": subjects, **SUBJECT_MAJOR_MAP[short_key]}

    # 模糊匹配：尝试各种顺序拼接首字
    for perm in permutations(subjects):
        short_key = "".join(abbreviations.get(s, s[0]) for s in perm)
        if short_key in SUBJECT_MAJOR_MAP:
            return {"subjects": subjects, "matched_key": short_key, **SUBJECT_MAJOR_MAP[short_key]}

    return {"subjects": subjects, "error": "未找到匹配的选科组合，请检查输入"}


def compare_schools(schools: list, admission_data: dict = None) -> dict:
    """院校对比"""
    if not admission_data:
        return {
            "schools": schools,
            "note": "需要本地录取数据才能进行详细对比，请从省考试院官网获取数据后导入",
        }

    result = {"schools": [], "comparison": {}}
    for school in schools:
        data = admission_data.get(school, {})
        result["schools"].append({
            "name": school,
            "data": data,
        })
    return result


# ========== 艺术类综合分计算 ==========

# 各省美术与设计类综合分公式
# 格式: (文化课系数, 术科系数, 术科满分, 说明)
ART_SCORE_FORMULAS = {
    "广东": lambda c, m: c * 0.4 + m * 2.5 * 0.6,  # 文化×40% + 术科×2.5×60%
    "广西": lambda c, m: c * 0.5 + (m / 300 * 750) * 0.5,  # 文化×50% + 术科折算×50%
    "湖南": lambda c, m: c * 0.3 + m * 2.5 * 0.7,  # 文化×30% + 术科×70%
    "湖北": lambda c, m: (c + m * 2.5) * 0.5,
    "河南": lambda c, m: c * 0.5 + (m / 300 * 750) * 0.5,
    "山东": lambda c, m: c * 0.5 + (m / 300 * 750) * 0.5,
    "浙江": lambda c, m: c * 0.5 + m * 7.5 * 0.5,  # 术科满分100
    "江苏": lambda c, m: c * 0.5 + (m / 300 * 750) * 0.5,
    "四川": lambda c, m: c + m,
    "北京": lambda c, m: c * 0.5 + (m / 300 * 750) * 0.5,
}

ART_FORMULA_DESC = {
    "广东": "文化×40% + 术科×2.5×60%",
    "广西": "文化×50% + 术科×50%（术科/300×750）",
    "湖南": "文化×30% + 术科×70%",
    "湖北": "(文化 + 术科×2.5) × 50%",
    "河南": "文化×50% + 术科×50%",
    "山东": "文化×50% + 术科×50%",
    "浙江": "文化×50% + 术科×7.5×50%",
    "江苏": "文化×50% + 术科×50%",
    "四川": "文化 + 术科（直接相加）",
    "北京": "文化×50% + 术科×50%",
}


def calc_art_score(province: str, culture: int, major_score: int) -> dict:
    """
    计算艺术类综合分
    :param province: 省份
    :param culture: 文化课成绩（满分750）
    :param major_score: 术科统考成绩（满分通常300，浙江为100）
    :return: 综合分及详细信息
    """
    province = province.replace("省", "").replace("市", "").replace("自治区", "").strip()

    if province not in ART_SCORE_FORMULAS:
        return {
            "error": f"暂不支持 {province} 的综合分计算",
            "supported": list(ART_SCORE_FORMULAS.keys()),
            "hint": f"请手动查阅 {province} 教育考试院官网获取综合分公式",
        }

    formula = ART_SCORE_FORMULAS[province]
    score = formula(culture, major_score)
    desc = ART_FORMULA_DESC[province]

    return {
        "province": province,
        "culture_score": culture,
        "major_score": major_score,
        "comprehensive_score": round(score, 2),
        "formula": desc,
        "note": f"综合分 = {desc} = {culture}和{major_score}代入后 = {round(score, 2)}",
        "warning": "⚠️ 此为参考公式，各省每年可能调整，请以当年省考试院公布为准",
    }


# ========== CLI ==========

def main():
    parser = argparse.ArgumentParser(description="高考志愿填报助手工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # score_to_rank
    s2r = subparsers.add_parser("score_to_rank", help="分数查位次")
    s2r.add_argument("--province", required=True, help="省份")
    s2r.add_argument("--year", type=int, required=True, help="年份")
    s2r.add_argument("--score", type=int, required=True, help="高考分数")
    s2r.add_argument("--category", required=True, help="科类（物理类/历史类/理科/文科）")

    # rank_to_score
    r2s = subparsers.add_parser("rank_to_score", help="位次查分数")
    r2s.add_argument("--province", required=True, help="省份")
    r2s.add_argument("--year", type=int, required=True, help="年份")
    r2s.add_argument("--rank", type=int, required=True, help="位次")
    r2s.add_argument("--category", required=True, help="科类")

    # recommend
    rec = subparsers.add_parser("recommend", help="生成冲稳保方案")
    rec.add_argument("--province", required=True, help="省份")
    rec.add_argument("--year", type=int, required=True, help="年份")
    rec.add_argument("--rank", type=int, required=True, help="位次")
    rec.add_argument("--category", required=True, help="科类")
    rec.add_argument("--data_file", help="院校录取数据文件路径(JSON)")
    # v1.2: 偏好筛选参数（全部可选）
    rec.add_argument("--city", nargs="*", help="心仪城市（如 广州 深圳 / 珠三角），不填=不筛选")
    rec.add_argument("--school_type", nargs="*", help="学校类型（如 公办/985/师范），不填=不筛选")
    rec.add_argument("--school", nargs="*", help="指定学校名称（模糊匹配），不填=不筛选")
    rec.add_argument("--major", nargs="*", help="心仪专业（如 计算机/法学），不填=不筛选")
    rec.add_argument("--exclude_city", nargs="*", help="排除城市，不填=不排除")
    rec.add_argument("--exclude_school_type", nargs="*", help="排除学校类型（如 民办），不填=不排除")
    rec.add_argument("--exclude_major", nargs="*", help="排除专业，不填=不排除")

    # major_query
    mq = subparsers.add_parser("major_query", help="选科-专业查询")
    mq.add_argument("--subjects", nargs="+", required=True, help="选科（如 物理 化学 生物）")

    # art_score (艺术类综合分计算)
    art = subparsers.add_parser("art_score", help="艺术类综合分计算")
    art.add_argument("--province", required=True, help="省份（如 广东）")
    art.add_argument("--culture", type=int, required=True, help="文化课成绩")
    art.add_argument("--major_score", type=int, required=True, help="术科统考成绩")
    art.add_argument("--art_type", default="美术与设计类", help="艺术类别（默认美术与设计类）")
    art.add_argument("--major_full", type=int, default=300, help="术科满分（默认300）")

    # compare
    cmp_parser = subparsers.add_parser("compare", help="院校对比")
    cmp_parser.add_argument("--schools", nargs="+", required=True, help="院校名称")

    # list_subjects
    subparsers.add_parser("list_subjects", help="列出所有选科组合")

    args = parser.parse_args()

    if args.command == "score_to_rank":
        score_dist = load_score_distribution(args.province, args.year, args.category)
        if score_dist is None:
            print(json.dumps({
                "error": f"未找到 {args.province} {args.year} {args.category} 的一分一段表数据",
                "hint": f"请从省考试院官网获取数据后保存到 {DATA_DIR}/{args.province}_{args.year}_{args.category}_score_dist.json",
                "format": [{"score": 650, "count": 120, "cumulative": 500}],
            }, ensure_ascii=False, indent=2))
        else:
            result = score_to_rank(score_dist, args.score)
            print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "rank_to_score":
        score_dist = load_score_distribution(args.province, args.year, args.category)
        if score_dist is None:
            print(json.dumps({"error": "数据文件不存在"}, ensure_ascii=False))
        else:
            result = rank_to_score(score_dist, args.rank)
            print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "recommend":
        if args.data_file:
            with open(args.data_file, "r", encoding="utf-8") as f:
                admission_data = json.load(f)
        else:
            # 从缓存目录搜索
            pattern = f"{args.province}_{args.year}_*_admission.json"
            files = list(DATA_DIR.glob(pattern))
            admission_data = []
            for f in files:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    if isinstance(data, list):
                        admission_data.extend(data)
                    elif isinstance(data, dict):
                        admission_data.append(data)

        if not admission_data:
            print(json.dumps({
                "error": f"未找到 {args.province} {args.year} 的院校录取数据",
                "hint": "请从省考试院官网或目标院校招生网获取数据后导入",
            }, ensure_ascii=False))
        else:
            # v1.2: 构建偏好筛选条件
            preferences = None
            has_prefs = any([
                args.city, args.school_type, args.school, args.major,
                args.exclude_city, args.exclude_school_type, args.exclude_major
            ])
            if has_prefs:
                preferences = {}
                if args.city:
                    preferences["cities"] = args.city
                if args.school_type:
                    preferences["school_types"] = args.school_type
                if args.school:
                    preferences["schools"] = args.school
                if args.major:
                    preferences["majors"] = args.major
                exclude = {}
                if args.exclude_city:
                    exclude["cities"] = args.exclude_city
                if args.exclude_school_type:
                    exclude["school_types"] = args.exclude_school_type
                if args.exclude_major:
                    exclude["majors"] = args.exclude_major
                if exclude:
                    preferences["exclude"] = exclude

            result = generate_recommendation(admission_data, args.rank, preferences=preferences)
            if preferences:
                result["active_filters"] = preferences
            print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "major_query":
        result = query_major(args.subjects)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "art_score":
        result = calc_art_score(args.province, args.culture, args.major_score)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "compare":
        result = compare_schools(args.schools)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "list_subjects":
        for k, v in SUBJECT_MAJOR_MAP.items():
            print(f"{k} → 专业覆盖率 {v['coverage']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
