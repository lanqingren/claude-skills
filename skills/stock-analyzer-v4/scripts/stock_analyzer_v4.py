#!/usr/bin/env python3
"""
A股股票分析工具 - 增强版 V4
多数据源自动切换：腾讯财经(主) -> 新浪财经(备1) -> 东方财富(备2)
新增功能:
  - 资金流向 (东方财富API)
  - 主要股东 (akshare)
Usage: python3 stock_analyzer_v4.py <stock_code>
"""

import sys
import requests
import json
import pandas as pd
from datetime import datetime
import math

# 数据源优先级配置
DATA_SOURCES = ['tencent', 'sina', 'eastmoney']

def get_market_prefix(symbol):
    """根据股票代码获取市场前缀"""
    if symbol.startswith('6'):
        return 'sh'  # 上海
    else:
        return 'sz'  # 深圳

def parse_tencent_data(data_str, symbol):
    """解析腾讯财经数据"""
    try:
        if '~' not in data_str:
            return None
        parts = data_str.split('"')[1].split('~')
        
        return {
            'name': parts[1],
            'code': parts[2],
            'price': float(parts[3]),
            'prev_close': float(parts[4]),
            'open': float(parts[5]),
            'volume': int(parts[6]),  # 手
            'bid_vol': int(parts[7]),
            'ask_vol': int(parts[8]),
            'bid1_price': float(parts[9]),
            'bid1_vol': int(parts[10]),
            'bids': [(float(parts[9+i*2]), int(parts[10+i*2])) for i in range(5)],
            'asks': [(float(parts[19+i*2]), int(parts[20+i*2])) for i in range(5)],
            'datetime': parts[30],
            'change': float(parts[31]),
            'change_pct': float(parts[32]),
            'high': float(parts[33]),
            'low': float(parts[34]),
            'vol_shou': int(parts[36]),
            'turnover_wan': float(parts[37]),
            'turnover_rate': float(parts[38]),
            'pe': float(parts[39]) if parts[39] else 0,
            'amplitude': float(parts[42]),
            'float_cap': float(parts[43]),
            'total_cap': float(parts[44]),
            'pb': float(parts[45]),
            'limit_up': float(parts[46]),
            'limit_down': float(parts[47]),
            'source': 'tencent'
        }
    except Exception as e:
        return None

def parse_sina_data(data_str, symbol):
    """解析新浪财经数据"""
    try:
        if '"' not in data_str:
            return None
        parts = data_str.split('"')[1].split(',')
        
        # 新浪数据格式: 名称,今日开盘价,昨日收盘价,当前价,今日最高价,今日最低价,竞买价,竞卖价,成交量(股),成交额(元),...
        name = parts[0]
        open_price = float(parts[1])
        prev_close = float(parts[2])
        price = float(parts[3])
        high = float(parts[4])
        low = float(parts[5])
        volume_gu = int(parts[8])
        turnover_yuan = float(parts[9])
        date_str = parts[30]
        time_str = parts[31]
        
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close > 0 else 0
        amplitude = ((high - low) / prev_close * 100) if prev_close > 0 else 0
        vol_shou = volume_gu // 100
        turnover_wan = turnover_yuan / 10000
        
        return {
            'name': name,
            'code': symbol,
            'price': price,
            'prev_close': prev_close,
            'open': open_price,
            'volume': vol_shou,
            'high': high,
            'low': low,
            'change': change,
            'change_pct': change_pct,
            'amplitude': amplitude,
            'vol_shou': vol_shou,
            'turnover_wan': turnover_wan,
            'turnover_rate': 0,  # 新浪不提供
            'pe': 0,  # 新浪不提供
            'pb': 0,  # 新浪不提供
            'float_cap': 0,
            'total_cap': 0,
            'source': 'sina'
        }
    except Exception as e:
        return None

