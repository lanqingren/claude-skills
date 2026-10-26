"""
run_fast.py - 多线程快速选股 (V4.0 分级关键词 + 并行)
=====================================================
用法: python run_fast.py <excel路径>
输出: TOP 10 套利空间推荐（含入选理由/风险/信号/交易计划/新闻）
"""
import sys
import io
# Force UTF-8 console output on Windows to prevent garbled names
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import akshare as ak
import pandas as pd
import numpy as np
import requests
import time
import os
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

TOP_N = 10
DATA_WINDOW = 60
MAX_WORKERS = 10

def fetch_market_indices():
    """获取三大指数实时行情，用于板块对比和相对强弱计算"""
    indices = {}
    try:
        r = requests.get(
            'https://qt.gtimg.cn/q=sh000001,sz399001,sz399006',
            headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.qq.com'},
            timeout=10
        )
        data = r.content.decode('gbk', errors='replace')
        for line in data.strip().split('\n'):
            line = line.strip()
            if not line or '~' not in line: continue
            parts = line.split('~')
            if len(parts) < 35: continue
            code = parts[2]
            idx_name = parts[1] if len(parts) > 1 else code
            indices[code] = {
                'name': idx_name,
                'price': float(parts[3]) if parts[3] else 0,
                'prev': float(parts[4]) if parts[4] else 0,
                'change': (float(parts[3]) - float(parts[4])) / float(parts[4]) * 100
                if parts[3] and parts[4] and float(parts[4]) != 0 else 0,
            }
    except:
        pass
    return indices


def fetch_stock_industry(code):
    """获取股票所属行业/板块信息"""
    try:
        clean_code = code.lstrip('sh').lstrip('sz').zfill(6)
        info = ak.stock_individual_info_em(symbol=clean_code)
        if info is not None and not info.empty:
            for _, row in info.iterrows():
                if '行业' in str(row.iloc[0]):
                    return str(row.iloc[1]).strip()
    except:
        pass
    return '未知'


def compute_dynamic_stop_loss(price, boll_lower, low_20):
    """动态止损 - 适合短线套利的波动率自适应止损
    
    短线套利核心原则：止损位必须设在真实技术支撑上
    - 波动大 → 止损宽（避免被正常波动洗出）
    - 波动小 → 止损窄（保护利润）
    
    止损位 = max(BOLL下轨, 20日低点) —— 取较高的支撑位
    硬性下限：距现价不低于 2%（防止止损过紧被频繁触发）
    去掉 8% 硬上限！如果技术支撑低于 8%，止损就设在那里
    同时返回 is_deep 标记，让套利评分处理深止损情况
    """
    if boll_lower > 0 and low_20 > 0:
        stop = max(boll_lower, low_20)
    elif boll_lower > 0:
        stop = boll_lower
    elif low_20 > 0:
        stop = low_20
    else:
        # 兜底：3.5% 固定止损
        return round(price * 0.965, 2), False
    
    # 2% 下限：防止止损过紧
    min_stop = price * 0.98
    stop = min(stop, min_stop)
    
    # 标记止损是否过深（>6%）
    is_deep = (price - stop) / price > 0.06
    
    return round(stop, 2), is_deep


