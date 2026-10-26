"""
stock_screener.py - wolffy1 选股结果批量技术分析评分 (V4.0-MVP 消息面版)
======================================================

更新日志:
- V4.0-MVP (消息面):
  - 新增东方财富个股新闻抓取 (stock_news_em)
  - 新增关键词情感打分 (利好/利空/中性)
  - 新增时效性衰减逻辑 (今日 100%, 昨日 50%, 前日 20%)
  - 综合评分 = 技术面 (85%) + 消息面 (15%)
- V3.1 (修复): 修复 BIAS/OBV, 新增 WR/CCI
- V3.0: 新增 BIAS, OBV, 关键高低点
- V2.0: 增加 VR, CR, BOLL

用法:
    python stock_screener.py "桌面上的 wolffy1 选股表格.xlsx"

数据源:
    历史指标 → akshare (纯历史，截止到上周五)
    今日实时 → 腾讯行情 API (延迟<3 分钟)
    消息面   → akshare.stock_news_em (最近新闻)
"""

import akshare as ak
import pandas as pd
import numpy as np
import requests
import time
import os
import sys
from datetime import datetime, timedelta

# ============================================================
# 配置区
# ============================================================

TOP_N = 10
DATA_WINDOW = 60
REQUEST_DELAY = 1.5

SCORE_STRONG = 70
SCORE_BULLISH = 40
SCORE_NEUTRAL = 0

# 消息面关键词库 (V4.0 分级版 - 2026-04-08 大幅扩充)
# 格式: (关键词, 强度权重)  权重 3.0=强信号, 1.0=普通, 0.5=弱信号

KEYWORDS_POSITIVE = [
    # === 强利好 (权重 3.0) ===
    ('IPO', 3.0), ('上市', 3.0), ('借壳', 3.0), ('重组', 3.0),
    ('并购', 3.0), ('收购', 3.0), ('分拆上市', 3.0),
    # === 普通利好 (权重 1.0) ===
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
    # === 弱利好 (权重 0.5) ===
    ('优化', 0.5), ('升级', 0.5), ('拓展', 0.5), ('布局', 0.5),
    ('推进', 0.5), ('签约', 0.5), ('合资', 0.5), ('成立', 0.5),
    ('研发', 0.5), ('落地', 0.5),
]

KEYWORDS_NEGATIVE = [
    # === 强利空 (权重 3.0) ===
    ('立案', 3.0), ('退市', 3.0), ('暴雷', 3.0), ('违约', 3.0),
    ('造假', 3.0), ('欺诈', 3.0), ('实控人被抓', 3.0),
    # === 普通利空 (权重 1.0) ===
    ('调查', 1.0), ('处罚', 1.0), ('减持', 1.0), ('预减', 1.0),
    ('亏损', 1.0), ('诉讼', 1.0), ('仲裁', 1.0), ('终止', 1.0),
    ('警示', 1.0), ('风险', 1.0), ('下跌', 1.0), ('监管', 1.0),
    ('问询', 1.0), ('不及预期', 1.0), ('下滑', 1.0), ('下降', 1.0),
    ('降薪', 1.0), ('质押', 1.0), ('资金流出', 1.0), ('净流出', 1.0),
    ('业绩下滑', 1.0), ('利润下降', 1.0), ('营收下降', 1.0),
    ('被举报', 1.0), ('召回', 1.0), ('停产', 1.0), ('裁员', 1.0),
    ('商誉减值', 1.0), ('资产减值', 1.0), ('坏账', 1.0),
    # === 弱利空 (权重 0.5) ===
    ('波动', 0.5), ('承压', 0.5), ('放缓', 0.5), ('警惕', 0.5),
    ('回调', 0.5), ('分歧', 0.5), ('争议', 0.5),
]

# ============================================================
# 消息面分析模块 (V4.0-MVP)
# ============================================================

