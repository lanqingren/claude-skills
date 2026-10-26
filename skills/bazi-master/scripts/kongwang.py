#!/usr/bin/env python3
"""
空亡查表脚本
输入: 日柱干支
输出: 空亡地支 + 各柱空亡情况
"""

# 六十甲子顺序（标准）
PAIRS = [
    "甲子","乙丑","丙寅","丁卯","戊辰","己巳","庚午","辛未","壬申","癸酉",
    "甲戌","乙亥","丙子","丁丑","戊寅","己卯","庚辰","辛巳","壬午","癸未",
    "甲申","乙酉","丙戌","丁亥","戊子","己丑","庚寅","辛卯","壬辰","癸巳",
    "甲午","乙未","丙申","丁酉","戊戌","己亥","庚子","辛丑","壬寅","癸卯",
    "甲辰","乙巳","丙午","丁未","戊申","己酉","庚戌","辛亥","壬子","癸丑",
    "甲寅","乙卯","丙辰","丁巳","戊午","己未","庚申","辛酉","壬戌","癸亥",
]

# 旬空表（从六十甲子推导）
XUN_KONG = {
    0:"戌亥",   # 甲子旬(0-9)
    10:"申酉",  # 甲戌旬(10-19)
    20:"午未",  # 甲申旬(20-29)
    30:"辰巳",  # 甲午旬(30-39)
    40:"寅卯",  # 甲辰旬(40-49)
    50:"子丑",  # 甲寅旬(50-59)
}

DIZHI = "子丑寅卯辰巳午未申酉戌亥"
DIZHI_SET = set(DIZHI)

def get_dayun(day_stem, day_branch):
    """查日柱空亡地支"""
    key = day_stem + day_branch
    if key not in PAIRS:
        return None
    pos = PAIRS.index(key)
    xun_start = (pos // 10) * 10
    xun_kong = XUN_KONG.get(xun_start, "")
    return set(xun_kong)  # 返回空亡地支集合

def check_all_kongwang(stems_dict, branches_dict):
    """检查四柱空亡情况"""
    day_stem = stems_dict.get("日柱","")
    day_branch = branches_dict.get("日柱","")

    kong_set = get_dayun(day_stem, day_branch)
    if not kong_set:
        return {}

    result = {}
    for pos in ["年柱","月柱","日柱","时柱"]:
        branch = branches_dict.get(pos,"")
        if branch in kong_set:
            result[pos] = f"空亡({branch})"
        else:
            result[pos] = "—"
    return result

def get_xun_name(day_stem, day_branch):
    """查日柱所在旬名
    旬名 = 旬首天干 + 旬尾地支
    例如：甲午组(30-39)叫"甲午旬"，甲辰组(40-49)叫"甲辰旬"
    """
    key = day_stem + day_branch
    if key not in PAIRS:
        return ""
    pos = PAIRS.index(key)
    xun_start = (pos // 10) * 10
    # 旬首天干 + 旬尾地支 = 旬名
    xun_first_stem = PAIRS[xun_start][0]   # 旬首天干
    xun_last_branch = PAIRS[xun_start + 9][1]  # 旬尾地支
    return xun_first_stem + xun_last_branch + "旬"

if __name__ == "__main__":
    # 用法示例
    print(get_dayun("壬", "寅"))
    print(check_all_kongwang({"日柱":"壬"}, {"日柱":"寅"}))
