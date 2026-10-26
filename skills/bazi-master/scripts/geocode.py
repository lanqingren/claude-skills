#!/usr/bin/env python3
"""
百度地理编码 + 真太阳时校正
输入: 地址字符串 或 (经度, 纬度)
输出: 经纬度 + 校正分钟数

【开源配置】请设置环境变量 BAIDU_AK
"""

import os
import requests

BAIDU_AK = os.environ.get("BAIDU_AK", "YOUR_BAIDU_AK")

def geocode(address):
    """将地址解析为经纬度"""
    url = "https://api.map.baidu.com/geocoding/v3/"
    params = {"address": address, "ak": BAIDU_AK, "output": "json"}
    try:
        r = requests.get(url, params=params, timeout=10)
        d = r.json()
        if d.get("status") == 0:
            loc = d["result"]["location"]
            return loc["lng"], loc["lat"]
    except:
        pass
    return None, None


def equation_of_time(date_str):
    """
    计算时差方程（Equation of Time）
    单位：分钟
    正值=真太阳时快于平太阳时，负值=慢于平太阳时
    """
    from datetime import datetime
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    N = (dt.month, dt.day)  # (month, day) for lookup
    # 查表法：一年中各天的时差（分钟），简化版
    # Keys: (月, 日) -> EoT(分钟)
    # 精确值来自天文计算，可用以下近似
    import math
    year = dt.year
    # 计算该年在365/366天中的序号
    days_in_year = 366 if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0) else 365
    # 儒略日计算
    from datetime import date as date_class
    n = (date_class(year, dt.month, dt.day) - date_class(year, 1, 1)).days + 1
    
    # 时差方程近似公式（ radians ）
    # EoT = 9.87*sin(2B) - 7.53*cos(B) - 1.5*sin(B)
    # B = 360°*(n - 81) / 365
    B = 2 * math.pi * (n - 81) / 365
    eot = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)
    return eot


def true_solar_adjustment(lng, date_str=None, beijing_lng=120.0):
    """
    计算真太阳时校正分钟
    公式: (当地经度 - 120) × 4分钟 + 时差方程
    date_str: YYYY-MM-DD，可选
    """
    if lng is None:
        return 0
    lng_adj = (lng - beijing_lng) * 4
    eot_adj = equation_of_time(date_str) if date_str else 0
    return lng_adj + eot_adj


def adjust_birth_time(birth_time_str, lng):
    """
    校正出生时间
    birth_time_str: "HH:MM" 格式（北京时间）
    lng: 出生地经度
    返回: 校正后的 "HH:MM"
    """
    from datetime import datetime, timedelta
    adjust_min = true_solar_adjustment(lng)
    try:
        h, m = map(int, birth_time_str.split(":"))
        dt = datetime(2000, 1, 1, h, m) + timedelta(minutes=adjust_min)
        return dt.strftime("%H:%M")
    except:
        return birth_time_str


if __name__ == "__main__":
    # 用法示例
    print(geocode("北京"))
    print(adjust_birth_time("14:30", 116.4))
