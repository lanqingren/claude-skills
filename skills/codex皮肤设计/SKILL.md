---
name: codex皮肤设计
description: 为 Codex 客户端创作一个完整的装饰皮肤。当用户需要新的 Codex 主题、指定风格背景、或按参考提示词生成皮肤时使用。本技能用 gpt-image-2 生成纯背景图并编写 theme.json，按皮肤 ID 落盘到环境变量 CODEX_SKIN_DIR 目录下的独立文件夹。这是纯皮肤设计指导，生效由客户端负责。
---

# Codex 皮肤设计指导

一个皮肤 = **一张纯背景壁纸 + 一份 theme.json**。你的工作只有两件事：
用 gpt-image-2 (优先查找 Gpt Image2 Generation Expert 是否可用) 画出合规的纯背景图、写好 theme.json，按规范放进皮肤目录即可。
如何注入、生效、切换都由客户端自动完成，本指导不涉及。

## 存放位置

- 皮肤根目录 = 环境变量 **`CODEX_SKIN_DIR`** 指向的目录。**每个皮肤是它下面一个
  以皮肤 ID 命名的独立文件夹**：`$CODEX_SKIN_DIR/<皮肤ID>/`。
- 读取变量：Windows 下 `%CODEX_SKIN_DIR%`（PowerShell `$env:CODEX_SKIN_DIR`）。
  若变量为空，回退到当前运行目录下的 `skin/`。
- 只在自己的皮肤文件夹内写文件；**不要改动 `common/`、`default/` 或其他皮肤目录**。

## 目录结构

根目录 = `$CODEX_SKIN_DIR`。你要新建的是其下**以皮肤 ID 命名的一个文件夹**：

```
$CODEX_SKIN_DIR/                 ← 皮肤根目录（环境变量指向）
├── common/  default/  ...       客户端自带，勿动
└── <皮肤ID>/                    ← 你要新建的文件夹（名字 = theme.json 的 id）
    ├── theme.json               必须：皮肤元数据（见字段表）
    ├── background.jpg           必须：gpt-image-2 生成的纯背景壁纸
    │                                  （文件名须与 theme.json 的 image 逐字一致）
    ├── skin.css                 可选：仅当需要该皮肤专属样式时才写
    └── inject.js                可选：仅当需要该皮肤专属逻辑时才写
```

**必须写入 `$CODEX_SKIN_DIR/<皮肤ID>/` 的文件：**

| 文件 | 必填 | 内容 |
|---|---|---|
| `theme.json` | 是 | 皮肤元数据，`id` 须等于文件夹名，`image` 须等于背景图文件名 |
| `background.jpg` | 是 | gpt-image-2 产出的 `2560 × 1440` 纯背景壁纸（也可 `.png`/`.webp`，扩展名与 `image` 一致） |
| `skin.css` | 否 | 该皮肤专属样式（非必要不创建，留空即用通用样式） |
| `inject.js` | 否 | 该皮肤专属逻辑（非必要不创建，留空即用通用逻辑） |

> 绝大多数皮肤只需 `theme.json` + `background.jpg` 两个文件即可，`skin.css`/`inject.js`
> 是高级覆盖项，非必要不创建。

可参考的现成模板：`$CODEX_SKIN_DIR/codex/`（含 theme.json + 背景图）；
其它示例 `gothic-void-crusade/`（含 colors 高级配色）、`red-white-scifi/`。

## 创作流程

1. **定方向**：和用户敲定皮肤风格，一句话说清 4 个要素——**主体、色系、明暗、氛围**。
   参考写法（照着造你自己的即可）：
   - “右侧一位原创成年女性，粉白玫瑰美妆，高调柔光，浪漫甜美” → 浅色人物系
   - “右侧一位原创成年男性，黑金舞台礼服，暖金轮廓光，克制电影感” → 暗色人物系
   - “无人物，红白未来城市 + 巨型能量球，晨曦冷调，宏大宁静” → 纯场景系
   - “米白手账纸背景，青绿/珊瑚撞色涂鸦，明亮活力，动漫少年” → 插画系
   把选定的方向填进第 4 步提示词模板的 `SCENE`/`SUBJECT`/`COLOR PALETTE` 等变量。
2. **起 ID 与名称**：ID 用全小写短横线（如 `sakura-dawn`），它同时是文件夹名与
   `theme.json` 的 `id`；`name` 为中文/显示名。
