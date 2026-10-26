# 赛博同事 / Cyber Colleague

把同事的聊天、文档、邮件和笔记整理成一个可复用的 AI Skill。  
Turn a coworker's chats, docs, emails, and notes into a reusable AI skill.

## 它做什么 / What It Does

- 提取工作方法、评审习惯和沟通风格。  
  Extracts work methods, review habits, and communication patterns.
- 把人工标签和原始材料证据结合起来。  
  Combines manual labels with evidence from source materials.
- 生成一个可持续迭代的同事技能包。  
  Generates a colleague skill package that can evolve over time.

## 支持的素材 / Supported Inputs

| 来源 Source | 消息 Messages | 文档 / Wiki Docs | 表格 Tables | 说明 Notes |
| --- | --- | --- | --- | --- |
| 飞书自动采集 Feishu auto collection | 支持 Yes | 支持 Yes | 支持 Yes | 需要应用凭据或浏览器模式 / Requires app credentials or browser mode |
| 钉钉自动采集 DingTalk auto collection | 部分 Partial | 支持 Yes | 支持 Yes | 历史消息依赖浏览器自动化 / Historical messages rely on browser automation |
| Slack 自动采集 Slack auto collection | 支持 Yes | 不支持 No | 不支持 No | 需要工作区 Bot / Requires a workspace bot |
| PDF | 不支持 No | 支持 Yes | 不支持 No | 手动上传 / Manual upload |
| 图片 / 截图 Images / screenshots | 支持 Yes | 不支持 No | 不支持 No | 手动上传 / Manual upload |
| 飞书 JSON 导出 Feishu JSON export | 支持 Yes | 支持 Yes | 不支持 No | 手动上传 / Manual upload |
| 邮件 `.eml` / `.mbox` | 支持 Yes | 不支持 No | 不支持 No | 手动上传 / Manual upload |
| Markdown / TXT | 支持 Yes | 支持 Yes | 不支持 No | 手动上传 / Manual upload |
| 直接粘贴文字 Pasted text | 支持 Yes | 不支持 No | 不支持 No | 手动输入 / Manual input |

## 本地使用 / Local Setup

```bash
git clone https://github.com/titanwings/colleague-skill ./skills/create-colleague
cd ./skills/create-colleague
python -m py_compile tools/*.py
```

如需启用自动采集，再按需安装依赖：  
Install optional dependencies only when you need auto-collectors:

```bash
python -m pip install -r requirements.txt
```

更详细的接入方式见 [INSTALL.md](INSTALL.md)。  
See [INSTALL.md](INSTALL.md) for source-specific setup.

## 调用方式 / How To Use

在支持本地 skill 的 agent 运行时中加载本目录后，按 [`SKILL.md`](SKILL.md) 的引导提供：  
Load this directory in any agent runtime that supports local skills, then follow [`SKILL.md`](SKILL.md) and provide:

1. 同事姓名或代号 / The coworker's name or alias
2. 角色简介 / A short role summary
3. 可选的人格或沟通标签 / Optional personality or communication labels
4. 一份或多份原始材料 / One or more source materials

生成后的同事 skill 默认位于 `./colleagues/{slug}/`。  
Generated colleague skills are stored in `./colleagues/{slug}/` by default.

## 安全与打包 / Security And Packaging

- 第三方凭据优先使用环境变量提供，不建议写入磁盘。  
  Prefer environment variables for third-party credentials instead of writing them to disk.
- SkillHub 打包脚本默认不包含本地 `colleagues/` 示例或真实数据。  
  The SkillHub packaging script excludes local `colleagues/` sample or real data by default.
- 浏览器模式只会读取你当前已能访问的页面内容，不会额外提升权限。  
  Browser mode only reads pages you can already access in your current browser session.

需要时再生成适合 SkillHub 上传的压缩包：  
Build a SkillHub-ready package only when you are ready:

```bash
python tools/package_skillhub.py
```

默认输出 / Default output:

```text
dist/create-colleague-skillhub-v1.2.1.zip
```

上传前检查见 [SKILLHUB_UPLOAD.md](SKILLHUB_UPLOAD.md)。  
Pre-upload checks are listed in [SKILLHUB_UPLOAD.md](SKILLHUB_UPLOAD.md).
