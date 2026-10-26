# HTML 报告输出指南

## 概述

从 v4.0.0 起，高考志愿填报报告**默认输出为自包含 HTML 文件**，而非 Markdown。

HTML 报告提供更好的可读性、视觉层次和交互体验。

## 模板文件

模板位置：`templates/report-template.html`

这是一个**占位符模板**，所有 `{{PLACEHOLDER}}` 标记需要 Agent 在生成时替换为实际内容。

## 占位符替换对照表

### 全局变量
| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{{REPORT_TITLE}}` | 报告标题 | 湖南2026物理类 志愿方案 |
| `{{REPORT_SUBTITLE}}` | 副标题 | 物化地 · 选科覆盖率94% |
| `{{SCORE}}` | 高考分数 | 475 |
| `{{RANK}}` | 全省位次 | 134255 |
| `{{SUBJECTS}}` | 选科组合 | 物化地 |
| `{{COVERAGE}}` | 选科覆盖率 | ~94% |
| `{{PROVINCE}}` | 省份 | 湖南省 |
| `{{GAOKAO_MODE}}` | 高考模式 | 新高考 3+1+2 |
| `{{CATEGORY}}` | 科类 | 物理类 |
| `{{REGION_PREF}}` | 地域偏好 | 不限 / 江浙沪 |
| `{{ECONOMY}}` | 家庭经济 | 中等 / 困难 / 优越 |
| `{{CAREER_PREF}}` | 发展诉求 | 优先好就业 |
| `{{LEVEL}}` | 可报考层次 | 省属重点/普通本科 |
| `{{BATCH_LINE}}` | 批次线 | 本科批 396分+ |
| `{{RUSH_PCT}}` | 冲刺比例 | 25 |
| `{{STABLE_PCT}}` | 稳妥比例 | 40 |
| `{{SAFE_PCT}}` | 保底比例 | 35 |
| `{{DATA_SOURCES}}` | 数据来源 | 湖南省教育考试院 |
| `{{GENERATED_AT}}` | 生成时间 | 2026-06-29 |
| `{{SKILL_VERSION}}` | Skill版本 | v4.0.0 |

### 复合区块（用 HTML 片段替换）

#### `{{SCORE_BREAKDOWN}}` — 单科成绩可视化

```html
<div class="info-card" style="grid-column:1/-1">
  <div class="ic-label" style="margin-bottom:12px">单科成绩</div>
  <div class="score-bars">
    <div class="score-bar">
      <span class="sb-label">语文</span>
      <div class="sb-track"><div class="sb-fill" style="width:84%;background:linear-gradient(90deg,var(--hero-accent),var(--hero-accent2))">101</div></div>
    </div>
    <div class="score-bar">
      <span class="sb-label">数学</span>
      <div class="sb-track"><div class="sb-fill" style="width:72%;background:linear-gradient(90deg,var(--hero-accent),var(--hero-accent2))">86</div></div>
    </div>
    <!-- 更多科目... -->
  </div>
</div>
```

注意：sb-fill 的 width = (单科分数/满分×100)%。主科满分150，副科满分100。所以 width% = score/fullmark*100。

#### `{{DATA_ALERT}}` — 数据异常预警（如有）

当分数与位次不匹配时使用：
```html
<div class="alert alert-danger">
  <div class="alert-title">数据核实</div>
  <div>475分在2024年对应约67000名，而134255名对应约405分。请登录省考试院官网核实位次。</div>
</div>
```

不需要时用空字符串替换。

#### `{{RUSH_VOLUNTEERS}}` / `{{STABLE_VOLUNTEERS}}` / `{{SAFE_VOLUNTEERS}}` — 志愿表格

```html
<div class="tier-card">
  <div class="tier-header rush">
    <span class="th-title">🏃 冲刺志愿</span>
    <span class="th-prob">录取概率 40-60%</span>
  </div>
  <table class="tier-table">
    <thead>
      <tr><th>#</th><th>院校</th><th>专业方向</th><th>2024分数</th><th>2024位次</th><th>性质</th><th>推荐理由</th></tr>
    </thead>
    <tbody>
      <tr>
        <td>1</td>
        <td class="school-name">湖南工程学院</td>
        <td>机械设计制造</td>
        <td>437</td>
        <td>103,402</td>
        <td><span class="badge badge-public">公办</span></td>
        <td>理工科优势，本省认可度高</td>
      </tr>
      <!-- 更多... -->
    </tbody>
  </table>