3. **建文件夹**：在 `$CODEX_SKIN_DIR` 下按皮肤 ID 新建目录 `$CODEX_SKIN_DIR/<皮肤ID>/`
   （先解析该环境变量取得真实路径；为空则回退到运行目录下的 `skin/`）。
4. **用 gpt-image-2 生成纯背景图**：**图像生成模型固定使用 `gpt-image-2`**。将下方
   “背景图硬约束 + 通用提示词模板”作为提示词，尺寸设为 `2560 × 1440`（16:9），
   产出一张**纯背景壁纸**（无任何 UI、文字、窗口）。把结果**保存为
   `$CODEX_SKIN_DIR/<皮肤ID>/background.jpg`**（或 .png/.webp），最终文件 ≤ 16 MB。
   - gpt-image-2 不直接吐 16:9 时，取最接近的横向尺寸生成后裁到 `2560 × 1440`。
5. **写 theme.json**：按下方字段表填写，保存为 `$CODEX_SKIN_DIR/<皮肤ID>/theme.json`；
   `id` 须等于文件夹名，`image` 必须与背景图文件名（含扩展名）逐字一致。
6. **（可选）专属资源**：仅当需要该皮肤独立样式/逻辑时，才在同目录写 `skin.css`
   / `inject.js`；否则不创建。
7. **交付**：文件放好即完成。告诉用户皮肤已就绪，可在客户端“选择皮肤”里选中它。
   （切换、生效由客户端负责，本指导不处理。）

## theme.json 字段表

```json
{
  "schemaVersion": 1,
  "id": "sakura-dawn",
  "name": "樱花晨曦",
  "brandSubtitle": "CODEX DREAM SKIN",
  "tagline": "把柔光与玫瑰带进今天的工作台。",
  "projectPrefix": "选择项目 · ",
  "projectLabel": "◉  选择项目",
  "statusText": "DREAM SKIN ONLINE",
  "quote": "MAKE SOMETHING WONDERFUL",
  "image": "background.jpg",
  "appearance": "auto",
  "art": { "focusX": 0.72, "focusY": 0.45, "safeArea": "left", "taskMode": "ambient" }
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `schemaVersion` | 是 | 固定为 `1` |
| `id` | 是 | 皮肤唯一标识，须等于文件夹名 |
| `name` | 是 | 前端列表显示名 |
| `image` | 是 | 背景图文件名，须与实际文件完全一致；缺此字段皮肤不生效 |
| `appearance` | 是 | `auto`/`light`/`dark`。`auto` 跟随系统外观；`light`/`dark` 强制固定 |
| `tagline` | 否 | 一句话描述，列表副标题 |
| `brandSubtitle` | 否 | 品牌小标题 |
| `projectPrefix` / `projectLabel` | 否 | 项目选择器文案装饰 |
| `statusText` / `quote` | 否 | 状态条/标语文案 |
| `art.focusX` / `art.focusY` | 否 | 主视觉焦点坐标，0~1（如右侧人物 focusX≈0.72） |
| `art.safeArea` | 否 | 文字安全区：`auto`/`left`/`right`/`center`/`none`，通常 `left` |
| `art.taskMode` | 否 | 任务页背景：`auto`/`ambient`/`banner`/`off` |
| `colors` | 否 | 高级配色覆盖（见 `gothic-void-crusade/theme.json`）：`background`/`panel`/`accent`/`text` 等 |
| `promoTitle` / `promoSub` / `promoUrl` | 否 | 推广信息 |

> 提示：`art` 与 `colors` 省略时，客户端会自动从背景图采样推断焦点、主色与明暗，
> 多数情况留空即可获得合理效果；只有想精确控制时才手写。

## 高级：skin.css / inject.js 怎么写（默认不要写）

> ⚠️ 先分清：调**颜色**用 `theme.json` 的 `colors`，调**焦点/明暗/任务页**用 `art`，
> 这两条能满足 95% 的需求。`skin.css` / `inject.js` 是**整体替换**通用资源（不是补丁、
> 不是追加），一旦创建就得自己扛起整套视觉，很容易把界面写崩。除非用户明确要求超出
> `theme.json` 能力的定制，否则**不要创建这两个文件**。

它们的存在规则（见根目录 `common/`）：
- 皮肤目录里**有** `skin.css` → 用它，**否则**回落到 `common/dream-skin.css`。
- 皮肤目录里**有** `inject.js` → 用它，**否则**回落到 `common/renderer-inject.js`。
- 想微调时的正确姿势：**复制** `common/` 下对应文件到你的皮肤目录，在副本上小改，
  而不是从零手写。

### skin.css 的契约

客户端会把 `inject.js` 注入渲染进程，给 `<html>` 挂上状态类并写入一批 CSS 变量；
你的 CSS 就靠这些**类**和**变量**生效。因此 `skin.css` 必须：

- 所有规则挂在 `html.codex-dream-skin` / `:root.codex-dream-skin` 作用域下，避免污染原生界面。
- **消费**（而非硬编码）客户端注入的变量，明暗才能自适配。核心变量：

  | 变量 | 含义 |
  |---|---|
  | `--dream-art` | 背景图 `url(...)`（客户端已把 base64 塞好，直接用） |
  | `--dream-art-position` | 背景焦点位置，如 `72% 45%` |
  | `--dream-accent` / `--dream-accent-ink` | 主强调色 / 其上文字色 |
  | `--dream-canvas` / `--dream-surface` / `--dream-sidebar` | 画布 / 卡片面 / 侧栏底色 |
  | `--dream-text` / `--dream-text-muted` | 正文 / 次要文字色 |
  | `--dream-line` / `--dream-line-soft` | 描边 / 柔和分隔线 |

- 明暗两态分别写在 `:root.codex-dream-skin`（浅）与 `:root.codex-dream-skin.dream-theme-dark`（暗）。
- 覆盖 Codex 原生样式时基本都要 `!important`（原生权重高）。
- 装饰层务必 `pointer-events: none`，别挡住真实按钮/输入框。

其它可用状态类：`dream-theme-light`/`dream-theme-dark`（明暗）、`dream-safe-left|right|center|none`
（文字安全区）、`dream-task-ambient|banner|off`（任务页背景强度）、`dream-home`/`dream-task`
（首页/任务页容器）、`#codex-dream-skin-chrome`（客户端注入的整屏背景层）。

