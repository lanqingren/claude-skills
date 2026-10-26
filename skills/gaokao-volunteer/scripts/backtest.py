#!/usr/bin/env python3
"""
高考志愿回测引擎
================
用 Year(N) 的投档数据模拟给 Year(N+1) 考生做志愿推荐，
然后用 Year(N+1) 的实际投档结果验证推荐准确度。

回测逻辑：
  1. 加载连续两年的投档数据
  2. 匹配两年共有的院校
  3. 对一系列模拟位次点（如每5000名一个），生成冲稳保方案
  4. 用次年实际投档线验证：推荐院校是否真的能录取？
  5. 输出命中率、滑档率、分数浪费等指标

用法：
  python backtest.py --year1 2024 --year2 2025 --province 贵州
"""

import json
import argparse
import os
from pathlib import Path
from collections import defaultdict

# ============================================================
# 数据加载
# ============================================================

DATA_DIR = Path(r"D:\GitHub\hermescn\data\gaokao-data")

def load_2024_data():
    """加载2024年贵州物理类投档数据（2133条，学校级别）"""
    filepath = DATA_DIR / "raw_2024.json"
    with open(filepath, "r", encoding="utf-8") as f:
        raw = json.load(f)
    
    schools = {}
    for r in raw:
        name = r.get("name", "").strip()
        rank_str = str(r.get("min_section", ""))
        if not name or not rank_str.isdigit():
            continue
        rank = int(rank_str)
        score = int(r["min"]) if str(r.get("min", "")).isdigit() else None
        
        # 同一学校取最低位次（最容易进的专业组）
        if name not in schools or rank > schools[name]["rank"]:
            schools[name] = {
                "school": name,
                "rank": rank,
                "score": score,
                "city": r.get("city_name", ""),
                "is_985": bool(r.get("f985")),
                "is_211": bool(r.get("f211")),
                "nature": r.get("nature_name", ""),  # 公办/民办
                "type": r.get("type_name", ""),
                "year": 2024,
            }
    return list(schools.values())


def load_2025_data():
    """加载2025年贵州物理类投档数据（767条，专业级别→聚合到学校级别）"""
    filepath = DATA_DIR / "贵州_2025_物理类_admission_raw.json"
    with open(filepath, "r", encoding="utf-8") as f:
        raw = json.load(f)
    
    schools = {}
    for r in raw:
        name = r.get("school", "").strip()
        rank = r.get("min_rank")
        if not name or not rank:
            continue
        rank = int(rank)
        score = r.get("min_score")
        
        # 聚合到学校级别：取最低位次
        if name not in schools or rank > schools[name]["rank"]:
            schools[name] = {
                "school": name,
                "rank": rank,
                "score": score,
                "year": 2025,
            }
    return list(schools.values())


def match_schools(year1_schools, year2_schools):
    """匹配两年共有的院校"""
    y1_map = {s["school"]: s for s in year1_schools}
    y2_map = {s["school"]: s for s in year2_schools}
    common_names = set(y1_map.keys()) & set(y2_map.keys())
    
    matched = []
    for name in common_names:
        matched.append({
            "school": name,
            "rank_y1": y1_map[name]["rank"],  # Year N 位次
            "rank_y2": y2_map[name]["rank"],  # Year N+1 位次（实际结果）
            "score_y1": y1_map[name].get("score"),
            "score_y2": y2_map[name].get("score"),
            "city": y1_map[name].get("city", ""),
            "is_985": y1_map[name].get("is_985", False),
            "is_211": y1_map[name].get("is_211", False),
            "nature": y1_map[name].get("nature", ""),
        })
    
    # 按Year N位次排序
    matched.sort(key=lambda x: x["rank_y1"])
    return matched


# ============================================================
# 冲稳保推荐模拟
# ============================================================

