#!/usr/bin/env python3
"""全国回测引擎v6 - 使用严格解析后的v2数据 + API + PDF"""

import json
import os
import re
from collections import defaultdict
from statistics import mean, median

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
V2_FILE = os.path.join(DATA_DIR, "province_scores", "all_provinces_v2.json")
MULTI_DIR = os.path.join(DATA_DIR, "multi_province")
OUTPUT_DIR = os.path.join(DATA_DIR, "backtest_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_v2_data():
    """加载严格解析的v2数据（只有真实位次的）"""
    grouped = defaultdict(list)
    
    if not os.path.exists(V2_FILE):
        return grouped
    
    with open(V2_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)
    
    for r in records:
        if not r.get("has_rank") or not r.get("rank"):
            continue
        
        prov = r["province"]
        year = r["year"]
        source = r["source"]
        
        # 科类
        subject = "综合"
        if "理科" in source:
            subject = "理科"
        elif "文科" in source:
            subject = "文科"
        elif "物理" in source:
            subject = "物理"
        elif "历史" in source:
            subject = "历史"
        
        key = f"{prov}_{year}_{subject}"
        
        school = r["school"].strip()
        school_clean = re.sub(r'\([^)]*\)', '', school).strip()
        
        rank = r["rank"]
        score = r.get("score")
        
        grouped[key].append({
            "school": school_clean,
            "rank": rank,
            "score": score,
            "source": source,
        })
    
    return grouped


def load_api_data():
    """API数据（北京、广东等）"""
    grouped = defaultdict(list)
    
    for fname in os.listdir(MULTI_DIR):
        if not fname.endswith("_admission.json") or "type" in fname:
            continue
        
        parts = fname.replace("_admission.json", "").split("_")
        if len(parts) < 2 or not parts[1].isdigit():
            continue
        
        prov = parts[0]
        year = int(parts[1])
        
        with open(os.path.join(MULTI_DIR, fname), "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for item in data:
            school = (item.get("school_name") or item.get("name", "")).strip()
            if not school:
                continue
            school_clean = re.sub(r'\([^)]*\)', '', school).strip()
            
            rank = None
            score = None
            try:
                rank = int(item["min_section"]) if item.get("min_section") else None
            except:
                pass
            try:
                score = int(item["min_score"]) if item.get("min_score") else None
            except:
                pass
            
            if not rank or rank <= 0:
                continue
            
            subject = "综合"
            type_val = str(item.get("type", ""))
            if "物理" in type_val:
                subject = "物理"
            elif "历史" in type_val:
                subject = "历史"
            
            key = f"{prov}_{year}_{subject}"
            grouped[key].append({"school": school_clean, "rank": rank, "score": score})
    
    return grouped


def load_pdf_data():
    """贵州PDF数据"""
    grouped = defaultdict(list)
    
    pdf_file = os.path.join(DATA_DIR, "贵州_2025_物理类_本科批投档_complete.json")
    raw_file = os.path.join(DATA_DIR, "raw_2024.json")
    
    # 2025 PDF数据
    if os.path.exists(pdf_file):
        with open(pdf_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            school = item.get("school", "").strip()
            if not school:
                continue
            school_clean = re.sub(r'\([^)]*\)', '', school).strip()
            rank = item.get("min_rank")
            if rank and rank > 0:
                grouped[f"贵州_2025_物理"].append({"school": school_clean, "rank": rank, "score": item.get("min_score")})
    
    return grouped


def deduplicate(records):
    best = {}
    for r in records:
        s = r["school"]
        rank = r.get("rank")
        if rank and (s not in best or rank < best[s]["rank"]):
            best[s] = r
    return list(best.values())


def main():
    print("=" * 70)
    print("全国回测引擎 v6 (严格位次数据)")
    print("=" * 70)
    
    v2 = load_v2_data()
    api = load_api_data()
    pdf = load_pdf_data()
    
    all_data = defaultdict(list)
    for src in [v2, api, pdf]:
        for key, records in src.items():
            all_data[key].extend(records)
    
    for key in all_data:
        all_data[key] = deduplicate(all_data[key])
    
    # 只保留有真实位次的
    print("\n数据概况:")
    for key in sorted(all_data.keys()):
        print(f"  {key}: {len(all_data[key])}所")
    
    # 按省份+科类分组找连续年份对
    prov_subj_years = defaultdict(dict)
    for key, records in all_data.items():
        parts = key.split("_")
        if len(parts) >= 3:
            prov = parts[0]
            year = int(parts[1])
            subject = "_".join(parts[2:])
            prov_subj_years[f"{prov}_{subject}"][year] = records
    
    print("\n" + "=" * 70)
    print("回测结果（仅使用真实位次数据）")
    print("=" * 70)
    
    all_results = []
    
    for prov_subj, year_data in sorted(prov_subj_years.items()):
        years = sorted(year_data.keys())
        for i in range(len(years) - 1):
            y1, y2 = years[i], years[i + 1]
            y1_data = year_data[y1]
            y2_data = year_data[y2]
            
            # 匹配共有学校
            y1_map = {r["school"]: r["rank"] for r in y1_data if r.get("rank")}
            y2_map = {r["school"]: r["rank"] for r in y2_data if r.get("rank")}
            common_schools = set(y1_map.keys()) & set(y2_map.keys())
            
            if len(common_schools) < 10:
                continue
            
            matched = [{"school": s, "r1": y1_map[s], "r2": y2_map[s]} for s in common_schools]
            
            # 回测5个策略区间
            # 偏移 = student_rank - school_rank
            # 正数=学生位次比学校差（冲一冲）, 负数=学生位次比学校好（保底）
            strategies = {
                "冲刺(+500~+5000)":   (500, 5000),
                "稳妥(-500~+500)":     (-500, 500),
                "稳下(-10000~-500)":  (-10000, -500),
                "保底(-25000~-10000)": (-25000, -10000),
                "垫底(<-25000)":       (-100000, -25000),
            }
            
            strat_results = {}
            for sname, (lo, hi) in strategies.items():
                hits = 0
                total = 0
                for m in matched:
                    # 考生排位 = 该校year1排位 + 中值偏移
                    student_rank = m["r1"] + (lo + hi) // 2
                    # 该校year2实际录取排位
                    actual_rank = m["r2"]
                    # 排位数字越小=成绩越好，student_rank <= actual_rank = 能录取
                    if student_rank <= actual_rank:
                        hits += 1
                    total += 1
                strat_results[sname] = {"hits": hits, "total": total, "rate": round(hits / total * 100, 1)}
            
            # 位次偏移统计
            shifts = [m["r2"] - m["r1"] for m in matched]
            avg_shift = int(mean(shifts))
            med_shift = int(median(shifts))
            forward = sum(1 for s in shifts if s < 0)
            backward = sum(1 for s in shifts if s > 0)
            
            result = {
                "label": f"{prov_subj} {y1}→{y2}",
                "matched": len(matched),
                "avg_shift": avg_shift,
                "med_shift": med_shift,
                "forward": forward,
                "backward": backward,
                "strategies": strat_results,
            }
            all_results.append(result)
            
            print(f"\n{'—'*50}")
            print(f"{prov_subj} {y1}→{y2} ({len(matched)}所)")
            print(f"  平均偏移: {avg_shift:+,}名 | 中位: {med_shift:+,}名")
            print(f"  位次前移(竞争加剧): {forward}所 | 后移(竞争缓解): {backward}所")
            for sname, sr in strat_results.items():
                bar = "█" * int(sr["rate"] / 5)
                print(f"  {sname}: {sr['rate']:5.1f}% ({sr['hits']}/{sr['total']}) {bar}")
    
    # 汇总
    print(f"\n{'='*70}")
    print("全国汇总（仅位次数据）")
    print("=" * 70)
    
    if all_results:
        total_matched = sum(r["matched"] for r in all_results)
        print(f"回测组数: {len(all_results)}")
        print(f"共有院校: {total_matched:,}")
        
        for sname in strategies.keys():
            th = sum(r["strategies"][sname]["hits"] for r in all_results)
            tt = sum(r["strategies"][sname]["total"] for r in all_results)
            rate = round(th / tt * 100, 1)
            bar = "█" * int(rate / 5)
            print(f"  {sname}: {rate:5.1f}% ({th}/{tt}) {bar}")
        
        # 保存
        out = os.path.join(OUTPUT_DIR, "backtest_v6_national.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n保存: {out}")


if __name__ == "__main__":
    main()
