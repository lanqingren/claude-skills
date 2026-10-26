#!/usr/bin/env python3
"""
神煞判断脚本
输入: 四柱 + 性别
输出: 各神煞是否有/无，及其位置
"""

# ===== 天乙贵人 =====
# 口诀：甲戊并牛羊，乙己鼠猴乡，丙丁猪鸡位，壬癸蛇兔藏，庚辛逢马虎
TIANYI_ZHI = {
    "甲":("丑","未"),"戊":("丑","未"),
    "乙":("子","申"),"己":("子","申"),
    "丙":("亥","酉"),"丁":("亥","酉"),
    "庚":("午","寅"),"辛":("午","寅"),
    "壬":("巳","卯"),"癸":("巳","卯"),
}

def check_tianyi(stems_dict, branches_dict):
    """检查天乙贵人
    stems_dict: {"年柱":"甲","月柱":"丁",...}
    branches_dict: {"年柱":"戌","月柱":"丑",...}
    返回: [(位置, 天干/地支), ...]
    """
    results = []
    for pos in ["年柱","月柱","日柱","时柱"]:
        stem = stems_dict.get(pos, "")
        branch = branches_dict.get(pos, "")
        if not stem or not branch:
            continue
        # 以日干查
        day_stem = stems_dict.get("日柱","")
        if day_stem in TIANYI_ZHI:
            needed = TIANYI_ZHI[day_stem]
            if branch in needed:
                results.append((pos, f"日干{day_stem}→天乙贵人于{branch}"))
        # 以年干查
        year_stem = stems_dict.get("年柱","")
        if year_stem in TIANYI_ZHI:
            needed = TIANYI_ZHI[year_stem]
            if branch in needed and (pos, f"年干{year_stem}→天乙贵人于{branch}") not in results:
                results.append((pos, f"年干{year_stem}→天乙贵人于{branch}"))
    return results

# ===== 文昌贵人 =====
# 甲见巳,乙见午,丙见申,丁见酉,戊见申,己见酉,庚见亥,辛见子,壬见寅,癸见卯
WENCHANG_ZHI = {
    "甲":"巳","乙":"午","丙":"申","丁":"酉","戊":"申",
    "己":"酉","庚":"亥","辛":"子","壬":"寅","癸":"卯",
}

def check_wenchang(stems_dict, branches_dict):
    """检查文昌贵人"""
    results = []
    day_stem = stems_dict.get("日柱","")
    if day_stem in WENCHANG_ZHI:
        wcz = WENCHANG_ZHI[day_stem]
        for pos in ["年柱","月柱","日柱","时柱"]:
            branch = branches_dict.get(pos,"")
            if branch == wcz:
                results.append((pos, f"文昌于{branch}"))
    return results

# ===== 桃花 =====
# 口诀：申子辰在酉，寅午戌在卯，巳酉丑在午，亥卯未在子
TAOHUA_ZHI = {
    ("申","子","辰"):"酉",
    ("寅","午","戌"):"卯",
    ("巳","酉","丑"):"午",
    ("亥","卯","未"):"子",
}

def check_taohua(branches_dict):
    """检查桃花（以日支查）"""
    day_branch = branches_dict.get("日柱","")
    year_branch = branches_dict.get("年柱","")
    for combo, thzhi in TAOHUA_ZHI.items():
        if day_branch in combo:
            return f"日支{day_branch}→桃花在{thzhi}"
        if year_branch in combo:
            return f"年支{year_branch}→桃花在{thzhi}"
    return None

# ===== 驿马 =====
# 口诀：申子辰马在寅，寅午戌马在申，巳酉丑马在亥，亥卯未马在巳
YIMA_ZHI = {
    ("申","子","辰"):"寅",
    ("寅","午","戌"):"申",
    ("巳","酉","丑"):"亥",
    ("亥","卯","未"):"巳",
}

def check_yima(branches_dict):
    """检查驿马（以日支查）"""
    day_branch = branches_dict.get("日柱","")
    year_branch = branches_dict.get("年柱","")
    for combo, yzhi in YIMA_ZHI.items():
        if day_branch in combo:
            return f"日支{day_branch}→驿马在{yzhi}"
        if year_branch in combo:
            return f"年支{year_branch}→驿马在{yzhi}"
    return None

# ===== 羊刃 =====
# 甲卯,乙寅(阴),丙午,丁巳(阴),戊午,己巳(阴),庚酉,辛申(阴),壬子,癸亥(阴)
YANGREN_ZHI = {
    "甲":"卯","乙":"寅","丙":"午","丁":"巳","戊":"午",
    "己":"巳","庚":"酉","辛":"申","壬":"子","癸":"亥",
}

def check_yangren(stems_dict, branches_dict):
    """检查羊刃（以日干查）"""
    results = []
    day_stem = stems_dict.get("日柱","")
    yr = YANGREN_ZHI.get(day_stem,"")
    if yr:
        for pos in ["年柱","月柱","日柱","时柱"]:
            branch = branches_dict.get(pos,"")
            if branch == yr:
                results.append((pos, f"羊刃于{branch}"))
    return results

# ===== 天罗地网 =====
# 天罗：火命+戌亥；地网：水/土命+辰巳；男忌天罗，女忌地网
TIANLUO = {"戌","亥"}
DIWANG = {"辰","巳"}
HUO_NAYIN = {"炉中火","山下火","霹雳火","天上火","佛灯火","山头火","城头土"}  # 火命纳音

def check_tianluo_wang(nayin_dict, branches_dict, gender):
    """检查天罗地网
    nayin_dict: {"年柱":"山头火","月柱":"涧下水",...}
    gender: 男/女
    """
    results = []
    day_nayin = nayin_dict.get("日柱","")
    day_branch = branches_dict.get("日柱","")

    is_huo = day_nayin in HUO_NAYIN
    is_shui = "水" in day_nayin
    is_tu = "土" in day_nayin

    # 天罗：火命+戌亥
    if is_huo and day_branch in TIANLUO:
        results.append(f"日柱{days_branch}纳音{day_nayin}→天罗")
        if gender == "男":
            results.append("（男忌天罗）")

    # 地网：水/土命+辰巳
    if (is_shui or is_tu) and day_branch in DIWANG:
        results.append(f"日柱{day_branch}纳音{day_nayin}→地网")
        if gender == "女":
            results.append("（女忌地网）")

    return results

if __name__ == "__main__":
    # 用法示例
    stems = {"年柱":"甲","月柱":"丁","日柱":"壬","时柱":"戊"}
    branches = {"年柱":"戌","月柱":"丑","日柱":"寅","时柱":"申"}
    print(check_tianyi(stems, branches))
    print(check_taohua(branches))