def simulate_recommendations(student_rank, schools_y1, config=None):
    """
    用Year N数据模拟给某位次考生的冲稳保推荐
    
    参数：
        student_rank: 考生位次（Year N+1的模拟位次）
        schools_y1: Year N的院校列表（用于生成推荐）
        config: 冲稳保参数
    
    返回：
        {"rush": [...], "stable": [...], "safe": [...]}
    """
    if config is None:
        config = {
            "rush_range": (-5000, -500),    # 冲：学校位次比考生高500-5000名
            "stable_range": (-500, 3000),    # 稳：学校位次在考生上下浮动
            "safe_range": (3000, 8000),      # 保：学校位次比考生低3000-8000名
        }
    
    result = {"rush": [], "stable": [], "safe": []}
    
    for s in schools_y1:
        school_rank = s["rank"]  # Year N 的该校最低位次
        delta = student_rank - school_rank  # 正数=考生位次低于学校（更容易进）
        
        school_info = {
            "school": s["school"],
            "rank_y1": school_rank,
            "rank_delta": delta,
            "city": s.get("city", ""),
            "is_985": s.get("is_985", False),
            "is_211": s.get("is_211", False),
            "nature": s.get("nature", ""),
        }
        
        if config["rush_range"][0] <= delta < config["rush_range"][1]:
            result["rush"].append(school_info)
        elif config["stable_range"][0] <= delta < config["stable_range"][1]:
            result["stable"].append(school_info)
        elif config["safe_range"][0] <= delta < config["safe_range"][1]:
            result["safe"].append(school_info)
    
    return result


# ============================================================
# 回测验证
# ============================================================

def validate_recommendations(recommendation, matched_schools):
    """
    用Year N+1实际数据验证推荐是否命中
    
    逻辑：如果该校Year N+1的实际录取位次 <= 考生位次，则命中（能录取）
         （位次数字越小=排名越靠前=越难进）
    """
    # 建立校名→Year N+1实际位次的映射
    y2_rank_map = {m["school"]: m["rank_y2"] for m in matched_schools}
    
    results = {"rush": [], "stable": [], "safe": []}
    
    for tier in ["rush", "stable", "safe"]:
        for rec in recommendation[tier]:
            school = rec["school"]
            actual_rank_y2 = y2_rank_map.get(school)
            
            if actual_rank_y2 is None:
                # 该校不在Year N+1数据中，无法验证
                results[tier].append({**rec, "actual_rank_y2": None, "hit": None})
            else:
                # 命中条件：考生位次优于（数字更小或等于）该校实际录取位次
                # student_rank <= actual_rank_y2 → 能录取
                student_rank = rec["rank_y1"] + rec["rank_delta"]
                hit = student_rank <= actual_rank_y2
                results[tier].append({
                    **rec,
                    "actual_rank_y2": actual_rank_y2,
                    "hit": hit,
                })
    
    return results


def run_backtest(matched_schools, year1_schools, rank_points=None):
    """
    对一系列位次点运行完整回测
    
    参数：
        matched_schools: 两年匹配的院校数据
        year1_schools: Year N院校列表（用于生成推荐）
        rank_points: 要测试的位次列表
    """
    if rank_points is None:
        # 从1万到10万，每1万取一个点
        rank_points = list(range(10000, 110000, 10000))
    
    # 只用matched schools的Year N数据来生成推荐（这样能验证）
    y1_for_recommend = [{"school": m["school"], "rank": m["rank_y1"],
                         "city": m["city"], "is_985": m["is_985"],
                         "is_211": m["is_211"], "nature": m["nature"]}
                        for m in matched_schools]
    
    all_results = []
    
    for rank in rank_points:
        rec = simulate_recommendations(rank, y1_for_recommend)
        validated = validate_recommendations(rec, matched_schools)
        
        # 统计命中率
        stats = {}
        for tier in ["rush", "stable", "safe"]:
            tier_results = validated[tier]
            verifiable = [r for r in tier_results if r["hit"] is not None]
            hits = [r for r in verifiable if r["hit"]]
            stats[tier] = {
                "total": len(tier_results),
                "verifiable": len(verifiable),
                "hits": len(hits),
                "hit_rate": len(hits) / len(verifiable) if verifiable else None,
            }
        
        # 滑档检测：三档全部未命中
        total_hits = sum(stats[t]["hits"] for t in ["rush", "stable", "safe"])
        total_verifiable = sum(stats[t]["verifiable"] for t in ["rush", "stable", "safe"])
        slid = total_verifiable > 0 and total_hits == 0
        
        all_results.append({
            "student_rank": rank,
            "stats": stats,
            "total_recommendations": sum(stats[t]["total"] for t in stats),
            "total_verifiable": total_verifiable,
            "total_hits": total_hits,
            "overall_hit_rate": total_hits / total_verifiable if total_verifiable else None,
            "slid": slid,
            "details": validated,
        })
    
    return all_results


# ============================================================
# 报告生成
# ============================================================

