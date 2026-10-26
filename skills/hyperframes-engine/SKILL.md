---
name: hyperframes-engine
description: "通过 hyperframes-engine MCP 服务生成 MP4 视频——模板选择、变量注入、图片资产、TTS 语音合成、内容图谱、帧渲染和 MP4 导出。支持模板快速生成和自由设计两条路径。"
---

# hyperframes-engine MCP 服务使用指南

## 概述

`hyperframes-engine` 是一个 MCP (Model Context Protocol) 服务，提供完整的 HTML-to-MP4 视频生成能力。其核心原理是：将带动画（CSS/GSAP）的 HTML 页面通过 headless Chromium 逐帧渲染为 PNG 序列，再用 ffmpeg 合成 MP4 视频，可选混入 TTS 旁白音轨。

**MCP 服务名称**: `hyperframes-engine`
**传输协议**: stdio JSON-RPC 2.0 / HTTP SSE
**依赖**: Chromium（渲染引擎）、ffmpeg（视频合成）、TTS（语音合成）

### 触发条件

当用户提出以下任一需求时，你必须遵循本技能：
- 生成视频、制作 MP4、导出视频
- 制作产品宣传片、品牌介绍、数据可视化视频
- 创建带动画的标题帧、海报帧、文字动画
- 为内容配音并导出为视频
- 将 HTML 动画渲染为视频文件

---

## 前置检查

**每次会话开始前必须调用 `check_environment`**，确认运行时依赖就绪：

```json
{"tool": "check_environment", "arguments": {}}
```

返回示例：
```json
{
  "chromium": {"ok": true, "version": "Chrome/131.0.0.0"},
  "ffmpeg": {"ok": true, "version": "ffmpeg version 7.1.1"},
  "tts": {"ok": true, "default_provider": "edge", "providers": ["edge"]}
}
```

若 `chromium` 或 `ffmpeg` 为 `false`，渲染工具将无法工作。`tts.ok` 为 `false` 时旁白功能不可用，但视频导出不受影响。

---

## 两大工作路径

根据用户需求，选择以下路径之一：

```
用户需求
    │
    ├─ 用户指定了模板名称 / 需求明确匹配某类模板
    │   └─ → 路径 A：模板快速生成（推荐优先使用）
    │
    └─ 用户要求自由设计 / 无匹配模板 / 明确说"不用模板"
        └─ → 路径 B：自由设计（引用子技能 hyperframes-ai-design）
```

### 路径决策指南

| 场景 | 走路径 | 说明 |
|------|--------|------|
| "做一个产品宣传片" | A | 使用 `frame-product-promo-30s` |
| "做一个品牌宣言开场" | A | 使用 `frame-bold-poster` |
| "做一个数据报告视频" | A | 使用 `frame-data-chart-nyt` 或 `frame-data-rollup` |
| "做一个赛博朋克风格的标题" | A | 使用 `frame-glitch-title` |
| "帮我自由设计一个独特的开场动画" | B | 无模板匹配，走自由设计 |
| "我要的效果模板里没有" | B | 走 hyperframes-ai-design |
| "先用模板试试，不满意再改" | A → B | 先用模板快速出片，不满意则走设计 |

---

## 路径 A：模板快速生成（9 步标准工作流）

### Step 1：搜索和选择模板

#### 1.1 列出所有可用模板

```json
{"tool": "list_templates", "arguments": {"top": 50}}
```

#### 1.2 按意图搜索模板

```json
{"tool": "search_templates", "arguments": {"intent": "产品宣传 多场景", "top": 5}}
```

搜索原理：将 `intent` 分词后与模板的 `name`/`description`/`tags`/`best_for` 做子串匹配，按匹配词数降序排列。

#### 1.3 获取模板详情

`search_templates` 已返回模板的完整信息（`id`、`name`、`description`、`tags`、`best_for` 等），无需额外调用。你可以直接根据返回的 `description` 和 `best_for` 向用户推荐最匹配的模板。

---

### Step 2：创建项目

