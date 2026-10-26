#!/usr/bin/env python3
"""全国多省份高考投档数据回测引擎 v3
- 加载 multi_province/ 下所有省份数据
- 对每省做 Year(2023) → Year(2024) 回测
- 计算冲稳保垫命中率、位次波动、最优参数
- 输出JSON + 控制台报告
"""
import json, os, sys
from collections import defaultdict
import statistics

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data\multi_province"

# v1.4 策略参数（待校准）
STRATEGIES = {
    "旧策略(传统)": {"冲": (500, 5000), "稳": (-2000, 500), "保": (-8000, -2000)},
    "v1.4校准": {"冲": (500, 5000), "稳上": (-500, 500), "稳下": (-10000, -500), "保": (-25000, -10000)},
}


def load_province_data(pname, year):
    """加载某省某年投档数据"""
    # 优先用不带type的新格式
    for pattern in [f"{pname}_{year}_admission.json"]:
        fpath = os.path.join(DATA_DIR, pattern)
        if os.path.exists(fpath):
            try:
                data = json.load(open(fpath, "r", encoding="utf-8"))
                if isinstance(data, list) and len(data) > 0:
                    return data
            except:
                pass
    return None


def extract_records(raw_data):
    """从原始数据提取关键信息"""
    records = []
    for item in raw_data:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "")
        min_score = item.get("min", None)
        min_section = item.get("min_section", None)
        batch = item.get("local_batch_name", "")
        type_name = item.get("local_type_name", "")
        level = item.get("level_name", "")
        school_id = item.get("school_id", "")
        
        # 只保留有排位数据的本科批记录
        if not name or min_section is None or min_section == "-" or min_section == "":
            continue
        if "本科" not in (batch + level):
            continue
        
        try:
            rank = int(min_section)
            score = int(min_score) if min_score and min_score != "-" else None
        except (ValueError, TypeError):
            continue
        
        # 用 school_id + 专业组 做唯一键（同一学校不同专业组分开计）
        sg = item.get("sg_name", "")
        key = f"{school_id}_{sg}" if school_id else f"{name}_{sg}"
        
        records.append({
            "key": key,
            "name": name,
            "school_id": school_id,
            "sg": sg,
            "score": score,
            "rank": rank,
            "type": type_name,
            "batch": batch,
        })
    return records


def backtest_province(pname, records_2023, records_2024):
    """对单省做回测"""
    # 匹配两年数据
    map_2023 = {r["key"]: r for r in records_2023}
    map_2024 = {r["key"]: r for r in records_2024}
    
    common_keys = set(map_2023.keys()) & set(map_2024.keys())
    if len(common_keys) < 10:
        return None
    
    matched = []
    for key in common_keys:
        r23 = map_2023[key]
        r24 = map_2024[key]
        matched.append({
            "key": key,
            "name": r23["name"],
            "rank_2023": r23["rank"],
            "rank_2024": r24["rank"],
            "score_2023": r23["score"],
            "score_2024": r24["score"],
            "shift": r24["rank"] - r23["rank"],  # 正=位次后移(变难考)
        })
    
    # 模拟：用2023年数据推荐，用2024年实际录取验证
    # 对每个模拟考生排位，计算各档命中率
    test_ranks = [5000, 10000, 15000, 20000, 30000, 50000, 80000, 100000]
    
    results = {
        "province": pname,
        "matched_count": len(matched),
        "shifts": [],
        "tier_hit_rates": {},
    }
    
    # 位次偏移统计
    shifts = [m["shift"] for m in matched]
    results["shifts"] = {
        "mean": round(statistics.mean(shifts)),
        "median": round(statistics.median(shifts)),
        "stdev": round(statistics.stdev(shifts)) if len(shifts) > 1 else 0,
        "forward_count": sum(1 for s in shifts if s > 0),  # 位次前移(变难考)
        "backward_count": sum(1 for s in shifts if s < 0),  # 位次后移(变容易)
        "stable_count": sum(1 for s in shifts if abs(s) <= 1000),
        "big_shift_count": sum(1 for s in shifts if abs(s) > 5000),
    }
    
    # 各策略命中率
    for strategy_name, tiers in STRATEGIES.items():
        tier_stats = {}
        for tier_name, (lo, hi) in tiers.items():
            # 对每个测试排位计算命中率
            hit_rates = []
            for test_rank in test_ranks:
                # 找2023年排位在[lo, hi]区间的学校（相对于test_rank）
                candidates = [m for m in matched if lo <= (test_rank - m["rank_2023"]) <= hi]
                if not candidates:
                    continue
                # 检查2024年是否录取（考生排位 ≤ 学校2024排位 = 录取）
                # 排位数字越小=成绩越好，考生排位≤学校最低排位=被录取
                hits = sum(1 for c in candidates if test_rank <= c["rank_2024"])
                rate = hits / len(candidates) if candidates else 0
                hit_rates.append(rate)
            
            if hit_rates:
                tier_stats[tier_name] = {
                    "avg_hit_rate": round(statistics.mean(hit_rates) * 100, 1),
                    "min": round(min(hit_rates) * 100, 1),
                    "max": round(max(hit_rates) * 100, 1),
                    "test_count": len(hit_rates),
                }
            else:
                tier_stats[tier_name] = {"avg_hit_rate": None, "test_count": 0}
        
        results["tier_hit_rates"][strategy_name] = tier_stats
    
    return results