def print_report(results, matched_count, year1, year2):
    """打印回测报告"""
    print()
    print("═" * 60)
    print(f"📊 高考志愿回测报告")
    print(f"   {year1}年数据 → 推荐 → {year2}年实际验证")
    print(f"   匹配院校: {matched_count} 所")
    print("═" * 60)
    print()
    
    # 期望命中率
    expected = {"rush": "40-60%", "stable": "70-85%", "safe": "90%+"}
    tier_name = {"rush": "🏃 冲刺", "stable": "⚖️ 稳妥", "safe": "🛡️ 保底"}
    
    print(f"{'考生位次':>8} │ {'冲档命中':>10} │ {'稳档命中':>10} │ {'保档命中':>10} │ {'总命中':>8} │ {'滑档':>4}")
    print("─" * 75)
    
    for r in results:
        rank = r["student_rank"]
        parts = []
        for tier in ["rush", "stable", "safe"]:
            s = r["stats"][tier]
            if s["verifiable"] > 0:
                parts.append(f"{s['hits']}/{s['verifiable']}")
            else:
                parts.append("-")
        
        total_str = f"{r['total_hits']}/{r['total_verifiable']}" if r["total_verifiable"] > 0 else "-"
        slid_str = "❌" if r["slid"] else "✅"
        
        print(f"{rank:>8,} │ {parts[0]:>10} │ {parts[1]:>10} │ {parts[2]:>10} │ {total_str:>8} │ {slid_str:>4}")
    
    print()
    print("─" * 60)
    print("📈 各档位命中率 vs 期望值")
    print("─" * 60)
    
    for tier in ["rush", "stable", "safe"]:
        hit_rates = []
        for r in results:
            hr = r["stats"][tier]["hit_rate"]
            if hr is not None:
                hit_rates.append(hr)
        
        if hit_rates:
            avg = sum(hit_rates) / len(hit_rates)
            print(f"{tier_name[tier]:8s} 平均命中率: {avg:.1%} （期望: {expected[tier]}）")
        else:
            print(f"{tier_name[tier]:8s} 无可验证数据")
    
    print()
    
    # 滑档分析
    slid_cases = [r for r in results if r["slid"]]
    if slid_cases:
        print(f"⚠️ 滑档案例: {len(slid_cases)} 个位次点出现全部未命中")
        for sc in slid_cases:
            print(f"   位次 {sc['student_rank']:,}: 推荐{sc['total_recommendations']}所，验证{sc['total_verifiable']}所，命中0所")
    else:
        print("✅ 无滑档案例")
    
    print()
    return results


def save_report(results, matched_count, year1, year2, output_path):
    """保存回测结果为JSON"""
    report = {
        "meta": {
            "year_reference": year1,
            "year_actual": year2,
            "matched_schools": matched_count,
            "province": "贵州",
            "category": "物理类",
        },
        "summary": {
            "total_rank_points": len(results),
            "avg_overall_hit_rate": sum(r["overall_hit_rate"] for r in results if r["overall_hit_rate"]) / max(1, len([r for r in results if r["overall_hit_rate"]])),
            "slid_cases": len([r for r in results if r["slid"]]),
        },
        "results": results,
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📁 回测结果已保存: {output_path}")


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="高考志愿回测引擎")
    parser.add_argument("--year1", type=int, default=2024, help="参考年份（用于生成推荐）")
    parser.add_argument("--year2", type=int, default=2025, help="验证年份（实际结果）")
    parser.add_argument("--output", default=None, help="输出文件路径")
    args = parser.parse_args()
    
    print(f"🔄 加载{args.year1}年数据...")
    y1_schools = load_2024_data() if args.year1 == 2024 else []
    print(f"   {len(y1_schools)} 所院校")
    
    print(f"🔄 加载{args.year2}年数据...")
    y2_schools = load_2025_data() if args.year2 == 2025 else []
    print(f"   {len(y2_schools)} 所院校")
    
    print(f"🔄 匹配两年共有院校...")
    matched = match_schools(y1_schools, y2_schools)
    print(f"   {len(matched)} 所共有院校")
    
    if len(matched) < 10:
        print("⚠️ 匹配院校太少，回测结果可能不具代表性")
    
    print(f"🔄 开始回测（{args.year1}→{args.year2}）...")
    results = run_backtest(matched, y1_schools)
    
    print_report(results, len(matched), args.year1, args.year2)
    
    output = args.output or str(DATA_DIR / f"backtest_{args.year1}_{args.year2}.json")
    save_report(results, len(matched), args.year1, args.year2, output)


if __name__ == "__main__":
    main()