KEYWORDS_POSITIVE = [
    ('IPO', 3.0), ('上市', 3.0), ('借壳', 3.0), ('重组', 3.0),
    ('并购', 3.0), ('收购', 3.0), ('分拆上市', 3.0),
    ('中标', 1.0), ('签订', 1.0), ('预增', 1.0), ('扭亏', 1.0),
    ('回购', 1.0), ('增持', 1.0), ('突破', 1.0), ('利好', 1.0),
    ('获批', 1.0), ('涨价', 1.0), ('上调', 1.0), ('分红', 1.0),
    ('派现', 1.0), ('派息', 1.0), ('送转', 1.0), ('战略合作', 1.0),
    ('独家', 1.0), ('创新高', 1.0), ('大单', 1.0), ('首单', 1.0),
    ('净利润', 1.0), ('增长', 1.0), ('取得', 1.0), ('投产', 1.0),
    ('扩产', 1.0), ('新产线', 1.0), ('订单', 1.0), ('放量', 1.0),
    ('业绩预告', 1.0), ('营收增', 1.0), ('利润增', 1.0), ('涨停', 1.0),
    ('行业龙头', 1.0), ('深化合作', 1.0), ('发布', 1.0), ('重仓', 1.0),
    ('业绩暴增', 1.0), ('大幅拉升', 1.0),
    ('优化', 0.5), ('升级', 0.5), ('拓展', 0.5), ('布局', 0.5),
    ('推进', 0.5), ('签约', 0.5), ('合资', 0.5), ('成立', 0.5),
    ('研发', 0.5), ('落地', 0.5),
]
KEYWORDS_NEGATIVE = [
    ('立案', 3.0), ('退市', 3.0), ('暴雷', 3.0), ('违约', 3.0),
    ('造假', 3.0), ('欺诈', 3.0), ('实控人被抓', 3.0),
    ('调查', 1.0), ('处罚', 1.0), ('减持', 1.0), ('预减', 1.0),
    ('亏损', 1.0), ('诉讼', 1.0), ('仲裁', 1.0), ('终止', 1.0),
    ('警示', 1.0), ('风险', 1.0), ('下跌', 1.0), ('监管', 1.0),
    ('问询', 1.0), ('不及预期', 1.0), ('下滑', 1.0), ('下降', 1.0),
    ('降薪', 1.0), ('质押', 1.0), ('资金流出', 1.0), ('净流出', 1.0),
    ('业绩下滑', 1.0), ('利润下降', 1.0), ('营收下降', 1.0),
    ('被举报', 1.0), ('召回', 1.0), ('停产', 1.0), ('裁员', 1.0),
    ('商誉减值', 1.0), ('资产减值', 1.0), ('坏账', 1.0),
    ('波动', 0.5), ('承压', 0.5), ('放缓', 0.5), ('警惕', 0.5),
    ('回调', 0.5), ('分歧', 0.5), ('争议', 0.5),
]

lock = threading.Lock()
done_count = 0
total_count = 0

def analyze_news_sentiment(symbol):
    score = 0
    summaries = []
    try:
        clean_code = symbol[2:] if len(symbol) > 2 and symbol[:2] in ('sh', 'sz') else symbol
        df = ak.stock_news_em(symbol=clean_code)
        if df is None or df.empty:
            return 0, []
        df = df.head(5)
        today = datetime.now().date()
        for _, row in df.iterrows():
            title = str(row.iloc[1])
            content = str(row.iloc[2])
            pub_time_str = str(row.iloc[3])
            try:
                pub_date = datetime.strptime(pub_time_str[:10], '%Y-%m-%d').date()
                days_diff = (today - pub_date).days
            except:
                days_diff = 1
            if days_diff == 0: decay = 1.0
            elif days_diff == 1: decay = 0.5
            elif days_diff == 2: decay = 0.2
            elif days_diff <= 5: decay = 0.1
            else: decay = 0.0
            text = title + " " + content[:500]
            pos_score = 0.0; pos_hits = []
            for kw, weight in KEYWORDS_POSITIVE:
                if kw in text:
                    pos_score += weight; pos_hits.append(kw)
            neg_score = 0.0; neg_hits = []
            for kw, weight in KEYWORDS_NEGATIVE:
                if kw in text:
                    neg_score += weight; neg_hits.append(kw)
            raw = (pos_score - neg_score * 1.5)
            item_score = raw * decay * 5
            score += item_score
            if pos_hits or neg_hits:
                tags = []
                if pos_hits: tags.append(f"+{','.join(pos_hits[:3])}")
                if neg_hits: tags.append(f"-{','.join(neg_hits[:3])}")
                if pos_score > 0 and neg_score == 0: status = "[BULL]"
                elif neg_score > 0 and pos_score == 0: status = "[BEAR]"
                elif pos_score > neg_score: status = "[BULL]"
                elif neg_score > pos_score: status = "[BEAR]"
                else: status = "[NEUTRAL]"
                summaries.append(f"{status}{' '.join(tags)} ({days_diff}d): {title[:40]}")
    except:
        pass
    score = max(-15, min(15, score))
    return score, summaries

