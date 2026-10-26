# 04 — 自动化与工作流配置指南

> **版本**：v1.0 (2026-06-01)
> **目标**：把重复操作沉淀为自动化任务
> **适用**：使用 `automation_update` 工具创建/管理自动化任务

---
## 问题诊断决策树

```
自动化不执行？
    │
    ▼
[1] 检查状态
    ├── status 是 "PAUSED"？ → 改成 "ACTIVE"
    └── status 是 "ACTIVE" → 继续排查 ▶

[2] 检查时间
    ├── rrule 写对了吗？→ 用在线 RRULE 验证器检查
    ├── BYHOUR 是 UTC 还是本地时间？→ 确认时区
    ├── validFrom/validUntil 过了有效期？
    └── 刚创建需要等几分钟 → 调度器有轮询间隔

[3] 检查执行记录
    ├── automation_runs 表有记录吗？
    ├── 有记录但输出不对 → 改 prompt
    └── 无记录 → 检查 cwds（工作目录）是否存在

[4] 检查模型配置
    ├── modelId 指定的模型还可用吗？
    └── 没有指定 → 使用默认模型
```

---
## 4.1 自动化类型速查

| 类型 | scheduleType | 适用场景 | 示例 |
|------|-------------|---------|------|
| 循环执行 | `"recurring"` | 每日/每周/每月定时任务 | 每日邮件摘要、每周报告 |
| 一次性 | `"once"` | 单次延迟执行 | 明天下午3点提醒开会 |

---
## 4.2 自动化配置结构

```json
{
  "name": "任务名称",
  "prompt": "要执行的任务描述（保持自给自足，不依赖交互）",
  "mode": "create",
  "scheduleType": "recurring",
  "rrule": "FREQ=DAILY;BYHOUR=9;BYMINUTE=0",
  "cwds": "工作目录（逗号分隔多个）",
  "status": "ACTIVE",
  "modelId": "使用的模型ID（可选，不填用默认）",
  "modelIsThinking": false,
  "validFrom": "2026-03-18",
  "validUntil": "2026-03-22"
}
```

**⚠️ 创建前检查清单：**
```
□ prompt 是否自给自足？（不依赖与用户交互）
□ rrule 时间是否正确？（注意时区）
□ cwds（工作目录）是否存在？
□ status 是否设为 "ACTIVE"？
□ 如是一次性任务，用 scheduleType="once" + scheduledAt
□ 如是循环任务，用 scheduleType="recurring" + rrule
```

---
## 4.3 RRULE 语法速查

### 4.3.1 基础规则

| 规则 | 说明 | 示例 |
|------|------|------|
| `FREQ=DAILY` | 每天 | `FREQ=DAILY;BYHOUR=9;BYMINUTE=0` |
| `FREQ=HOURLY` | 每小时 | `FREQ=HOURLY;BYMINUTE=0` |
| `FREQ=WEEKLY` | 每周 | `FREQ=WEEKLY;BYDAY=MO` |
| `FREQ=MONTHLY` | 每月 | `FREQ=MONTHLY;BYMONTHDAY=1` |
| `FREQ=YEARLY` | 每年 | `FREQ=YEARLY;BYMONTH=1;BYMONTHDAY=1` |

### 4.3.2 BYDAY 星期对照

| 缩写 | 全称 |
|------|------|
| MO | 周一 Monday |
| TU | 周二 Tuesday |
| WE | 周三 Wednesday |
| TH | 周四 Thursday |
| FR | 周五 Friday |
| SA | 周六 Saturday |
| SU | 周日 Sunday |

### 4.3.3 常用组合模板

```json
// 每天9:30执行
{"scheduleType": "recurring", "rrule": "FREQ=DAILY;BYHOUR=9;BYMINUTE=30"}

// 工作日（周一到周五）每天9:00
{"scheduleType": "recurring", "rrule": "FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9;BYMINUTE=0"}

// 每周一、三、五9:00执行
{"scheduleType": "recurring", "rrule": "FREQ=WEEKLY;BYDAY=MO,WE,FR;BYHOUR=9;BYMINUTE=0"}

// 每月1号8:00执行
{"scheduleType": "recurring", "rrule": "FREQ=MONTHLY;BYMONTHDAY=1;BYHOUR=8;BYMINUTE=0"}

// 每小时执行一次
{"scheduleType": "recurring", "rrule": "FREQ=HOURLY;BYMINUTE=0"}

// 工作日（周一到周五）每小时执行
{"scheduleType": "recurring", "rrule": "FREQ=HOURLY;BYDAY=MO,TU,WE,TH,FR"}

// 有效期：3月18日到3月22日
{"validFrom": "2026-03-18", "validUntil": "2026-03-22"}

// 每季度第一天 9:00（1月1日、4月1日、7月1日、10月1日）
{"scheduleType": "recurring", "rrule": "FREQ=MONTHLY;BYMONTH=1,4,7,10;BYMONTHDAY=1;BYHOUR=9;BYMINUTE=0"}
```