```json
{"tool": "create_project", "arguments": {
  "name": "产品宣传片",
  "intent": "介绍 Acme AI 产品的核心功能和优势，展示产品界面和用户场景",
  "aspect": "16:9"
}}
```

**参数说明**：
- `name`（必填）：项目名称，用于显示和识别
- `intent`（必填）：项目意图描述，越详细越好，影响后续内容图谱的 `synopsis`
- `aspect`（可选，默认 `"16:9"`）：画幅比例，支持 `"16:9"` / `"9:16"` / `"1:1"`

返回 `project_id`（格式 `proj_{unix毫秒}`），后续所有操作都需要它。

---

### Step 3：绑定模板和设置变量

#### 3.1 绑定模板

```json
{"tool": "set_template", "arguments": {
  "project_id": "proj_1712345678000",
  "template_id": "frame-product-promo-30s"
}}
```

#### 3.2 设置模板变量

**模板变量机制**：每个模板的 HTML 中使用 `{{变量名}}` 语法定义可替换内容。`apply_template` 工具（或直接用 `set_variables`）将变量注入模板，替换所有 `{{变量名}}` 占位符。

你需要先了解所选模板支持哪些变量。查看 `search_templates` 返回结果中模板的 `description` 字段，或参考下方常见模板变量：

**常见模板变量示例**：

`frame-bold-poster` 模板变量：
```json
{"tool": "set_variables", "arguments": {
  "project_id": "proj_1712345678000",
  "variables": "{\"kicker\":\"MANIFESTO\",\"date\":\"Vol.04 · 2026\",\"figure\":\"03\",\"headline\":[\"Make it\",\"loud.\",\"Make it last.\"],\"standfirst\":\"Every slide should land like a printed page.\",\"footer_left\":\"Bold Poster\",\"footer_right\":\"html-video\"}"
}}
```

`frame-glitch-title` 模板变量：
```json
{"tool": "set_variables", "arguments": {
  "project_id": "proj_1712345678000",
  "variables": "{\"title\":\"CYBERPUNK 2077\",\"subtitle\":\"Welcome to the future\"}"
}}
```

`vfx-text-cursor` 模板变量：
```json
{"tool": "set_variables", "arguments": {
  "project_id": "proj_1712345678000",
  "variables": "{\"text\":\"Hello, World!\",\"speed_cps\":30}"
}}
```

**注意**：`variables` 参数必须是合法的 JSON 字符串，key 对应模板中的 `{{key}}` 占位符。

---

### Step 4：构建内容图谱

内容图谱（ContentGraph）定义了视频中所有帧的**节点**及其**播放顺序**。这是一个有向图结构，支持拓扑排序。

```json
{"tool": "generate_content_graph", "arguments": {
  "project_id": "proj_1712345678000",
  "graph_json": "{\"schemaVersion\":1,\"intent\":\"介绍 Acme AI 产品\",\"synopsis\":\"3 帧产品宣传视频：标题帧 → 功能介绍帧 → CTA 结尾\",\"nodes\":[{\"id\":\"frame-1\",\"kind\":\"entity\",\"label\":\"标题帧\",\"frameIntent\":\"展示产品名称和品牌标语\",\"durationSec\":5.0,\"props\":{\"title\":\"Acme AI\"}},{\"id\":\"frame-2\",\"kind\":\"entity\",\"label\":\"功能介绍\",\"frameIntent\":\"展示三大核心功能\",\"durationSec\":6.0},{\"id\":\"frame-3\",\"kind\":\"text\",\"label\":\"CTA 结尾\",\"frameIntent\":\"呼吁用户注册试用\",\"durationSec\":4.0}],\"edges\":[{\"from\":\"frame-1\",\"to\":\"frame-2\",\"kind\":\"sequence\"},{\"from\":\"frame-2\",\"to\":\"frame-3\",\"kind\":\"sequence\"}]}"
}}
```

返回包含 `render_order`（拓扑排序后的节点 ID 列表），后续帧生成按此顺序。

**节点 `kind` 类型**：
- `entity`：实体/人物/事件/产品
- `data`：数值/图表/统计
- `text`：纯文本段落/描述

