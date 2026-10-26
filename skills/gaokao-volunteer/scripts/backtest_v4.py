#!/usr/bin/env python3
"""全国高考投档回测引擎 v4 - 统一格式版
支持API格式和PDF格式数据，学校级别匹配
"""
import json, os, statistics
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
MULTI_DIR = os.path.join(DATA_DIR, "multi_province")


def load_api_format(fpath):
    """加载API格式数据（北京/广东/raw_2024）"""
    data = json.load(open(fpath, "r", encoding="utf-8"))
    schools = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "")
        rank = item.get("min_section", None)
        batch = item.get("local_batch_name", "")
        if not name or rank in (None, "-", ""):
            continue
        if "本科" not in batch and "本科" not in str(item.get("level_name", "")):
            continue
        try:
            rank = int(rank)
        except:
            continue
        # 取每校最低排位（最容易进的）
        if name not in schools or rank < schools[name]:
            schools[name] = rank
    return schools


def load_pdf_format(fpath):
    """加载PDF格式数据（贵州2025）"""
    data = json.load(open(fpath, "r", encoding="utf-8"))
    schools = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        name = item.get("school", "")
        rank = item.get("min_rank", None)
        if not name or rank in (None, "", 0):
            continue
        try:
            rank = int(rank)
        except:
            continue
        if name not in schools or rank < schools[name]:
            schools[name] = rank
    return schools


def run_backtest(pname, schools_old, schools_new, year_old, year_new):
    """单省回测"""
    common = set(schools_old.keys()) & set(schools_new.keys())
    if len(common) < 20:
        return None
    
    matched = []
    for name in common:
        r_old = schools_old[name]
        r_new = schools_new[name]
        matched.append({
            "name": name,
            "rank_old": r_old,
            "rank_new": r_new,
            "shift": r_new - r_old,
        })
    
    # 位次偏移统计
    shifts = [m["shift"] for m in matched]
    shift_stats = {
        "matched": len(matched),
        "mean": round(statistics.mean(shifts)),
        "median": round(statistics.median(shifts)),
        "stdev": round(statistics.stdev(shifts)),
        "forward": sum(1 for s in shifts if s > 0),
        "backward": sum(1 for s in shifts if s < 0),
        "big_shift": sum(1 for s in shifts if abs(s) > 5000),
    }
    
    # 策略回测
    test_ranks = [5000, 10000, 20000, 30000, 50000, 80000, 100000, 150000]
    tiers = {
        "冲(500-5000)": (500, 5000),
        "稳上(-500~500)": (-500, 500),
        "稳下(-10000~-500)": (-10000, -500),
        "保(-25000~-10000)": (-25000, -10000),
        "垫(>-25000)": (-100000, -25000),
    }
    
    tier_results = {}
    for tier_name, (lo, hi) in tiers.items():
        rates = []
        for test_rank in test_ranks:
            candidates = [m for m in matched if lo <= (test_rank - m["rank_old"]) <= hi]
            if not candidates:
                continue
            # 录取 = 考生排位 ≤ 学校新排位
            hits = sum(1 for c in candidates if test_rank <= c["rank_new"])
            rates.append(hits / len(candidates))
        
        if rates:
            tier_results[tier_name] = {
                "avg": round(statistics.mean(rates) * 100, 1),
                "min": round(min(rates) * 100, 1),
                "max": round(max(rates) * 100, 1),
                "n": len(rates),
            }
    
    return {"province": pname, "years": f"{year_old}→{year_new}", **shift_stats, "tiers": tier_results}


