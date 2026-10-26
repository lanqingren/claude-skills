# 从零构建 Composition HTML 完整规则

本文档定义了 HyperFrames 中每个 Composition HTML 文件的完整构建规范，
包括骨架结构、层次体系、GSAP 编排规则和禁止事项。

---

## 一、HTML 文件基本骨架

每个 composition 文件必须以以下结构为起点：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=1920, initial-scale=1.0" />
  <title>HyperFrames Composition</title>

  <!-- GSAP 核心库 -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>

  <style>
    /* 基础重置 */
    *, *::before, *::after {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    html, body {
      width: 1920px;
      height: 1080px;
      overflow: hidden;
      background: #000;
    }

    /* 舞台容器 */
    #stage {
      position: relative;
      width: 1920px;
      height: 1080px;
      overflow: hidden;
    }
  </style>
</head>
<body>
  <div id="stage">

    <!-- 背景层 -->
    <div class="layer-background" style="z-index: 10;"></div>

    <!-- 装饰层 -->
    <div class="layer-decoration" style="z-index: 20;"></div>

    <!-- 内容层 -->
    <div class="layer-content" style="z-index: 30;"></div>

    <!-- 叠加层 -->
    <div class="layer-overlay" style="z-index: 40;"></div>

  </div>

  <script>
    // 动画逻辑写在此处
  </script>
</body>
</html>
```

**视口固定为 1920×1080**，不使用响应式布局，所有尺寸使用 px 绝对值。

---

## 二、层次结构规范

HyperFrames 采用四层固定层次模型，每层职责明确、不得混用：

### background-layer（背景层）z-index: 10

职责：纯视觉背景，不承载任何文字信息。
内容：纯色填充、渐变背景、背景图片、大面积色块。
约束：不得含有可读信息，不得设置 pointer-events。

```css
.layer-background {
  position: absolute;
  inset: 0;
  z-index: 10;
}
```

---

### decoration-layer（装饰层）z-index: 20

职责：纯视觉装饰，增加空间感与风格感，不承载信息。
内容：几何形状、线条、粒子、图案、抽象元素。
约束：所有装饰件的不透明度应控制在 10%-25% 之间，不得抢夺视觉焦点。

```css
.layer-decoration {
  position: absolute;
  inset: 0;
  z-index: 20;
  pointer-events: none;
}
```

---

### content-layer（内容层）z-index: 30

职责：所有可读内容的唯一承载层。
内容：标题、副标题、正文、数据、品牌标识。
约束：文字对比度必须满足 WCAG AA 标准（对比度 ≥ 4.5:1）。

```css
.layer-content {
  position: absolute;
  inset: 0;
  z-index: 30;
}
```

---

### overlay-layer（叠加层）z-index: 40

职责：全局视觉修饰，叠加在所有内容之上。
内容：扫光效果、全局渐变遮罩、噪点纹理、品牌水印。
约束：不透明度不超过 15%，不得遮挡可读内容。

```css
.layer-overlay {
  position: absolute;
  inset: 0;
  z-index: 40;
  pointer-events: none;
}
```

---

## 三、window.__timelines 注册规范

每个 composition 必须将所有 GSAP Timeline 注册到 `window.__timelines`，
供 HyperFrames 渲染引擎统一调度与时序控制。

```javascript
// 初始化注册容器
window.__timelines = window.__timelines || {};

// 创建主时间线
const mainTimeline = gsap.timeline({ paused: true });

// 添加入场动画序列
mainTimeline
  .from('.headline', {
    duration: 0.8,
    y: 60,
    opacity: 0,
    ease: 'power2.out'
  })
  .from('.subtitle', {
    duration: 0.6,
    y: 40,
    opacity: 0,
    ease: 'power2.out'
  }, '-=0.3');

// 注册到全局调度器
window.__timelines.main = mainTimeline;

// 如有环境动效时间线，单独注册
const ambientTimeline = gsap.timeline({ repeat: -1, yoyo: true });
// ...
window.__timelines.ambient = ambientTimeline;

// 通知渲染引擎时间线已就绪
if (typeof window.__onTimelinesReady === 'function') {
  window.__onTimelinesReady();
}
```

**命名规范**：
- `main` — 主入场时间线，必须存在
- `ambient` — 环境循环动效（可选）
- `outro` — 收尾退场动效（可选）

---

## 四、GSAP Choreography 规则

### 入场动画（Entrance）

使用 `power2.out`，强调快速到达目标位置后缓慢停止的动感：

```javascript
// 标准入场：从下方位移 + 淡入
gsap.from(element, {
  duration: 0.8,
  y: 60,
  opacity: 0,
  ease: 'power2.out'
});

// 强力入场（标题专用）：更大位移
gsap.from('.headline', {
  duration: 1.0,
  y: 100,
  opacity: 0,
  ease: 'power2.out'
});
```

**入场规则**：
- 元素按视觉层次依次入场，间隔 0.2-0.3 秒
- 背景层最先入场，内容层最后
- 初始状态（opacity: 0）必须通过 CSS 预设，避免闪烁

---

### 环境动效（Ambient）

使用 `sine.inOut`，创造平滑的呼吸感循环，不打断主视觉焦点：

```javascript
// 浮动效果（装饰件常用）
gsap.to('.deco-circle', {
  duration: 4,
  y: -20,
  ease: 'sine.inOut',
  repeat: -1,
  yoyo: true
});

