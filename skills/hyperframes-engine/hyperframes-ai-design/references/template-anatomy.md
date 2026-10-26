# 模板包结构规范

本文档定义了 HyperFrames 模板包的完整目录结构、元数据字段规范和变量使用规则。

---

## 一、template.html-video.yaml 完整字段说明

每个模板根目录下必须包含一个 `template.html-video.yaml` 文件，
作为模板的元数据配置文件，供 HyperFrames 引擎识别和加载。

### 完整字段定义

```yaml
# 模板唯一标识符（格式：小写字母 + 连字符，全局唯一）
id: swiss-pulse-announcement

# 模板展示名称（中文，简洁明了）
name: 瑞士脉冲公告模板

# 模板功能描述（1-2 句话，说明适用场景）
description: 基于国际主义平面设计风格的公告展示模板，强调几何秩序与信息清晰度，
  适用于产品发布、活动预告等场景。

# 渲染引擎标识（固定值）
engine: html-video

# 模板分类（从预定义列表中选择）
# 可选值：announcement / product / brand / event / data / editorial / ambient
category: announcement

# 标签列表（用于搜索过滤，3-8 个）
tags:
  - 瑞士风格
  - 极简
  - 几何
  - 公告
  - 商务

# 最佳使用场景（描述性文字，供 AI 推断时参考）
best_for:
  - 企业公告与新闻发布
  - 产品发布倒计时
  - 活动信息展示
  - 品牌形象宣传

# 视觉风格（与 design-intent.md 中的风格 id 对应）
style: swiss-pulse

# 内容密度（sparse / standard / rich）
content_density: standard

# 运动能量（static / gentle / medium / dynamic）
motion_energy: medium

# 入口文件路径（相对于模板根目录）
source_entry: source/index.html

# 预览图路径（相对于模板根目录）
preview_image: preview/thumbnail.png

# 预览视频路径（可选，相对于模板根目录）
preview_video: preview/demo.mp4

# 模板版本号（语义化版本）
version: "1.0.0"

# 创建日期（ISO 8601 格式）
created_at: "2026-07-06"

# 最后更新日期
updated_at: "2026-07-06"

# 模板作者（可选）
author: HyperFrames AI

# 支持的宽高比列表
aspect_ratios:
  - "16:9"

# 标准分辨率
resolution:
  width: 1920
  height: 1080

# 可用模板变量声明（必须与 source/index.html 中的变量保持一致）
variables:
  - name: title
    type: text
    label: 主标题
    default: "请输入标题"
    max_length: 40

  - name: subtitle
    type: text
    label: 副标题
    default: "请输入副标题"
    max_length: 80

  - name: brand_name
    type: text
    label: 品牌名称
    default: "Brand Name"
    max_length: 30

  - name: accent_color
    type: color
    label: 强调色
    default: "#E63946"

  - name: date_text
    type: text
    label: 日期文字
    default: "2026.07"
    max_length: 20
```

---

## 二、templates/ 目录结构

标准模板包的完整目录布局如下：

```
templates/
└── swiss-pulse-announcement/          # 模板根目录（与 id 相同）
    │
    ├── template.html-video.yaml       # 模板元数据（必须）
    │
    ├── source/                        # 源文件目录（必须）
    │   ├── index.html                 # 主入口文件（必须）
    │   └── assets/                    # 静态资源（可选）
    │       ├── fonts/                 # 内嵌字体文件
    │       └── images/                # base64 内嵌图片源文件
    │
    └── preview/                       # 预览素材目录（必须）
        ├── thumbnail.png              # 静态缩略图（1920×1080 或 960×540）
        └── demo.mp4                   # 动效预览视频（可选，5-10 秒）
```

### source/ 子目录说明

- `source/index.html` — 模板的唯一入口文件，包含完整的 HTML + CSS + JS
- `source/assets/` — 存放所有静态资源，使用时需通过相对路径引用
- 严禁在 source/ 中放置多个 HTML 文件，每个模板只有一个入口

### preview/ 子目录说明

- `thumbnail.png` — 用于模板列表展示的静态截图
- `demo.mp4` — 用于模板详情页的动效预览（建议 5-10 秒循环片段）
- 预览素材需在模板完成后手动生成，不由 AI 自动生成

---

## 三、模板变量使用规范

在 `source/index.html` 中使用 `{{变量名}}` 语法声明占位符：

### 基础变量语法

```html
<!-- 文字变量 -->
<h1 class="headline">{{title}}</h1>
<p class="subtitle">{{subtitle}}</p>
<span class="brand">{{brand_name}}</span>

<!-- 颜色变量（用于 CSS 自定义属性）-->
<style>
  :root {
    --accent: {{accent_color}};
  }
</style>

<!-- 日期与数字变量 -->
<div class="date-display">{{date_text}}</div>
```

### 变量命名规范

| 变量类型   | 命名格式           | 示例                          |
|------------|--------------------|-------------------------------|
| 主要文字   | `title`            | `{{title}}`                   |
| 副标题     | `subtitle`         | `{{subtitle}}`                |
| 品牌相关   | `brand_*`          | `{{brand_name}}`              |
| 颜色相关   | `*_color`          | `{{accent_color}}`            |
| 日期时间   | `*_date` / `*_time`| `{{event_date}}`              |
| 数值数据   | `*_value` / `*_num`| `{{growth_value}}`            |
| 描述性文字 | `*_text` / `*_desc`| `{{tagline_text}}`            |

### 变量抽取原则

**应当变量化的内容**：
- 所有展示文字（标题、副标题、标语、说明）
- 品牌名称、产品名称
- 日期、时间、数字数据
- 主色调、强调色（如需支持换色）
- 背景图片路径（如使用图片背景）

**应当硬编码的内容**：
- 视觉风格相关的配色（非品牌色的装饰色）
- 布局参数（位置、尺寸、间距）
- 动效参数（时长、缓动函数、延迟）
- 装饰件的形状与样式
- 字体名称与字号

---

## 四、版本控制建议

### 版本号规则（遵循语义化版本）

```
主版本.次版本.修订版本
  1.0.0
  │ │ └── 修订：修复 bug、调整细节，不影响变量接口
  │ └──── 次版本：新增变量或功能，向下兼容
  └────── 主版本：变量接口破坏性变更，需重新配置
```

### 变更记录实践

在 `template.html-video.yaml` 中维护简短变更历史：

```yaml
# 变更记录（最新在前，保留最近 3-5 条）
changelog:
  - version: "1.1.0"
    date: "2026-07-10"
    note: "新增 tagline_text 变量支持三行副标题"
  - version: "1.0.0"
    date: "2026-07-06"
    note: "初始版本发布"
```

### 模板 id 稳定性原则

- 模板 id 一旦发布，严禁修改（其他系统可能持有对该 id 的引用）
- 如需大幅重构，创建新模板并废弃旧模板
- 废弃时在 yaml 中添加 `deprecated: true` 和 `successor_id` 字段
