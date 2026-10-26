# 生成质量硬约束检查清单

每次交付 Composition HTML 前必须逐项确认。FAIL 即重写，不得跳过。

---

## 视觉元素（8-10 个）

| # | 检查项 | 判断标准 | FAIL 示例 | PASS 示例 |
|---|--------|---------|---------|---------|
| 1 | 视觉元素总数 8-10 | 数清：背景+装饰件+标题+副标题+图表+线条+图标… | 只有标题+背景=2个 | 标题+副标题+3装饰件+分隔线+标签+背景=9个 |
| 2 | 背景层存在 | `background-layer` div 有明确背景色/渐变 | `<body>` 无背景色 | `background:#0a0a1a` 深色底 |
| 3 | 装饰件数量 2-5 | 统计 `decoration-layer` 下子元素 | 0个装饰件 | 3个几何形状 |
| 4 | 装饰件 opacity 10-25% | 每个装饰件 `opacity: 0.10`~`0.25` | opacity:0.8（抢夺注意力） | opacity:0.15 |
| 5 | 无空白大区域 | 屏幕四象限各有视觉内容 | 右下角完全空白 | 右下角有小装饰件 |

---

## 排版

| # | 检查项 | 判断标准 | FAIL | PASS |
|---|--------|---------|------|------|
| 6 | headline ≥ 64px | `font-size` 数值或 CSS var | `font-size:2rem`（32px） | `font-size:72px` |
| 7 | body text ≥ 28px | 所有正文段落 | `font-size:14px` | `font-size:30px` |
| 8 | 最多 3 级文字层级 | H1/H2/H3 或等效 class | H1+H2+H3+H4+caption=5级 | 标题+副标题+说明=3级 |
| 9 | line-height ≥ 1.5 | 所有文字块 | `line-height:1.2` | `line-height:1.6` |
| 10 | 对比度 WCAG AA | 前景/背景色对比 ≥ 4.5:1 | 灰字#888 on #0a0a1a（对比~2:1） | 白字#f0f0f0 on #0a0a1a（对比~15:1） |
| 11 | 无渐变文字 | 禁止 `-webkit-background-clip:text` | `background-clip:text;color:transparent` | 单色文字 |

---

## 运动（GSAP）

| # | 检查项 | 判断标准 | FAIL | PASS |
|---|--------|---------|------|------|
| 12 | `window.__timelines` 已初始化 | 文件顶部有 `window.__timelines = window.__timelines \|\| []` | 无此行 | 初始化语句存在 |
| 13 | 所有 timeline 已注册 | 每个 `gsap.timeline()` 后 `.push()` 到数组 | `const tl = gsap.timeline()` 未注册 | `window.__timelines.push(tl)` |
| 14 | 装饰件有 ambient motion | 每个装饰件至少 1 个持续循环动画 | 装饰件静止无动画 | `gsap.to(deco, {rotation:360, repeat:-1, duration:20, ease:'none'})` |
| 15 | ease 多样性 | 入场/ambient/收尾 使用不同 ease | 全部 `ease:'linear'` | 入场 `power2.out`，ambient `sine.inOut`，收尾 `power3.in` |
| 16 | 无 `setTimeout` 控制动画时序 | 全部用 GSAP timeline delay | `setTimeout(()=>animate(), 1000)` | `tl.to(..., {delay:1})` |

---

## 技术

| # | 检查项 | 判断标准 | FAIL | PASS |
|---|--------|---------|------|------|
| 17 | 完整独立 HTML 文件 | 包含 `<!DOCTYPE html>`、`<html>`、`<head>`、`<body>` | 仅片段 `<div>...</div>` | 完整文件结构 |
| 18 | GSAP 从 CDN 加载 | `<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/...">` | 无 GSAP 引用 | CDN script tag 存在 |
| 19 | 无外部图片依赖 | `<img src>` 只引用资产 ID 或 data URI，不引用外部 URL | `<img src="https://example.com/img.jpg">` | `<img src="./asset_abc.jpg">` 或 data URI |
| 20 | viewport meta 正确 | `<meta name="viewport" content="width=device-width,initial-scale=1">` | 无 viewport meta | meta tag 存在 |
| 21 | 无 `console.log` 遗留 | 生产代码不含调试语句 | `console.log('debug')` | 无 |

---

## 可访问性

| # | 检查项 | 判断标准 | FAIL | PASS |
|---|--------|---------|------|------|
| 22 | 主要文字有 `role` 或语义标签 | headline 用 `<h1>`/`<h2>` 或 `aria-label` | `<div class="title">` 无语义 | `<h1>` 或 `<div role="heading" aria-level="1">` |
| 23 | 装饰件标记为 presentational | `aria-hidden="true"` | 装饰 div 无 aria 属性 | `<div class="deco" aria-hidden="true">` |

---

## 禁止项速查（任意一项触发 → 强制重写）

1. 渐变文字（`-webkit-background-clip: text`）
2. cyan-on-dark（`#00ffxx` 系在深色背景上）
3. 重复卡片网格（≥3 个相同结构的卡片平铺）
4. 纯 `#000000` 背景
5. 纯 `#ffffff` 背景（除非刻意明调风格且已确认）
6. 无 GSAP 的静态帧（装饰件必须有 ambient motion）
7. 字体大小 < 28px 的正文
8. `setTimeout` 控制动画时序
9. 外部图片 URL（非资产系统内的 http/https 图片）