def parse_eastmoney_data(data, symbol):
    """解析东方财富数据"""
    try:
        if 'data' not in data or data['data'] is None:
            return None
        d = data['data']
        
        price = float(d.get('f43', 0))
        prev_close = float(d.get('f60', 0))
        change = price - prev_close if price and prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0
        high = float(d.get('f44', 0))
        low = float(d.get('f45', 0))
        open_price = float(d.get('f46', 0))
        volume_gu = float(d.get('f47', 0))
        turnover_yuan = float(d.get('f48', 0))
        amplitude = ((high - low) / prev_close * 100) if prev_close > 0 else 0
        
        return {
            'name': d.get('f58', symbol),
            'code': d.get('f57', symbol),
            'price': price,
            'prev_close': prev_close,
            'open': open_price,
            'volume': volume_gu / 100,
            'high': high,
            'low': low,
            'change': change,
            'change_pct': change_pct,
            'amplitude': amplitude,
            'vol_shou': volume_gu / 100,
            'turnover_wan': turnover_yuan / 10000,
            'turnover_rate': float(d.get('f168', 0)),
            'pe': float(d.get('f162', 0)),
            'pb': float(d.get('f167', 0)),
            'float_cap': float(d.get('f21', 0)) * 10000 if d.get('f21') else 0,
            'total_cap': float(d.get('f20', 0)) * 10000 if d.get('f20') else 0,
            'source': 'eastmoney'
        }
    except Exception as e:
        return None

def get_stock_data_tencent(symbol):
    """从腾讯财经获取数据"""
    try:
        prefix = get_market_prefix(symbol)
        url = f"https://qt.gtimg.cn/q={prefix}{symbol}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=10)
        data = parse_tencent_data(resp.text, symbol)
        if data:
            return data, None
        return None, "腾讯财经数据解析失败"
    except Exception as e:
        return None, f"腾讯财经请求失败: {str(e)}"

def get_stock_data_sina(symbol):
    """从新浪财经获取数据"""
    try:
        prefix = get_market_prefix(symbol)
        url = f"https://hq.sinajs.cn/list={prefix}{symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://finance.sina.com.cn'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        data = parse_sina_data(resp.text, symbol)
        if data:
            return data, None
        return None, "新浪财经数据解析失败"
    except Exception as e:
        return None, f"新浪财经请求失败: {str(e)}"

def get_stock_data_eastmoney(symbol):
    """从东方财富获取数据"""
    try:
        secid = f"{'1' if symbol.startswith('6') else '0'}.{symbol}"
        url = f"https://push2.eastmoney.com/api/qt/stock/get?ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&volt=2&fields=f43,f44,f45,f46,f47,f48,f57,f58,f60,f162,f167,f173,f20,f21,f168,f169,f170,f171&secid={secid}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=10)
        data = parse_eastmoney_data(resp.json(), symbol)
        if data:
            return data, None
        return None, "东方财富数据解析失败"
    except Exception as e:
        return None, f"东方财富请求失败: {str(e)}"

def get_stock_data(symbol):
    """获取股票数据 - 多数据源自动切换"""
    errors = []
    
    # 1. 主数据源: 腾讯财经
    data, error = get_stock_data_tencent(symbol)
    if data:
        return data, None
    errors.append(f"腾讯: {error}")
    
    # 2. 备用1: 新浪财经
    data, error = get_stock_data_sina(symbol)
    if data:
        return data, None
    errors.append(f"新浪: {error}")
    
    # 3. 备用2: 东方财富
    data, error = get_stock_data_eastmoney(symbol)
    if data:
        return data, None
    errors.append(f"东财: {error}")
    
    return None, f"所有数据源均失败: {'; '.join(errors)}"

def get_history_data(symbol):
    """获取历史K线数据"""
    try:
        import akshare as ak
        hist = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date="20240101", adjust="qfq")
        return hist, None
    except:
        return None, None

def get_company_profile(symbol):
    """获取公司基本面信息"""
    try:
        import akshare as ak
        profile = ak.stock_individual_info_em(symbol=symbol)
        profile_dict = dict(zip(profile['item'], profile['value']))
        return profile_dict, None
    except:
        return None, None

