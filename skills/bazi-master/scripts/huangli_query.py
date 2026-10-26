#!/usr/bin/env python3
"""
【开源配置说明】
本脚本使用以下环境变量（必需）：
  HUANGLI_KEY - 黄历API密钥，申请地址：https://api.t1qq.com/
  BAIDU_AK    - 百度地图AK，申请地址：https://lbsyun.baidu.com/
"""

import os

# ===== 开源用户请设置以下环境变量 =====
HUANGLI_KEY = os.environ.get("HUANGLI_KEY", "YOUR_HUANGLI_KEY")
BAIDU_AK    = os.environ.get("BAIDU_AK", "YOUR_BAIDU_AK")
# =====================================

"""
黄历查询 + 八字排盘脚本
支持真太阳时校正
用法:
  query(date_str)  - 查日期（北京时间）
  query_bazi(date_str, birth_time_str, location)
    date_str: "YYYY-MM-DD"
    birth_time_str: "HH:MM"（北京时间）
    location: 地址字符串
"""


# 十二时辰对应的Hour GanZhi（北京时间23:00开始为子时）
# 时柱表：23-1子时，1-3丑时，3-5寅时，5-7卯时...
HOUR_GANZHI = [
    (23, "子"), (1, "子"),   # 子时 23-1
    (1, "丑"), (3, "丑"),    # 丑时 1-3
    (3, "寅"), (5, "寅"),    # 寅时 3-5
    (5, "卯"), (7, "卯"),    # 卯时 5-7
    (7, "辰"), (9, "辰"),    # 辰时 7-9
    (9, "巳"), (11, "巳"),   # 巳时 9-11
    (11, "午"), (13, "午"),  # 午时 11-13
    (13, "未"), (15, "未"),  # 未时 13-15
    (15, "申"), (17, "申"),  # 申时 15-17
    (17, "酉"), (19, "酉"),  # 酉时 17-19
    (19, "戌"), (21, "戌"),  # 戌时 19-21
    (21, "亥"), (23, "亥"),  # 亥时 21-23
]

# 时柱天干表（五虎遁起时）
# 日干决定时干：甲己日起甲子，乙庚日起丙子，丙辛日起戊子，丁壬日起庚子，戊癸日起壬子
DAY_STEM_TO_HOUR_START = {
    "甲": "甲", "己": "甲",
    "乙": "丙", "庚": "丙",
    "丙": "戊", "辛": "戊",
    "丁": "庚", "壬": "庚",
    "戊": "壬", "癸": "壬",
}
TIANGAN = "甲乙丙丁戊己庚辛壬癸"
TG_IDX = {g: i for i, g in enumerate(TIANGAN)}
DIZHI = "子丑寅卯辰巳午未申酉戌亥"
DZ_IDX = {z: i for i, z in enumerate(DIZHI)}


def get_hour_ganzhi(day_stem, hour_minutes):
    """
    根据日干和北京时间分钟数计算时柱干支
    hour_minutes: 0-1439（从0:00开始的分钟数）
    """
    # 确定时辰（12个时辰，每2小时一个）
    # 子时: 23-1, 丑时: 1-3, 寅时: 3-5 ... 亥时: 21-23
    if hour_minutes >= 23 * 60 or hour_minutes < 1 * 60:
        zhi = "子"
    elif hour_minutes < 3 * 60:
        zhi = "丑"
    elif hour_minutes < 5 * 60:
        zhi = "寅"
    elif hour_minutes < 7 * 60:
        zhi = "卯"
    elif hour_minutes < 9 * 60:
        zhi = "辰"
    elif hour_minutes < 11 * 60:
        zhi = "巳"
    elif hour_minutes < 13 * 60:
        zhi = "午"
    elif hour_minutes < 15 * 60:
        zhi = "未"
    elif hour_minutes < 17 * 60:
        zhi = "申"
    elif hour_minutes < 19 * 60:
        zhi = "酉"
    elif hour_minutes < 21 * 60:
        zhi = "戌"
    else:
        zhi = "亥"

    # 起时口诀：日干决定时干起点
    start_gan = DAY_STEM_TO_HOUR_START.get(day_stem, "甲")
    start_gan_idx = TG_IDX[start_gan]
    zhi_idx = DZ_IDX[zhi]
    # 时干 = (起时干index + 时辰index) % 10
    offset = (zhi_idx - DZ_IDX["子"] + 12) % 12  # 0-11
    gan_idx = (start_gan_idx + offset) % 10
    return TIANGAN[gan_idx] + zhi


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
    """时差方程（Equation of Time），单位分钟"""
    import math
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    year = dt.year
    from datetime import date as date_class
    n = (date_class(year, dt.month, dt.day) - date_class(year, 1, 1)).days + 1
    B = 2 * math.pi * (n - 81) / 365
    return 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)