def analyze_news_sentiment(symbol):
    """
    抓取最近新闻并进行情感打分
    返回：(score, summary_list)
    """
    score = 0
    summaries = []
    
    try:
        # stock_news_em 只需要纯股票代码，不需要市场前缀
        clean_code = symbol[2:] if len(symbol) > 2 and symbol[:2] in ('sh', 'sz') else symbol
        
        # 获取最近 5 条新闻
        # akshare 的新闻接口有时候不稳定，这里做个容错
        df = ak.stock_news_em(symbol=clean_code)
        if df is None or df.empty:
            return 0, []
        
        # 取前 5 条
        df = df.head(5)
        today = datetime.now().date()
        
        for _, row in df.iterrows():
            title = str(row.get('新闻标题', ''))
            content = str(row.get('新闻内容', ''))
            pub_time_str = str(row.get('发布时间', ''))
            
            # 尝试解析时间
            try:
                # 格式通常是 '2026-04-07 12:00:00'
                pub_date = datetime.strptime(pub_time_str[:10], '%Y-%m-%d').date()
                days_diff = (today - pub_date).days
            except:
                days_diff = 1  # 解析失败默认衰减
            
            # 时效性衰减
            if days_diff == 0:
                decay = 1.0
            elif days_diff == 1:
                decay = 0.5
            elif days_diff == 2:
                decay = 0.2
            elif days_diff <= 5:
                decay = 0.1
            else:
                decay = 0.0
            
            # 关键词匹配（分级加权）
            text = title + " " + content[:500]  # 标题 + 前 500 字
            
            pos_score = 0.0
            pos_hits = []
            for kw, weight in KEYWORDS_POSITIVE:
                if kw in text:
                    pos_score += weight
                    pos_hits.append(kw)
            
            neg_score = 0.0
            neg_hits = []
            for kw, weight in KEYWORDS_NEGATIVE:
                if kw in text:
                    neg_score += weight
                    neg_hits.append(kw)
            
            # 加权计分：利空权重更高 (x1.5)
            raw = (pos_score - neg_score * 1.5)
            item_score = raw * decay * 5  # 基础分 * 衰减
            
            score += item_score
            
            # 记录关键新闻
            if pos_hits or neg_hits:
                tags = []
                if pos_hits:
                    tags.append(f"[+{','.join(pos_hits[:3])}]")
                if neg_hits:
                    tags.append(f"[-{','.join(neg_hits[:3])}]")
                # 根据正负词情况判断，而不是只看 item_score（衰减可能让分数变低）
                if pos_score > 0 and neg_score == 0:
                    status = "[BULL]"
                elif neg_score > 0 and pos_score == 0:
                    status = "[BEAR]"
                elif pos_score > neg_score:
                    status = "[BULL]"
                elif neg_score > pos_score:
                    status = "[BEAR]"
                else:
                    status = "[NEUTRAL]"
                summaries.append(f"{status}{' '.join(tags)} ({days_diff}天前): {title[:40]}")

    except Exception as e:
        summaries.append(f"消息获取失败：{e}")
    
    # 限制总分范围 -15 到 +15
    score = max(-15, min(15, score))
    
    return score, summaries


# ============================================================
# 实时行情获取（腾讯 API）
# ============================================================

def fetch_realtime_prices(codes):
    """从腾讯行情 API 批量获取实时数据"""
    results = {}
    for i in range(0, len(codes), 20):
        batch = codes[i:i+20]
        query = ','.join([f"sh{c}" if c.startswith('6') else f"sz{c}" for c in batch])
        try:
            r = requests.get(
                f"https://qt.gtimg.cn/q={query}",
                headers={'Referer': 'https://finance.qq.com', 'User-Agent': 'Mozilla/5.0'},
                timeout=10
            )
            data = r.content.decode('gbk', errors='replace')
            for line in data.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue
                parts = line.split('~')
                if len(parts) < 35:
                    continue
                code = parts[2]
                results[code] = {
                    'price': float(parts[3]),
                    'prev': float(parts[4]),
                    'open': float(parts[5]),
                    'high': float(parts[33]),
                    'low': float(parts[34]),
                    'vol_ratio': float(parts[38]) if parts[38] else 0,
                    'change': (float(parts[3]) - float(parts[4])) / float(parts[4]) * 100,
                }
            time.sleep(0.3)
        except Exception as e:
            print(f"ERR 腾讯 API 请求失败：{e}")
    return results