def main():
    print("=" * 75)
    print("🔬 全国高考投档回测引擎 v4（统一学校级别匹配）")
    print("=" * 75)
    
    all_results = []
    
    # === 贵州 2024→2025 ===
    print("\n📂 贵州")
    gz_2024 = load_api_format(os.path.join(DATA_DIR, "raw_2024.json"))
    gz_2025 = load_pdf_format(os.path.join(DATA_DIR, "贵州_2025_物理类_本科批投档_complete.json"))
    print(f"  2024(API): {len(gz_2024)}所 | 2025(PDF): {len(gz_2025)}所")
    r = run_backtest("贵州", gz_2024, gz_2025, 2024, 2025)
    if r:
        print(f"  匹配: {r['matched']}所 | 偏移: 均{r['mean']:+d} 中{r['median']:+d} σ{r['stdev']}")
        print(f"  前移{r['forward']} | 后移{r['backward']} | 大偏移{r['big_shift']}")
        for t, s in r["tiers"].items():
            print(f"    {t}: {s['avg']}% ({s['min']}-{s['max']}%, n={s['n']})")
        all_results.append(r)
    
    # === 北京 2023→2024 ===
    print("\n📂 北京")
    bj_2023 = load_api_format(os.path.join(MULTI_DIR, "北京_2023_admission.json"))
    bj_2024 = load_api_format(os.path.join(MULTI_DIR, "北京_2024_admission.json"))
    print(f"  2023: {len(bj_2023)}所 | 2024: {len(bj_2024)}所")
    r = run_backtest("北京", bj_2023, bj_2024, 2023, 2024)
    if r:
        print(f"  匹配: {r['matched']}所 | 偏移: 均{r['mean']:+d} 中{r['median']:+d} σ{r['stdev']}")
        for t, s in r["tiers"].items():
            print(f"    {t}: {s['avg']}% ({s['min']}-{s['max']}%, n={s['n']})")
        all_results.append(r)
    
    # === 广东 2023→2024 ===
    print("\n📂 广东")
    gd_2023 = load_api_format(os.path.join(MULTI_DIR, "广东_2023_admission.json"))
    gd_2024 = load_api_format(os.path.join(MULTI_DIR, "广东_2024_admission.json"))
    print(f"  2023: {len(gd_2023)}所 | 2024: {len(gd_2024)}所")
    r = run_backtest("广东", gd_2023, gd_2024, 2023, 2024)
    if r:
        print(f"  匹配: {r['matched']}所 | 偏移: 均{r['mean']:+d} 中{r['median']:+d} σ{r['stdev']}")
        for t, s in r["tiers"].items():
            print(f"    {t}: {s['avg']}% ({s['min']}-{s['max']}%, n={s['n']})")
        all_results.append(r)
    
    # === 广东 2022→2023（额外验证）===
    print("\n📂 广东（2022→2023）")
    gd_2022 = load_api_format(os.path.join(MULTI_DIR, "广东_2022_admission.json"))
    print(f"  2022: {len(gd_2022)}所 | 2023: {len(gd_2023)}所")
    r = run_backtest("广东2", gd_2022, gd_2023, 2022, 2023)
    if r:
        print(f"  匹配: {r['matched']}所 | 偏移: 均{r['mean']:+d} 中{r['median']:+d} σ{r['stdev']}")
        for t, s in r["tiers"].items():
            print(f"    {t}: {s['avg']}% ({s['min']}-{s['max']}%, n={s['n']})")
        all_results.append(r)
    
    # === 汇总 ===
    print(f"\n{'='*75}")
    print(f"📈 全国汇总 ({len(all_results)}组回测)")
    print(f"{'='*75}")
    
    total_matched = sum(r["matched"] for r in all_results)
    print(f"\n总匹配院校: {total_matched:,}")
    
    # 各档命中率汇总
    tier_names = ["冲(500-5000)", "稳上(-500~500)", "稳下(-10000~-500)", "保(-25000~-10000)", "垫(>-25000)"]
    print(f"\n{'组别':<16} {'匹配数':>6} {'冲':>7} {'稳上':>7} {'稳下':>7} {'保':>7} {'垫':>7}")
    print("─" * 75)
    for r in all_results:
        vals = []
        for t in tier_names:
            v = r["tiers"].get(t, {}).get("avg", "—")
            vals.append(f"{v:>6.1f}%" if isinstance(v, (int, float)) else f"{str(v):>7}")
        print(f"{r['province']+r['years']:<16} {r['matched']:>6} {' '.join(vals)}")
    
    # 加权平均
    print("─" * 75)
    print(f"{'加权平均':<16} {total_matched:>6}", end=" ")
    for t in tier_names:
        vals = []
        weights = []
        for r in all_results:
            v = r["tiers"].get(t, {}).get("avg")
            if v is not None:
                vals.append(v * r["matched"])
                weights.append(r["matched"])
        if vals:
            avg = sum(vals) / sum(weights)
            print(f"{avg:>6.1f}%", end=" ")
        else:
            print("    —  ", end=" ")
    print()
    
    # 保存
    output = os.path.join(DATA_DIR, "backtest_unified.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 保存: {output}")


if __name__ == "__main__":
    main()
