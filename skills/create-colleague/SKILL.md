---
name: create-colleague
description: Use when turning a coworker's chats, docs, emails, and notes into a reusable AI skill that captures work methods and communication patterns.
argument-hint: "[colleague-name-or-slug]"
version: "1.2.1"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash
---

# 赛博同事 / Cyber Colleague

把同事的聊天、文档、邮件和笔记蒸馏成一个可复用、可迭代的 AI Skill。  
Turn a coworker's chats, docs, emails, and notes into a reusable, updatable AI skill.

## 使用语言 / Language

- 默认跟随用户当前对话语言回复。  
  Match the user's language in the current conversation.
- 对外文档和说明尽量采用中英对照。  
  Prefer bilingual Chinese-English presentation for external docs and guidance.

## 适用场景 / When To Use

在这些场景下启用本 skill：  
Use this skill in the following situations:

- 用户要“创建一个同事 skill / 赛博同事 / colleague skill”。  
  The user wants to create a colleague skill or cyber colleague.
- 用户要从聊天记录、文档、邮件、截图中提炼某位同事的工作方式。  
  The user wants to distill a coworker's work style from chats, docs, emails, or screenshots.
- 用户要对已生成的同事 skill 追加材料、纠正结论、重新生成。  
  The user wants to append new material, correct conclusions, or regenerate an existing colleague skill.

## 核心原则 / Core Principles

- 先证据，后结论。  
  Evidence first, conclusions second.
- 工作能力和沟通风格分开整理，但最终合并呈现。  
  Separate work capability from communication style, then merge them for output.
- 如果材料不足，要明确说“不足”，不要强行脑补。  
  If material is insufficient, say so explicitly instead of guessing.
- 更新已有 skill 时，优先增量修改并保留历史版本。  
  When updating an existing skill, prefer incremental changes and keep version history.

## 输入材料 / Accepted Inputs

- 飞书、钉钉、Slack 自动采集结果。  
  Auto-collected output from Feishu, DingTalk, or Slack.
- 飞书 JSON 导出、邮件 `.eml/.mbox`、Markdown、TXT。  
  Feishu JSON exports, email `.eml/.mbox`, Markdown, and TXT.
- PDF、截图、图片、直接粘贴的聊天或文档片段。  
  PDFs, screenshots, images, and pasted chat or document excerpts.
- 用户手动填写的角色简介、印象标签、背景信息。  
  Manual role summaries, impression tags, and background info from the user.

## 工具映射 / Tool Map

| 任务 Task | 工具 / 命令 Tool or Command |
| --- | --- |
| 读取 PDF、图片、文本 | `Read` |
| 写入或更新 skill 文件 | `Write` / `Edit` |
| 解析飞书 JSON | `python tools/feishu_parser.py` |
| 解析邮件 | `python tools/email_parser.py` |
| 飞书自动采集 | `python tools/feishu_auto_collector.py` |
| 飞书浏览器模式 | `python tools/feishu_browser.py` |
| 飞书 MCP 模式 | `python tools/feishu_mcp_client.py` |
| 钉钉自动采集 | `python tools/dingtalk_auto_collector.py` |
| Slack 自动采集 | `python tools/slack_auto_collector.py` |
| 创建 / 更新 / 列出 skill | `python tools/skill_writer.py` |
| 版本管理 | `python tools/version_manager.py` |

## 主流程 / Main Flow

### 1. 收集基础信息 / Collect Basic Info

至少确认这些信息：  
Confirm at least these items:

1. 同事姓名或代号。  
   Coworker name or alias.
2. 角色简介。  
   Short role summary.
3. 可选标签：人格、沟通风格、团队印象。  
   Optional tags: personality, communication style, team impression.

### 2. 选择材料来源 / Choose Input Sources

优先给用户这些选项：  
Offer these options first:

- 自动采集 / Auto-collect
- 上传文件 / Upload files
- 粘贴文本 / Paste text
- 仅基于手填信息生成 / Generate from manual info only

如果用户提供的是飞书链接，先判断走浏览器模式还是 MCP 模式。  
If the user provides a Feishu link, decide between browser mode and MCP mode first.

### 3. 分成两条线分析 / Analyze In Two Tracks

**A. 工作能力 / Work Capability**
- 负责范围、系统边界、技术栈、评审重点、输出偏好。  
  Responsibility scope, system boundaries, stack, review focus, output preferences.

**B. 沟通与风格 / Communication And Style**
- 表达方式、决策习惯、协作方式、常见语气。  
  Expression style, decision habits, collaboration style, common tone.

### 4. 先预览再落盘 / Preview Before Writing

先给用户看摘要，再决定是否写入文件：  
Show the user a summary before writing files:

- Work 摘要 / Work summary
- Persona 摘要 / Persona summary
- 需要保留的不确定项 / Uncertainties that should remain explicit

### 5. 写入 Skill / Write The Skill

默认写入到 `./colleagues/{slug}/`，包含：  
Write to `./colleagues/{slug}/` by default, including:

- `meta.json`
- `work.md`
- `persona.md`
- `SKILL.md`

如果是更新已有 skill，先备份旧版本，再做增量改写。  
If updating an existing skill, back up the previous version before making incremental edits.

## 输出结构 / Output Structure

- `work.md`：工作方法、评审习惯、技术判断。  
  `work.md`: work methods, review habits, technical judgment.
- `persona.md`：表达风格、沟通方式、行为偏好。  
  `persona.md`: communication style, tone, behavior preferences.
- `meta.json`：基础档案、来源、版本信息。  
  `meta.json`: profile, sources, and version info.
- `SKILL.md`：给运行时使用的完整合成版本。  
  `SKILL.md`: the merged runtime-facing skill document.

## 管理命令 / Management Commands

列出已有同事 skill：  
List existing colleague skills:

```bash
python tools/skill_writer.py --action list --base-dir ./colleagues
```

创建新同事 skill：  
Create a new colleague skill:

```bash
python tools/skill_writer.py --action create --slug <slug> --name <name> --base-dir ./colleagues
```

更新已有同事 skill：  
Update an existing colleague skill:

```bash
python tools/skill_writer.py --action update --slug <slug> --base-dir ./colleagues
```

查看版本历史：  
Inspect version history:

```bash
python tools/version_manager.py --action list --slug <slug> --base-dir ./colleagues
```

回滚到旧版本：  
Rollback to a previous version:

```bash
python tools/version_manager.py --action rollback --slug <slug> --version <version> --base-dir ./colleagues
```

## 安全要求 / Safety Requirements

- 默认使用环境变量传入第三方凭据。  
  Use environment variables for third-party credentials by default.
- 不把真实聊天、文档或凭据打进发布包。  
  Do not package real chats, docs, or credentials into release archives.
- 浏览器模式只读取当前账号本来就能访问的内容。  
  Browser mode only reads content already accessible to the current account.
- 对证据不足、权限不足、依赖缺失要明确报出，不要伪装成成功。  
  Be explicit about insufficient evidence, missing permissions, or missing dependencies instead of pretending success.

## 成功标准 / Success Criteria

- 用户能基于最少输入创建一个结构完整的同事 skill。  
  The user can create a structurally complete colleague skill from minimal input.
- 新材料能增量并入已有 skill，并保留历史版本。  
  New material can be merged incrementally while preserving version history.
- 文档和对外说明保持中英文对照。  
  Docs and outward-facing guidance stay bilingual.