# ============================================================
# 历史 K 线数据（akshare，纯历史）
# ============================================================

def fetch_history(symbol):
    """获取日 K 线数据"""
    try:
        df = ak.stock_zh_a_daily(symbol=symbol)
        if df is None or len(df) < 30:
            return None
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').tail(DATA_WINDOW)
        return df
    except Exception:
        return None


# ============================================================
# 技术指标计算 (V3.1 修复版)
# ============================================================

def compute_indicators(df, realtime_price=None):
    """计算所有技术指标 - 仅使用历史 K 线数据"""
    close = df['close'].values.astype(float)
    high = df['high'].values.astype(float)
    low = df['low'].values.astype(float)
    volume = df['volume'].values.astype(float)
    result = {}

    # --- 均线系统 ---
    mas = {}
    for period in [5, 10, 20, 60]:
        if len(close) >= period:
            mas[period] = np.mean(close[-period:])
    result['ma'] = mas

    last_close = close[-1]

    # --- 趋势判断 ---
    if all(k in mas for k in [5, 10, 20]):
        if last_close > mas[5] > mas[10] > mas[20]:
            result['trend'] = 'bullish_aligned'
        elif last_close > mas[5] > mas[10]:
            result['trend'] = 'bullish'
        elif last_close > mas[5]:
            result['trend'] = 'above_ma5'
        elif last_close < mas[20]:
            result['trend'] = 'bearish'
        else:
            result['trend'] = 'sideways'
    else:
        result['trend'] = 'insufficient_data'

    # --- MACD ---
    ema12 = pd.Series(close).ewm(span=12, adjust=False).mean()
    ema26 = pd.Series(close).ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    macd = 2 * (dif - dea)
    result['macd'] = macd.iloc[-1]
    result['macd_prev'] = macd.iloc[-2]

    # --- KDJ ---
    low_9 = pd.Series(low).rolling(9).min()
    high_9 = pd.Series(high).rolling(9).max()
    rsv = (close - low_9.values) / (high_9.values - low_9.values + 0.01) * 100
    rsv = pd.Series(rsv).fillna(50)
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    j = 3 * k - 2 * d
    result['k'] = k.iloc[-1]
    result['d'] = d.iloc[-1]
    result['j'] = j.iloc[-1]

    # --- WR (威廉指标) ---
    if len(high) >= 10:
        wr1 = (high_9.iloc[-1] - close[-1]) / (high_9.iloc[-1] - low_9.iloc[-1] + 0.01) * 100
        high_10 = pd.Series(high).rolling(10).max().iloc[-1]
        low_10 = pd.Series(low).rolling(10).min().iloc[-1]
        wr2 = (high_10 - close[-1]) / (high_10 - low_10 + 0.01) * 100
        result['wr1'] = wr1
        result['wr2'] = wr2
    else:
        result['wr1'] = 50
        result['wr2'] = 50

    # --- RSI ---
    delta = pd.Series(close).diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    result['rsi'] = rsi.iloc[-1]

    # --- CCI (顺势指标) ---
    if len(close) >= 14:
        open_prices = df['open'].values.astype(float)
        tp = (high + low + close + open_prices) / 3
        tp_sma = pd.Series(tp).rolling(14).mean()
        tp_md = pd.Series(tp).rolling(14).apply(lambda x: np.mean(np.abs(x - np.mean(x))))
        cci = (tp[-1] - tp_sma.iloc[-1]) / (0.015 * tp_md.iloc[-1] + 0.01)
        result['cci'] = cci
    else:
        result['cci'] = 0

    # --- BOLL (布林带) ---
    ma20_s = pd.Series(close).rolling(20).mean()
    std20 = pd.Series(close).rolling(20).std()
    result['boll_upper'] = ma20_s.iloc[-1] + 2 * std20.iloc[-1]
    result['boll_mid'] = ma20_s.iloc[-1]
    result['boll_lower'] = ma20_s.iloc[-1] - 2 * std20.iloc[-1]
    
    # --- VR (成交量比率) ---
    changes = pd.Series(close).diff()
    up_vol = volume.copy()
    up_vol[changes <= 0] = 0
    down_vol = volume.copy()
    down_vol[changes >= 0] = 0
    n_vr = min(26, len(close))
    result['vr'] = up_vol[-n_vr:].sum() / (down_vol[-n_vr:].sum() + 0.01) * 100

    # --- CR (能量指标) ---
    open_prices = df['open'].values.astype(float)
    mid = (high + low + close + open_prices) / 4
    prev_mid = np.roll(mid, 1)
    prev_mid[0] = mid[0]
    n_cr = min(26, len(close))
    up_power = np.maximum(0, high[-n_cr:] - prev_mid[-n_cr:]).sum()
    down_power = np.maximum(0, prev_mid[-n_cr:] - low[-n_cr:]).sum()
    result['cr'] = up_power / (down_power + 0.01) * 100

    # --- BIAS (乖离率) - 修复：用实时价格计算 ---
    if len(close) >= 6:
        ma6 = np.mean(close[-6:])
        price_for_bias = realtime_price if realtime_price else last_close
        result['bias6'] = (price_for_bias - ma6) / ma6 * 100
    else:
        result['bias6'] = 0
    
    # --- OBV (能量潮) - 修复 ---
    obv_series = pd.Series(0.0, index=df.index)
    for t in range(1, len(df)):
        if close[t] > close[t-1]:
            obv_series.iloc[t] = obv_series.iloc[t-1] + volume[t]
        elif close[t] < close[t-1]:
            obv_series.iloc[t] = obv_series.iloc[t-1] - volume[t]
        else:
            obv_series.iloc[t] = obv_series.iloc[t-1]
    
    obv_5 = np.mean(obv_series.tail(5))
    obv_10 = np.mean(obv_series.tail(10))
    result['obv_trend'] = 'bullish' if obv_5 > obv_10 else 'bearish'

    # --- 关键高低点 ---
    result['high_20'] = np.max(high[-20:])
    result['low_20'] = np.min(low[-20:])
    if len(high) >= 60:
        result['high_60'] = np.max(high[-60:])
        result['low_60'] = np.min(low[-60:])
    else:
        result['high_60'] = result['high_20']
        result['low_60'] = result['low_20']

    # --- 5 日动量 ---
    result['mom5'] = (last_close - close[-5]) / close[-5] * 100 if len(close) >= 5 else 0
    result['last_close'] = last_close
    result['last_date'] = str(df['date'].iloc[-1].date()) if 'date' in df.columns else 'unknown'

    return result


