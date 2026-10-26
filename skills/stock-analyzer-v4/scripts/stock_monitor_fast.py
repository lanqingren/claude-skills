#!/usr/bin/env python3
"""
股票快速扫描监控 - V1.0
多API轮询 + 轻量级实时数据获取
Usage: python3 stock_monitor_fast.py [stock_list_file]
"""

import sys
import requests
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# ============ 多API配置 ============
API_SOURCES = [
    {
        'name': '腾讯财经',
        'url': 'https://qt.gtimg.cn/q={symbol}',
        'timeout': 5,
        'parser': 'tencent'
    },
    {
        'name': '新浪财经',
        'url': 'https://hq.sinajs.cn/list={symbol}',
        'timeout': 5,
        'parser': 'sina',
        'headers': {'Referer': 'https://finance.sina.com.cn'}
    },
    {
        'name': '东方财富',
        'url': 'https://push2.eastmoney.com/api/qt/stock/get?ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&volt=2&fields=f43,f44,f45,f46,f47,f48,f57,f58,f60,f162,f167,f173,f20,f21,f168,f169,f170,f171&secid={secid}',
        'timeout': 5,
        'parser': 'eastmoney'
    }
]

def get_symbol_prefix(symbol):
    """获取市场前缀"""
    return 'sh' if symbol.startswith('6') else 'sz'

def get_secid(symbol):
    """东方财富专用ID格式"""
    return f"{'1' if symbol.startswith('6') else '0'}.{symbol}"

def parse_tencent(data_str):
    """解析腾讯数据"""
    try:
        if '~' not in data_str:
            return None
        parts = data_str.split('"')[1].split('~')
        price = float(parts[3])
        prev_close = float(parts[4])
        change_pct = float(parts[32])
        turnover_rate = float(parts[38]) if parts[38] else 0
        volume_ratio = float(parts[49]) if len(parts) > 49 and parts[49] else 1.0
        
        return {
            'name': parts[1],
            'code': parts[2],
            'price': price,
            'change_pct': change_pct,
            'turnover_rate': turnover_rate,
            'volume_ratio': volume_ratio,
            'high': float(parts[33]),
            'low': float(parts[34]),
            'source': '腾讯'
        }
    except:
        return None

def parse_sina(data_str):
    """解析新浪数据"""
    try:
        parts = data_str.split('"')[1].split(',')
        price = float(parts[3])
        prev_close = float(parts[2])
        change_pct = (price - prev_close) / prev_close * 100 if prev_close else 0
        
        return {
            'name': parts[0],
            'price': price,
            'change_pct': change_pct,
            'turnover_rate': 0,  # 新浪不提供
            'volume_ratio': 1.0,  # 新浪不提供
            'high': float(parts[4]),
            'low': float(parts[5]),
            'source': '新浪'
        }
    except:
        return None

def parse_eastmoney(json_data):
    """解析东方财富数据"""
    try:
        d = json_data.get('data', {})
        price = float(d.get('f43', 0)) / 100  # 东财价格需要除以100
        prev_close = float(d.get('f60', 0)) / 100
        change_pct = (float(d.get('f170', 0)))  # 涨跌幅
        turnover_rate = float(d.get('f168', 0))
        volume_ratio = float(d.get('f50', 0)) if d.get('f50') else 1.0
        
        return {
            'name': d.get('f58', ''),
            'price': price,
            'change_pct': change_pct,
            'turnover_rate': turnover_rate,
            'volume_ratio': volume_ratio,
            'high': float(d.get('f44', 0)) / 100,
            'low': float(d.get('f45', 0)) / 100,
            'source': '东财'
        }
    except:
        return None

def fetch_stock_data(symbol, api_config):
    """从指定API获取数据"""
    try:
        url = api_config['url'].format(
            symbol=get_symbol_prefix(symbol) + symbol,
            secid=get_secid(symbol)
        )
        headers = api_config.get('headers', {})
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        
        resp = requests.get(url, headers=headers, timeout=api_config['timeout'])
        
        parser = api_config['parser']
        if parser == 'tencent':
            data = parse_tencent(resp.text)
        elif parser == 'sina':
            data = parse_sina(resp.text)
        elif parser == 'eastmoney':
            data = parse_eastmoney(resp.json())
        else:
            data = None
            
        if data:
            data['code'] = symbol
            return data, None
        return None, f"{api_config['name']}解析失败"
    except Exception as e:
        return None, f"{api_config['name']}: {str(e)[:30]}"

def get_stock_data_multi_api(symbol):
    """多API轮询获取数据"""
    errors = []
    
    for api in API_SOURCES:
        data, error = fetch_stock_data(symbol, api)
        if data:
            return data, None
        errors.append(error)
        time.sleep(0.1)  # 短暂延迟避免请求过快
    
    return None, f"所有API失败: {'; '.join(errors)}"