def fetch_realtime_prices(codes):
    results = {}
    for i in range(0, len(codes), 20):
        batch = codes[i:i+20]
        query = ','.join([f"sh{c}" if c.startswith('6') else f"sz{c}" for c in batch])
        try:
            r = requests.get(f"https://qt.gtimg.cn/q={query}", headers={'Referer': 'https://finance.qq.com', 'User-Agent': 'Mozilla/5.0'}, timeout=10)
            data = r.content.decode('gbk', errors='replace')
            for line in data.strip().split('\n'):
                line = line.strip()
                if not line: continue
                parts = line.split('~')
                if len(parts) < 35: continue
                code = parts[2]
                results[code] = {
                    'price': float(parts[3]), 'prev': float(parts[4]), 'open': float(parts[5]),
                    'high': float(parts[33]), 'low': float(parts[34]),
                    'vol_ratio': float(parts[38]) if parts[38] else 0,
                    'change': (float(parts[3]) - float(parts[4])) / float(parts[4]) * 100,
                }
            time.sleep(0.3)
        except:
            pass
    return results

def fetch_history(symbol):
    try:
        df = ak.stock_zh_a_daily(symbol=symbol)
        if df is None or len(df) < 30: return None
        df['date'] = pd.to_datetime(df['date'])
        return df.sort_values('date').tail(DATA_WINDOW)
    except:
        return None

def compute_indicators(df, realtime_price=None):
    close = df['close'].values.astype(float)
    high = df['high'].values.astype(float)
    low = df['low'].values.astype(float)
    volume = df['volume'].values.astype(float)
    result = {}
    mas = {}
    for p in [5, 10, 20, 60]:
        if len(close) >= p: mas[p] = np.mean(close[-p:])
    result['ma'] = mas
    last_close = close[-1]
    if all(k in mas for k in [5, 10, 20]):
        if last_close > mas[5] > mas[10] > mas[20]: result['trend'] = 'bullish_aligned'
        elif last_close > mas[5] > mas[10]: result['trend'] = 'bullish'
        elif last_close > mas[5]: result['trend'] = 'above_ma5'
        elif last_close < mas[20]: result['trend'] = 'bearish'
        else: result['trend'] = 'sideways'
    else: result['trend'] = 'insufficient_data'
    ema12 = pd.Series(close).ewm(span=12, adjust=False).mean()
    ema26 = pd.Series(close).ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26; dea = dif.ewm(span=9, adjust=False).mean()
    macd = 2 * (dif - dea)
    result['macd'] = macd.iloc[-1]; result['macd_prev'] = macd.iloc[-2]
    low_9 = pd.Series(low).rolling(9).min(); high_9 = pd.Series(high).rolling(9).max()
    rsv = (close - low_9.values) / (high_9.values - low_9.values + 0.01) * 100
    rsv = pd.Series(rsv).fillna(50); k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean(); j = 3 * k - 2 * d
    result['k'] = k.iloc[-1]; result['d'] = d.iloc[-1]; result['j'] = j.iloc[-1]
    if len(high) >= 10:
        wr1 = (high_9.iloc[-1] - close[-1]) / (high_9.iloc[-1] - low_9.iloc[-1] + 0.01) * 100
        h10 = pd.Series(high).rolling(10).max().iloc[-1]; l10 = pd.Series(low).rolling(10).min().iloc[-1]
        wr2 = (h10 - close[-1]) / (h10 - l10 + 0.01) * 100
        result['wr1'] = wr1; result['wr2'] = wr2
    else: result['wr1'] = 50; result['wr2'] = 50
    delta = pd.Series(close).diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    result['rsi'] = (100 - (100 / (1 + rs))).iloc[-1]
    if len(close) >= 14:
        op = df['open'].values.astype(float); tp = (high + low + close + op) / 3
        tp_sma = pd.Series(tp).rolling(14).mean()
        tp_md = pd.Series(tp).rolling(14).apply(lambda x: np.mean(np.abs(x - np.mean(x))))
        result['cci'] = (tp[-1] - tp_sma.iloc[-1]) / (0.015 * tp_md.iloc[-1] + 0.01)
    else: result['cci'] = 0
    m20 = pd.Series(close).rolling(20).mean(); s20 = pd.Series(close).rolling(20).std()
    result['boll_upper'] = m20.iloc[-1] + 2 * s20.iloc[-1]
    result['boll_mid'] = m20.iloc[-1]; result['boll_lower'] = m20.iloc[-1] - 2 * s20.iloc[-1]
    chg = pd.Series(close).diff()
    uv = volume.copy(); uv[chg <= 0] = 0; dv = volume.copy(); dv[chg >= 0] = 0
    nv = min(26, len(close)); result['vr'] = uv[-nv:].sum() / (dv[-nv:].sum() + 0.01) * 100
    op = df['open'].values.astype(float); mid = (high + low + close + op) / 4
    pm = np.roll(mid, 1); pm[0] = mid[0]; nc = min(26, len(close))
    up = np.maximum(0, high[-nc:] - pm[-nc:]).sum(); dn = np.maximum(0, pm[-nc:] - low[-nc:]).sum()
    result['cr'] = up / (dn + 0.01) * 100
    if len(close) >= 6:
        ma6 = np.mean(close[-6:]); pf = realtime_price if realtime_price else last_close
        result['bias6'] = (pf - ma6) / ma6 * 100
    else: result['bias6'] = 0
    obv = pd.Series(0.0, index=df.index)
    for t in range(1, len(df)):
        if close[t] > close[t-1]: obv.iloc[t] = obv.iloc[t-1] + volume[t]
        elif close[t] < close[t-1]: obv.iloc[t] = obv.iloc[t-1] - volume[t]
        else: obv.iloc[t] = obv.iloc[t-1]
    result['obv_trend'] = 'bullish' if np.mean(obv.tail(5)) > np.mean(obv.tail(10)) else 'bearish'
    result['high_20'] = np.max(high[-20:]); result['low_20'] = np.min(low[-20:])
    result['mom5'] = (last_close - close[-5]) / close[-5] * 100 if len(close) >= 5 else 0
    result['last_close'] = last_close
    result['last_date'] = str(df['date'].iloc[-1].date())
    return result