// 缩放脉冲（强调元素）
gsap.to('.pulse-element', {
  duration: 3,
  scale: 1.05,
  opacity: 0.8,
  ease: 'sine.inOut',
  repeat: -1,
  yoyo: true
});
```

**环境动效规则**：
- 幅度克制：位移不超过 30px，缩放不超过 1.1
- 每个装饰件的动效时长应有差异，避免同步感（±0.5-1 秒随机化）

---

### 收尾动画（Outro）

使用 `power3.in`，快速加速离场，制造干净利落的退出感：

```javascript
// 标准退场
gsap.to('.content-group', {
  duration: 0.6,
  y: -80,
  opacity: 0,
  ease: 'power3.in'
});
```

---

## 五、装饰件实现模板

### 圆形（Circle）

```html
<!-- HTML 结构 -->
<div class="deco-circle" style="
  position: absolute;
  width: 400px;
  height: 400px;
  border-radius: 50%;
  border: 1px solid currentColor;
  top: -100px;
  right: -100px;
  opacity: 0.15;
"></div>
```

```javascript
// GSAP 动效
gsap.to('.deco-circle', {
  duration: 6,
  scale: 1.08,
  ease: 'sine.inOut',
  repeat: -1,
  yoyo: true
});
```

---

### 矩形（Rect）

```html
<!-- HTML 结构 -->
<div class="deco-rect" style="
  position: absolute;
  width: 200px;
  height: 3px;
  background: currentColor;
  bottom: 120px;
  left: 80px;
  opacity: 0.2;
  transform-origin: left center;
"></div>
```

```javascript
// GSAP 动效：宽度扩展入场
gsap.from('.deco-rect', {
  duration: 1.2,
  scaleX: 0,
  ease: 'power2.out'
});
```

---

### 三角形（Triangle）

```html
<!-- 使用 clip-path 实现 -->
<div class="deco-triangle" style="
  position: absolute;
  width: 120px;
  height: 120px;
  background: currentColor;
  clip-path: polygon(50% 0%, 0% 100%, 100% 100%);
  bottom: 200px;
  right: 300px;
  opacity: 0.12;
"></div>
```

```javascript
// GSAP 动效：旋转漂浮
gsap.to('.deco-triangle', {
  duration: 8,
  rotation: 15,
  y: -25,
  ease: 'sine.inOut',
  repeat: -1,
  yoyo: true
});
```

---

## 六、排版规则

| 层级       | 用途         | 字号范围      | 行高        | 字重        |
|------------|--------------|---------------|-------------|-------------|
| 一级标题   | 主视觉焦点   | 64px – 160px  | 1.0 – 1.15  | 700 – 900   |
| 二级标题   | 副标题/标语  | 28px – 56px   | 1.2 – 1.35  | 400 – 600   |
| 正文       | 说明/数据    | 18px – 28px   | 1.4 – 1.6   | 300 – 400   |

**核心排版原则**：
- 最多使用 3 个层级，超过 3 级会破坏视觉层次
- 同一 composition 最多使用 2 种字体（标题体 + 正文体）
- 文字与背景对比度不低于 4.5:1（WCAG AA）
- 避免纯白 `#FFFFFF` 直接写在纯黑 `#000000` 上，应使用 `#F0F0F0` 软化

---

## 七、禁止项完整列表

以下行为在任何 composition 中均被**严格禁止**：

1. **禁止使用 JavaScript 动态修改 DOM 结构**
   原因：渲染引擎在动画执行前已完成 DOM 快照，运行时 DOM 变更会导致时序错乱

2. **禁止使用 CSS animation / transition 替代 GSAP**
   原因：无法被 `window.__timelines` 调度，导致动效脱离统一时序控制

3. **禁止在 decoration-layer 中放置文字信息**
   原因：装饰层不在可访问性检查范围内，文字将被忽略

4. **禁止装饰件不透明度超过 25%**
   原因：高透明度装饰件会与内容层产生视觉竞争，降低信息可读性

5. **禁止单帧出现超过 14 个视觉元素**
   原因：元素过多导致视觉噪声，渲染性能下降

6. **禁止使用外部图片 URL（http/https）**
   原因：网络图片在离线渲染环境中无法加载，应使用 base64 内嵌或 CSS 生成图形

7. **禁止硬编码具体内容文字**
   原因：所有可替换内容必须使用模板变量，保证模板复用性

8. **禁止在 overlay-layer 中使用超过 15% 不透明度的遮罩**
   原因：过重的叠加层会显著降低下层内容的可读性

9. **禁止在环境动效中使用 linear 缓动做循环动画**
   原因：linear 循环在视觉上产生机械感，破坏自然流动体验