def check_anomaly(data):
    """检查异常条件"""
    anomalies = []
    
    change_pct = data.get('change_pct', 0)
    volume_ratio = data.get('volume_ratio', 1.0)
    turnover_rate = data.get('turnover_rate', 0)
    
    # 条件1: 涨跌幅超过 ±5%
    if abs(change_pct) >= 5:
        direction = '大涨📈' if change_pct > 0 else '大跌📉'
        anomalies.append(f"{direction} {change_pct:+.2f}%")
    
    # 条件2: 量比 >= 2
    if volume_ratio >= 2:
        anomalies.append(f"放量⚡ 量比{volume_ratio:.1f}")
    
    # 条件3: 换手率 > 10%（活跃）
    if turnover_rate >= 10:
        anomalies.append(f"高换手🔥 {turnover_rate:.1f}%")
    
    return anomalies

def scan_single_stock(symbol):
    """扫描单只股票"""
    data, error = get_stock_data_multi_api(symbol)
    if data is None:
        return {'code': symbol, 'error': error, 'anomalies': []}
    
    anomalies = check_anomaly(data)
    return {
        'code': symbol,
        'name': data.get('name', ''),
        'price': data.get('price', 0),
        'change_pct': data.get('change_pct', 0),
        'source': data.get('source', ''),
        'anomalies': anomalies
    }

def scan_stocks(stock_list, max_workers=10):
    """并行扫描多只股票"""
    results = []
    errors = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {
            executor.submit(scan_single_stock, symbol): symbol 
            for symbol in stock_list
        }
        
        for future in as_completed(future_to_symbol):
            result = future.result()
            if result.get('error'):
                errors.append(f"{result['code']}: {result['error']}")
            results.append(result)
    
    return results, errors

def load_stock_list(filepath):
    """从文件加载股票列表"""
    stocks = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and line[:6].isdigit():
                    stocks.append(line[:6])
    except FileNotFoundError:
        print(f"错误: 找不到文件 {filepath}")
        sys.exit(1)
    return stocks

def main():
    # 获取股票列表
    if len(sys.argv) > 1:
        stock_file = sys.argv[1]
    else:
        stock_file = '/root/.openclaw/workspace/memory/stock_watchlist.md'
    
    print(f"📊 股票快速扫描监控")
    print(f"📁 股票列表: {stock_file}")
    print(f"⏰ 扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 加载股票列表
    stock_list = load_stock_list(stock_file)
    print(f"📝 共加载 {len(stock_list)} 只股票\n")
    
    # 开始扫描
    start_time = time.time()
    results, errors = scan_stocks(stock_list)
    scan_time = time.time() - start_time
    
    # 分析结果
    anomaly_stocks = [r for r in results if r.get('anomalies')]
    success_count = len([r for r in results if not r.get('error')])
    
    print(f"✅ 扫描完成: {success_count}/{len(stock_list)} 只成功")
    print(f"⏱️ 耗时: {scan_time:.1f}秒")
    print(f"🔍 发现异常: {len(anomaly_stocks)} 只\n")
    
    # 输出异常股票
    if anomaly_stocks:
        print("🚨 异常波动股票列表:")
        print("-" * 60)
        for stock in sorted(anomaly_stocks, key=lambda x: abs(x.get('change_pct', 0)), reverse=True):
            anomalies = ' | '.join(stock['anomalies'])
            change_str = f"{stock['change_pct']:+.2f}%"
            print(f"  {stock['code']} {stock['name'][:8]:<8} ¥{stock['price']:<7} {change_str:<8} ({stock['source']}) {anomalies}")
        print()
    
    # 输出失败记录
    if errors:
        print(f"⚠️ 获取失败 ({len(errors)}只):")
        for err in errors[:5]:  # 只显示前5个错误
            print(f"  {err}")
        if len(errors) > 5:
            print(f"  ... 还有 {len(errors)-5} 个")
        print()
    
    # 生成简报摘要
    print("=" * 60)
    print("📋 监控简报摘要")
    print("-" * 60)
    
    # 涨跌统计
    up_count = len([r for r in results if r.get('change_pct', 0) > 0])
    down_count = len([r for r in results if r.get('change_pct', 0) < 0])
    flat_count = len([r for r in results if r.get('change_pct', 0) == 0])
    
    print(f"  上涨: {up_count}只 | 下跌: {down_count}只 | 平盘: {flat_count}只")
    
    # 涨跌幅前5
    valid_results = [r for r in results if r.get('price')]
    if valid_results:
        print(f"\n  📈 涨幅前3:")
        for r in sorted(valid_results, key=lambda x: x.get('change_pct', 0), reverse=True)[:3]:
            print(f"     {r['code']} {r['name'][:8]:<8} +{r['change_pct']:.2f}%")
        
        print(f"\n  📉 跌幅前3:")
        for r in sorted(valid_results, key=lambda x: x.get('change_pct', 0))[:3]:
            print(f"     {r['code']} {r['name'][:8]:<8} {r['change_pct']:.2f}%")
    
    # 输出JSON格式（供其他程序解析）
    output = {
        'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_stocks': len(stock_list),
        'success_count': success_count,
        'anomaly_count': len(anomaly_stocks),
        'scan_duration': round(scan_time, 2),
        'anomaly_stocks': anomaly_stocks,
        'errors': errors[:10]
    }
    
    # 保存结果到文件
    output_file = '/tmp/stock_monitor_result.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n💾 详细结果已保存: {output_file}")
    
    return output

if __name__ == '__main__':
    main()
