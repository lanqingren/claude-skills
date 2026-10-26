#!/usr/bin/env python3
"""
大运计算脚本 - 黄历API版本

核心逻辑（来自JS源码 dayun-calculator.js）：
1. 顺排：出生日 → 找下一个12节 → 天数÷3 = 起运年龄
2. 逆排：出生日 → 找上一个12节 → 天数÷3 = 起运年龄
3. 大运序列：顺排+1，逆排-1，循环%10/%12

节气获取：黄历API（支持精确节气时间查询）
"""

import os
import requests
from datetime import datetime, timedelta

# 【开源配置】请设置环境变量：HUANGLI_KEY（必选）、BAIDU_AK（可选，真太阳时校正用）
HUANGLI_KEY = os.environ.get("HUANGLI_KEY", "YOUR_HUANGLI_KEY")
BAIDU_AK    = os.environ.get("BAIDU_AK", "YOUR_BAIDU_AK")
HUANGLI_URL = "https://api.t1qq.com/api/tool/day/time"

TIANGAN = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
DIZHI   = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
TG = {g: i for i, g in enumerate(TIANGAN)}
DZ = {z: i for i, z in enumerate(DIZHI)}

DAYUN_JIEQI_SET = {
    "立春","惊蛰","清明","立夏","芒种","小暑",
    "立秋","白露","寒露","立冬","大雪","小寒"
}


def is_twelve_jie(name):
    return name in DAYUN_JIEQI_SET


def get_jieqi_from_api(y, m, d):
    """从黄历API获取节气信息"""
    params = {'key': HUANGLI_KEY, 'y': str(y), 'm': str(m), 'd': str(d)}
    r = requests.get(HUANGLI_URL, params=params, timeout=10)
    data = r.json()
    if data.get('code') != 200:
        return None, None
    dd = data.get('data', {})
    jq = dd.get('jieQi', {})
    prev = jq.get('prev', {})
    next_jq = jq.get('next', {})
    return prev, next_jq


def find_next_jie(birth_dt, depth=0):
    """
    顺排：往后找最近的有效节气（12节之一）。
    使用黄历API。
    """
    if depth > 30:
        return "小寒", None

    prev, next_jq = get_jieqi_from_api(birth_dt.year, birth_dt.month, birth_dt.day)
    if not next_jq:
        return "小寒", None

    next_name = next_jq.get('qi', '')
    next_time_str = next_jq.get('time', '')

    if not next_time_str or not next_name:
        return "小寒", None

    next_dt = datetime.strptime(next_time_str, '%Y-%m-%d %H:%M:%S')

    if is_twelve_jie(next_name):
        return next_name, next_dt

    # 不是12节，用节气时间+1天继续查（确保进入下一天）
    return find_next_jie(next_dt + timedelta(days=1), depth + 1)


def find_prev_jie(birth_dt, depth=0):
    """
    逆排：往前找最近的有效节气（12节之一）。
    使用黄历API。
    """
    if depth > 30:
        return "立春", None

    prev, next_jq = get_jieqi_from_api(birth_dt.year, birth_dt.month, birth_dt.day)
    if not prev:
        return "立春", None

    prev_name = prev.get('qi', '')
    prev_time_str = prev.get('time', '')

    if not prev_time_str or not prev_name:
        # 往前退一个月再试
        return find_prev_jie(birth_dt - timedelta(days=30), depth + 1)

    prev_dt = datetime.strptime(prev_time_str, '%Y-%m-%d %H:%M:%S')

    if is_twelve_jie(prev_name):
        return prev_name, prev_dt

    # 不是12节，往前推1天再查
    return find_prev_jie(prev_dt - timedelta(days=1), depth + 1)


def determine_direction(year_gan, gender):
    """大运方向判断（同性相从）"""
    is_yang = TG[year_gan] % 2 == 0
    is_male = gender == "男"
    if (is_yang and is_male) or (not is_yang and not is_male):
        return "顺排"
    return "逆排"


def calc_start_age(birth_date, target_jieqi_date, lunar_month=None):
    """
    精确计算起运年龄和起运日期
    公式: 天数差 / 3 = 起运年龄（岁）
    
    阴历11月或12月出生: 不+1，直接取整数部分
    其他月份: +1
    
    起运日期 = 出生日期 + (起运年龄 × 365天)
    
    返回: (大运起始年龄, 总天数差, qiyun_age, 起运日期)
    """
    if target_jieqi_date is None:
        return 8, 0.0, 8.0, None

    ms_diff = abs((target_jieqi_date - birth_date).total_seconds() * 1000)
    days_exact = ms_diff / 86400000.0

    if days_exact <= 0:
        return 8, 0.0, 8.0, None

    # 核心公式: 天数差 / 3 = 起运年龄（岁）
    qiyun_age = days_exact / 3.0
    
    # 阴历11月或12月: 不+1；其他月份: +1
    if lunar_month in (11, 12):
        start_age = int(qiyun_age)
    else:
        start_age = int(qiyun_age) + 1
    
    # 起运日期 = 出生日期 + (qiyun_age × 365天)
    qiyun_start_date = birth_date + timedelta(days=qiyun_age * 365)

    return start_age, round(days_exact, 2), round(qiyun_age, 4), qiyun_start_date


