#!/usr/bin/env python3
"""
地支藏干查表脚本
输入: 地支
输出: {本气, 中气, 余气}
"""

# 地支藏干表
ZANGAN_MAP = {
    "子":{"本气":"癸","中气":"","余气":""},  # 子藏癸
    "丑":{"本气":"己","中气":"癸","余气":"辛"},
    "寅":{"本气":"甲","中气":"丙","余气":"戊"},
    "卯":{"本气":"乙","中气":"","余气":""},  # 卯藏乙
    "辰":{"本气":"戊","中气":"乙","余气":"癸"},
    "巳":{"本气":"丙","中气":"庚","余气":"戊"},
    "午":{"本气":"丁","中气":"己","余气":""},  # 午藏丁己
    "未":{"本气":"己","中气":"丁","余气":"乙"},
    "申":{"本气":"庚","中气":"壬","余气":"戊"},
    "酉":{"本气":"辛","中气":"","余气":""},  # 酉藏辛
    "戌":{"本气":"戊","中气":"辛","余气":"丁"},
    "亥":{"本气":"壬","中气":"甲","余气":""},  # 亥藏壬甲
}

def get_zanggan(branch):
    """查单支藏干"""
    return ZANGAN_MAP.get(branch, {"本气":"","中气":"","余气":""})

def get_all_zanggan(branch):
    """获取藏干列表（不含空）"""
    info = get_zanggan(branch)
    result = []
    if info["本气"]:
        result.append(info["本气"])
    if info["中气"]:
        result.append(info["中气"])
    if info["余气"]:
        result.append(info["余气"])
    return result

def get_all_zanggan_str(branch):
    """获取藏干字符串（用于显示）"""
    return "".join(get_all_zanggan(branch))

if __name__ == "__main__":
    # 用法示例
    print(get_zanggan("子"))
    print(get_all_zanggan_str("寅"))