**边 `kind` 类型**：
- `sequence`：软顺序约束（播放顺序提示，不强制依赖）
- `dependency`：强依赖（To 必须在 From 之后，参与拓扑排序）
- `contrast`：对比关系（仅语义标注，不影响排序）

---

### Step 5：生成帧 HTML

每帧是完整的独立 HTML 文件，包含所有 CSS 和 JS（内联）。

#### 5.1 模板路径：使用 `apply_template` 生成帧 HTML

```json
{"tool": "apply_template", "arguments": {
  "template_id": "frame-bold-poster",
  "variables": "{\"kicker\":\"MANIFESTO\",\"headline\":[\"Make it\",\"loud.\",\"Make it last.\"]}"
}}
```

返回 `{"html_content": "<!DOCTYPE html>..."}` — 已将变量注入模板的完整 HTML。

然后调用 `generate_frames`：

```json
{"tool": "generate_frames", "arguments": {
  "project_id": "proj_1712345678000",
  "frames": "[{\"node_id\":\"frame-1\",\"html_content\":\"<!DOCTYPE html>...\",\"duration_sec\":5}]"
}}
```

#### 5.2 多帧项目示例

```json
{"tool": "generate_frames", "arguments": {
  "project_id": "proj_1712345678000",
  "frames": "[{\"node_id\":\"frame-1\",\"html_content\":\"<!DOCTYPE html><html>...帧1完整HTML...</html>\",\"duration_sec\":5},{\"node_id\":\"frame-2\",\"html_content\":\"<!DOCTYPE html><html>...帧2完整HTML...</html>\",\"duration_sec\":6},{\"node_id\":\"frame-3\",\"html_content\":\"<!DOCTYPE html><html>...帧3完整HTML...</html>\",\"duration_sec\":4}]"
}}
```

**帧 HTML 必须满足的要求**：
- 完整独立的 HTML 文件（含 `<!DOCTYPE html>`）
- 所有 CSS 和 JS 内联（不依赖外部文件）
- 动画使用 CSS `@keyframes` 或 GSAP（CDN 引用：`https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js`）
- GSAP timeline 必须注册到 `window.__timelines = window.__timelines || []`
- 视口尺寸 1920×1080（16:9 默认）

#### 5.3 修改已有帧

```json
{"tool": "edit_frame", "arguments": {
  "project_id": "proj_1712345678000",
  "node_id": "frame-1",
  "html_content": "<!DOCTYPE html>...修改后的HTML..."
}}
```

---

### Step 6：上传图片资产

如果帧 HTML 中引用了本地图片，需要先将图片加入到项目的资产库。

#### 6.1 添加图片

```json
{"tool": "add_image", "arguments": {
  "project_id": "proj_1712345678000",
  "file_path": "D:/images/product-screenshot.png",
  "caption": "产品界面截图"
}}
```

返回：
```json
{
  "id": "a1b2c3d4e5f6a7b8",
  "kind": "image",
  "filename": "a1b2c3d4e5f6a7b8_product-screenshot.png",
  "path": "~/.html-video/projects/proj_1712345678000/assets/a1b2c3d4e5f6a7b8_product-screenshot.png",
  "caption": "产品界面截图"
}
```

**图片引用方式**：
- 在帧 HTML 中使用 `<img src="product-screenshot.png">` — 渲染时引擎会自动在资产库中按文件名匹配
- 或使用 SHA 前缀匹配：`<img src="a1b2c3d4_product-screenshot.png">`

#### 6.2 添加数据文件

```json
{"tool": "add_data", "arguments": {
  "project_id": "proj_1712345678000",
  "file_path": "D:/data/sales.csv"
}}
```

支持 CSV 和 JSON 格式的数据文件。

#### 6.3 查看所有资产

```json
{"tool": "list_assets", "arguments": {
  "project_id": "proj_1712345678000"
}}
```

---

### Step 7：预览帧

在导出前预览单帧截图，确认视觉效果：