def main():
    print("=" * 70)
    print("🔬 全国多省份高考投档数据回测引擎 v3")
    print("=" * 70)
    
    # 扫描所有可用省份
    province_years = defaultdict(set)
    for f in os.listdir(DATA_DIR):
        if f.endswith("_admission.json") and "type" not in f and "student" not in f:
            # 格式: 省名_年份_admission.json
            parts = f.replace("_admission.json", "").rsplit("_", 1)
            if len(parts) == 2:
                pname = parts[0]
                try:
                    year = int(parts[1])
                    province_years[pname].add(year)
                except:
                    pass
    
    # 找有2023+2024两年数据的省份
    backtest_provinces = {p: sorted(list(years)) for p, years in province_years.items() if 2023 in years and 2024 in years}
    
    print(f"\n📊 可用数据:")
    for p, yrs in sorted(backtest_provinces.items()):
        print(f"  {p}: {yrs}")
    print(f"\n共 {len(backtest_provinces)} 个省份有两年数据可回测")
    
    if not backtest_provinces:
        print("\n❌ 没有省份同时有2023和2024年数据！")
        print("请先运行 fetch_all_provinces.py 下载全国数据")
        return
    
    # 逐省回测
    all_results = []
    for pname in sorted(backtest_provinces.keys()):
        print(f"\n{'─'*50}")
        print(f"📂 {pname}")
        
        r2023 = load_province_data(pname, 2023)
        r2024 = load_province_data(pname, 2024)
        
        if not r2023 or not r2024:
            print(f"  ❌ 数据加载失败")
            continue
        
        rec23 = extract_records(r2023)
        rec24 = extract_records(r2024)
        
        print(f"  2023年: {len(rec23)}条有效记录")
        print(f"  2024年: {len(rec24)}条有效记录")
        
        result = backtest_province(pname, rec23, rec24)
        if result:
            print(f"  匹配: {result['matched_count']}所院校专业组")
            s = result["shifts"]
            print(f"  位次偏移: 均值{s['mean']:+d} | 中位数{s['median']:+d} | 标准差±{s['stdev']}")
            print(f"  前移(变难): {s['forward_count']} | 后移(变易): {s['backward_count']} | 大偏移(>5000): {s['big_shift_count']}")
            
            for strat, tiers in result["tier_hit_rates"].items():
                print(f"  [{strat}]")
                for tier, stats in tiers.items():
                    if stats["avg_hit_rate"] is not None:
                        print(f"    {tier}: {stats['avg_hit_rate']}% ({stats['min']}%-{stats['max']}%, {stats['test_count']}个测试点)")
            
            all_results.append(result)
        else:
            print(f"  ❌ 匹配数量不足")
    
    # 汇总统计
    print(f"\n{'='*70}")
    print(f"📈 全国汇总 ({len(all_results)}个省份)")
    print(f"{'='*70}")
    
    if not all_results:
        print("无有效回测结果")
        return
    
    # 汇总位次偏移
    all_shifts = []
    total_matched = 0
    for r in all_results:
        all_shifts.append(r["shifts"]["mean"])
        total_matched += r["matched_count"]
    
    print(f"\n总匹配院校专业组: {total_matched:,}")
    print(f"各省位次偏移均值: {statistics.mean(all_shifts):+.0f}")
    print(f"各省位次偏移范围: {min(all_shifts):+.0f} ~ {max(all_shifts):+.0f}")
    
    # 汇总各策略命中率
    for strategy_name in STRATEGIES.keys():
        print(f"\n[{strategy_name}] 各档平均命中率:")
        tier_names = list(STRATEGIES[strategy_name].keys())
        for tier_name in tier_names:
            rates = []
            for r in all_results:
                t = r["tier_hit_rates"].get(strategy_name, {}).get(tier_name, {})
                if t.get("avg_hit_rate") is not None:
                    rates.append(t["avg_hit_rate"])
            if rates:
                print(f"  {tier_name}: {statistics.mean(rates):.1f}% (范围{min(rates):.1f}%-{max(rates):.1f}%, {len(rates)}省)")
    
    # 保存
    output_path = os.path.join(os.path.dirname(DATA_DIR), "backtest_all_provinces.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 详细结果已保存: {output_path}")


if __name__ == "__main__":
    main()