def true_solar_adjustment(lng, date_str=None):
    """
    计算真太阳时校正分钟
    = 经度校正 + 时差方程
    date_str: YYYY-MM-DD，可选
    """
    if lng is None:
        return 0
    lng_adj = (lng - 120.0) * 4
    eot_adj = equation_of_time(date_str) if date_str else 0
    return lng_adj + eot_adj


def query(date_str, birth_time_str=None, location=None, lunar=False):
    """
    主查询函数
    date_str: "YYYY-MM-DD"
    birth_time_str: "HH:MM" 可选
    location: 地址字符串 可选（需要 birth_time_str 同时提供才生效）
    lunar: False=阳历（默认），True=阴历（自动转阳历后查询）
    """
    # 阴历转阳历
    if lunar:
        import sys
        from lunardate import LunarDate
        y, m, d = map(int, date_str.split('-'))
        solar = LunarDate(y, m, d).toSolarDate()
        date_str = f"{solar.year:04d}-{solar.month:02d}-{solar.day:02d}"
    year, month, day = date_str.split('-')
    url = "https://api.t1qq.com/api/tool/day/time"
    params = {"key": HUANGLI_KEY, "y": year, "m": month, "d": day}
    r = requests.get(url, params=params, timeout=10)
    data = r.json()
    if data.get("code") != 200:
        return None

    dd = data.get("data", {})
    bz = dd.get("baizi", {})
    na = dd.get("naYin", {})
    jq = dd.get("jieQi", {}).get("next", {})
    xk = dd.get("xunKong", {})

    # 解析阴历月份
    lunar_str = dd.get("lunar", "")
    lunar_month = None
    if lunar_str:
        import re
        if '十一月' in lunar_str:
            lunar_month = 11
        elif '十二月' in lunar_str:
            lunar_month = 12
        else:
            month_map = {'正':1,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}
            m = re.search(r'([正一二三四五六七八九]+)月', lunar_str)
            if m:
                mc = m.group(1)
                lunar_month = month_map.get(mc[0])

    result = {
        "yearGanZhi": bz.get("year", ""),
        "monthGanZhi": bz.get("month", ""),
        "dayGanZhi": bz.get("day", ""),
        "hourGanZhi": bz.get("hour", ""),
        "yearNayin": na.get("year", ""),
        "monthNayin": na.get("month", ""),
        "dayNayin": na.get("day", ""),
        "hourNayin": na.get("hour", ""),
        "jieQiNext": jq.get("qi", ""),
        "jieQiNextTime": jq.get("time", ""),
        "xunKongDay": xk.get("day", ""),
        "lunarMonth": lunar_month,
        "lunarString": lunar_str,
        "raw": data,
    }

    # 真太阳时校正（可选）
    # 条件：有出生时间 + 有地点 + 有有效的BAIDU_AK
    if birth_time_str and location and BAIDU_AK not in ("", "YOUR_BAIDU_AK"):
        lng, lat = geocode(location)
        if lng is not None and lat is not None:
            adjust_min = true_solar_adjustment(lng, date_str)
            h, m = map(int, birth_time_str.split(":"))
            total_min = h * 60 + m
            adjusted_min = (total_min + int(adjust_min)) % 1440
            adj_h = adjusted_min // 60
            adj_m = adjusted_min % 60

            day_stem = result["dayGanZhi"][0]
            correct_hour_gz = get_hour_ganzhi(day_stem, adjusted_min)

            result["adjustedTime"] = f"{adj_h:02d}:{adj_m:02d}"
            result["hourGanZhi"] = correct_hour_gz
            result["hourNayin"] = na.get("hour", "")
            result["longitude"] = lng
            result["latitude"] = lat
            result["adjustmentMinutes"] = adjust_min
            result["location"] = location
        else:
            # geocode失败，跳过校正，用API原始时柱
            result["location"] = location
            result["adjustedTime"] = None
    else:
        # 无地点或无BAIDU_AK，跳过校正，用API原始时柱
        if location:
            result["location"] = location

    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2:
        date = sys.argv[1]
        time_str = sys.argv[2] if len(sys.argv) > 2 else None
        loc = sys.argv[3] if len(sys.argv) > 3 else None
        r = query(date, time_str, loc)
        if r:
            print(f"年柱: {r['yearGanZhi']} ({r['yearNayin']})")
            print(f"月柱: {r['monthGanZhi']} ({r['monthNayin']})")
            print(f"日柱: {r['dayGanZhi']} ({r['dayNayin']})")
            if "hourGanZhi" in r:
                print(f"时柱: {r['hourGanZhi']} ({r['hourNayin']})")
            if "adjustedTime" in r:
                print(f"真太阳时: {r['adjustedTime']}（原始{time_str}，校正{r['adjustmentMinutes']:+.0f}分钟）")
    else:
        print("用法: python huangli_query.py YYYY-MM-DD [HH:MM] [地址]")