```json
{"tool": "render_preview", "arguments": {
  "project_id": "proj_1712345678000",
  "node_id": "frame-1",
  "width": 1920,
  "height": 1080
}}
```

返回：
```json
{
  "format": "png",
  "data": "iVBORw0KGgo...base64编码的PNG图片..."
}
```

将 `data` 字段的 base64 字符串解码即可查看截图。建议在每帧生成后都预览确认。

---

### Step 8：旁白配音（可选）

#### 8.1 列出可用语音

```json
{"tool": "list_voices", "arguments": {}}
```

或按 provider 筛选：
```json
{"tool": "list_voices", "arguments": {"provider": "edge"}}
```


默认语音为 `zh-CN-XiaoxiaoNeural`（晓晓），默认 provider 为 `edge`。

#### 8.2 获取旁白草稿

```json
{"tool": "draft_narration", "arguments": {
  "project_id": "proj_1712345678000"
}}
```

返回每帧的旁白写作提示，包含 `node_id`、`duration_sec` 和空的 `narration_text` 占位。

#### 8.3 生成旁白音频

根据草稿填写每帧旁白文本后，并行调用 TTS 生成音频：

```json
{"tool": "generate_narration", "arguments": {
  "project_id": "proj_1712345678000",
  "narrations": "{\"frame-1\":\"欢迎来到 Acme AI，新一代智能办公助手。\",\"frame-2\":\"三大核心功能：智能文档、自动会议纪要、一键数据分析。\",\"frame-3\":\"立即注册，免费试用 30 天。开启您的智能办公之旅。\"}",
  "voice_id": "zh-CN-YunxiNeural",
  "provider": "edge"
}}
```

返回每帧的音频路径和实际时长（毫秒）：
```json
{
  "ok": true,
  "results": {
    "frame-1": {"audio_path": ".../narration/frame-1.mp3", "duration_ms": 3500},
    "frame-2": {"audio_path": ".../narration/frame-2.mp3", "duration_ms": 5200},
    "frame-3": {"audio_path": ".../narration/frame-3.mp3", "duration_ms": 2800}
  }
}
```

**注意**：
- TTS 并发上限为 5，多帧会自动排队
- 单帧 TTS 失败不影响其他帧（失败帧带 `error` 字段）
- 旁白文本应简洁，与帧时长匹配（语速约 4-5 字/秒）

#### 8.4 按旁白时长调整帧时长

```json
{"tool": "fit_durations", "arguments": {
  "project_id": "proj_1712345678000",
  "padding_sec": 0.5
}}
```

确保每帧的视觉时长 ≥ 旁白时长 + padding（默认 0.5 秒缓冲），避免旁白被截断。

---

### Step 9：导出 MP4

#### 9.1 启动导出

```json
{"tool": "export_mp4", "arguments": {
  "project_id": "proj_1712345678000",
  "fps": 30,
  "with_narration": true,
  "output_path": "D:/output/product-demo.mp4"
}}
```

**参数说明**：
- `fps`（可选，默认 30）：输出帧率，支持 30 / 60
- `with_narration`（可选，默认 false）：是否混入旁白音轨
- `output_path`（可选）：自定义输出路径，不指定则输出到项目目录

**导出流程**（内部）：
1. 渲染阶段（0-60%）：chromedp 逐帧截图 → PNG 序列
2. 拼接阶段（60-85%）：ffmpeg 将 PNG 序列合成为 MP4 片段 → concat 合并
3. 混音阶段（85-100%）：若 `with_narration=true`，ffmpeg 将旁白音轨混入视频

#### 9.2 查询导出进度

导出是耗时操作，通过轮询获取进度：

```json
{"tool": "get_export_progress", "arguments": {
  "project_id": "proj_1712345678000"
}}
```

返回：
```json
{
  "status": "rendering",
  "percent": 45,
  "message": "Rendering frame 2/3 (45%)"
}
```

**状态枚举**：`idle` / `rendering` / `concat` / `mux` / `complete` / `error`

#### 9.3 导出完成后

返回 `output_path`，视频文件已就绪。

---

## 路径 B：自由设计

