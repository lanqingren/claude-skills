#!/usr/bin/env python3
"""
高考志愿数据每日采集 + 回测 + 报告
作为 hermes cron --script 运行
输出：采集报告文本（由hermes deliver到origin）
"""
import subprocess, sys, os, json

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"

def run_cmd(cmd, timeout=300):
    """运行命令，返回stdout"""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=SKILL_DIR,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"}
        )
        return r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT after {timeout}s]"
    except Exception as e:
        return f"[ERROR: {e}]"

def main():
    report_lines = []
    report_lines.append("🎓 高考志愿数据每日采集报告")
    report_lines.append(f"时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 60)
    
    # 1. 运行数据采集
    report_lines.append("\n📦 步骤1: 数据采集")
    collect_script = os.path.join(SKILL_DIR, "scripts", "daily_collect.py")
    collect_output = run_cmd(f'cmd.exe /c "python {collect_script} --source all"', timeout=300)
    report_lines.append(collect_output[-2000:])  # 只取最后2000字符
    
    # 2. 解析采集报告
    report_lines.append("\n📊 步骤2: 采集结果")
    
    # 查找最新的collect_report
    reports_dir = os.path.join(DATA_DIR, "collect_reports")
    if os.path.exists(reports_dir):
        reports = sorted([f for f in os.listdir(reports_dir) if f.endswith('.json')])
        if reports:
            latest_report_path = os.path.join(reports_dir, reports[-1])
            with open(latest_report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            report_lines.append(f"总数据量: {report_data.get('total_records', 0)} 条")
            report_lines.append(f"新增数据: {report_data.get('new_records', 0)} 条")
            
            source_stats = report_data.get('source_stats', {})
            for src, cnt in source_stats.items():
                report_lines.append(f"  数据源 {src}: +{cnt} 条")
            
            # 回测结果
            bt = report_data.get('backtest', {})
            nat = bt.get('national', {})
            if nat:
                report_lines.append(f"\n回测结果: {nat.get('pairs', 0)}对")
                report_lines.append(f"  冲: {nat.get('C', 0)}%")
                report_lines.append(f"  稳: {nat.get('W', 0)}%")
                report_lines.append(f"  保: {nat.get('B', 0)}%")
            
            # 各省回测
            provinces_bt = bt.get('provinces', {})
            if provinces_bt:
                report_lines.append(f"\n各省回测 ({len(provinces_bt)}个省份):")
                for prov in sorted(provinces_bt.keys()):
                    cats = provinces_bt[prov]
                    for cat in sorted(cats.keys()):
                        r = cats[cat]
                        report_lines.append(f"  {prov} {cat}: {r['pairs']}对 C={r['C']}% W={r['W']}% B={r['B']}%")
    
    # 3. 数据覆盖情况
    report_lines.append("\n🗺️ 步骤3: 数据覆盖情况")
    gap_file = os.path.join(DATA_DIR, "data_gap_analysis.json")
    if os.path.exists(gap_file):
        with open(gap_file, 'r', encoding='utf-8') as f:
            gap = json.load(f)
        
        year_cov = gap.get('year_coverage', {})
        report_lines.append(f"2023年: {year_cov.get('2023', 0)}所院校")
        report_lines.append(f"2024年: {year_cov.get('2024', 0)}所院校")
        report_lines.append(f"2025年: {year_cov.get('2025', 0)}所院校")
        
        gap_provs = gap.get('gap_provinces', [])
        if gap_provs:
            report_lines.append(f"\n缺失数据的省份 ({len(gap_provs)}个):")
            for gp in gap_provs:
                prov = gp['province']
                missing = gp['missing_years']
                report_lines.append(f"  {prov}: 缺{missing}")
        else:
            report_lines.append("\n✅ 所有省份数据完整！")
    
    # 4. 建议
    report_lines.append("\n💡 采集建议")
    if os.path.exists(gap_file):
        with open(gap_file, 'r', encoding='utf-8') as f:
            gap = json.load(f)
        gap_provs = gap.get('gap_provinces', [])
        if gap_provs:
            prov_names = [gp['province'] for gp in gap_provs[:5]]
            report_lines.append(f"  优先补充: {', '.join(prov_names)}")
            report_lines.append(f"  建议从各省考试院官网获取剩余省份的2025年数据")
    
    report_lines.append("\n" + "=" * 60)
    report_lines.append("✅ 采集完成")
    
    output = "\n".join(report_lines)
    print(output)
    
    # 同时保存到文件
    summary_file = os.path.join(DATA_DIR, "collect_reports", f"summary_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    os.makedirs(os.path.dirname(summary_file), exist_ok=True)
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(output)

if __name__ == '__main__':
    main()
