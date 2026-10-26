# 保存为模板完整流程

本文档定义了将一次性 composition 转化为可复用模板的完整流程，
包括决策标准、操作步骤、变量抽取建议和完整示例。

---

## 一、判断是否值得保存为模板

并非每个 composition 都适合保存为模板。在保存之前，先通过以下决策标准评估：

### 适合保存为模板（满足 2 项以上）

- 该设计具有清晰可辨的视觉风格，未来类似场景会重复使用
- 核心布局和视觉结构可以通用，仅文字内容需要替换
- 已在真实场景中验证过视觉效果，质量达到 quality-checklist 要求
- 设计涵盖某个常用类别（公告、产品展示、品牌宣传、数据展示）
- 有 2 个以上的潜在使用方提出类似需求

### 不适合保存为模板（满足任意 1 项）

- 设计高度依赖特定品牌资产（特殊字体、专属图案），无法泛化
- 布局和视觉元素为某次活动定制，无法复用
- 内容密度极低或极高，通用性差
- 设计质量未通过基础检查清单（如对比度不足、动效缺失）

---

## 二、保存流程：逐步操作

### 第一步：确定模板 id 和目录名

根据风格和用途生成唯一标识符，格式为：`{风格}-{用途}`

```
swiss-pulse-announcement     # 瑞士风格 + 公告
velvet-standard-product      # 天鹅绒标准 + 产品展示
neon-grid-event              # 霓虹网格 + 活动
organic-flow-brand           # 有机流动 + 品牌
```

---

### 第二步：在 templates/ 下创建目录结构

```bash
# 目标目录结构
templates/
└── {template-id}/
    ├── template.html-video.yaml
    ├── source/
    │   └── index.html
    └── preview/
        └── thumbnail.png
```

具体操作：
1. 创建 `templates/{template-id}/` 根目录
2. 创建 `templates/{template-id}/source/` 子目录
3. 创建 `templates/{template-id}/preview/` 子目录
4. 将 composition HTML 复制到 `source/index.html`（先复制，再变量化）

---

### 第三步：编写 template.html-video.yaml

参考 template-anatomy.md 中的完整字段说明，填写所有必填字段。
重点确认以下字段与实际内容一致：
- `variables` 列表与 source/index.html 中的占位符完全对应
- `style` 与实际视觉风格匹配
- `best_for` 描述真实适用场景

---

### 第四步：对 source/index.html 进行变量化处理

将硬编码的可替换内容替换为 `{{变量名}}` 占位符。
详见本文第三节"变量抽取建议"。

---

### 第五步：验证模板可用性

- 在浏览器中打开 source/index.html，检查占位符是否正确显示
- 手动替换变量值，确认视觉效果不受影响
- 对照 quality-checklist.md 完成完整检查

---

## 三、变量抽取建议

### 应当变量化的内容

**文字内容类**：
- 主标题文字 → `{{title}}`
- 副标题文字 → `{{subtitle}}`
- 品牌/产品名称 → `{{brand_name}}` / `{{product_name}}`
- 标语/口号 → `{{tagline}}`
- 日期文字 → `{{date_text}}`
- 数字/数据 → `{{value_text}}`
- 说明性文字 → `{{description}}`

**颜色类**（仅当风格允许自定义时）：
- 主强调色 → `{{accent_color}}`
- 背景色 → `{{bg_color}}`

**媒体类**（如模板使用图片）：
- 背景图 → `{{bg_image_url}}`
- 产品图 → `{{product_image_url}}`

---

### 应当硬编码的内容

**布局参数**：元素的绝对位置（top/left/right/bottom）、尺寸（width/height）
**动效参数**：GSAP 时长（duration）、缓动函数（ease）、延迟（delay）
**装饰件**：装饰元素的形状、颜色、大小、透明度
**字体设置**：font-family、font-size、font-weight、line-height
**视觉风格色**：非品牌色的装饰配色（如网格线颜色、背景辅助色）

---

### 变量过度抽取的反模式（禁止）

不要将以下内容变量化，会破坏模板的视觉一致性：
- 字号和行高（会破坏排版比例）
- 动效时长（会破坏 choreography 节奏）
- 装饰件数量和位置（会破坏视觉平衡）
- CSS 布局参数（可能导致元素重叠或溢出）

---

## 四、完整 YAML 示例

以下为一个真实可用的模板元数据文件示例：

```yaml
# 模板元数据：瑞士脉冲风格 × 企业公告
id: swiss-pulse-announcement
name: 瑞士脉冲企业公告

description: >
  基于瑞士国际主义平面设计风格的企业公告模板。
  采用几何线条与强色块对比，传达理性、专业与冲击力。
  适用于新闻发布、里程碑宣传和重要声明场景。

engine: html-video
category: announcement

tags:
  - 瑞士风格
  - 极简
  - 几何
  - 企业
  - 公告
  - 专业

style: swiss-pulse
content_density: standard
motion_energy: medium

best_for:
  - 企业重要公告与声明
  - 产品发布里程碑
  - 季度目标与成果展示
  - 品牌形象宣传片

source_entry: source/index.html
preview_image: preview/thumbnail.png
preview_video: preview/demo.mp4

version: "1.0.0"
created_at: "2026-07-06"
updated_at: "2026-07-06"
author: HyperFrames AI

aspect_ratios:
  - "16:9"

resolution:
  width: 1920
  height: 1080

variables:
  - name: title
    type: text
    label: 主标题
    description: 公告的核心主题，建议不超过 20 个字
    default: "重要公告"
    max_length: 40

  - name: subtitle
    type: text
    label: 副标题
    description: 对主标题的补充说明
    default: "副标题内容"
    max_length: 60

  - name: brand_name
    type: text
    label: 品牌名称
    description: 企业或品牌的名称，显示在右下角
    default: "品牌名称"
    max_length: 30

  - name: date_text
    type: text
    label: 日期文字
    description: 公告的发布日期或活动时间
    default: "2026.07"
    max_length: 20

  - name: tagline
    type: text
    label: 标语
    description: 品牌口号或本次公告的简短说明
    default: "持续创新，共创未来"
    max_length: 30

  - name: accent_color
    type: color
    label: 强调色
    description: 用于标题下划线和几何装饰元素的颜色
    default: "#E63946"

changelog:
  - version: "1.0.0"
    date: "2026-07-06"
    note: "初始版本"
```

---

## 五、保存检查清单

保存模板前，逐项确认：

- [ ] `id` 在整个 templates/ 目录中唯一
- [ ] `template.html-video.yaml` 中的 `variables` 与 HTML 中占位符完全一致
- [ ] `source/index.html` 中所有可替换文字均已变量化
- [ ] `source/index.html` 中无硬编码的动效参数以外的业务文字
- [ ] `preview/thumbnail.png` 已准备（可暂用截图替代）
- [ ] 在浏览器中打开 source/index.html 无报错
- [ ] `window.__timelines.main` 已正确注册