def score(hi, rt, ns=0):
    sv = 0; sig = []
    tr = hi.get('trend', '')
    if tr == 'bullish_aligned': sv += 17; sig.append(('MA 多头排列', 17))
    elif tr == 'bullish': sv += 13; sig.append(('MA 偏多', 13))
    elif tr == 'above_ma5': sv += 8; sig.append(('站上 MA5', 8))
    elif tr == 'bearish': sv -= 8; sig.append(('跌破 MA20', -8))
    if hi['macd'] > 0 and hi['macd'] > hi['macd_prev']: sv += 13; sig.append(('MACD 红柱放大', 13))
    elif hi['macd'] > 0: sv += 5; sig.append(('MACD 金叉', 5))
    elif hi['macd'] < 0 and hi['macd'] < hi['macd_prev']: sv -= 8; sig.append(('MACD 绿柱放大', -8))
    elif hi['macd'] < 0 and hi['macd'] > hi['macd_prev']: sv += 2; sig.append(('MACD 绿柱缩小(改善)', 2))
    elif abs(hi['macd']) < 0.01: sv += 0; sig.append(('MACD 零轴附近', 0))
    else: sv -= 5; sig.append(('MACD 死叉', -5))
    kv = hi['k']; rv = hi['rsi']; w1 = hi.get('wr1', 50); cc = hi.get('cci', 0)
    if 40 < kv < 80: sv += 2.5; sig.append(('KDJ 健康', 2.5))
    elif kv > 80: sv -= 2; sig.append(('KDJ 超买', -2))
    elif kv < 20: sv += 2.5; sig.append(('KDJ 超卖', 2.5))
    if 50 < rv < 70: sv += 2.5; sig.append(('RSI 健康', 2.5))
    elif rv > 70: sv -= 2; sig.append(('RSI 超买', -2))
    elif rv < 30: sv += 2.5; sig.append(('RSI 超卖', 2.5))
    if w1 > 80: sv += 2.5; sig.append(('WR 超卖', 2.5))
    elif w1 < 20: sv -= 2; sig.append(('WR 超买', -2))
    if cc > 100: sv -= 1.5; sig.append(('CCI 超买', -1.5))
    elif cc < -100: sv += 1.5; sig.append(('CCI 超卖', 1.5))
    else: sv += 0.5; sig.append(('CCI 正常', 0.5))
    pr = rt.get('price', 0); bu = hi.get('boll_upper', 0); bl = hi.get('boll_lower', 0); b6 = hi.get('bias6', 0)
    if bl > 0:
        if pr <= bl: sv += 8; sig.append(('触及下轨', 8))
        elif pr >= bu: sv -= 4; sig.append(('触及上轨', -4))
    if abs(b6) < 3: sv += 5; sig.append(('乖离率健康', 5))
    elif b6 > 8: sv -= 8; sig.append(('乖离率过大', -8))
    elif b6 < -8: sv += 6; sig.append(('乖离率极负', 6))
    vr = hi.get('vr', 0); cr = hi.get('cr', 0); ov = hi.get('obv_trend', 'bearish')
    if 160 < vr < 250: sv += 4; sig.append(('VR 黄金', 4))
    elif vr > 300: sv -= 4; sig.append(('VR 过热', -4))
    elif 40 < vr <= 160: sv += 2; sig.append(('VR 偏强', 2))
    if 100 < cr < 200: sv += 4; sig.append(('CR 健康', 4))
    elif cr > 300: sv -= 4; sig.append(('CR 过热', -4))
    if ov == 'bullish': sv += 5; sig.append(('OBV 流入', 5))
    else: sv -= 5; sig.append(('OBV 流出', -5))
    vl = rt.get('vol_ratio', 1); tc = rt.get('change', 0)
    if vl > 2.0 and tc > 0: sv += 8; sig.append(('放量上涨', 8))
    elif vl > 1.5 and tc > 0: sv += 4; sig.append(('温和放量', 4))
    elif vl > 2.0 and tc < 0: sv -= 8; sig.append(('放量下跌', -8))
    elif vl < 0.8 and tc < 0: sv += 4; sig.append(('缩量下跌', 4))
    m5 = hi.get('mom5', 0)
    if m5 > 5: sv += 4; sig.append(('5 日强势', 4))
    elif m5 < -5: sv -= 4; sig.append(('5 日弱势', -4))
    if tc > 5: sv += 7; sig.append(('今日大涨', 7))
    elif tc > 2: sv += 3; sig.append(('今日上涨', 3))
    elif tc < -3: sv -= 4; sig.append(('今日大跌', -4))
    ts = sv; ms = max(-15, min(15, ns))
    if ms > 5: sig.append((f'消息利好({ms})', ms))
    elif ms < -5: sig.append((f'消息利空({ms})', ms))
    elif abs(ms) <= 2: sig.append(('消息平静', 0))
    else: sig.append((f'消息微扰({ms})', ms))
    return ts + ms, sig, ts, ms

