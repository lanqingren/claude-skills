"""
intraday_analysis.py - 盘中分时分析
====================================

用法:
    python intraday_analysis.py <股票代码> <持仓成本(可选)>

示例:
    python intraday_analysis.py 002428 50.935
    python intraday_analysis.py 300456

数据源: 东方财富分钟K线 API
"""

import sys
import json
import numpy as np
import requests

def fetch_minute_data(code, period=5):
    """获取东方财富分钟K线"""
    market = "1" if code.startswith('6') else "0"
    url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": f"{market}.{code}",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": period,  # 1=1min, 5=5min, 15=15min, 30=30min, 60=60min
        "fqt": 1,
        "end": "20500101",
        "lmt": 100,
    }
    r = requests.get(url, params=params, timeout=10)
    data = r.json()
    if not data.get('data'):
        return None
    return data['data']


def main():
    if len(sys.argv) < 2:
        print("用法: python intraday_analysis.py <股票代码> [持仓成本]")
        sys.exit(1)

    code = sys.argv[1]
    cost = float(sys.argv[2]) if len(sys.argv) > 2 else None

    data = fetch_minute_data(code, period=5)
    if not data:
        print(f"无法获取 {code} 的分钟数据")
        sys.exit(1)

    name = data.get('name', code)
    pre_close = data.get('preKPrice', 0)
    klines = data.get('klines', [])

    if not klines:
        print("没有分时数据")
        sys.exit(1)

    # Parse: 时间,开盘,收盘,最高,最低,成交量(手),成交额,涨跌幅,涨跌额,振幅,换手率
    records = []
    for line in klines:
        parts = line.split(',')
        records.append({
            'time': parts[0],
            'open': float(parts[1]),
            'close': float(parts[2]),
            'high': float(parts[3]),
            'low': float(parts[4]),
            'volume': int(parts[5]),
            'amount': float(parts[6]),
            'change_pct': float(parts[7]),
            'change_amt': float(parts[8]),
            'amplitude': float(parts[9]),
            'turnover': float(parts[10]),
        })

    print("="*70)
    print(f"  {name} ({code}) 盘中分时分析")
    print(f"  数据截止: {records[-1]['time']}")
    print(f"  昨收: {pre_close}")
    print("="*70)

    current = records[-1]['close']
    high = max(r['high'] for r in records)
    low = min(r['low'] for r in records)
    total_vol = sum(r['volume'] for r in records)
    total_amt = sum(r['amount'] for r in records)

    print(f"\n当前价: {current}")
    print(f"今日最高: {high}")
    print(f"今日最低: {low}")
    print(f"今开: {records[0]['open']}")
    print(f"涨幅: {(current - pre_close)/pre_close*100:.2f}%")
    print(f"振幅: {(high - low)/pre_close*100:.2f}%")
    print(f"总成交量: {total_vol} 手")
    print(f"总成交额: {total_amt/1e8:.2f} 亿")
    print(f"总换手率: {records[-1]['turnover']:.2f}%")

    if cost is not None:
        pnl = current - cost
        pnl_pct = pnl / cost * 100
        print(f"\n你的成本: {cost}")
        print(f"当前盈亏: {pnl:+.3f} ({pnl_pct:+.2f}%)")

    # 关键时间点
    print("\n" + "="*60)
    print("  关键时间点价格走势")
    print("="*60)
    for kt in ['09:30','09:35','09:45','10:00','10:30','11:00','11:30','13:00','13:30','14:00','14:30','15:00']:
        for r in records:
            if kt in r['time']:
                print(f"  {r['time']}: {r['close']:.2f} (O:{r['open']:.2f} H:{r['high']:.2f} L:{r['low']:.2f}) V:{r['volume']}手")
                break

    # 每10分钟平均成交量
    print("\n" + "="*60)
    print("  每10分钟平均成交量")
    print("="*60)
    for i in range(0, len(records), 10):
        chunk = records[i:i+10]
        avg_vol = np.mean([r['volume'] for r in chunk])
        avg_price = np.mean([r['close'] for r in chunk])
        t_start = chunk[0]['time'][-8:]
        t_end = chunk[-1]['time'][-8:]
        print(f"  {t_start} - {t_end}: 均量={avg_vol:.0f}手, 均价={avg_price:.2f}")

    print(f"\n* 以上分析仅供参考，不构成投资建议")


if __name__ == '__main__':
    main()
