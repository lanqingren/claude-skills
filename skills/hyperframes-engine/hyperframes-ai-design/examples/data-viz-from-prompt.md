# 数据可视化帧示例：从用户描述到生成帧 HTML

## 场景描述

用户输入：
> "展示 Rust 在 GitHub Stars 排行中的增长数据，风格专业"

---

## Step 1：意图解析

解析用户描述，推断关键参数：

```json
{
  "frame_type": "data_visualization",
  "topic": "Rust GitHub Stars 增长数据",
  "style_hint": "专业",
  "inferred_style": "Corporate Clean",
  "chart_type": "bar_chart",
  "data_points": 5,
  "color_mood": "blue_grey",
  "motion_level": "data_reveal",
  "language": "zh-CN"
}
```

**推断逻辑：**
- "展示数据" + "风格专业" → Corporate Clean（清晰层次、精确对齐）
- 增长数据 → 条形图最直观
- 蓝灰色系符合技术报告审美，可信度高

---

## Step 2：设计系统确认

选定风格：**Corporate Clean**

```json
{
  "design_system": {
    "style": "Corporate Clean",
    "colors": {
      "background": "#0f1923",
      "surface": "#1a2535",
      "primary": "#4a9eff",
      "accent": "#60d9a0",
      "text_primary": "#e8edf2",
      "text_secondary": "#8a9bb0",
      "grid_line": "rgba(255,255,255,0.06)"
    },
    "typography": {
      "chart_title_size": "48px",
      "axis_label_size": "20px",
      "data_label_size": "22px",
      "font_family": "'Inter', 'Helvetica Neue', sans-serif"
    },
    "geometry": {
      "bar_radius": "4px",
      "grid_lines": true,
      "decorators": ["top_accent_bar", "source_label"]
    }
  }
}
```

---