### 4.3.4 RRULE 常见错误

| 错误写法 | 正确写法 | 说明 |
|---------|---------|------|
| `BYDAY=Monday` | `BYDAY=MO` | 必须用双字母缩写 |
| `BYHOUR=9:30` | `BYHOUR=9;BYMINUTE=30` | 时间分两个字段 |
| `FREQ=WEEKLY;BYDAY=MO-FR` | `FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR` | WEEKLY不能BYDAY=多天范围，用DAILY |
| `BYMONTH=Jan` | `BYMONTH=1` | 月份用数字 |

---
## 4.4 常用自动化场景模板

### 场景1：每日邮件摘要

```json
{
  "name": "每日邮件摘要",
  "prompt": "使用邮箱连接器查看最近24小时的邮件，生成结构化Markdown摘要。包含：发件人、主题、时间、重要程度（高/中/低）、是否需要回复。按重要程度排序，需要回复的标⭐。输出格式：\n## 邮件摘要（{日期}）\n### 🔴 高优先级（需回复）\n### 🟡 中优先级\n### 🟢 低优先级",
  "mode": "create",
  "scheduleType": "recurring",
  "rrule": "FREQ=DAILY;BYHOUR=9;BYMINUTE=0",
  "status": "ACTIVE"
}
```

### 场景2：每日AI新闻推送

```json
{
  "name": "AI行业日报",
  "prompt": "使用 daily-ai-news 技能，聚合并总结过去24小时的AI领域重要动态。筛选3-5条最有价值的内容，每条包含：标题、一句话摘要、来源链接。输出格式：简洁Markdown列表。",
  "mode": "create",
  "scheduleType": "recurring",
  "rrule": "FREQ=DAILY;BYHOUR=8;BYMINUTE=30",
  "status": "ACTIVE"
}
```

### 场景3：每周投资日历提醒

```json
{
  "name": "本周投资日历",
  "prompt": "使用 westock-data 查询本周投资日历（重要财报发布、新股上市、分红派息、股东大会等），整理成Markdown表格推送。表格格式：| 日期 | 事件类型 | 影响标的 | 备注 |",
  "mode": "create",
  "scheduleType": "recurring",
  "rrule": "FREQ=WEEKLY;BYDAY=SU;BYHOUR=20;BYMINUTE=0",
  "status": "ACTIVE"
}
```

### 场景4：一次性提醒

```json
{
  "name": "开会提醒",
  "prompt": "提醒用户：下午3点有项目会议，请提前准备以下材料：1.上周工作进展 2.本周计划 3.需要讨论的议题",
  "mode": "create",
  "scheduleType": "once",
  "scheduledAt": "2026-05-30T15:00:00+08:00",
  "status": "ACTIVE"
}
```

### 场景5：工作日晨间任务规划

```json
{
  "name": "工作日晨间规划",
  "prompt": "检查今日待办事项，按优先级排序。对于需要人工决策的事项标记出来，等待用户确认。整理为：\n## 今日任务（{日期}）\n### 必做（今日截止）\n### 应做（本周截止）\n### 可做（不紧急）\n### ⚠️ 需要决策（请确认）",
  "mode": "create",
  "scheduleType": "recurring",
  "rrule": "FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=7;BYMINUTE=30",
  "status": "ACTIVE"
}
```

### 场景6：周末工作复盘

```json
{
  "name": "周末工作复盘",
  "prompt": "回顾本周完成的任务，分析时间分配，识别效率痛点，生成一份简洁的工作复盘报告：\n## 本周复盘\n### 完成的任务（X项）\n### 未完成的原因\n### 时间分析\n### 下周改进点",
  "mode": "create",
  "scheduleType": "recurring",
  "rrule": "FREQ=WEEKLY;BYDAY=FR;BYHOUR=18;BYMINUTE=0",
  "status": "ACTIVE"
}
```

---
## 4.5 Prompt 编写规范

