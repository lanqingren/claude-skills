#!/usr/bin/env python3
"""
十二长生查表脚本
输入: 天干 + 地支
输出: 该天干在地支的长生状态
"""

STAGES = ["长生","沐浴","冠带","临官","帝旺","衰","病","死","墓","绝","胎","养"]

# 各天干长生位（地支序号：子0丑1寅2卯3辰4巳5午6未7申8酉9戌10亥11）
CHANGSHENG_ZHI = {
    "甲":"亥","乙":"午","丙":"寅","丁":"酉","戊":"寅",
    "己":"酉","庚":"巳","辛":"子","壬":"申","癸":"卯",
}

DIZHI_IDX = {"子":0,"丑":1,"寅":2,"卯":3,"辰":4,"巳":5,"午":6,"未":7,"申":8,"酉":9,"戌":10,"亥":11}

def get_changsheng(stem, branch):
    """查天干在地支的十二长生状态"""
    changsheng_zhi = CHANGSHENG_ZHI.get(stem, "")
    if not changsheng_zhi:
        return "未知"
    cs_pos = DIZHI_IDX[changsheng_zhi]  # 长生所在位置（0-11）
    target_pos = DIZHI_IDX[branch]      # 目标地支位置
    offset = (target_pos - cs_pos) % 12
    return STAGES[offset]

def get_changsheng_all(stem):
    """获取某天干完整的十二长生序列"""
    cs_zhi = CHANGSHENG_ZHI.get(stem, "")
    if not cs_zhi:
        return {}
    cs_pos = DIZHI_IDX[cs_zhi]
    result = {}
    for i, zhi in enumerate("子丑寅卯辰巳午未申酉戌亥"):
        offset = (i - cs_pos) % 12
        result[zhi] = STAGES[offset]
    return result

def get_dishi(stem, branch):
    """地势 = 十二长生状态（同get_changsheng，名称不同）"""
    return get_changsheng(stem, branch)

# 禄位：临官 = 禄
def get_lu(stem):
    """查天干的禄位（临官位）"""
    cs_zhi = CHANGSHENG_ZHI.get(stem, "")
    if not cs_zhi:
        return ""
    cs_pos = DIZHI_IDX[cs_zhi]
    # 临官 = 长生+3
    lw_pos = (cs_pos + 3) % 12
    LU_STEMS = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
    return LU_STEMS[lw_pos] + "禄"

def get_wang(stem):
    """查天干的帝旺位"""
    cs_zhi = CHANGSHENG_ZHI.get(stem, "")
    if not cs_zhi:
        return ""
    cs_pos = DIZHI_IDX[cs_zhi]
    ww_pos = (cs_pos + 4) % 12
    DIZHI_LIST = "子丑寅卯辰巳午未申酉戌亥"
    return stem + DIZHI_LIST[ww_pos]

if __name__ == "__main__":
    # 用法示例
    print(get_changsheng("壬", "寅"))
    print(get_changsheng_all("壬"))