def get_money_flow(symbol):
    """获取资金流向数据 - akshare"""
    try:
        import akshare as ak
        market = 'sh' if symbol.startswith('6') else 'sz'
        df = ak.stock_individual_fund_flow(stock=symbol, market=market)
        
        if df is None or df.empty:
            return {'status': 'error', 'msg': '暂无数据'}
        
        # 取最新一天的数据
        latest = df.iloc[-1]
        
        main_net = float(latest.get('主力净流入-净额', 0) or 0)
        main_pct = float(latest.get('主力净流入-净占比', 0) or 0)
        super_net = float(latest.get('超大单净流入-净额', 0) or 0)
        big_net = float(latest.get('大单净流入-净额', 0) or 0)
        mid_net = float(latest.get('中单净流入-净额', 0) or 0)
        small_net = float(latest.get('小单净流入-净额', 0) or 0)
        
        return {
            'main_net': main_net,
            'main_pct': main_pct,
            'super_net': super_net,
            'big_net': big_net,
            'mid_net': mid_net,
            'small_net': small_net,
            'date': str(latest.get('日期', '')),
            'status': 'success'
        }
    except Exception as e:
        return {'status': 'error', 'msg': str(e)}

def get_top_shareholders(symbol):
    """获取主要股东 - akshare"""
    try:
        import akshare as ak
        df = ak.stock_main_stock_holder(stock=symbol)
        
        if df is None or df.empty:
            return {'status': 'error', 'msg': '暂无数据'}
        
        # 取前5大股东
        top5 = df.head(5)
        
        result = []
        for idx, row in top5.iterrows():
            holder_name = str(row.get('股东名称', '--'))
            hold_pct = row.get('持股比例')
            hold_num = row.get('持股数量')
            
            # 清理数据
            if holder_name == 'nan' or not holder_name:
                holder_name = '--'
            
            # 格式化持股比例
            try:
                hold_pct = float(hold_pct) if hold_pct and not pd.isna(hold_pct) else 0
                hold_pct_fmt = f"{hold_pct:.2f}%"
            except:
                hold_pct_fmt = '--'
            
            # 格式化持股数量
            try:
                hold_num = float(hold_num) if hold_num and not pd.isna(hold_num) else 0
                if hold_num >= 1e8:
                    hold_num_fmt = f"{hold_num/1e8:.2f}亿股"
                elif hold_num >= 1e4:
                    hold_num_fmt = f"{hold_num/1e4:.2f}万股"
                else:
                    hold_num_fmt = f"{hold_num:.0f}股"
            except:
                hold_num_fmt = '--'
            
            result.append({
                'name': holder_name,
                'pct': hold_pct_fmt,
                'num': hold_num_fmt
            })
        
        return {'status': 'success', 'holders': result}
    except Exception as e:
        return {'status': 'error', 'msg': str(e)}

def calculate_ma(prices, periods=[5, 10, 20, 60]):
    """计算移动平均线"""
    if prices is None or len(prices) == 0:
        return {}
    mas = {}
    for period in periods:
        if len(prices) >= period:
            mas[f'MA{period}'] = prices.tail(period).mean()
    return mas

def calculate_macd(prices):
    """计算MACD"""
    if prices is None or len(prices) < 26:
        return None
    ema_fast = prices.ewm(span=12).mean()
    ema_slow = prices.ewm(span=26).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=9).mean()
    macd = (dif - dea) * 2
    
    current_dif = dif.iloc[-1]
    current_dea = dea.iloc[-1]
    prev_dif = dif.iloc[-2] if len(dif) > 1 else current_dif
    prev_dea = dea.iloc[-2] if len(dea) > 1 else current_dea
    
    signal_type = '金叉✅' if current_dif > current_dea and prev_dif <= prev_dea else '死叉❌' if current_dif < current_dea and prev_dif >= prev_dea else '中性➖'
    
    return {'DIF': current_dif, 'DEA': current_dea, 'MACD': macd.iloc[-1], 'signal': signal_type, 'trend': '看多📈' if current_dif > current_dea else '看空📉'}

def calculate_rsi(prices, period=14):
    """计算RSI"""
    if prices is None or len(prices) < period:
        return None
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def format_cap(cap):
    """格式化市值"""
    if cap is None or cap == 0:
        return "--"
    if cap >= 1e12:
        return f"{cap/1e12:.2f}万亿"
    elif cap >= 1e8:
        return f"{cap/1e8:.2f}亿"
    return f"{cap/1e4:.2f}万"

