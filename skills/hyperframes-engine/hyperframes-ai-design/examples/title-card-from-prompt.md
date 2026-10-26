# 标题帧设计示例：从用户描述到生成帧 HTML

## 场景描述

用户输入：
> "帮我做一个 Rust 编程语言介绍视频的标题帧，要现代感强"

---

## Step 1：意图解析

解析用户描述，推断关键参数：

```json
{
  "frame_type": "title_card",
  "topic": "Rust 编程语言介绍",
  "style_hint": "现代感强",
  "inferred_style": "Swiss Pulse",
  "alt_style": "Neon Grid",
  "color_mood": "dark_tech",
  "motion_level": "ambient",
  "language": "zh-CN"
}
```

**推断逻辑：**
- "现代感强" → 倾向 Swiss Pulse（几何精确、高对比度）或 Neon Grid（发光线条、科技氛围）
- Rust 语言主题 → 偏向工程美学，选择 **Swiss Pulse**
- 编程类内容 → 深色背景更符合开发者审美

---

## Step 2：设计系统确认

选定风格：**Swiss Pulse**

```json
{
  "design_system": {
    "style": "Swiss Pulse",
    "colors": {
      "background": "#0a0a1a",
      "primary": "#ffffff",
      "accent": "#ff4500",
      "accent_secondary": "#e8e8e8",
      "dim": "rgba(255,255,255,0.15)"
    },
    "typography": {
      "title_size": "96px",
      "subtitle_size": "32px",
      "font_family": "'Inter', 'Helvetica Neue', sans-serif",
      "font_weight_title": 900,
      "font_weight_subtitle": 300
    },
    "geometry": {
      "decorators": ["circle_outline", "diagonal_line", "rect_fill", "small_dots"],
      "motion": "ambient_drift"
    }
  }
}
```

---

## Step 3：Prompt 展开

**简短 Prompt：**
> Rust 2024 标题帧，深色背景，白色大标题，橙色点缀

**展开后完整描述：**
- 背景：深海军蓝近黑 `#0a0a1a`，右上角有轻微网格纹理
- 标题："Rust 2024"，96px，极粗体，纯白
- 副标题："内存安全 · 零成本抽象 · 并发无惧"，32px，细体，浅灰
- 装饰件：左侧橙色大圆（镂空），右下角斜切矩形，两条平行斜线
- 入场动画：标题从下方 40px 飞入，背景渐显，装饰件旋转展开
- 时长：入场约 1.2 秒，ambient 循环

---