# ============================================================
# 评分模型 (V4.0-MVP: 技术面 85 分 + 消息面 15 分)
# ============================================================

def score(hist_ind, realtime, news_score=0):
    """综合评分：历史技术指标 (85 分) + 今日实时数据 (部分) + 消息面 (15 分)"""
    score_val = 0
    signals = []

    # === 1. 均线趋势 (Max 17) === (原 20, 缩减比例以适配总分 85)
    trend = hist_ind.get('trend', '')
    if trend == 'bullish_aligned':
        score_val += 17; signals.append(('MA 多头排列', 17))
    elif trend == 'bullish':
        score_val += 13; signals.append(('MA 偏多', 13))
    elif trend == 'above_ma5':
        score_val += 8; signals.append(('站上 MA5', 8))
    elif trend == 'bearish':
        score_val -= 8; signals.append(('跌破 MA20', -8))

    # === 2. MACD 趋势 (Max 13) === (原 15)
    if hist_ind['macd'] > 0 and hist_ind['macd'] > hist_ind['macd_prev']:
        score_val += 13; signals.append(('MACD 红柱放大', 13))
    elif hist_ind['macd'] > 0:
        score_val += 5; signals.append(('MACD 金叉', 5))
    elif hist_ind['macd'] < 0 and hist_ind['macd'] < hist_ind['macd_prev']:
        score_val -= 8; signals.append(('MACD 绿柱放大', -8))
    elif hist_ind['macd'] < 0 and hist_ind['macd'] > hist_ind['macd_prev']:
        score_val += 2; signals.append(('MACD 绿柱缩小(改善)', 2))
    else:
        score_val -= 5; signals.append(('MACD 死叉', -5))

    # === 3. KDJ/RSI/WR/CCI (Max 10) === (原 12)
    k_val = hist_ind['k']
    rsi_val = hist_ind['rsi']
    wr1 = hist_ind.get('wr1', 50)
    cci = hist_ind.get('cci', 0)
    
    if 40 < k_val < 80:
        score_val += 2.5; signals.append(('KDJ 健康', 2.5))
    elif k_val > 80:
        score_val -= 2; signals.append(('KDJ 超买', -2))
    elif k_val < 20:
        score_val += 2.5; signals.append(('KDJ 超卖', 2.5))
    
    if 50 < rsi_val < 70:
        score_val += 2.5; signals.append(('RSI 健康', 2.5))
    elif rsi_val > 70:
        score_val -= 2; signals.append(('RSI 超买', -2))
    elif rsi_val < 30:
        score_val += 2.5; signals.append(('RSI 超卖', 2.5))

    if wr1 > 80:
        score_val += 2.5; signals.append(('WR 超卖', 2.5))
    elif wr1 < 20:
        score_val -= 2; signals.append(('WR 超买', -2))

    if cci > 100:
        score_val -= 1.5; signals.append(('CCI 超买', -1.5))
    elif cci < -100:
        score_val += 1.5; signals.append(('CCI 超卖', 1.5))
    else:
        score_val += 0.5; signals.append(('CCI 正常', 0.5))

    # === 4. BOLL/BIAS 位置 (Max 13) === (原 15)
    price = realtime.get('price', 0)
    b_u = hist_ind.get('boll_upper', 0)
    b_l = hist_ind.get('boll_lower', 0)
    m20 = hist_ind.get('ma', {}).get(20, 0)
    bias6 = hist_ind.get('bias6', 0)
    
    if b_l > 0:
        if price <= b_l:
            score_val += 8; signals.append(('触及下轨', 8))
        elif price >= b_u:
            score_val -= 4; signals.append(('触及上轨', -4))
    
    if abs(bias6) < 3:
        score_val += 5; signals.append(('乖离率健康', 5))
    elif bias6 > 8:
        score_val -= 8; signals.append(('乖离率过大', -8))
    elif bias6 < -8:
        score_val += 6; signals.append(('乖离率极负', 6))

    # === 5. VR/CR/OBV 资金动能 (Max 13) === (原 15)
    vr = hist_ind.get('vr', 0)
    cr = hist_ind.get('cr', 0)
    obv = hist_ind.get('obv_trend', 'bearish')
    
    if 160 < vr < 250:
        score_val += 4; signals.append(('VR 黄金', 4))
    elif vr > 300:
        score_val -= 4; signals.append(('VR 过热', -4))
    elif 40 < vr <= 160:
        score_val += 2; signals.append(('VR 偏强', 2))

    if 100 < cr < 200:
        score_val += 4; signals.append(('CR 健康', 4))
    elif cr > 300:
        score_val -= 4; signals.append(('CR 过热', -4))
    
    if obv == 'bullish':
        score_val += 5; signals.append(('OBV 流入', 5))
    else:
        score_val -= 5; signals.append(('OBV 流出', -5))

    # === 6. 量价关系 (Max 8) === (原 10)
    vol_ratio = realtime.get('vol_ratio', 1)
    today_chg = realtime.get('change', 0)

    if vol_ratio > 2.0 and today_chg > 0:
        score_val += 8; signals.append(('放量上涨', 8))
    elif vol_ratio > 1.5 and today_chg > 0:
        score_val += 4; signals.append(('温和放量', 4))
    elif vol_ratio > 2.0 and today_chg < 0:
        score_val -= 8; signals.append(('放量下跌', -8))
    elif vol_ratio < 0.8 and today_chg < 0:
        score_val += 4; signals.append(('缩量下跌', 4))

    # === 7. 动量与表现 (Max 11) === (原 13)
    mom5 = hist_ind.get('mom5', 0)
    if mom5 > 5:
        score_val += 4; signals.append(('5 日强势', 4))
    elif mom5 < -5:
        score_val -= 4; signals.append(('5 日弱势', -4))

    if today_chg > 5:
        score_val += 7; signals.append(('今日大涨', 7))
    elif today_chg > 2:
        score_val += 3; signals.append(('今日上涨', 3))
    elif today_chg < -3:
        score_val -= 4; signals.append(('今日大跌', -4))

    # 此时 score_val 满分为 85 (技术面 + 实时面)
    tech_score = score_val

    # === 8. 消息面 (Max 15) === (新增 V4.0-MVP)
    # news_score 范围 [-15, 15]
    msg_score = max(-15, min(15, news_score))
    if msg_score > 5:
        signals.append((f'消息面利好 ({msg_score})', msg_score))
    elif msg_score < -5:
        signals.append((f'消息面利空 ({msg_score})', msg_score))
    elif abs(msg_score) <= 2:
        signals.append(('消息面平静', 0))
    else:
        signals.append((f'消息面微扰 ({msg_score})', msg_score))

    final_score = tech_score + msg_score

    return final_score, signals, tech_score, msg_score