def get_conclusion(sv):
    if sv >= 70: return '强势看多'
    elif sv >= 40: return '偏多'
    elif sv >= 0: return '震荡'
    else: return '偏空'

def process_one(code, name, symbol, rt):
    df_hist = fetch_history(symbol)
    if df_hist is None: return None
    ns, nsum = analyze_news_sentiment(symbol)
    hi = compute_indicators(df_hist, realtime_price=rt['price'])
    fs, sig, ts, ms = score(hi, rt, ns)
    cc = get_conclusion(fs)
    ca = df_hist['close'].values.astype(float)
    m5r = (rt['price'] - ca[-4]) / ca[-4] * 100 if len(ca) >= 4 else 0
    global done_count
    with lock:
        done_count += 1
    # 不输出进度，避免撑爆工具上下文
    return {
        'name': name, 'code': code, 'price': rt['price'],
        'today_change': rt['change'], 'open': rt['open'],
        'high': rt['high'], 'low': rt['low'], 'vol_ratio': rt['vol_ratio'],
        'score': fs, 'tech_score': ts, 'msg_score': ms,
        'conclusion': cc, 'ma5': hi.get('ma',{}).get(5,0),
        'ma20': hi.get('ma',{}).get(20,0), 'macd': hi['macd'],
        'kdj_k': hi['k'], 'rsi': hi['rsi'], 'wr1': hi.get('wr1',0),
        'cci': hi.get('cci',0), 'bias6': hi.get('bias6',0),
        'obv_trend': hi.get('obv_trend','bearish'),
        'vr': hi.get('vr',0), 'cr': hi.get('cr',0),
        'boll_upper': hi.get('boll_upper',0), 'boll_lower': hi.get('boll_lower',0),
        'high_20': hi.get('high_20',0), 'low_20': hi.get('low_20',0),
        'mom5_hist': hi.get('mom5',0), 'mom5_realtime': m5r,
        'hist_last_close': hi.get('last_close',0),
        'hist_last_date': hi.get('last_date',''),
        'news_summaries': '; '.join(nsum[:3]),
        'signals': '; '.join([x[0] for x in sig]),
    }