## Step 4：完整 HTML 代码

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=1920, height=1080">
  <title>Rust 2024 标题帧</title>
  <style>
    /* 重置与基础 */
    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
      width: 1920px;
      height: 1080px;
      overflow: hidden;
      background: #0a0a1a;
      font-family: 'Inter', 'Helvetica Neue', 'PingFang SC', sans-serif;
      position: relative;
    }

    /* 背景网格纹理 */
    .bg-grid {
      position: absolute;
      inset: 0;
      background-image:
        linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
      background-size: 60px 60px;
      opacity: 0;
    }

    /* 装饰件：左侧大圆（镂空） */
    .deco-circle {
      position: absolute;
      left: -120px;
      top: 50%;
      transform: translateY(-50%);
      width: 520px;
      height: 520px;
      border: 3px solid #ff4500;
      border-radius: 50%;
      opacity: 0;
    }

    /* 装饰件：右下角斜切矩形 */
    .deco-rect {
      position: absolute;
      right: 80px;
      bottom: 60px;
      width: 200px;
      height: 4px;
      background: #ff4500;
      transform: rotate(-12deg);
      opacity: 0;
    }

    /* 装饰件：斜线组 */
    .deco-lines {
      position: absolute;
      right: 160px;
      bottom: 100px;
      width: 140px;
      height: 4px;
      background: rgba(255,255,255,0.2);
      transform: rotate(-12deg);
      opacity: 0;
    }

    /* 装饰件：小圆点矩阵 */
    .deco-dots {
      position: absolute;
      right: 200px;
      top: 120px;
      display: grid;
      grid-template-columns: repeat(5, 12px);
      gap: 14px;
      opacity: 0;
    }
    .deco-dots span {
      width: 4px;
      height: 4px;
      border-radius: 50%;
      background: rgba(255, 69, 0, 0.6);
      display: block;
    }

    /* 主内容区 */
    .content {
      position: absolute;
      left: 160px;
      top: 50%;
      transform: translateY(-50%);
    }

    /* 顶部标签 */
    .label {
      font-size: 18px;
      font-weight: 400;
      letter-spacing: 6px;
      color: #ff4500;
      text-transform: uppercase;
      margin-bottom: 24px;
      opacity: 0;
    }

    /* 主标题 */
    .title {
      font-size: 96px;
      font-weight: 900;
      color: #ffffff;
      line-height: 1;
      letter-spacing: -2px;
      margin-bottom: 32px;
      opacity: 0;
      transform: translateY(40px);
    }

    /* 分割线 */
    .divider {
      width: 0;
      height: 2px;
      background: linear-gradient(90deg, #ff4500, transparent);
      margin-bottom: 28px;
    }

    /* 副标题 */
    .subtitle {
      font-size: 32px;
      font-weight: 300;
      color: #e8e8e8;
      letter-spacing: 2px;
      opacity: 0;
    }
  </style>
</head>
<body>
  <!-- 背景层 -->
  <div class="bg-grid" id="bgGrid"></div>

  <!-- 装饰件层 -->
  <div class="deco-circle" id="decoCircle"></div>
  <div class="deco-rect" id="decoRect"></div>
  <div class="deco-lines" id="decoLines"></div>
  <div class="deco-dots" id="decoDots">
    <!-- 5x3 点矩阵 -->
    <span></span><span></span><span></span><span></span><span></span>
    <span></span><span></span><span></span><span></span><span></span>
    <span></span><span></span><span></span><span></span><span></span>
  </div>

  <!-- 主内容 -->
  <div class="content">
    <div class="label" id="label">Programming Language</div>
    <h1 class="title" id="title">Rust 2024</h1>
    <div class="divider" id="divider"></div>
    <p class="subtitle" id="subtitle">内存安全 · 零成本抽象 · 并发无惧</p>
  </div>

  <!-- GSAP CDN -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
  <script>
    // 注册 window.__timelines 供帧渲染器调用
    window.__timelines = {};

    // 入场动画时间线
    const tlIntro = gsap.timeline({ paused: true });

    tlIntro
      // 背景网格渐显
      .to('#bgGrid', { opacity: 1, duration: 0.8, ease: 'power2.out' }, 0)
      // 装饰圆展开
      .to('#decoCircle', { opacity: 0.7, scale: 1, duration: 1.0, ease: 'expo.out' }, 0.1)
      // 标签淡入
      .to('#label', { opacity: 1, y: 0, duration: 0.6, ease: 'power3.out' }, 0.2)
      // 主标题从下飞入
      .to('#title', { opacity: 1, y: 0, duration: 0.8, ease: 'expo.out' }, 0.35)
      // 分割线伸展
      .to('#divider', { width: 480, duration: 0.6, ease: 'power2.out' }, 0.55)
      // 副标题淡入
      .to('#subtitle', { opacity: 1, duration: 0.7, ease: 'power2.out' }, 0.7)
      // 右侧装饰件
      .to('#decoRect', { opacity: 1, duration: 0.4, ease: 'power2.out' }, 0.5)
      .to('#decoLines', { opacity: 1, duration: 0.4, ease: 'power2.out' }, 0.6)
      .to('#decoDots', { opacity: 1, duration: 0.5, ease: 'power2.out' }, 0.65);

    window.__timelines.intro = tlIntro;

    // Ambient 循环动画（入场完成后自动启动）
    const tlAmbient = gsap.timeline({ repeat: -1, yoyo: true });

    tlAmbient
      .to('#decoCircle', {
        rotation: 8,
        x: 10,
        duration: 6,
        ease: 'sine.inOut'
      })
      .to('#decoDots', {
        y: -8,
        duration: 5,
        ease: 'sine.inOut'
      }, 0);

    window.__timelines.ambient = tlAmbient;

    // 自动播放入场动画
    tlIntro.play();
  </script>
</body>
</html>
```

---

## Step 5：验证通过说明

| 检查项 | 状态 | 备注 |
|--------|------|------|
| 分辨率 1920×1080 | ✅ | body 固定宽高 |
| 标题字号 ≥ 80px | ✅ | 96px |
| 副标题字号 ≥ 28px | ✅ | 32px |
| 几何装饰件 ≥ 3 个 | ✅ | 圆、矩形、斜线、点阵共 4 个 |
| window.__timelines 注册 | ✅ | intro + ambient |
| 入场动画时长合理 | ✅ | 约 1.4s 完成 |
| 深色背景 | ✅ | #0a0a1a |
| UTF-8 编码 | ✅ | |

---

## generate_frames 调用示例

```python
# 生成单帧截图
result = generate_frames(
    frames=[
        {
            "frame_id": "rust-2024-title",
            "html_content": "<...上方完整 HTML...>",
            "duration": 3.0,        # 帧停留时长（秒）
            "capture_at": 1.5,      # 截图时间点（入场完成后）
            "width": 1920,
            "height": 1080,
            "format": "png"
        }
    ],
    output_dir="./output/rust-intro/",
    filename_prefix="frame"
)

print(result)
# 输出：{"frames": [{"id": "rust-2024-title", "path": "./output/rust-intro/frame_001.png", "status": "ok"}]}
```

**也可导出为视频片段：**

```python
result = generate_frames(
    frames=[{"frame_id": "rust-2024-title", "html_content": "...", "duration": 4.0}],
    output_format="webm",
    fps=60,
    output_dir="./output/rust-intro/"
)
```
