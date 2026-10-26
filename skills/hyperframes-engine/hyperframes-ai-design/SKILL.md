# Hyperframes AI 自由设计技能

## 触发条件

当以下任一条件成立时，必须遵循本技能：

- 用户未指定模板，要求 AI 自由创作帧 HTML
- 用户明确要求"自由设计"或"不用模板"
- 现有模板均不适合用户描述的内容

本技能指导 AI 为 `generate_frames` 工具生成高质量的 Composition HTML。

---

## 7 步工作流（强制顺序，HARD-GATE 保护）

### Step 1：意图解析

读取 `references/design-intent.md`。

从用户描述推断：
- **视觉风格**（8 种之一，见 design-intent.md）
- **内容密度**（精简 / 标准 / 丰富）
- **运动能量**（静态 / 轻柔 / 动感）
- **时长预估**（每帧 3-10 秒）
- **色调方向**（暗调 / 明调 / 中性）

**输出格式**：
```
推断风格：Swiss Pulse
内容密度：标准
运动能量：动感
色调：暗调
每帧时长：5s
```

---

### Step 2：设计系统确认

- 项目有 `design.md` → 读取精确的 hex 颜色、字体名称、间距约束
- 没有 → 根据推断风格向用户确认一次，格式：

```
我将使用以下设计系统，请确认或调整：
- 主色：#1a1a2e（深蓝黑）
- 强调色：#e94560（荧光红）
- 字体：Inter（标题）/ DM Sans（正文）
- 风格：Swiss Pulse — 几何精准 + 高对比
```

★ **HARD-GATE：Step 2 完成前不得写任何 HTML**

---

### Step 3：Prompt 扩展（单帧项目可跳过）

读取 `references/composition-from-scratch.md`。

按以下格式展开设计 Prompt：

```
[标题+风格块]
项目：xxx，风格：Swiss Pulse，色调：暗调

[节奏声明]
帧总数 N，整体节奏：3s 建立 → 5s 展开 → 2s 收尾

[全局规则]
- 背景层：2-5 个几何装饰件，每件带 GSAP ambient motion
- 字体：Inter 700（标题 ≥ 64px），DM Sans 400（正文 ≥ 28px）
- 禁止：渐变文字 / cyan-on-dark / 纯黑白背景

[逐帧 beat]
帧1（frame-1，5s）：标题入场，headline 从下飞入，背景几何块 scale+fade
帧2（frame-2，6s）：核心数据展示...

[循环主题]
右上角装饰圆持续旋转，贯穿全片

[负面提示]
避免：卡片网格布局 / 过多文字 / 低对比配色
```

★ **HARD-GATE：Step 3 完成前不得进入构建**

---

### Step 4：构建 Composition HTML

读取 `references/composition-from-scratch.md` 中的完整规则集。

每帧 HTML 必须满足：

**结构层次**（按 z-index 从低到高）：
1. `background-layer`：纯色或渐变背景（无图片背景！）
2. `decoration-layer`：2-5 个几何/抽象装饰件，opacity 10-25%
3. `content-layer`：主体文字和图表
4. `overlay-layer`（可选）：装饰线、噪点纹理

**排版硬约束**：
- headline ≥ 64px，font-weight ≥ 700
- body text ≥ 28px，line-height ≥ 1.5
- 最多 3 级文字层级
- 对比度 WCAG AA（4.5:1）

**GSAP 运动约束**：
- 所有 timeline 注册到 `window.__timelines = window.__timelines || []`
- 使用 `gsap.timeline()` 并 `.push(tl)` 到数组
- 每个装饰件至少有一个 ambient motion（慢速旋转/脉冲/漂移）
- ease 多样：入场用 `power2.out`，ambient 用 `sine.inOut`，收尾用 `power3.in`

**禁止项**：
- 渐变文字（`-webkit-background-clip: text`）
- cyan-on-dark（#00ffxx 系配色）
- 重复卡片网格
- 纯 `#000000` 或 `#ffffff` 背景

**CDN 引用模板**：
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
```

---

### Step 5：验证

在交付前检查以下项目（心算/代码审查，无需实际运行）：

- [ ] `window.__timelines` 数组已初始化并注册所有 timeline
- [ ] 装饰件数量 2-5 个，每件有 ambient motion
- [ ] headline ≥ 64px，body ≥ 28px
- [ ] 禁止项全部规避
- [ ] 视觉元素总数 8-10 个（含装饰件）
- [ ] HTML 为完整独立文件（含 `<!DOCTYPE html>`）

★ **HARD-GATE：验证通过前不得交付**

---

### Step 6：交付

读取 `references/save-as-template.md`，了解如何将设计保存为模板。

交付格式：
1. 完整 HTML 代码
2. 调用示例（generate_frames 工具参数）
3. 保存为模板的建议（如果设计值得复用）

---

### Step 7：多轮迭代

读取 `references/iteration-dialogue.md`。

主动询问：
- 视觉效果是否符合预期？
- 是否需要调整某帧的文字/颜色/运动？
- 是否要将此设计保存为模板？

---

## 参考文件索引

| 文件 | 何时读取 |
|------|---------|
| `references/design-intent.md` | Step 1：风格推断 |
| `references/composition-from-scratch.md` | Step 3-4：构建规则 |
| `references/template-anatomy.md` | Step 6：了解模板结构 |
| `references/save-as-template.md` | Step 6：保存模板流程 |
| `references/iteration-dialogue.md` | Step 7：迭代对话 |
| `references/quality-checklist.md` | Step 5：验证清单 |
| `examples/title-card-from-prompt.md` | 参考标题帧示例 |
| `examples/data-viz-from-prompt.md` | 参考数据可视化示例 |
| `examples/brand-intro-from-prompt.md` | 参考品牌介绍示例 |