def format_moneyflow(amount):
    """格式化资金流向金额"""
    if amount is None or amount == 0:
        return "0"
    amount = float(amount)
    if abs(amount) >= 1e8:
        return f"{amount/1e8:.2f}亿"
    elif abs(amount) >= 1e4:
        return f"{amount/1e4:.2f}万"
    return f"{amount:.0f}"

def get_industry(name):
    """检测行业"""
    keywords = {"茅台": "白酒", "五粮液": "白酒", "电力": "电力", "宁德": "新能源", "比亚迪": "新能源", 
                "银行": "银行", "平安": "保险", "中芯": "半导体", "药": "医药", "车": "汽车",
                "重工": "工程机械", "中车": "轨交设备", "电信": "通信", "科技": "科技"}
    for k, v in keywords.items():
        if k in name:
            return v
    return "其他"

def get_policy(industry):
    """获取行业政策"""
    policies = {
        "白酒": {"policy": "消费提振、内需扩张", "trend": "中性偏多", "risk": "消费降级、库存去化", "opportunity": "高端化、国际化"},
        "电力": {"policy": "双碳目标、电力市场化改革", "trend": "利好", "risk": "煤价波动、电价压力", "opportunity": "绿电、储能"},
        "新能源": {"policy": "碳中和、新能源车补贴", "trend": "利好", "risk": "产能过剩、价格战", "opportunity": "技术迭代、出海"},
        "银行": {"policy": "降准降息、地产支持", "trend": "中性", "risk": "息差收窄、不良风险", "opportunity": "财富管理"},
        "半导体": {"policy": "国产替代、大基金", "trend": "利好", "risk": "技术封锁、周期下行", "opportunity": "AI芯片、先进封装"},
        "医药": {"policy": "医保谈判、创新药支持", "trend": "中性", "risk": "集采降价、研发失败", "opportunity": "创新药出海"},
        "工程机械": {"policy": "基建投资、设备更新", "trend": "中性偏多", "risk": "地产投资下滑", "opportunity": "出海、电动化"},
        "轨交设备": {"policy": "高铁建设、一带一路", "trend": "中性偏多", "risk": "投资放缓", "opportunity": "设备更新、维保"},
        "通信": {"policy": "5G建设、数字中国", "trend": "利好", "risk": "CAPEX周期", "opportunity": "算力网络、AI应用"}
    }
    return policies.get(industry, {"policy": "需关注行业政策", "trend": "中性", "risk": "行业竞争", "opportunity": "行业整合"})