### inject.js 的契约

`inject.js` 是一段**立即执行函数（IIFE）**，客户端在运行时替换其中 3 个占位符后执行。
自定义时**必须原样保留末尾这行调用与 3 个占位符**（各出现且仅一次）：

```js
((cssText, artDataUrl, rawConfig) => {
  // cssText    = 你的 skin.css 文本（客户端已读入并转义）
  // artDataUrl = 背景图 base64 data URL（如 data:image/jpeg;base64,...）
  // rawConfig  = 解析后的 theme.json 对象（含 appearance / art / colors 等）
  //
  // 职责：把 cssText 注入 <style>、给 <html> 挂 codex-dream-skin 等状态类、
  //       用 root.style.setProperty("--dream-*", ...) 写入变量；
  //       并用 MutationObserver 在 Codex 界面重渲染后自愈（脚本须幂等、可重复执行）。
  return { installed: true };
})(__DREAM_CSS_JSON__, __DREAM_ART_JSON__, __DREAM_THEME_JSON__)
```

- `__DREAM_CSS_JSON__` → 替换为 skin.css 文本的 JS 字符串字面量。
- `__DREAM_ART_JSON__` → 替换为背景图 data URL 的字符串字面量。
- `__DREAM_THEME_JSON__` → 替换为 theme.json 的 JSON 对象。

强烈建议：**别从零写**。直接复制 `common/renderer-inject.js`（已实现幂等注入、明暗探测、
背景图采样、MutationObserver 自愈），只在其逻辑上做增量改动。

## 背景图硬约束（生成时必须满足）

1. 实际尺寸与文件都是 `2560 × 1440`、16:9；不是拉伸的假比例。
2. 边到边铺满的**新壁纸**，不是擦除 UI 的截图、mockup、海报或拼图。
3. 左侧 `x=0%–52%` 为低信息文字安全区：无脸/手/密集花朵/强光斑，但也不是纯白或死黑矩形；
   要能在其上叠加 Codex 原生标题与正文。
4. 同一环境/透视/光线自然连续到 `x=0%–100%`，`x=45%–62%` 无垂直分割缝。
5. 主视觉与识别性道具集中在 `x=62%–88%`、`y=16%–72%`；关键内容距四边至少 8%。
6. 叠加浅色与暗色半透明蒙层后都有层次：无纯白烧穿、无纯黑死区。
7. 画面无任何可读文字、姓名、签名、品牌、Logo、水印。
8. 画面无窗口边框、菜单栏、侧栏、卡片、按钮、图标、输入框、聊天/代码面板、指针、设备外框。
9. 人物必须明确成年，自然且无重复/多余/畸形的脸、手指、肢体。

