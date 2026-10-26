#!/usr/bin/env python3
"""
高考志愿多省份回测引擎 v2
==========================
使用连续两年的投档数据做回测：
  Year N 数据 → 模拟推荐 → Year N+1 实际录取验证

支持多省份、多科类、多批次。
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict
import statistics

DATA_DIR = Path(r"D:\GitHub\hermescn\data\gaokao-data")
MULTI_DIR = DATA_DIR / "multi_province"


def load_guizhou_2024():
    """贵州2024物理类投档（2133条，学校级别聚合）"""
    with open(DATA_DIR / "raw_2024.json", "r", encoding="utf-8") as f:
        raw = json.load(f)
    
    schools = {}
    for r in raw:
        name = r.get("name", "").strip()
        rank_str = str(r.get("min_section", ""))
        batch = r.get("local_batch_name", "")
        if not name or not rank_str.isdigit():
            continue
        # 只取本科批
        if "本科" not in batch:
            continue
        rank = int(rank_str)
        score = int(r["min"]) if str(r.get("min", "")).isdigit() else None
        
        if name not in schools or rank > schools[name]["min_rank"]:
            schools[name] = {
                "school": name,
                "min_rank": rank,
                "min_score": score,
                "city": r.get("city_name", ""),
                "is_985": bool(r.get("f985")),
                "is_211": bool(r.get("f211")),
                "nature": r.get("nature_name", ""),
                "type": r.get("type_name", ""),
            }
    return list(schools.values())


def load_guizhou_2025():
    """贵州2025物理类投档（18325条专业级，聚合到学校级）"""
    filepath = DATA_DIR / "贵州_2025_物理类_本科批投档_complete.json"
    if not filepath.exists():
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
        
        if name not in schools or rank > schools[name]["min_rank"]:
            schools[name] = {
                "school": name,
                "min_rank": rank,
                "min_score": r.get("min_score"),
                "city": "",
                "is_985": False,
                "is_211": False,
                "nature": "",
                "type": "",
            }
    return list(schools.values())


def load_guangdong(year):
    """广东考生投档数据（从multi_province筛选）"""
    filepath = MULTI_DIR / f"广东_{year}_admission.json"
    if not filepath.exists():
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        raw = json.load(f)
    
    # 筛选广东物理类考生
    schools = {}
    for r in raw:
        if r.get("local_province_name") != "广东":
            continue
        if r.get("local_type_name") != "物理类":
            continue
        if "本科" not in r.get("local_batch_name", ""):
            continue
        
        name = r.get("name", "").strip()
        rank_str = str(r.get("min_section", ""))
        if not name or not rank_str.isdigit():
            continue
        rank = int(rank_str)
        score = int(r["min"]) if str(r.get("min", "")).isdigit() else None
        
        if name not in schools or rank > schools[name]["min_rank"]:
            schools[name] = {
                "school": name,
                "min_rank": rank,
                "min_score": score,
                "city": r.get("city_name", ""),
                "is_985": bool(r.get("f985")),
                "is_211": bool(r.get("f211")),
                "nature": r.get("nature_name", ""),
                "type": r.get("type_name", ""),
            }
    return list(schools.values())


def match_years(year1_schools, year2_schools):
    """匹配两年共有院校"""
    y1 = {s["school"]: s for s in year1_schools}
    y2 = {s["school"]: s for s in year2_schools}
    common = set(y1.keys()) & set(y2.keys())
    
    matched = []
    for name in common:
        matched.append({
            "school": name,
            "rank_y1": y1[name]["min_rank"],
            "rank_y2": y2[name]["min_rank"],
            "score_y1": y1[name].get("min_score"),
            "score_y2": y2[name].get("min_score"),
            "is_985": y1[name].get("is_985", False),
            "is_211": y1[name].get("is_211", False),
            "nature": y1[name].get("nature", ""),
            "city": y1[name].get("city", ""),
        })
    matched.sort(key=lambda x: x["rank_y1"])
    return matched


def simulate_recommend(student_rank, schools, config):
    """模拟冲稳保推荐"""
    result = {"rush": [], "stable": [], "safe": []}
    
    for s in schools:
        delta = student_rank - s["min_rank"]  # 正=考生位次低于学校=更容易进
        info = {**s, "rank_delta": delta}
        
        if config["rush"][0] <= delta < config["rush"][1]:
            result["rush"].append(info)
        elif config["stable"][0] <= delta < config["stable"][1]:
            result["stable"].append(info)
        elif config["safe"][0] <= delta < config["safe"][1]:
            result["safe"].append(info)
    
    return result


def validate(recs, rank_map_y2, student_rank):
    """验证推荐是否命中"""
    for tier in ["rush", "stable", "safe"]:
        for rec in recs[tier]:
            actual = rank_map_y2.get(rec["school"])
            if actual is None:
                rec["actual_rank_y2"] = None
                rec["hit"] = None
            else:
                rec["actual_rank_y2"] = actual
                # 命中=考生位次优于（数字更小或等于）学校实际录取最低位次
                rec["hit"] = student_rank <= actual
    return recs


def run_backtest(matched, config, rank_points=None):
    """对多个位次点运行回测"""
    if rank_points is None:
        all_ranks = [m["rank_y1"] for m in matched]
        if all_ranks:
            lo, hi = min(all_ranks), max(all_ranks)
            step = max((hi - lo) // 15, 1000)
            rank_points = list(range(int(lo), int(hi), int(step)))
    
    y1_schools = [{"school": m["school"], "min_rank": m["rank_y1"],
                    "is_985": m["is_985"], "is_211": m["is_211"],
                    "nature": m["nature"], "city": m["city"]}
                   for m in matched]
    y2_map = {m["school"]: m["rank_y2"] for m in matched}
    
    results = []
    for rank in rank_points:
        recs = simulate_recommend(rank, y1_schools, config)
        validated = validate(recs, y2_map, rank)
        
        stats = {}
        for tier in ["rush", "stable", "safe"]:
            verifiable = [r for r in validated[tier] if r["hit"] is not None]
            hits = [r for r in verifiable if r["hit"]]
            stats[tier] = {
                "total": len(validated[tier]),
                "verifiable": len(verifiable),
                "hits": len(hits),
                "hit_rate": len(hits) / len(verifiable) if verifiable else None,
            }
        
        total_v = sum(s["verifiable"] for s in stats.values())
        total_h = sum(s["hits"] for s in stats.values())
        
        results.append({
            "student_rank": rank,
            "stats": stats,
            "total_verifiable": total_v,
            "total_hits": total_h,
            "overall_hit_rate": total_h / total_v if total_v else None,
            "slid": total_v > 0 and total_h == 0,
            "details": validated,
        })
    
    return results


def analyze_rank_shift(matched):
    """分析院校位次年际波动"""
    shifts = []
    for m in matched:
        shift = m["rank_y2"] - m["rank_y1"]
        shift_pct = shift / m["rank_y1"] * 100 if m["rank_y1"] else 0
        shifts.append({
            "school": m["school"],
            "rank_y1": m["rank_y1"],
            "rank_y2": m["rank_y2"],
            "shift": shift,
            "shift_pct": shift_pct,
            "is_985": m.get("is_985"),
            "is_211": m.get("is_211"),
            "nature": m.get("nature", ""),
        })
    return shifts


def print_full_report(results, matched, shifts, label):
    """打印完整回测报告"""
    print()
    print("═" * 70)
    print(f"📊 回测报告: {label}")
    print(f"   匹配院校: {len(matched)} 所")
    print("═" * 70)
    
    # 1. 命中率表
    print(f"\n{'考生位次':>8} │ {'冲(期望40-60%)':>16} │ {'稳(期望70-85%)':>16} │ {'保(期望90%+)':>16} │ {'滑档':>4}")
    print("─" * 80)
    
    tier_hit_rates = {"rush": [], "stable": [], "safe": []}
    
    for r in results:
        rank = r["student_rank"]
        parts = []
        for tier in ["rush", "stable", "safe"]:
            s = r["stats"][tier]
            if s["verifiable"] > 0:
                pct = s["hits"] / s["verifiable"]
                parts.append(f"{s['hits']}/{s['verifiable']} ({pct:.0%})")
                tier_hit_rates[tier].append(pct)
            else:
                parts.append("-")
        
        slid = "❌" if r["slid"] else "✅"
        print(f"{rank:>8,} │ {parts[0]:>16} │ {parts[1]:>16} │ {parts[2]:>16} │ {slid:>4}")
    
    # 2. 平均命中率
    print(f"\n{'─'*70}")
    print("📈 平均命中率 vs 期望值:")
    expected = {"rush": "40-60%", "stable": "70-85%", "safe": "90%+"}
    tier_names = {"rush": "🏃 冲", "stable": "⚖️ 稳", "safe": "🛡️ 保"}
    
    for tier in ["rush", "stable", "safe"]:
        rates = tier_hit_rates[tier]
        if rates:
            avg = statistics.mean(rates)
            print(f"  {tier_names[tier]}: {avg:.1%} （期望 {expected[tier]}）")
        else:
            print(f"  {tier_names[tier]}: 无数据")
    
    # 3. 位次波动分析
    print(f"\n{'─'*70}")
    print("📉 院校位次年际波动分析:")
    shift_values = [s["shift"] for s in shifts]
    if shift_values:
        print(f"  平均偏移: {statistics.mean(shift_values):+,.0f}")
        print(f"  中位偏移: {statistics.median(shift_values):+,.0f}")
        print(f"  波动标准差: {statistics.stdev(shift_values):,.0f}")
        print(f"  恶化（更难考）: {len([s for s in shift_values if s < 0])}/{len(shift_values)} ({len([s for s in shift_values if s < 0])/len(shift_values):.0%})")
        print(f"  偏移>5000名的: {len([s for s in shift_values if abs(s) > 5000])}/{len(shift_values)} ({len([s for s in shift_values if abs(s) > 5000])/len(shift_values):.0%})")
        print(f"  偏移>10000名的: {len([s for s in shift_values if abs(s) > 10000])}/{len(shift_values)} ({len([s for s in shift_values if abs(s) > 10000])/len(shift_values):.0%})")
    
    # 4. 滑档分析
    slid_cases = [r for r in results if r["slid"]]
    if slid_cases:
        print(f"\n⚠️ 滑档案例 ({len(slid_cases)}个位次点):")
        for sc in slid_cases:
            print(f"  位次 {sc['student_rank']:,}: 推荐{sum(sc['stats'][t]['total'] for t in ['rush','stable','safe'])}所, 验证{sc['total_verifiable']}所, 命中0所")
    
    # 5. 按院校类型分析命中率
    print(f"\n{'─'*70}")
    print("🏫 按院校类型分析:")
    
    by_type = defaultdict(lambda: {"total": 0, "hits": 0})
    for r in results:
        for tier in ["rush", "stable", "safe"]:
            for d in r["details"][tier]:
                if d["hit"] is not None:
                    if d.get("is_985"):
                        cat = "985"
                    elif d.get("is_211"):
                        cat = "211"
                    elif "民办" in d.get("nature", ""):
                        cat = "民办"
                    elif "公办" in d.get("nature", ""):
                        cat = "公办"
                    else:
                        cat = "其他"
                    by_type[cat]["total"] += 1
                    if d["hit"]:
                        by_type[cat]["hits"] += 1
    
    for cat, counts in sorted(by_type.items(), key=lambda x: -x[1]["total"]):
        if counts["total"] > 0:
            rate = counts["hits"] / counts["total"]
            print(f"  {cat:6s}: {counts['hits']}/{counts['total']} = {rate:.1%}")
    
    print()
    return results, shifts


def main():
    config_sets = {
        "current": {
            "rush": (-5000, -500),
            "stable": (-500, 3000),
            "safe": (3000, 8000),
        },
        "conservative": {
            "rush": (-3000, -500),
            "stable": (-500, 5000),
            "safe": (5000, 12000),
        },
        "wide": {
            "rush": (-8000, -1000),
            "stable": (-1000, 5000),
            "safe": (5000, 15000),
        },
    }
    
    all_results = {}
    
    # ============ 贵州回测 ============
    print("=" * 70)
    print("🔄 加载贵州数据...")
    gz_2024 = load_guizhou_2024()
    gz_2025 = load_guizhou_2025()
    print(f"  2024: {len(gz_2024)} 所, 2025: {len(gz_2025)} 所")
    
    gz_matched = match_years(gz_2024, gz_2025)
    print(f"  匹配: {len(gz_matched)} 所共有院校")
    
    if len(gz_matched) >= 20:
        gz_shifts = analyze_rank_shift(gz_matched)
        
        print(f"\n🔄 贵州回测（3种策略对比）...")
        for config_name, config in config_sets.items():
            results = run_backtest(gz_matched, config)
            label = f"贵州 2024→2025 [{config_name}]"
            all_results[f"贵州_{config_name}"] = (results, gz_shifts)
            print_full_report(results, gz_matched, gz_shifts, label)
    
    # ============ 广东回测 ============
    print("=" * 70)
    print("🔄 加载广东数据...")
    for y1, y2 in [(2022, 2023), (2023, 2024)]:
        gd_y1 = load_guangdong(y1)
        gd_y2 = load_guangdong(y2)
        if not gd_y1 or not gd_y2:
            print(f"  {y1}→{y2}: 数据不足 ({len(gd_y1)}/{len(gd_y2)})")
            continue
        
        gd_matched = match_years(gd_y1, gd_y2)
        print(f"  广东 {y1}→{y2}: {len(gd_y1)}/{len(gd_y2)} 所, 匹配 {len(gd_matched)} 所")
        
        if len(gd_matched) >= 10:
            gd_shifts = analyze_rank_shift(gd_matched)
            results = run_backtest(gd_matched, config_sets["current"])
            all_results[f"广东_{y1}_{y2}"] = (results, gd_shifts)
            print_full_report(results, gd_matched, gd_shifts, f"广东 {y1}→{y2} [current]")
    
    # ============ 综合分析 ============
    print("\n" + "═" * 70)
    print("📋 多省份综合分析")
    print("═" * 70)
    
    print("\n📊 各回测的平均命中率汇总:")
    print(f"{'回测':>25s} │ {'冲':>8s} │ {'稳':>8s} │ {'保':>8s} │ {'滑档数':>6s}")
    print("─" * 65)
    
    for key, (results, shifts) in all_results.items():
        tier_rates = {"rush": [], "stable": [], "safe": []}
        slid_count = 0
        for r in results:
            for tier in ["rush", "stable", "safe"]:
                if r["stats"][tier]["hit_rate"] is not None:
                    tier_rates[tier].append(r["stats"][tier]["hit_rate"])
            if r["slid"]:
                slid_count += 1
        
        avg_rush = statistics.mean(tier_rates["rush"]) if tier_rates["rush"] else 0
        avg_stable = statistics.mean(tier_rates["stable"]) if tier_rates["stable"] else 0
        avg_safe = statistics.mean(tier_rates["safe"]) if tier_rates["safe"] else 0
        
        print(f"{key:>25s} │ {avg_rush:>7.0%} │ {avg_stable:>7.0%} │ {avg_safe:>7.0%} │ {slid_count:>6}")
    
    # ============ 保存结果 ============
    output_path = DATA_DIR / "backtest_multi_province.json"
    save_data = {}
    for key, (results, shifts) in all_results.items():
        save_data[key] = {
            "results": results,
            "rank_shifts": shifts,
            "summary": {
                "avg_rush": statistics.mean([r["stats"]["rush"]["hit_rate"] for r in results if r["stats"]["rush"]["hit_rate"] is not None]) if any(r["stats"]["rush"]["hit_rate"] for r in results) else 0,
                "avg_stable": statistics.mean([r["stats"]["stable"]["hit_rate"] for r in results if r["stats"]["stable"]["hit_rate"] is not None]) if any(r["stats"]["stable"]["hit_rate"] for r in results) else 0,
                "avg_safe": statistics.mean([r["stats"]["safe"]["hit_rate"] for r in results if r["stats"]["safe"]["hit_rate"] is not None]) if any(r["stats"]["safe"]["hit_rate"] for r in results) else 0,
            }
        }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    print(f"\n📁 完整回测结果 → {output_path}")


if __name__ == "__main__":
    main()