</div>
```

三档用不同 class：`rush` / `stable` / `safe`。

#### `{{SCHOOL_DETAILS}}` — 院校深度解析

```html
<div class="sd-card">
  <div class="sd-name">🏫 岳阳学院</div>
  <div class="sd-meta"><span>公办本科</span><span>湖南岳阳</span><span>2022转设</span></div>
  <div class="sd-body">
    <div class="sd-col">
      <div class="sd-col-label pro">✅ 核心优势</div>
      <ul>
        <li>公办院校，学费低（5000-8000元/年）</li>
        <li>长沙都市圈辐射</li>
      </ul>
    </div>
    <div class="sd-col">
      <div class="sd-col-label con">⚠️ 明显短板</div>
      <ul>
        <li>新转设院校，办学底蕴浅</li>
        <li>实习机会少于长沙</li>
      </ul>
    </div>
  </div>
  <div class="alert alert-info" style="margin-top:12px">
    <div class="alert-title">录取参考</div>
    <div>2024物理类最低 415分（位次124423），录取概率约75%</div>
  </div>
</div>
```

#### `{{MAJOR_DETAILS}}` — 专业深度解析

```html
<div class="major-card">
  <div class="mc-title">📚 电气工程及其自动化</div>
  <div class="mc-sub">工学 · 学制4年 · 核心课程：电路原理、电机学、电力系统分析</div>
  <div class="mc-grid">
    <div class="mc-item"><div class="mc-label">就业率</div><div class="mc-value">95%+</div></div>
    <div class="mc-item"><div class="mc-label">起薪</div><div class="mc-value">8k-15k</div></div>
    <div class="mc-item"><div class="mc-label">核心方向</div><div class="mc-value">国家电网/南方电网</div></div>
    <div class="mc-item"><div class="mc-label">长期趋势</div><div class="mc-value">⬆️ 稳定增长</div></div>
  </div>
  <div class="alert alert-warning" style="margin-top:12px">
    <div class="alert-title">报考提醒</div>
    <div>需选考物理+化学，部分院校要求数学单科成绩</div>
  </div>
</div>
```

#### `{{PITFALL_WARNINGS}}` — 天坑专业提醒

```html
<div class="alert alert-danger">
  <div class="alert-title">天坑专业预警</div>
  <div>生化环材（生物/化学/环境/材料）科研为主就业窄；"信息管理与信息系统"≠"计算机科学"（管理学 vs CS）</div>
</div>
```

#### `{{RISK_ALERTS}}` — 风险提醒

```html
<div class="alert alert-warning">
  <div class="alert-title">投档规则</div>
  <div>湖南采用院校专业组模式，组内调剂。不服从调剂有退档风险。建议稳/保志愿勾选服从。</div>
</div>
<div class="alert alert-danger">
  <div class="alert-title">数据核实</div>
  <div>本报告基于2024年数据，2026年实际录取可能有波动。请查阅2026年一分一段表确认位次。</div>
</div>
```

#### `{{COST_TABLE}}` — 费用参考

```html
<div class="cost-table-wrap">
<table class="cost-table">
  <thead><tr><th>院校类型</th><th>学费/年</th><th>住宿/年</th><th>总计/年</th></tr></thead>
  <tbody>
    <tr><td>公办本科</td><td>5,000-8,000</td><td>800-1,500</td><td>~6,000-9,500</td></tr>
    <tr><td>民办本科</td><td>20,000-30,000</td><td>2,000-3,000</td><td>~22,000-33,000</td></tr>
    <tr><td>公办高职</td><td>3,500-7,000</td><td>800-1,500</td><td>~4,300-8,500</td></tr>
  </tbody>
</table>
</div>
```

## 输出流程

1. 读取 `templates/report-template.html` 原始内容
2. 按对照表逐个替换所有 `{{PLACEHOLDER}}`
3. 复合区块按上述 HTML 片段格式组装
4. 保存为 `.html` 文件到报告目录
5. 用 `[System.IO.File]::WriteAllText(path, html, [System.Text.UTF8Encoding]::new($false))` 写入

## 文件命名规则

```
{省份}{年份}{科类}_{分数}分_{描述}.html
```

示例：`湖南2026物理类_475分_志愿方案.html`

## 注意事项

- **必须自包含**：所有 CSS 内联在 `<style>` 中，不引用外部资源
- **UTF-8 无 BOM**：写入时使用 UTF8Encoding($false)
- **打印友好**：`@media print` 已配置，支持浏览器打印为 PDF
- **响应式**：移动端自动适配
- **导航栏**：顶部 sticky 导航，快速跳转各板块