def analyze_stock(symbol):
    """股票分析主函数"""
    symbol = str(symbol).replace('.sh', '').replace('.sz', '').replace('.SH', '').replace('.SZ', '').strip()
    
    # 获取数据 - 多数据源自动切换
    data, error = get_stock_data(symbol)
    if error:
        return f"❌ {error}"
    
    # 获取历史数据用于技术指标
    hist_data, _ = get_history_data(symbol)
    
    # 提取数据
    name = data['name']
    code = data['code']
    price = data['price']
    prev_close = data['prev_close']
    open_price = data['open']
    high = data['high']
    low = data['low']
    change = data['change']
    change_pct = data['change_pct']
    amplitude = data.get('amplitude', 0)
    vol_shou = data.get('vol_shou', 0)
    turnover_wan = data.get('turnover_wan', 0)
    turnover_rate = data.get('turnover_rate', 0)
    pe = data.get('pe', 0)
    pb = data.get('pb', 0)
    float_cap = data.get('float_cap', 0)
    total_cap = data.get('total_cap', 0)
    source = data.get('source', 'unknown')
    
    # 数据源标记
    source_tag = {"tencent": "🐧腾讯", "sina": "📰新浪", "eastmoney": "📊东财"}.get(source, "📊")
    
    # 技术指标
    ma = calculate_ma(hist_data['收盘']) if hist_data is not None else {}
    macd = calculate_macd(hist_data['收盘']) if hist_data is not None else None
    rsi = calculate_rsi(hist_data['收盘']) if hist_data is not None else None
    
    # 行业和政策
    industry = get_industry(name)
    policy = get_policy(industry)
    
    # 获取公司基本面
    profile, _ = get_company_profile(symbol)
    
    # 获取资金流向
    money_flow = get_money_flow(symbol)
    
    # 获取主要股东
    top_holders = get_top_shareholders(symbol)
    
    # 生成报告
    report = f"""
{'='*70}
📊 {name} ({code}) 实时行情分析 [{source_tag}数据源]
{'='*70}

【一、实时行情】
💰 当前价格: ¥{price:.2f}
📈 今日涨跌: {change:+.2f} ({change_pct:+.2f}%) {'📈上涨' if change > 0 else '📉下跌' if change < 0 else '➖平盘'}
📊 今日振幅: {amplitude:.2f}%
📊 今日最高: ¥{high:.2f} | 最低: ¥{low:.2f}
📊 昨日收盘: ¥{prev_close:.2f}
📊 今日开盘: ¥{open_price:.2f}

【二、量能指标】
📊 成交量: {vol_shou/10000:.2f}万手
📊 成交额: {turnover_wan/10000:.2f}亿元
📊 换手率: {turnover_rate:.2f}% {'🔥活跃' if turnover_rate > 5 else '➖正常' if turnover_rate > 1 else '📉低迷' if turnover_rate > 0 else '--'}
📊 总市值: {format_cap(total_cap)}
📊 流通市值: {format_cap(float_cap)}

【三、估值指标】
"""
    
    if pe:
        pe_status = "💚低估" if pe < 15 else "💛合理" if pe < 30 else "❤️偏高"
        report += f"📊 动态市盈率: {pe:.2f}倍 [{pe_status}]\n"
    else:
        report += "📊 动态市盈率: --\n"
    
    if pb:
        pb_status = "💚低估" if pb < 1.5 else "💛合理" if pb < 3 else "❤️偏高"
        report += f"📊 市净率: {pb:.2f}倍 [{pb_status}]\n"
    else:
        report += "📊 市净率: --\n"
    
    report += f"""
【四、技术分析】
"""
    
    if ma:
        trend = "多头排列📈" if price > ma.get('MA5',0) > ma.get('MA10',0) > ma.get('MA20',0) else "空头排列📉" if price < ma.get('MA5',0) < ma.get('MA10',0) < ma.get('MA20',0) else "震荡整理➖"
        report += f"""
📈 均线系统:
  • MA5:  ¥{ma.get('MA5',0):.2f} {'✅' if price > ma.get('MA5',0) else '❌'}
  • MA10: ¥{ma.get('MA10',0):.2f} {'✅' if price > ma.get('MA10',0) else '❌'}
  • MA20: ¥{ma.get('MA20',0):.2f} {'✅' if price > ma.get('MA20',0) else '❌'}
  • MA60: ¥{ma.get('MA60',0):.2f} {'✅' if price > ma.get('MA60',0) else '❌'}
  • 趋势: {trend}
"""
    
    if macd:
        report += f"""
📊 MACD:
  • DIF: {macd['DIF']:.3f} | DEA: {macd['DEA']:.3f} | 柱: {macd['MACD']:.3f}
  • 信号: {macd['signal']} | 趋势: {macd['trend']}
"""
    
    if rsi:
        rsi_status = "超买⚠️" if rsi > 70 else "超卖💡" if rsi < 30 else "中性➖"
        report += f"📊 RSI: {rsi:.1f} ({rsi_status})\n"
    
    report += f"""
【五、公司基本面】
"""
    
    if profile:
        total_shares = profile.get('总股本', 0)
        float_shares = profile.get('流通股', 0)
        try:
            total_shares_fmt = f"{float(total_shares)/1e8:.2f}亿股" if float(total_shares) > 1e8 else f"{float(total_shares)/1e4:.2f}万股"
            float_shares_fmt = f"{float(float_shares)/1e8:.2f}亿股" if float(float_shares) > 1e8 else f"{float(float_shares)/1e4:.2f}万股"
        except:
            total_shares_fmt = str(total_shares)
            float_shares_fmt = str(float_shares)
        
        list_date = profile.get('上市时间', '--')
        if list_date and len(str(list_date)) == 8:
            list_date = f"{str(list_date)[:4]}-{str(list_date)[4:6]}-{str(list_date)[6:8]}"
        
        business = profile.get('主营业务', '--')
        if business and len(str(business)) > 80:
            business = str(business)[:80] + "..."
        
        report += f"""
📋 公司概况:
  • 公司全称: {profile.get('公司名称', profile.get('证券简称', '--'))}
  • 所属行业: {profile.get('所属行业', profile.get('行业', '--'))}
  • 主营业务: {business}
  • 上市日期: {list_date}
  • 总股本: {total_shares_fmt}
  • 流通股: {float_shares_fmt}
"""
    else:
        report += "📋 公司概况: 数据暂不可用\n"
    
    report += f"""
【六、行业分析】
🏭 所属行业: {industry}
📜 政策环境: {policy['policy']}
📈 行业趋势: {policy['trend']}
⚠️ 行业风险: {policy['risk']}
💡 行业机会: {policy['opportunity']}
"""
    
    # 综合评分
    score = 50
    reasons = []
    
    if pe and 0 < pe < 30:
        score += 10
        reasons.append("估值合理")
    if macd and '金叉' in macd['signal']:
        score += 10
        reasons.append("MACD金叉")
    if rsi and 40 < rsi < 60:
        score += 5
        reasons.append("RSI健康")
    if policy['trend'] == '利好':
        score += 10
        reasons.append("政策利好")
    
    score = min(100, score)
    
    if score >= 75:
        rating = "买入 ⭐⭐⭐"
    elif score >= 60:
        rating = "增持 ⭐⭐"
    elif score >= 45:
        rating = "持有 ⭐"
    else:
        rating = "观望 ⚠️"
    
    report += f"""
【七、综合投资建议】
⭐ 综合评分: {score}/100
📊 投资评级: {rating}
✅ 积极因素: {' | '.join(reasons) if reasons else '暂无'}

💡 操作建议:
  • 短线 (1-4周): {'积极关注' if score >= 65 else '谨慎' if score < 45 else '观望'}
  • 中线 (1-6月): {'配置' if score >= 60 else '等待'}
  • 长线 (6月+): {'持有' if score >= 60 else '观察'}

{'='*70}

【八、资金流向】
"""
    
    # 资金流向
    if money_flow and money_flow.get('status') == 'success':
        main_net = money_flow.get('main_net', 0)
        main_pct = money_flow.get('main_pct', 0)
        
        if main_net > 0:
            flow_status = "净流入 📈"
            flow_emoji = "🟢"
        elif main_net < 0:
            flow_status = "净流出 📉"
            flow_emoji = "🔴"
        else:
            flow_status = "持平 ➖"
            flow_emoji = "🟡"
        
        report += f"""
💰 主力资金动向 ({flow_emoji}{flow_status}):
  • 主力净流入: {format_moneyflow(main_net)} ({main_pct:+.2f}%)
  • 超大单净流入: {format_moneyflow(money_flow.get('super_net', 0))}
  • 大单净流入: {format_moneyflow(money_flow.get('big_net', 0))}
  • 中单净流入: {format_moneyflow(money_flow.get('mid_net', 0))}
  • 小单净流入: {format_moneyflow(money_flow.get('small_net', 0))}
"""
    else:
        report += "\n💰 资金流向数据暂不可用\n"
    
    report += f"""
{'='*70}

【九、主要股东】
"""
    
    # 主要股东
    if top_holders and top_holders.get('status') == 'success':
        holders = top_holders.get('holders', [])
        if holders:
            report += f"""
🏢 前五大流通股东:
"""
            for i, holder in enumerate(holders, 1):
                report += f"  {i}. {holder['name']} - 持股{holder['pct']} ({holder['num']})\n"
        else:
            report += "\n🏢 流通股东数据暂不可用\n"
    else:
        report += "\n🏢 流通股东数据暂不可用\n"
    
    report += f"""
{'='*70}

⚠️ 风险提示:
  • 以上分析仅供参考，不构成投资建议
  • 股市有风险，投资需谨慎
  • 数据来源: {source_tag} (多源自动切换)

{'='*70}
"""
    
    return report

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 stock_analyzer_v4.py <stock_code>")
        print("Example: python3 stock_analyzer_v4.py 600519")
        sys.exit(1)
    
    symbol = sys.argv[1]
    result = analyze_stock(symbol)
    print(result)
