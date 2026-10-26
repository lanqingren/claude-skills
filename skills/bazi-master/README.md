# 八字命理分析工具 (Bazi Master)

[![Version](https://img.shields.io/badge/version-v1.0.0-blue)]()

基于《子平真诠》理论，支持四柱排盘、大运流年、真太阳时校正的八字命理分析工具。

## 功能特性

- ✅ 四柱排盘（年柱、月柱、日柱、时柱）
- ✅ 纳音五行（60甲子完整映射）
- ✅ 大运流年计算（支持顺排/逆排）
- ✅ 真太阳时校正（根据出生地经度自动校正）
- ✅ 十神、藏干、地支冲合刑害

- ✅ 流月推算（五虎遁公式）
- ✅ 生肖、命宫、五虎遁日起

## 项目结构

```
bazi-skill/
├── SKILL.md              # 核心技能文档（算法说明）
├── README.md             # 本文件
├── .gitignore
├── scripts/
│   ├── dayun_api.py      # 大运计算
│   ├── huangli_query.py  # 黄历查询 + 四柱排盘
│   ├── geocode.py        # 地理编码 + 真太阳时
│   ├── lunar.py          # 阴历转换
│   ├── nayin.py          # 纳音五行
│   ├── zanggan.py        # 藏干
│   ├── changsheng.py     # 长生十二宫
│   ├── shensha.py        # 神煞
│   └── kongwang.py       # 空亡
└── references/
    └── 八字分析框架.md    # 参考文档
```

## 安装配置

### 1. 克隆项目

```bash
git clone <repository-url>
cd bazi-skill
```

### 2. 安装依赖

```bash
pip install requests python-lunardate
```

### 3. 配置 API 密钥

本工具使用两个 API：

**黄历 API**（必选）
- 申请地址：https://api.t1qq.com/
- API Key 获取后设置环境变量：

```bash
export HUANGLI_KEY="你的黄历API密钥"
```

**百度地图 AK**（可选，用于真太阳时校正。如不配置，将跳过校正直接使用上海浦东时间）
- 申请地址：https://lbsyun.baidu.com/
- 创建应用后设置环境变量：

```bash
export BAIDU_AK="你的百度地图AK"
```

### 4. 验证安装

```bash
cd scripts
python3 -c "
import sys
sys.path.insert(0, '.')
from huangli_query import query
r = query('2003-06-15', '14:30', '上海浦东')
print('四柱:', r['yearGanZhi'], r['monthGanZhi'], r['dayGanZhi'], r['hourGanZhi'])
"
```

## 使用方式

### 基础用法

```python
import sys
sys.path.insert(0, 'scripts')

from huangli_query import query
from dayun_api import calculate_dayun_full

# 查询四柱
r = query('2003-06-15', '14:30', '上海浦东')
print(r['yearGanZhi'])      # 年柱
print(r['monthGanZhi'])     # 月柱
print(r['dayGanZhi'])       # 日柱
print(r['hourGanZhi'])      # 时柱（已真太阳时校正）

# 计算大运
dayun = calculate_dayun_full(
    birth_date='2003-06-15',
    year_gan='甲',
    month_gan='丁',
    month_zhi='丑',
    gender='男',
    birth_time_str='14:30',
    lunar_month=1  # 阴历正月
)
print(dayun['direction'])        # 顺排/逆排
print(dayun['qiyun_start_date']) # 起运日期
```

### 输入格式

```
生日：YYYY-MM-DD HH:MM [城市/地址]
性别：男/女
```

示例：
- 阳历：`2003-06-15 14:30 上海浦东`
- 阴历：需说明，工具会自动转换

### 输出内容

- 四柱天干地支 + 纳音五行
- 真太阳时校正（如有地址）
- 大运起运日期 + 十年大运序列
- 流年分析

## 算法说明

### 起运年龄计算

```
间隔天数 = 出生日期到起运节气的天数
qiyun_age = 间隔天数 / 3
起运日期 = 出生日期 + qiyun_age × 365天
```

阴历11月/12月：直接取 `floor(qiyun_age)`
其他月份：`floor(qiyun_age) + 1`

### 真太阳时校正

```
校正分钟 = (出生地经度 - 120) × 4 + 时差方程
时差方程 ≈ -7.5~+7.5分钟（随节气变化）
```

### 流年/流月/流日

- 流年：`(目标年 - 4) % 10/%12` 取天干地支
- 流月：五虎遁公式推算
- 流日：黄历 API 直接查询

## 免责声明

本工具仅供参考娱乐，不构成任何命运决策依据。命运掌握在自己手中。