### 必须包含的四大要素

```
1. 明确的任务目标：
   "查看邮箱最近24小时的邮件"
   （而不是"处理邮件"）

2. 使用的工具/技能：
   "使用邮箱连接器"
   （让AI知道用什么工具）

3. 输出格式要求：
   "生成Markdown表格，包含发件人、主题、时间、重要性"
   （不给格式就会随意输出）

4. 边界约束：
   "只统计最近24小时，超过24小时的不计入"
   "如果某类数据为空，输出'无'而不是省略该部分"
```

### 编写检查清单

```
□ 任务是自给自足的吗？（不依赖用户交互）
□ 输出格式是否明确？（Markdown/表格/JSON/纯文本？）
□ 时间范围/数据范围是否指定？（避免返回过多数据）
□ 失败场景是否考虑？（如果工具不可用怎么做？）
□ 输出量是否受控？（避免每次输出几十页数据）
```

---
## 4.6 自动化管理命令

```json
// 查看所有自动化
{"mode": "list"}

// 查看单个自动化详情
{"mode": "view", "id": "automation-id"}

// 创建自动化
{"mode": "create", "name": "任务名", "prompt": "任务描述", ...}

// 更新自动化（只传需要修改的字段）
{"mode": "update", "id": "automation-id", "status": "PAUSED"}

// 暂停/恢复
{"mode": "update", "id": "automation-id", "status": "PAUSED"}   // 暂停
{"mode": "update", "id": "automation-id", "status": "ACTIVE"}   // 恢复

// 删除自动化
{"mode": "delete", "id": "automation-id"}
```

**⚠️ 删除注意事项**：
- 必须使用 `automation_update` 工具的 `delete` 模式
- **严禁**使用 `rm`、`sqlite3` 或文件系统操作删除
- 删除是软删除，数据保留但隐藏，可由支持工具恢复

---
## 4.7 自动化故障排查

### 4.7.1 任务不执行

```
排查顺序：
1. status = "PAUSED"？→ 改成 "ACTIVE"
2. 刚创建不到5分钟？→ 调度器有轮询间隔，再等一会
3. validFrom 是未来时间？→ 等到那个时间才触发
4. validUntil 是过去时间？→ 已过期，修改有效期
5. cwds（工作目录）不存在？→ 检查目录是否正确
6. modelId 指定的模型不可用？→ 去掉 modelId 用默认模型
```

### 4.7.2 任务执行了但结果不对

```
排查顺序：
1. prompt 不够具体？→ 补全"工具+格式+约束"
2. 输出被截断？→ 精简 prompt，减少输出量
3. 时间范围理解错误？→ 明确写清楚"最近24小时"而非"今天"
4. 依赖的skill/连接器不可用？→ 检查prompt中引用的工具
```

### 4.7.3 时区问题

```
RRULE 中 BYHOUR 通常使用系统本地时间
如需确认：创建一个简单的测试自动化（如5分钟后执行），观察是否按时触发
```

---
## 4.8 推荐自动化配置

| 名称 | 频率 | 用途 | 优先级 |
|------|------|------|-------|
| 工作日晨间规划 | 工作日7:30 | 查看今日待办，生成优先级排序 | ⭐⭐⭐ |
| 每日邮件摘要 | 每天9:00 | 汇总过去24小时邮件 | ⭐⭐⭐ |
| AI行业日报 | 每天8:30 | 汇总AI领域最新动态 | ⭐⭐ |
| 周末工作复盘 | 每周五18:00 | 回顾一周工作，分析效率 | ⭐⭐ |
| 投资日历提醒 | 每周日20:00 | 预告下周重要财经事件 | ⭐ |

---
## 4.9 扩展阅读

- `05-quick-cards.md` 卡片3：自动化配置的即查即用步骤
- `troubleshooting.md` — 自动化任务的跨领域诊断决策树
- 官方文档：https://www.codebuddy.cn/docs/workbuddy/Overview

---
## 4.10 踩坑经验

- 自动化 prompt 必须自给自足，不能依赖用户交互（没有人在线回答）
- rrule 的 BYHOUR 是系统本地时间，测试时注意时区
- 删除自动化只能用 automation_update delete 模式，绝不能用 rm/sqlite3
- 刚创建的自动化可能5分钟内不触发，调度器有轮询间隔
- cwds 必须是有效存在的目录，否则任务会失败
- 一次性任务用 scheduleType="once"，不要用 recurring+validUntil