def get_conclusion(score_val):
    if score_val >= SCORE_STRONG:
        return '强势看多'
    elif score_val >= SCORE_BULLISH:
        return '偏多'
    elif score_val >= SCORE_NEUTRAL:
        return '震荡'
    else:
        return '偏空'


# ============================================================
# 主流程
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("用法：python stock_screener.py <wolffy1_Excel 文件路径>")
        sys.exit(1)

    excel_path = sys.argv[1]
    if not os.path.exists(excel_path):
        print(f"Error: 文件不存在 - {excel_path}")
        sys.exit(1)

    print(f"读取文件：{excel_path}")
    df_input = pd.read_excel(excel_path, sheet_name=0, dtype={'代码': str})
    df_input['代码'] = df_input['代码'].astype(str).str.zfill(6)
    print(f"共 {len(df_input)} 只股票\n")

    print("获取实时行情（腾讯 API）...")
    codes = df_input['代码'].tolist()
    realtime = fetch_realtime_prices(codes)
    print(f"实时行情获取成功：{len(realtime)}/{len(codes)} 只\n")

    results = []

    for i, (_, row) in enumerate(df_input.iterrows()):
        code = row['代码']
        name = str(row['名称']).strip()
        symbol = f"sh{code}" if code.startswith('6') else f"sz{code}"

        rt = realtime.get(code)
        if rt is None:
            print(f"  [{i+1}/{len(df_input)}] {name}({code}): 实时行情获取失败，跳过")
            continue

        df_hist = fetch_history(symbol)
        if df_hist is None:
            print(f"  [{i+1}/{len(df_input)}] {name}({code}): 历史数据不足，跳过")
            continue

        # 1. 获取消息面得分
        print(f"  [{i+1}/{len(df_input)}] {name}({code}): 分析消息面...", end="", flush=True)
        news_score, news_summaries = analyze_news_sentiment(symbol)
        
        # 2. 计算技术指标 (传入实时价格计算 BIAS)
        hist_ind = compute_indicators(df_hist, realtime_price=rt['price'])
        
        # 3. 综合评分
        final_score, signals, tech_score, msg_score = score(hist_ind, rt, news_score)
        conclusion = get_conclusion(final_score)

        close_arr = df_hist['close'].values.astype(float)
        mom5_realtime = (rt['price'] - close_arr[-4]) / close_arr[-4] * 100 if len(close_arr) >= 4 else 0

        results.append({
            'name': name, 'code': code,
            'price': rt['price'], 'today_change': rt['change'],
            'open': rt['open'], 'high': rt['high'], 'low': rt['low'],
            'vol_ratio': rt['vol_ratio'],
            'score': final_score, 'tech_score': tech_score, 'msg_score': msg_score,
            'conclusion': conclusion,
            'ma5': hist_ind.get('ma', {}).get(5, 0),
            'ma20': hist_ind.get('ma', {}).get(20, 0),
            'macd': hist_ind['macd'],
            'kdj_k': hist_ind['k'],
            'rsi': hist_ind['rsi'],
            'wr1': hist_ind.get('wr1', 0),
            'cci': hist_ind.get('cci', 0),
            'bias6': hist_ind.get('bias6', 0),
            'obv_trend': hist_ind.get('obv_trend', 'bearish'),
            'vr': hist_ind.get('vr', 0),
            'cr': hist_ind.get('cr', 0),
            'boll_upper': hist_ind.get('boll_upper', 0),
            'boll_lower': hist_ind.get('boll_lower', 0),
            'high_20': hist_ind.get('high_20', 0),
            'low_20': hist_ind.get('low_20', 0),
            'mom5_hist': hist_ind.get('mom5', 0),
            'mom5_realtime': mom5_realtime,
            'hist_last_close': hist_ind.get('last_close', 0),
            'hist_last_date': hist_ind.get('last_date', ''),
            'news_summaries': news_summaries,
            'signals': '; '.join([s[0] for s in signals]),
        })

        print(f" 总分:{final_score:.1f} (技术:{tech_score:.1f} 消息:{msg_score:.1f}) {conclusion}")
        time.sleep(REQUEST_DELAY)

    if not results:
        print("\n没有有效的分析结果")
        sys.exit(1)

    df_results = pd.DataFrame(results).sort_values('score', ascending=False)
    top = df_results.head(TOP_N)

    print("\n" + "="*100)
    print(f"  TOP {TOP_N} 核心股评分排名（V4.0-MVP: 含消息面分析）")
    print(f"  历史数据截止：{results[0]['hist_last_date']}")
    print("="*100)

    for i, (_, row) in enumerate(top.iterrows()):
        print(f"\n{'='*70}")
        print(f"  TOP {i+1}: [{row['conclusion']}] {row['name']}({row['code']})")
        print(f"  总分:{row['score']:.1f} | 技术:{row['tech_score']:.1f} | 消息:{row['msg_score']:.1f}")
        print(f"  现价：{row['price']:.2f} | 今日：{row['today_change']:+.2f}%")
        print(f"  MA5={row['ma5']:.2f} MA20={row['ma20']:.2f} | BIAS(6): {row['bias6']:.2f}%")
        print(f"  MACD={row['macd']:.3f} | K={row['kdj_k']:.1f} | RSI={row['rsi']:.1f}")
        print(f"  WR1={row['wr1']:.1f} CCI={row['cci']:.1f} | OBV: {row['obv_trend']}")
        print(f"  VR={row['vr']:.0f} CR={row['cr']:.0f}")
        print(f"  压力位 (20H): {row['high_20']:.2f} | 支撑位 (20L): {row['low_20']:.2f}")
        print(f"  信号：{row['signals']}")
        
        # 打印消息摘要
        if row['news_summaries']:
            print(f"  📰 消息摘要:")
            for news in row['news_summaries']:
                print(f"     {news}")

    print(f"\n{'='*100}")
    print(f"  * 指标说明：WR 识别拐点，CCI 识别极端行情，BIAS 判断偏离度")
    print(f"  * 消息面：基于东方财富新闻关键词匹配 + 时效性衰减 (V4.0-MVP)")
    print(f"{'='*100}")

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'analysis_result.csv')
    df_results.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n完整结果已保存：{output_path}")


if __name__ == '__main__':
    main()