## 通用提示词模板（喂给 gpt-image-2）

**图像生成一律用 `gpt-image-2` 模型**，尺寸 `2560 × 1440`。把下面整段作为提示词，
花括号变量替换为第 1 步定好的方向；无授权人物参考时保留 “original fictional adult” 默认值。
末尾 `AVOID` 一行是通用负面词，支持负面提示词的话可单独粘贴使用。

```text
USE CASE: {photorealistic-natural / stylized-concept}
ASSET TYPE: Adaptive desktop wallpaper for Codex
PRIMARY REQUEST: Create one standalone desktop wallpaper, exactly 2560x1440 pixels, 16:9 landscape, opaque, edge-to-edge continuous artwork. This is the source background that sits underneath a real Codex interface, not a screenshot and not a UI concept.
COMPOSITION: Reserve x=0%-52% as a calm text-safe zone with low visual information and continuous natural texture. Place the visual subject center at x=68%-76%; keep face, hands, and identity-critical details within x=62%-88%. Keep all critical vertical details within y=16%-72%; face within y=20%-52%. Keep every essential detail at least 8% from every edge. The left safe zone must contain no face, hands, dense flowers, sharp architecture, or hard edge.
SCENE: {describe 5-12 visible environment objects, wardrobe, props, season, atmosphere}. Concentrate detail and directional lighting around the right-side subject. Rebuild the left side as one believable continuation of the same scene.
SUBJECT: Show one original fictional adult {woman/man/person} by default. Do not imitate any named public figure, celebrity, private person, copyrighted character, or brand mascot.
MATERIALS: {name 3-6 concrete materials and how they absorb/scatter/reflect light}.
LIGHTING AND MOOD: {light direction, softness, time of day, emotional tone}.
COLOR PALETTE: {4-6 named colors}; keep strongest contrast around the right-side focal area.
LIGHT/DARK COMPATIBILITY: Broad tonal separation, controlled midtones. Avoid pure white and crushed black in the left safe zone. Preserve texture under a light or dark translucent overlay.
INVARIANTS: One continuous physical scene across x=0%-100%, one perspective, at most one primary subject, natural anatomy, no vertical seam, no UI geometry. Output only the final opaque wallpaper.
AVOID: screenshot, UI, software window, sidebar, panel, card, rounded rectangle, button, icon, input box, code editor, cursor, device frame, poster, readable text, typography, logo, watermark, split screen, collage, duplicate person, extra limbs, malformed hands, cropped face, cropped hands.
```

## 护栏（务必遵守）

- **只用无 UI 的纯背景壁纸**：绝不把截图、假窗口、侧栏、卡片、输入框、Logo
  或烤进位图的文字当作皮肤背景。
- **appearance 权威性**：`auto` 跟随系统外观，图片亮度只微调配色，不得翻转明暗模式；
  `light`/`dark` 为强制值。
- **肖像与版权**：默认生成原创虚构成年人物；只有在拥有肖像与素材使用权时才使用真人参考图，
  不得用姓名诱导模仿未授权真人；未成年、名人肖像、受版权角色一律禁止。
- **图片体积**：拒绝空文件或超过 16 MB 的图片。
- **文件名一致**：`theme.json` 的 `image` 必须与皮肤目录中的实际背景图文件名逐字一致，
  否则该皮肤会被判为“资源不完备”。

## 自检清单（交付前）

- [ ] 已解析 `CODEX_SKIN_DIR`，文件夹落在 `$CODEX_SKIN_DIR/<皮肤ID>/`（不是别处）
- [ ] `$CODEX_SKIN_DIR/<皮肤ID>/theme.json` 存在，`id` 与文件夹名一致，`image` 指向存在的背景图
- [ ] `$CODEX_SKIN_DIR/<皮肤ID>/background.jpg` 由 gpt-image-2 生成，`2560 × 1440`、16:9、无任何 UI/文字、≤ 16 MB
- [ ] 未误改 `common/`、`default/` 或其他皮肤目录
- [ ] 左侧 `x=0%–52%` 干净可叠字，浅/暗蒙层下均有层次
- [ ] 在客户端“选择皮肤”里能看到并选中该皮肤

