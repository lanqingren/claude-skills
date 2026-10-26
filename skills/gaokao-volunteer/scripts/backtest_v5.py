#!/usr/bin/env python3
"""全国多省份回测引擎v5 - 使用dxsbb HTML表格数据 + API数据 + PDF数据"""

import json
import os
import re
from collections import defaultdict
from statistics import mean, median

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
DXSBB_DIR = os.path.join(DATA_DIR, "province_scores")
MULTI_DIR = os.path.join(DATA_DIR, "multi_province")
OUTPUT_DIR = os.path.join(DATA_DIR, "backtest_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_dxsbb_data():
    """加载从dxsbb.com提取的HTML表格数据"""
    records = []
    
    # 加载all_provinces_scores.json
    all_file = os.path.join(DXSBB_DIR, "all_provinces_scores.json")
    if os.path.exists(all_file):
        with open(all_file, "r", encoding="utf-8") as f:
            records = json.load(f)
    
    # 按省份+年份+科类分组
    grouped = defaultdict(list)  # key -> [records]
    
    for r in records:
        prov = r.get("province", "")
        year = r.get("year", 0)
        source = r.get("source", "")
        
        # 提取科类
        subject = "unknown"
        if "物理" in source:
            subject = "物理"
        elif "历史" in source:
            subject = "历史"
        elif "理科" in source:
            subject = "理科"
        elif "文科" in source:
            subject = "文科"
        elif "综合" in source or prov in ["山东", "浙江", "海南", "上海"]:
            subject = "综合"
        
        key = f"{prov}_{year}_{subject}"
        
        school = r.get("school", "").strip()
        if not school:
            continue
        
        # 清理学校名 - 去除括号内容（校区等）
        school_clean = re.sub(r'\([^)]*\)', '', school).strip()
        
        rank = r.get("rank")
        score = r.get("score")
        
        if rank and isinstance(rank, int) and rank > 0:
            grouped[key].append({
                "school": school_clean,
                "rank": rank,
                "score": score,
                "source": source,
            })
        elif score and isinstance(score, int) and score > 0:
            grouped[key].append({
                "school": school_clean,
                "rank": None,
                "score": score,
                "source": source,
            })
    
    return grouped


def load_api_data():
    """加载从API获取的数据"""
    grouped = defaultdict(list)
    
    if not os.path.exists(MULTI_DIR):
        return grouped
    
    for fname in os.listdir(MULTI_DIR):
        if not fname.endswith("_admission.json") or "type" in fname:
            continue
        
        parts = fname.replace("_admission.json", "").split("_")
        if len(parts) < 2:
            continue
        
        prov = parts[0]
        year = int(parts[1]) if parts[1].isdigit() else 0
        
        filepath = os.path.join(MULTI_DIR, fname)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            continue
        
        for item in data:
            school = item.get("school_name") or item.get("name", "")
            school = school.strip()
            if not school:
                continue
            
            school_clean = re.sub(r'\([^)]*\)', '', school).strip()
            
            rank_str = item.get("min_section", "")
            score_str = item.get("min_score", "")
            
            rank = None
            score = None
            try:
                rank = int(rank_str) if rank_str else None
            except:
                pass
            try:
                score = int(score_str) if score_str else None
            except:
                pass
            
            # 确定科类
            subject = "综合"
            type_val = item.get("type", "")
            if "物理" in str(type_val):
                subject = "物理"
            elif "历史" in str(type_val):
                subject = "历史"
            
            key = f"{prov}_{year}_{subject}"
            
            if rank and rank > 0:
                grouped[key].append({
                    "school": school_clean,
                    "rank": rank,
                    "score": score,
                    "source": "api",
                })
    
    return grouped


def load_pdf_data():
    """加载从PDF提取的贵州数据"""
    grouped = defaultdict(list)
    
    pdf_file = os.path.join(DATA_DIR, "贵州_2025_物理类_本科批投档_complete.json")
    if os.path.exists(pdf_file):
        with open(pdf_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for item in data:
            school = item.get("school", "").strip()
            if not school:
                continue
            
            school_clean = re.sub(r'\([^)]*\)', '', school).strip()
            rank = item.get("min_rank")
            score = item.get("min_score")
            
            key = "贵州_2025_物理"
            grouped[key].append({
                "school": school_clean,
                "rank": rank,
                "score": score,
                "source": "pdf",
            })
    
    return grouped


def deduplicate_schools(records):
    """对同一学校取最低排位（最好成绩）"""
    school_best = {}
    for r in records:
        school = r["school"]
        rank = r.get("rank")
        if not rank:
            continue
        if school not in school_best or rank < school_best[school]["rank"]:
            school_best[school] = r
    return list(school_best.values())


def match_schools(year1_data, year2_data):
    """匹配两年都有的学校"""
    y1_map = {r["school"]: r["rank"] for r in year1_data if r.get("rank")}
    y2_map = {r["school"]: r["rank"] for r in year2_data if r.get("rank")}
    
    common = []
    for school in set(y1_map.keys()) & set(y2_map.keys()):
        common.append({
            "school": school,
            "rank_y1": y1_map[school],
            "rank_y2": y2_map[school],
        })
    
    return common


def backtest_strategy(common_schools, label=""):
    """回测策略命中率"""
    if not common_schools:
        return None
    
    results = {
        "label": label,
        "total_schools": len(common_schools),
        "strategies": {},
    }
    
    # 策略定义（位次偏移范围）
    strategies = {
        "冲高(-5000~-500)": (-5000, -500),
        "稳妥(-500~+500)": (-500, 500),
        "稳下(-10000~-500)": (-10000, -500),
        "保底(-25000~-10000)": (-25000, -10000),
        "垫底(<-25000)": (-999999, -25000),
    }
    
    for strat_name, (low, high) in strategies.items():
        hits = 0
        total = 0
        
        for c in common_schools:
            rank1 = c["rank_y1"]
            rank2 = c["rank_y2"]
            
            # 模拟: 用year1的排位作为推荐区间
            # 如果rank1在[rank1+low, rank1+high]区间，则考生排位=rank1
            # 实际录取需要 考生排位 <= rank2 (year2的投档排位)
            # 即 rank1 <= rank2
            
            test_rank = rank1  # 考生排位 = year1排位+偏移
            # 对每个策略，模拟考生排位在区间内的中值
            mid_offset = (low + high) / 2
            student_rank = int(rank1 + mid_offset)
            
            # 这所学校在year2的录取排位是rank2
            # 如果student_rank <= rank2，则被录取
            if student_rank <= rank2:
                hits += 1
            total += 1
        
        if total > 0:
            results["strategies"][strat_name] = {
                "total": total,
                "hits": hits,
                "rate": round(hits / total * 100, 1),
            }
    
    # 计算位次偏移统计
    shifts = [c["rank_y2"] - c["rank_y1"] for c in common_schools]
    results["avg_shift"] = int(mean(shifts)) if shifts else 0
    results["median_shift"] = int(median(shifts)) if shifts else 0
    results["forward_count"] = sum(1 for s in shifts if s < 0)  # 位次前移(数字变小)
    results["backward_count"] = sum(1 for s in shifts if s > 0)  # 位次后移
    
    return results


def main():
    print("=" * 70)
    print("全国高考志愿回测引擎 v5 (HTML表格+API+PDF)")
    print("=" * 70)
    
    # 加载所有数据
    print("\n加载数据...")
    dxsbb_data = load_dxsbb_data()
    api_data = load_api_data()
    pdf_data = load_pdf_data()
    
    # 合并所有数据
    all_data = defaultdict(list)
    
    for source in [dxsbb_data, api_data, pdf_data]:
        for key, records in source.items():
            all_data[key].extend(records)
    
    # 去重
    for key in all_data:
        all_data[key] = deduplicate_schools(all_data[key])
    
    print(f"\n数据源统计:")
    print(f"  dxsbb HTML表格: {sum(len(v) for v in dxsbb_data.values())}条")
    print(f"  API数据: {sum(len(v) for v in api_data.values())}条")
    print(f"  PDF数据: {sum(len(v) for v in pdf_data.values())}条")
    print(f"  合计(去重后): {sum(len(v) for v in all_data.values())}条")
    
    # 显示各省份-年份-科类的数据量
    print(f"\n{'Key':<30} {'学校数':>8}")
    print("-" * 40)
    for key in sorted(all_data.keys()):
        print(f"  {key:<28} {len(all_data[key]):>8}")
    
    # 找到可以回测的省份-科类对（有连续两年数据）
    print("\n" + "=" * 70)
    print("回测结果")
    print("=" * 70)
    
    # 按省份和科类分组
    prov_subject_years = defaultdict(lambda: defaultdict(dict))
    for key, records in all_data.items():
        parts = key.split("_")
        if len(parts) >= 3:
            prov = parts[0]
            year = int(parts[1])
            subject = "_".join(parts[2:])
            prov_subject_years[f"{prov}_{subject}"][year] = records
    
    all_results = []
    
    for prov_subj, year_data in sorted(prov_subject_years.items()):
        years = sorted(year_data.keys())
        
        # 对每对连续年份做回测
        for i in range(len(years) - 1):
            y1, y2 = years[i], years[i + 1]
            y1_data = year_data[y1]
            y2_data = year_data[y2]
            
            common = match_schools(y1_data, y2_data)
            
            if len(common) < 10:  # 太少不回测
                continue
            
            label = f"{prov_subj} {y1}→{y2}"
            result = backtest_strategy(common, label)
            
            if result:
                all_results.append(result)
                print(f"\n{label} ({len(common)}所共有院校)")
                print(f"  平均偏移: {result['avg_shift']:,}名, 中位: {result['median_shift']:,}名")
                print(f"  位次前移: {result['forward_count']}所, 后移: {result['backward_count']}所")
                for strat, data in result["strategies"].items():
                    print(f"  {strat}: {data['rate']}% ({data['hits']}/{data['total']})")
    
    # 汇总统计
    print("\n" + "=" * 70)
    print("全国汇总")
    print("=" * 70)
    
    if all_results:
        total_schools = sum(r["total_schools"] for r in all_results)
        print(f"回测组数: {len(all_results)}")
        print(f"总共有院校: {total_schools:,}")
        
        # 按策略汇总
        strategies = all_results[0]["strategies"].keys()
        for strat in strategies:
            total_hits = sum(r["strategies"].get(strat, {}).get("hits", 0) for r in all_results)
            total_tests = sum(r["strategies"].get(strat, {}).get("total", 0) for r in all_results)
            if total_tests > 0:
                rate = round(total_hits / total_tests * 100, 1)
                print(f"  {strat}: {rate}% ({total_hits}/{total_tests})")
        
        # 保存结果
        output_file = os.path.join(OUTPUT_DIR, "backtest_national_v5.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存: {output_file}")


if __name__ == "__main__":
    main()