## 完整 HTML 代码

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=1920, height=1080">
  <title>Rust GitHub Stars 增长数据</title>
  <style>
    /* 重置与基础 */
    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
      width: 1920px;
      height: 1080px;
      overflow: hidden;
      background: #0f1923;
      font-family: 'Inter', 'Helvetica Neue', 'PingFang SC', sans-serif;
      color: #e8edf2;
      display: flex;
      flex-direction: column;
      padding: 80px 120px 60px;
    }

    /* 顶部装饰线 */
    .top-accent {
      width: 0;
      height: 3px;
      background: linear-gradient(90deg, #4a9eff, #60d9a0);
      margin-bottom: 40px;
      border-radius: 2px;
    }

    /* 标题区域 */
    .header {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      margin-bottom: 60px;
      opacity: 0;
    }

    .chart-title {
      font-size: 48px;
      font-weight: 700;
      color: #e8edf2;
      line-height: 1.2;
    }

    .chart-subtitle {
      font-size: 22px;
      font-weight: 400;
      color: #8a9bb0;
      margin-top: 8px;
    }

    .badge {
      display: flex;
      align-items: center;
      gap: 10px;
      background: rgba(74, 158, 255, 0.12);
      border: 1px solid rgba(74, 158, 255, 0.3);
      padding: 10px 20px;
      border-radius: 6px;
      font-size: 18px;
      color: #4a9eff;
    }

    .badge-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #4a9eff;
    }

    /* 图表容器 */
    .chart-area {
      flex: 1;
      display: flex;
      gap: 0;
      position: relative;
    }

    /* Y 轴标签区 */
    .y-axis {
      width: 80px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding-bottom: 56px;
      opacity: 0;
    }

    .y-label {
      font-size: 18px;
      color: #8a9bb0;
      text-align: right;
    }

    /* 图表主体（网格 + 条形） */
    .chart-body {
      flex: 1;
      position: relative;
      display: flex;
      flex-direction: column;
    }

    /* 水平网格线 */
    .grid-lines {
      position: absolute;
      inset: 0;
      bottom: 56px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      pointer-events: none;
    }

    .grid-line {
      width: 100%;
      height: 1px;
      background: rgba(255,255,255,0.06);
    }

    /* 条形图区域 */
    .bars-container {
      flex: 1;
      display: flex;
      align-items: flex-end;
      gap: 40px;
      padding: 0 40px;
      margin-bottom: 0;
    }

    /* 单个条形组 */
    .bar-group {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      height: 100%;
      justify-content: flex-end;
      gap: 0;
    }

    /* 数据标签（条顶） */
    .data-label {
      font-size: 22px;
      font-weight: 700;
      color: #e8edf2;
      margin-bottom: 10px;
      opacity: 0;
    }

    /* 条形本体 */
    .bar {
      width: 100%;
      height: 0; /* 初始高度 0，动画展开 */
      background: linear-gradient(180deg, #4a9eff 0%, #2266cc 100%);
      border-radius: 4px 4px 0 0;
      position: relative;
      transition: none;
    }

    /* 高亮条（当前年份） */
    .bar.highlight {
      background: linear-gradient(180deg, #60d9a0 0%, #2d9966 100%);
    }

    /* X 轴标签 */
    .x-axis {
      display: flex;
      gap: 40px;
      padding: 0 40px;
      margin-top: 0;
    }

    .x-label {
      flex: 1;
      text-align: center;
      font-size: 20px;
      color: #8a9bb0;
      padding-top: 14px;
      border-top: 1px solid rgba(255,255,255,0.1);
    }

    /* 底部来源标注 */
    .source-line {
      margin-top: 24px;
      font-size: 16px;
      color: rgba(255,255,255,0.25);
      opacity: 0;
    }

    /* 装饰件：右上角小卡片 */
    .stat-card {
      position: absolute;
      right: 0;
      top: 0;
      background: #1a2535;
      border: 1px solid rgba(96, 217, 160, 0.25);
      border-radius: 8px;
      padding: 20px 28px;
      opacity: 0;
    }

    .stat-value {
      font-size: 42px;
      font-weight: 800;
      color: #60d9a0;
      line-height: 1;
    }

    .stat-desc {
      font-size: 16px;
      color: #8a9bb0;
      margin-top: 6px;
    }
  </style>
</head>
<body>
  <!-- 顶部装饰线 -->
  <div class="top-accent" id="topAccent"></div>

  <!-- 标题区 -->
  <div class="header" id="header">
    <div>
      <div class="chart-title">Rust GitHub Stars 年度增长</div>
      <div class="chart-subtitle">与主流系统语言对比 · 2020–2024</div>
    </div>
    <div class="badge">
      <div class="badge-dot"></div>
      数据来源：GitHub Archive
    </div>
  </div>

  <!-- 图表区 -->
  <div class="chart-area">
    <!-- Y 轴 -->
    <div class="y-axis" id="yAxis">
      <div class="y-label">90k</div>
      <div class="y-label">70k</div>
      <div class="y-label">50k</div>
      <div class="y-label">30k</div>
      <div class="y-label">10k</div>
    </div>

    <!-- 图表主体 -->
    <div class="chart-body">
      <!-- 网格线 -->
      <div class="grid-lines">
        <div class="grid-line"></div>
        <div class="grid-line"></div>
        <div class="grid-line"></div>
        <div class="grid-line"></div>
        <div class="grid-line"></div>
      </div>

      <!-- 数据条 -->
      <div class="bars-container" id="barsContainer">
        <!-- 数据：(年份, stars增量k, 是否高亮) -->
        <div class="bar-group">
          <div class="data-label" id="dl0">+28k</div>
          <div class="bar" id="bar0" data-target="31" style="max-height: calc(100% - 40px)"></div>
        </div>
        <div class="bar-group">
          <div class="data-label" id="dl1">+42k</div>
          <div class="bar" id="bar1" data-target="47"></div>
        </div>
        <div class="bar-group">
          <div class="data-label" id="dl2">+55k</div>
          <div class="bar" id="bar2" data-target="61"></div>
        </div>
        <div class="bar-group">
          <div class="data-label" id="dl3">+67k</div>
          <div class="bar" id="bar3" data-target="74"></div>
        </div>
        <div class="bar-group">
          <div class="data-label" id="dl4">+83k</div>
          <div class="bar highlight" id="bar4" data-target="92"></div>
        </div>
      </div>

      <!-- X 轴标签 -->
      <div class="x-axis" id="xAxis">
        <div class="x-label">2020</div>
        <div class="x-label">2021</div>
        <div class="x-label">2022</div>
        <div class="x-label">2023</div>
        <div class="x-label">2024</div>
      </div>
    </div>

    <!-- 右上角统计卡片 -->
    <div class="stat-card" id="statCard">
      <div class="stat-value">+197%</div>
      <div class="stat-desc">4年累计增长率</div>
    </div>
  </div>

  <!-- 来源标注 -->
  <div class="source-line" id="sourceLine">
    * Stars 数据为各年度新增量，统计截止至每年 12 月 31 日
  </div>

  <!-- GSAP CDN -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
  <script>
    // 注册 window.__timelines
    window.__timelines = {};

    // 图表容器总高度（用于计算条形高度比例）
    const CHART_MAX_HEIGHT = 480; // px，对应最大数据值 100k
    const MAX_VALUE = 100;

    // 条形数据
    const barData = [28, 42, 55, 67, 83];

    // 入场时间线
    const tlIntro = gsap.timeline({ paused: true });

    tlIntro
      // 顶部装饰线伸展
      .to('#topAccent', { width: '100%', duration: 0.6, ease: 'power2.out' }, 0)
      // 标题淡入
      .to('#header', { opacity: 1, y: 0, duration: 0.7, ease: 'power3.out' }, 0.2)
      // Y 轴淡入
      .to('#yAxis', { opacity: 1, duration: 0.5, ease: 'power2.out' }, 0.3)
      // 统计卡片飞入
      .to('#statCard', { opacity: 1, x: 0, duration: 0.6, ease: 'back.out(1.5)' }, 0.4);

    // 条形依次增长动画
    barData.forEach((value, i) => {
      const targetHeight = (value / MAX_VALUE) * CHART_MAX_HEIGHT;
      tlIntro
        .to(`#bar${i}`, {
          height: targetHeight,
          duration: 0.7,
          ease: 'power2.out'
        }, 0.6 + i * 0.12)
        .to(`#dl${i}`, {
          opacity: 1,
          duration: 0.3,
          ease: 'power2.out'
        }, 0.6 + i * 0.12 + 0.5);
    });

    // 来源标注淡入
    tlIntro.to('#sourceLine', { opacity: 1, duration: 0.5 }, 1.8);

    window.__timelines.intro = tlIntro;

    // Ambient 微动效（轻微呼吸感）
    const tlAmbient = gsap.timeline({ repeat: -1, yoyo: true });
    tlAmbient.to('#statCard', {
      y: -4,
      duration: 3,
      ease: 'sine.inOut'
    });

    window.__timelines.ambient = tlAmbient;

    // 自动播放
    tlIntro.play();
  </script>
</body>
</html>
```

---

## generate_frames 调用示例

```python
# 生成数据可视化帧
result = generate_frames(
    frames=[
        {
            "frame_id": "rust-github-stars",
            "html_content": "<...上方完整 HTML...>",
            "duration": 5.0,        # 停留较长，供观众读取数据
            "capture_at": 2.5,      # 所有条形动画完成后截图
            "width": 1920,
            "height": 1080,
            "format": "png"
        }
    ],
    output_dir="./output/rust-data/",
    filename_prefix="data_viz"
)

# 也可生成带动画的视频片段
result_video = generate_frames(
    frames=[{
        "frame_id": "rust-github-stars",
        "html_content": "...",
        "duration": 4.0
    }],
    output_format="webm",
    fps=60,
    output_dir="./output/rust-data/"
)
```
