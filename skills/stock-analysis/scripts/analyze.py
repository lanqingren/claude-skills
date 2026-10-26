"""
analyze.py - 通用个股分析脚本
用法: 
  python analyze.py <代码> [成本]        单只分析
  python analyze.py <代码1> <代码2> ...  多只对比
"""
import sys
import io
# Force UTF-8 console output on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_fast as rf

# 三大指数缓存
MARKET_INDICES = {}

def fetch_indices_if_needed():
    """懒加载获取三大指数，用于板块对比"""
    global MARKET_INDICES
    if not MARKET_INDICES:
        MARKET_INDICES = rf.fetch_market_indices()
    return MARKET_INDICES

def analyze(code, cost=0):
    # 自动补市场前缀
    if code.startswith('6'):
        symbol = f"sh{code}"
    elif code.startswith(('0','3')):
        symbol = f"sz{code}"
    else:
        symbol = code
    
    rt = rf.fetch_realtime_prices([code])
    if code not in rt:
        print(f"❌ {code}: 实时行情获取失败")
        return None
        
    hist = rf.fetch_history(symbol)
    if hist is None:
        print(f"❌ {code}: 历史数据不足")
        return None
        
    res = rf.process_one(code, rf.fetch_history.__dict__.get('name',''), symbol, rt[code])
    # process_one 需要 name，但我们没有，手动构建
    return res, rt[code]

def analyze_with_name(code, name, cost=0):
    if code.startswith('6'):
        symbol = f"sh{code}"
    else:
        symbol = f"sz{code}"
    
    rt = rf.fetch_realtime_prices([code])
    if code not in rt:
        print(f"❌ {name}({code}): 行情获取失败")
        return None
        
    hist = rf.fetch_history(symbol)
    if hist is None:
        print(f"❌ {name}({code}): 历史数据不足")
        return None
        
    res = rf.process_one(code, name, symbol, rt[code])
    return res, rt[code]

def show_stock(res, rt, cost=0, index=0):
    name = res['name']
    code = res['code']
    
    if index == 0 and len(sys.argv) > 2:
        print(f"\n{'='*60}")
        print(f"  多股对比")
        print(f"{'='*60}")
    
    pnl = 0
    pnl_pct = 0
    if cost > 0:
        pnl = res['price'] - cost
        pnl_pct = pnl / cost * 100
    
    if cost > 0:
        print(f"\n{'─'*60}")
        print(f"  【{name}({code})】成本: {cost:.2f}")
    else:
        print(f"\n{'─'*60}")
        print(f"  【{name}({code})】")
    
    print(f"  现价: {res['price']:.2f} | 今日: {res['today_change']:+.2f}% | 量比: {res['vol_ratio']:.1f}x")
    if cost > 0:
        print(f"  浮盈: {pnl:+.3f} ({pnl_pct:+.2f}%)")
    print(f"  总分: {res['score']:.1f} (技术:{res['tech_score']:.1f} 消息:{res['msg_score']:.1f})")
    print(f"  结论: {res['conclusion']}")
    print(f"  BIAS: {res['bias6']:.1f}% | OBV: {res['obv_trend']}")
    print(f"  20H: {res['high_20']:.2f} | 20L: {res['low_20']:.2f}")
    
    # 信号
    sigs = res['signals'].split('; ')
    pos = [s for s in sigs if any(k in s for k in ['排列','放大','健康','流入','上涨','超卖','黄金','偏强','金叉'])]
    neg = [s for s in sigs if any(k in s for k in ['超买','死叉','流出','跌破','过大','下跌','绿柱'])]
    if pos: print(f"  利好: {'; '.join(pos[:3])}")
    if neg: print(f"  利空: {'; '.join(neg[:3])}")
    
    # 建议（动态止损）
    sl = rf.compute_dynamic_stop_loss(res['price'], res.get('boll_lower', 0), res.get('low_20', 0))
    trend = "多头" if res['ma5'] > res['ma20'] else "空头"
    print(f"  目标: {res['high_20']:.2f} | 止损: {sl:.2f} | 趋势: {trend}")
    
    # 板块对比
    indices = fetch_indices_if_needed()
    code_clean = code.lstrip('sz').lstrip('sh').zfill(6)
    if code_clean.startswith('6'):
        bench = indices.get('上证指数', indices.get('000001', {}))
    elif code_clean.startswith('3'):
        bench = indices.get('创业板指', indices.get('399006', {}))
    else:
        bench = indices.get('深证成指', indices.get('399001', {}))
    if bench.get('change') is not None:
        bench_name = bench.get('name', '基准指数')
        bench_chg = bench['change']
        relative = res['today_change'] - bench_chg
        direction = '强于' if relative > 0 else '弱于'
        print(f"  板块对比: 相对{bench_name}{direction}{abs(relative):.2f}% (个股{res['today_change']:+.2f}% vs {bench_name}{bench_chg:+.2f}%)")
    
    if res['news_summaries'] and str(res['news_summaries']).strip():
        print(f"  新闻: {str(res['news_summaries'])[:100]}")
    
    return res['score']

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python analyze.py <代码> [成本] 或 <代码1> <代码2> ...")
        sys.exit(1)
    
    # 股票名称映射（常见股）
    name_map = {
        '300706': '阿石创', '000633': '合金投资', '300456': '赛微电子',
        '002428': '云南锗业', '600519': '贵州茅台', '000001': '平安银行',
        '601318': '中国平安', '600036': '招商银行', '000831': '中国稀土',
        '000537': '泰发集团', '000533': '顺发恒业', '301155': '中矿资源',
        '601218': '华控科技', '002667': '华仁药业', '002796': '华控科技',
        '601615': '华通线缆', '300129': '泰胜科技', '002173': '华仁医药',
        '600397': '华通装备', '601138': '工业富联', '600711': '盛屯矿业',
        '002182': '宝钢包装', '000021': '深科技', '605196': '华通线缆',
        '603031': '诺德股份', '000880': '潍柴重机', '300831': '华仁药业',
        '002413': '华控赛格',
    }
    
    # 支持两种模式:
    # 1. analyze.py code1 [cost1] code2 [cost2] ...
    # 2. analyze.py code1 code2 code3 ... (无成本)
    
    stocks = []
    i = 1
    while i < len(sys.argv):
        code = sys.argv[i]
        cost = 0
        # 检查下一个参数是否是数字（成本）
        if i + 1 < len(sys.argv):
            try:
                cost = float(sys.argv[i+1])
                i += 2
            except ValueError:
                i += 1
        else:
            i += 1
        
        name = name_map.get(code.lstrip('sz').lstrip('sh'), code)
        stocks.append((code, name, cost))
    
    if not stocks:
        print("未提供股票代码")
        sys.exit(1)
    
    for idx, (code, name, cost) in enumerate(stocks):
        code_clean = code.lstrip('sz').lstrip('sh').zfill(6)
        if code_clean.startswith('6'):
            symbol = f"sh{code_clean}"
        else:
            symbol = f"sz{code_clean}"
        
        rt = rf.fetch_realtime_prices([code_clean])
        if code_clean not in rt:
            print(f"❌ {name}({code_clean}): 行情获取失败")
            continue
            
        hist = rf.fetch_history(symbol)
        if hist is None:
            print(f"❌ {name}({code_clean}): 历史数据不足")
            continue
            
        res = rf.process_one(code_clean, name, symbol, rt[code_clean])
        if res:
            show_stock(res, rt[code_clean], cost, idx)
    
    print(f"\n{'='*60}")
    print(f"  以上分析仅供参考，不构成投资建议")
    print(f"{'='*60}")
