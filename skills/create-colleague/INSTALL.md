# 赛博同事 / Cyber Colleague 安装与验证

## 1. 基础准备 / Basic Setup

```bash
git clone https://github.com/titanwings/colleague-skill ./skills/create-colleague
cd ./skills/create-colleague
python -m py_compile tools/*.py
```

如只使用手动上传的 PDF、截图、邮件、Markdown 或粘贴文本，做到这里就够了。  
If you only use manually uploaded PDFs, screenshots, emails, Markdown, or pasted text, this is enough.

## 2. 可选依赖 / Optional Dependencies

自动采集只在需要时安装对应依赖：  
Install dependencies only when you need auto-collection:

```bash
python -m pip install -r requirements.txt
```

如果你只需要部分来源，也可以按需安装：  
If you only need specific sources, install selectively:

```bash
python -m pip install requests
python -m pip install slack-sdk
python -m pip install playwright
playwright install chromium
```

## 3. 推荐环境变量 / Recommended Environment Variables

### 飞书自动采集 / Feishu Auto Collection

```text
COLLEAGUE_FEISHU_APP_ID
COLLEAGUE_FEISHU_APP_SECRET
COLLEAGUE_FEISHU_USER_ACCESS_TOKEN
COLLEAGUE_FEISHU_REFRESH_TOKEN
COLLEAGUE_FEISHU_P2P_CHAT_ID
```

说明 / Notes:
- 配置文件只保留非敏感字段。  
  Config files persist only non-sensitive fields.
- 应用密钥和用户凭据建议通过环境变量注入。  
  App secrets and user credentials should be injected via environment variables.
- 私聊消息采集需要用户身份授权。  
  Private chat collection requires user-level authorization.

### 飞书 MCP / Feishu MCP

```text
COLLEAGUE_FEISHU_APP_ID
COLLEAGUE_FEISHU_APP_SECRET
COLLEAGUE_FEISHU_USER_ACCESS_TOKEN
```

### 钉钉自动采集 / DingTalk Auto Collection

```text
COLLEAGUE_DINGTALK_APP_KEY
COLLEAGUE_DINGTALK_APP_SECRET
```

说明 / Notes:
- 历史消息采集依赖浏览器自动化。  
  Historical message collection relies on browser automation.
- 配置文件默认只保留非敏感字段。  
  Config files keep only non-sensitive fields by default.

### Slack 自动采集 / Slack Auto Collection

```text
COLLEAGUE_SLACK_BOT_TOKEN
```

说明 / Notes:
- Bot 需要先加入目标频道。  
  The bot must be added to target channels first.
- 实际权限范围以脚本提示和工作区配置为准。  
  Required scopes depend on script prompts and workspace configuration.

## 4. 浏览器模式 / Browser Mode

浏览器模式适合读取你当前账号已经可以访问的页面：  
Browser mode is suitable for pages your current account can already access:

```bash
python tools/feishu_browser.py --help
```

说明 / Notes:
- 该模式不会提升权限，只使用当前浏览器会话可访问的内容。  
  This mode does not elevate permissions; it only uses content already accessible in your current browser session.
- 首次使用前请确认本机浏览器环境和 Playwright 已准备完成。  
  Make sure your local browser environment and Playwright are ready before first use.

## 5. 快速验收 / Quick Verification

建议先跑这些命令确认入口正常：  
Run these commands first to verify the entry points:

```bash
python tools/skill_writer.py --help
python tools/version_manager.py --help
python tools/email_parser.py --help
python tools/feishu_browser.py --help
python tools/feishu_auto_collector.py --help
python tools/dingtalk_auto_collector.py --help
python tools/slack_auto_collector.py --help
python tools/feishu_mcp_client.py --help
```

## 6. SkillHub 上传 / SkillHub Upload

等你准备好再生成 SkillHub 版本压缩包：  
Generate the SkillHub package only when you are ready:

```bash
python tools/package_skillhub.py
```

默认输出 / Default output:

```text
dist/create-colleague-skillhub-v1.2.1.zip
```

上传前确认 / Before upload:

1. zip 根目录直接包含 `SKILL.md` / The zip root directly contains `SKILL.md`
2. 不包含本地 `colleagues/` 示例或真实数据 / It does not include local `colleagues/` sample or real data
3. 不包含任何第三方凭据 / It does not include any third-party credentials

更多检查项见 [SKILLHUB_UPLOAD.md](SKILLHUB_UPLOAD.md)。  
See [SKILLHUB_UPLOAD.md](SKILLHUB_UPLOAD.md) for the full checklist.
