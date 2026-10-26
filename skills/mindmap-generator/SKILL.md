---
name: mindmap-generator
description: 使用 Matplotlib 生成分层思维导图 PNG 图片，支持自定义数据结构、颜色和布局。
metadata:
  category: 可视化
  emoji: 🧠
triggers:
  - 思维导图
  - mindmap
  - 生成导图
---

# MindMap Generator Skill

使用 Python + Matplotlib 生成分层思维导图。

## 功能特点

- 🎨 自定义配色方案
- 📐 自动布局避免节点重叠
- 🔗 L形连接线设计
- 💫 圆角矩形节点带阴影
- 📝 支持四层结构：中心 → 终端 → 模块 → 功能项

## 使用方法

### 1. 准备数据

定义你的思维导图数据结构：

```python
layout = [
    ('终端名称', 颜色, [
        ('模块名', Y位置, ['功能项1', '功能项2']),
        ('模块名', Y位置, ['功能项']),
    ]),
]
```

### 2. 运行脚本

```bash
python3 mindmap_generator.py
```

### 3. 查看结果

生成的图片保存在 `~/Desktop/智慧驿站需求思维导图.png`

## 完整示例代码

```python
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 创建图形
fig, ax = plt.subplots(1, 1, figsize=(36, 30), facecolor='#fafbfc')
ax.set_xlim(0, 140)
ax.set_ylim(-15, 105)
ax.axis('off')
ax.set_facecolor('#fafbfc')

# 颜色定义
colors = {
    'center': '#2d3436',
    'mobile_member': '#0984e3',
    'mobile_merchant': '#e17055',
    'admin': '#00b894',
    'device': '#a29bfe',
}

def draw_rounded_box(ax, x, y, width, height, color, text, fontsize=12, 
                     text_color='white', alpha=1.0, shadow=True, border_color=None):
    """绘制圆角矩形带阴影"""
    if shadow:
        shadow_box = FancyBboxPatch((x - width/2 + 0.15, y - height/2 - 0.15), 
                                     width, height,
                                     boxstyle="round,pad=0.02,rounding_size=0.4",
                                     facecolor='#00000012', edgecolor='none',
                                     transform=ax.transData)
        ax.add_patch(shadow_box)
    
    box = FancyBboxPatch((x - width/2, y - height/2), width, height,
                         boxstyle="round,pad=0.02,rounding_size=0.4",
                         facecolor=color, edgecolor=border_color or color,
                         linewidth=2 if border_color else 0,
                         alpha=alpha, transform=ax.transData)
    ax.add_patch(box)
    
    ax.text(x, y, text, ha='center', va='center', fontsize=fontsize,
            color=text_color, fontweight='bold', wrap=True)

def draw_connection(ax, x1, y1, x2, y2, color, linewidth=2):
    """绘制L形连接线"""
    mid_x = x1 + (x2 - x1) * 0.4
    ax.plot([x1, mid_x], [y1, y1], color=color, linewidth=linewidth, 
            solid_capstyle='round', zorder=1)
    ax.plot([mid_x, mid_x], [y1, y2], color=color, linewidth=linewidth, 
            solid_capstyle='round', zorder=1)
    ax.plot([mid_x, x2], [y2, y2], color=color, linewidth=linewidth, 
            solid_capstyle='round', zorder=1)

# 中心节点
center_x, center_y = 5, 45
draw_rounded_box(ax, center_x, center_y, 7, 3.5, colors['center'], 
                 '智慧驿站', fontsize=13)

# 数据定义
layout = [
    ('移动端-会员', colors['mobile_member'], [
        ('首页', 82, ['banner', '推荐服务']),
        ('扫码', 76, ['扫描二维码']),
        ('我的', 65, ['我的', '我的订单', '我的积分', '帮助中心', '设置', '我的二维码'])
    ]),
    ('移动端-商户', colors['mobile_merchant'], [
        ('消费记录', 52, ['消费记录']),
        ('扫码', 47, ['扫码']),
        ('首页', 42, ['首页'])
    ]),
    ('管理端', colors['admin'], [
        ('设备监控', 28, ['设备监控列表', '新增设备', '刷新设备列表']),
        ('用户管理', 23, ['用户列表']),
        ('商户管理', 17, ['商户列表', '新增商户', '商户详情']),
        ('商户分类', 12, ['商户分类列表']),
        ('站点管理', 7, ['站点列表']),
        ('订单管理', 2, ['订单管理']),
        ('数据统计', -3, ['数据统计'])
    ]),
    ('设备端', colors['device'], [
        ('睿科设备调试', -12, ['睿科设备调试'])
    ])
]

terminal_x = 20
module_x = 40
func_x = 62

for term_name, color, modules in layout:
    term_y = sum(m[1] for m in modules) / len(modules)
    
    draw_connection(ax, center_x + 3.5, center_y, terminal_x - 4, term_y, color, 3)
    draw_rounded_box(ax, terminal_x, term_y, 9, 3, color, term_name, fontsize=11)
    
    for mod_name, mod_y, funcs in modules:
        draw_connection(ax, terminal_x + 4.5, term_y, module_x - 4, mod_y, color, 2)
        draw_rounded_box(ax, module_x, mod_y, 10, 2.5, 'white', mod_name, 
                         fontsize=10, text_color=color, alpha=0.95, border_color=color)
        
        func_spacing = 2.8
        func_start_y = mod_y + (len(funcs) - 1) * func_spacing / 2
        
        for j, func in enumerate(funcs):
            fy = func_start_y - j * func_spacing
            ax.plot([module_x + 5, func_x - 3.5], [mod_y, fy], 
                    color='#b2bec3', linewidth=1, alpha=0.7, zorder=1)
            draw_rounded_box(ax, func_x, fy, 11, 2, '#f8f9fa', func, 
                             fontsize=9, text_color='#2d3436', alpha=0.9, 
                             shadow=False, border_color='#dfe6e9')

# 标题
ax.text(70, 100, '智慧驿站需求列表 · 思维导图', ha='center', va='top', 
        fontsize=16, fontweight='bold', color='#2d3436')

# 图例
legend_x, legend_y = 118, 92
legend_items = [
    ('移动端-会员', colors['mobile_member']),
    ('移动端-商户', colors['mobile_merchant']),
    ('管理端', colors['admin']),
    ('设备端', colors['device'])
]

legend_bg = FancyBboxPatch((legend_x - 2, legend_y - 2), 18, 18,
                           boxstyle="round,pad=0.02,rounding_size=0.5",
                           facecolor='white', edgecolor='#b2bec3', linewidth=1.5,
                           transform=ax.transData)
ax.add_patch(legend_bg)

ax.text(legend_x + 7, legend_y + 14, '图例', ha='center', va='center', 
        fontsize=10, fontweight='bold', color='#2d3436')

for i, (name, color) in enumerate(legend_items):
    ly = legend_y + 10 - i * 3
    box = FancyBboxPatch((legend_x, ly - 0.6), 2, 1.2,
                         boxstyle="round,pad=0.02,rounding_size=0.2",
                         facecolor=color, edgecolor='none',
                         transform=ax.transData)
    ax.add_patch(box)
    ax.text(legend_x + 3, ly, name, ha='left', va='center', 
            fontsize=8, color='#2d3436')

# 保存
output_path = os.path.expanduser('~/Desktop/思维导图.png')
plt.tight_layout()
plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='#fafbfc', 
            edgecolor='none', pad_inches=0.2)
plt.close()

print(f"思维导图已生成: {output_path}")
```

## 自定义指南

### 修改颜色

在 `colors` 字典中定义你的配色：

```python
colors = {
    'center': '#2d3436',      # 中心节点
    'branch1': '#0984e3',     # 分支1颜色
    'branch2': '#e17055',     # 分支2颜色
}
```

### 调整布局

- `terminal_x`, `module_x`, `func_x`：控制各层水平位置
- `mod_y` 数值：控制模块垂直位置（越大越靠上）
- `figsize`：控制画布大小

### 调整间距

- `func_spacing`：功能项之间的垂直间距
- 修改 `set_ylim` 范围：控制整体垂直显示区域

## 依赖

```bash
pip3 install matplotlib
```

## 注意事项

1. 确保系统安装了中文字体（如 PingFang SC）
2. 如果中文显示为方框，修改 `font.sans-serif` 为你系统可用的字体
3. 节点较多时，适当增大 `figsize` 和 Y轴范围