def main():
    global total_count, done_count
    excel_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not excel_path:
        desktop = os.path.expanduser('~') + '/Desktop'
        for f in os.listdir(desktop):
            if 'wolffy1' in f: excel_path = os.path.join(desktop, f); break
    if not excel_path or not os.path.exists(excel_path):
        print(f"Error: file not found - {excel_path}"); sys.exit(1)
    df_input = pd.read_excel(excel_path, sheet_name=0, dtype={'代码': str})
    df_input['代码'] = df_input['代码'].astype(str).str.zfill(6)
    total_count = len(df_input)
    codes = df_input['代码'].tolist()
    realtime = fetch_realtime_prices(codes)
    tasks = []
    for _, row in df_input.iterrows():
        code = row['代码']; name = str(row['名称']).strip()
        if code not in realtime: continue
        symbol = f"sh{code}" if code.startswith('6') else f"sz{code}"
        tasks.append((code, name, symbol, realtime[code]))
    results = []
    start = time.time()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_one, *t): t for t in tasks}
        for future in as_completed(futures):
            try:
                r = future.result()
                if r: results.append(r)
            except:
                pass
    elapsed = time.time() - start
    if not results: print("No results"); sys.exit(1)
    df_r = pd.DataFrame(results).sort_values('score', ascending=False)
    
    # ====== 获取三大指数用于板块对比 ======
    indices = fetch_market_indices()
    sh_idx = indices.get('上证指数', indices.get('000001', {}))
    sz_idx = indices.get('深证成指', indices.get('399001', {}))
    cyb_idx = indices.get('创业板指', indices.get('399006', {}))
    
    # ====== TOP 10 Arbitrage Picks ======
    cands = df_r[(df_r['tech_score'] >= 30) & (df_r['today_change'] < 7.0) & (df_r['today_change'] > 0) & (df_r['vol_ratio'] >= 1.5) & (df_r['bias6'].abs() < 8.0) & (df_r['high_20'] > df_r['price'])].copy()
    # 动态止损：基于 BOLL 下轨和 20 日低点，波动率自适应
    # compute_dynamic_stop_loss 返回 (stop_loss, is_deep) 元组
    if len(cands) > 0:
        stop_results = cands.apply(
            lambda r: compute_dynamic_stop_loss(r['price'], r['boll_lower'], r['low_20']), axis=1
        )
        cands['stop_loss'] = [s[0] for s in stop_results]
        cands['stop_is_deep'] = [s[1] for s in stop_results]
    else:
        cands['stop_loss'] = []
        cands['stop_is_deep'] = []
    cands['upside'] = (cands['high_20'] - cands['price']) / cands['price'] * 100
    cands['downside'] = (cands['price'] - cands['stop_loss']) / cands['price'] * 100
    cands['rr'] = cands['upside'] / (cands['downside'] + 0.01)
    # 套利分数归一化到 0-100 范围 (V4.3 权重调整)
    # 修复核心问题：技术面 > 空间，短线套利首要看技术强度
    # 空间: 40->25, 技术面: 30->40
    cands['arb_score'] = (
        np.clip(cands['tech_score'] / 85.0 * 40, 0, 40) +    # 技术面归一化（85=满分40）
        np.clip(cands['upside'] / 30.0 * 25, 0, 25) +        # 空间归一化（30%=满分25）
        np.clip((cands['msg_score'] + 15) / 30.0 * 10, 0, 10) + # 消息面归一化
        np.clip(cands['rr'] / 10.0 * 15, 0, 15) -            # R/R归一化
        np.clip(cands['today_change'] / 7.0 * 10, 0, 10)      # 涨幅惩罚（5->10，追高更痛）
    )
    # 趋势一致性加分：MACD>0 且 OBV 流入 +5 分
    cands.loc[(cands['macd'] > 0) & (cands['obv_trend'] == 'bullish'), 'arb_score'] += 5
    # 止损过深惩罚：止损距现价 >6% 扣 10 分（短线不能扛太深）
    cands.loc[cands['stop_is_deep'] == True, 'arb_score'] -= 10
    # 可达性评估
    def calc_reach(row):
        tech, up, macd = row['tech_score'], row['upside'], row['macd']
        if tech >= 40 and macd > 0 and up <= 15:
            return '可达'
        elif tech >= 35 and up <= 20 and macd > -0.05:
            return '有可能'
        else:
            return '低可达'
    cands['reachability'] = cands.apply(calc_reach, axis=1)
    arb_top = cands.sort_values('arb_score', ascending=False).head(TOP_N)
    
    # 如果没有符合套利筛选条件的股票，直接输出评分排名
    if arb_top.empty:
        print(f"\n{'='*70}")
        print(f"  [WARN] 无符合套利筛选条件的股票")
        print(f"  Historical data cutoff: {results[0]['hist_last_date']}")
        idx_info = []
        if sh_idx.get('price', 0) > 0: idx_info.append(f"上证 {sh_idx['change']:+.2f}%")
        if sz_idx.get('price', 0) > 0: idx_info.append(f"深成 {sz_idx['change']:+.2f}%")
        if cyb_idx.get('price', 0) > 0: idx_info.append(f"创业板 {cyb_idx['change']:+.2f}%")
        if idx_info: print(f"  大盘指数: {' | '.join(idx_info)}")
        print(f"{'='*70}")
        print(f"\n  按综合评分排名（未通过套利筛选）:")
        print(f"  {'#':<3} {'股票':<12} {'现价':>7} {'涨幅':>7} {'评分':>6} {'结论':>8}")
        print(f"  {'─'*50}")
        for i, (_, r) in enumerate(df_r.head(10).iterrows()):
            print(f"  {i+1:<2} {r['name']+'('+r['code']+')':<12} {r['price']:>7.2f} {r['today_change']:>+6.2f}% {r['score']:>6.1f} {r['conclusion']:>8}")
        print(f"\n  完整结果已保存: {os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'analysis_result.csv')}")
        return
    
    print(f"\n{'='*70}")
    print(f"  TOP {TOP_N} Arbitrage Picks (space + risk/reward)")
    print(f"  Historical data cutoff: {results[0]['hist_last_date']}")
    # 板块对比：显示三大指数涨跌幅
    idx_info = []
    if sh_idx.get('price', 0) > 0: idx_info.append(f"上证 {sh_idx['change']:+.2f}%")
    if sz_idx.get('price', 0) > 0: idx_info.append(f"深成 {sz_idx['change']:+.2f}%")
    if cyb_idx.get('price', 0) > 0: idx_info.append(f"创业板 {cyb_idx['change']:+.2f}%")
    if idx_info: print(f"  大盘指数: {' | '.join(idx_info)}")
    print(f"{'='*70}")
    
    # 摘要表格（减少输出，防止工具上下文爆满）
    print(f"\n  {'#':<3} {'股票':<12} {'现价':>7} {'涨幅':>7} {'量比':>5} {'空间':>7} {'R/R':>5} {'评分':>6}")
    print(f"  {'─'*65}")
    for i, (_, r) in enumerate(arb_top.iterrows()):
        upside = (r['high_20'] - r['price']) / r['price'] * 100
        downside = (r['price'] - r['stop_loss']) / r['price'] * 100
        rr = upside / (downside + 0.01)
        tag = '***' if i == 0 else '   '
        print(f"  {tag}{i+1:<2} {r['name']+'('+r['code']+')':<12} {r['price']:>7.2f} {r['today_change']:>+6.2f}% {r['vol_ratio']:>5.1f}x {upside:>+6.1f}% {rr:>5.1f} {r['score']:>6.1f}")
    
    # 首推详情
    r = arb_top.iloc[0]
    upside = (r['high_20'] - r['price']) / r['price'] * 100
    downside = (r['price'] - r['stop_loss']) / r['price'] * 100
    rr = upside / (downside + 0.01)
    
    reasons = []
    if upside > 15: reasons.append(f"空间大:{upside:.0f}%")
    if rr > 3: reasons.append(f"盈亏比优:1:{rr:.0f}")
    if r['vol_ratio'] > 3: reasons.append(f"放量:{r['vol_ratio']:.1f}x")
    if r['obv_trend'] == 'bullish': reasons.append("OBV流入")
    if r['bias6'] < 3: reasons.append(f"BIAS低:{r['bias6']:.1f}%")
    if r['tech_score'] >= 40: reasons.append(f"技术强:{r['tech_score']:.0f}分")
    if r['today_change'] < 3: reasons.append(f"今涨仅{r['today_change']:.1f}%")
    if r['msg_score'] > 0: reasons.append(f"消息+{r['msg_score']:.0f}")
    
    risks = []
    if r['kdj_k'] > 80: risks.append(f"KDJ超买({r['kdj_k']:.0f})")
    if r['rsi'] > 70: risks.append(f"RSI超买({r['rsi']:.0f})")
    if r['wr1'] < 20: risks.append(f"WR超买({r['wr1']:.0f})")
    if r['today_change'] > 5: risks.append(f"今涨{r['today_change']:.1f}%")
    if r['bias6'] > 6: risks.append(f"BIAS偏高({r['bias6']:.1f}%)")
    if r['msg_score'] < -3: risks.append(f"消息偏空({r['msg_score']:.0f})")
    if r['tech_score'] < 35: risks.append(f"技术偏弱({r['tech_score']:.0f})")
    
    sigs = str(r['signals']).split('; ')
    pos = [s for s in sigs if any(k in s for k in ['排列','放大','健康','流入','上涨','超卖','黄金','偏强','金叉','大涨'])]
    neg = [s for s in sigs if any(k in s for k in ['超买','死叉','流出','跌破','过大','下跌','绿柱'])]
    
    print(f"\n  {'─'*65}")
    print(f"  首推: {r['name']}({r['code']}) 总分:{r['score']:.1f} (技术:{r['tech_score']:.1f} 消息:{r['msg_score']:.1f})")
    print(f"  现价:{r['price']:.2f} 今涨:{r['today_change']:+.2f}% 量比:{r['vol_ratio']:.1f}x")
    print(f"  空间+{upside:.1f}% | R/R 1:{rr:.1f} | 止损:{r['stop_loss']:.2f}")
    print(f"  可达性: {r['reachability']}")
    # 板块对比：相对强弱
    if r['code'].startswith('6') and sh_idx.get('change') is not None:
        bench_name, bench_chg = '上证指数', sh_idx['change']
    elif r['code'].startswith('3') and cyb_idx.get('change') is not None:
        bench_name, bench_chg = '创业板指', cyb_idx['change']
    elif sz_idx.get('change') is not None:
        bench_name, bench_chg = '深证成指', sz_idx['change']
    else:
        bench_name, bench_chg = None, None
    if bench_name and bench_chg is not None:
        relative = r['today_change'] - bench_chg
        direction = '强于' if relative > 0 else '弱于'
        print(f"  板块对比: 相对{bench_name}{direction}{abs(relative):.2f}% (个股{r['today_change']:+.2f}% vs {bench_name}{bench_chg:+.2f}%)")
    if reasons: print(f"  理由: {'; '.join(reasons)}")
    if pos: print(f"  信号: {'; '.join(pos[:3])}")
    if risks: print(f"  风险: {'; '.join(risks)}")
    if r['news_summaries'] and str(r['news_summaries']).strip():
        print(f"  新闻: {str(r['news_summaries'])[:120]}")
    print(f"  入场:{r['ma5']:.2f}-{r['price']:.2f} | 目标:{r['high_20']:.2f}")
    
    # Save CSV with timestamp
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'analysis_result.csv')
    df_r['analysis_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    df_r.to_csv(out, index=False, encoding='utf-8-sig')
    print(f"\n  完整结果已保存: {out}")
    print(f"\n  * 以上分析仅供参考，不构成投资建议。股市有风险，投资需谨慎。")

if __name__ == '__main__':
    main()