当用户明确要求"自由设计/不用模板/原创设计"，或 `search_templates` 无匹配结果时，走此路径。

**必须先读取子技能文件 `hyperframes-ai-design\SKILL.md`**，按其 7 步强制工作流完成设计后，再回到本文件的路径 A Step 4（构建内容图谱 → 生成帧 → 预览 → 旁白 → 导出）。

> 子技能 `hyperframes-ai-design\` 目录包含完整的设计规范（6 个参考文档 + 3 个示例），涵盖 8 种视觉风格、Composition HTML 构建规则、质量检查清单等。此处不再赘述。

---


## 错误处理指南

### 工具返回约定

- 工具返回文本（JSON 字符串），不抛出 JSON-RPC error（协议级错误除外）
- 成功响应通常包含 `"ok": true` 字段
- 错误响应直接返回错误描述字符串或带 `"error"` 字段的 JSON

### 常见错误及处理

| 错误场景 | 表现 | 处理方式 |
|---------|------|---------|
| chromium 未安装 | `render_preview` / `export_mp4` 报错 | 提示用户安装 Chromium/Chrome |
| ffmpeg 未安装 | `export_mp4` 报错 | 提示用户安装 ffmpeg |
| 模板 ID 不存在 | `apply_template` 报错 | 用 `search_templates` 重新确认模板 ID |
| 图片文件不存在 | `add_image` 报错 | 确认 `file_path` 是绝对路径且文件存在 |
| 旁白 TTS 单帧失败 | 该帧返回 `"error"` 字段 | 其他帧正常，可重试失败帧 |
| 旁白拼接失败 | `export_mp4` 自动降级 | 导出无音频版本，检查旁白文件 |
| 变量 JSON 格式错误 | `set_variables` 报错 | 检查 `variables` 是否为合法 JSON 字符串 |

### 最佳实践

1. **增量构建**：一次生成一帧，预览确认后再继续
2. **先预览再导出**：用 `render_preview` 确认每帧视觉效果
3. **旁白文本要简短**：每帧旁白控制在帧时长的 80% 以内（约 4-5 字/秒）
4. **及时保存 project_id**：所有操作依赖 project_id，丢失后无法恢复
5. **图片用绝对路径**：`add_image` 的 `file_path` 必须为绝对路径且可读
6. **变量验证**：设置变量前先用 `apply_template` 试生成，确认变量名正确
7. **大项目分批导出**：帧数超过 10 的项目建议分批渲染预览

---

## 附录：模板快速匹配指南

根据用户描述中的关键词，推荐对应模板：

| 用户关键词 | 推荐模板 | 原因 |
|-----------|---------|------|
| 产品宣传、产品介绍、推广 | `frame-product-promo-30s` | 30 秒多场景产品宣传 |
| 品牌宣言、开场、杂志风 | `frame-bold-poster` | 1970s 欧洲社论海报 |
| 数据、图表、统计、KPI | `frame-data-chart-nyt` / `frame-data-rollup` | 专业数据可视化 |
| 赛博朋克、故障、科技感 | `frame-glitch-title` | 故障特效标题 |
| 打字、代码、终端 | `vfx-text-cursor` | 打字机逐字效果 |
| 极简、干净、现代 | `frame-build-minimal` | 极简构建风格 |
| Logo、结尾、品牌 | `frame-logo-outro` | 品牌 Logo 结尾 |
| 电影感、漏光、艺术 | `frame-light-leak-cinema` | 电影漏光效果 |
| 网格、瑞士、排版 | `frame-swiss-grid` | 瑞士网格排版 |
| 动态文字、动画标题 | `frame-kinetic-type` | 动态文字排版 |
| 温暖、复古、胶片 | `frame-warm-grain` | 温暖胶片颗粒感 |
| 奢华、高端、丝绸 | 走路径 B（Velvet Standard） | 模板中没有该风格 |
| 赛博霓虹、电竞 | 走路径 B（Neon Grid） | `frame-glitch-title` 不够则走设计 |
| 单色极简 | 走路径 B（Minimal Mono） | 走自由设计更灵活 |