def get_year_ganzhi_from_api(birth_date):
    """从黄历API获取年柱（自动处理立春分界）"""
    y, m, d = birth_date.year, birth_date.month, birth_date.day
    params = {'key': HUANGLI_KEY, 'y': str(y), 'm': str(m), 'd': str(d)}
    r = requests.get(HUANGLI_URL, params=params, timeout=10)
    data = r.json()
    if data.get('code') != 200:
        return None
    dd = data.get('data', {})
    bz = dd.get('baizi', {})
    year_gz = bz.get('year', '')
    return year_gz


def get_bazi_from_api(birth_date_str):
    """从黄历API获取完整八字（自动处理立春分界）"""
    y, m, d = birth_date_str[:4], birth_date_str[5:7], birth_date_str[8:10]
    params = {'key': HUANGLI_KEY, 'y': y, 'm': m, 'd': d}
    r = requests.get(HUANGLI_URL, params=params, timeout=10)
    data = r.json()
    if data.get('code') != 200:
        return None
    bz = data.get('data', {}).get('baizi', {})
    return {
        'year_ganzhi': bz.get('year', ''),
        'month_ganzhi': bz.get('month', ''),
        'day_ganzhi': bz.get('day', ''),
        'hour_ganzhi': bz.get('hour', ''),
    }


def calculate_dayun_full(birth_date_str, year_gan=None, month_gan=None, month_zhi=None, gender='男', birth_time_str=None, location=None, lunar_month=None):
    """
    完整大运计算入口
    新策略: 直接给出起运日期和每步大运的日期范围，不再用"几岁"来标注
    """
    # 解析出生日期和时间
    birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
    if birth_time_str:
        try:
            h, m = map(int, birth_time_str.split(':'))
            birth_date = birth_date.replace(hour=h, minute=m)
        except:
            pass  # 保持午夜00:00
    
    # 如果没有传入年柱/月柱，从黄历API获取（自动处理立春分界）
    if not year_gan or not month_gan or not month_zhi:
        bazi = get_bazi_from_api(birth_date_str)
        if bazi:
            year_gan = bazi['year_ganzhi'][0] if not year_gan else year_gan
            month_gan = bazi['month_ganzhi'][0] if not month_gan else month_gan
            month_zhi = bazi['month_ganzhi'][1] if not month_zhi else month_zhi
    
    direction = determine_direction(year_gan, gender)
    month_stem_idx = TG[month_gan]
    month_branch_idx = DZ[month_zhi]

    # 找节气
    if direction == "顺排":
        jq_name, jq_dt = find_next_jie(birth_date)
    else:
        jq_name, jq_dt = find_prev_jie(birth_date)

    # 计算起运年龄和起运日期
    start_age, days_diff, qiyun_age, qiyun_start_date = calc_start_age(birth_date, jq_dt, lunar_month)

    # 推算10步大运，以实际日期为准
    all_dayuns = []
    for i in range(10):
        if direction == "顺排":
            gan_idx = (month_stem_idx + i + 1) % 10
            zhi_idx = (month_branch_idx + i + 1) % 12
        else:
            gan_idx = (month_stem_idx - (i + 1) + 10) % 10
            zhi_idx = (month_branch_idx - (i + 1) + 12) % 12

        gan = TIANGAN[gan_idx]
        zhi = DIZHI[zhi_idx]
        ganzhi = gan + zhi

        # 每步大运从起运日开始，每步加10年
        decade_start_date = qiyun_start_date + timedelta(days=i * 10 * 365)
        decade_end_date = decade_start_date + timedelta(days=10 * 365 - 1)

        all_dayuns.append({
            'index': i + 1,
            'ganzhi': ganzhi,
            'start_date': decade_start_date.strftime('%Y-%m-%d'),
            'end_date': decade_end_date.strftime('%Y-%m-%d'),
        })

    return {
        'direction': direction,
        'jq_name': jq_name,
        'jq_dt': jq_dt,
        'start_age': start_age,
        'days_diff': days_diff,
        'qiyun_age': qiyun_age,
        'qiyun_start_date': qiyun_start_date.strftime('%Y-%m-%d') if qiyun_start_date else None,
        'dayuns': all_dayuns,
    }



