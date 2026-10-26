---
name: wecom-cli-installer
description: 企业微信 CLI 一键安装助手。当用户提到「安装企业微信 CLI」「安装 wecom-cli」「企微 CLI 怎么安装」「一键安装企微」「配置企业微信机器人」「初始化企微 CLI」「wecom-cli 安装」「企业微信命令行工具安装」「wecom-cli 装了但没反应」「wecom-cli 报错」「wecom-cli 连接失败」「wecom-cli 找不到命令」「wecom-cli 失败」时，使用本 Skill。自动完成 Node.js 检测、CLI 安装、Skills 技能包安装、验证和初始化引导全流程，并提供故障排查指引。
---

# 企业微信 CLI 一键安装助手

## 工具简介

本 Skill 提供企业微信 CLI（wecom-cli）的全自动安装向导，涵盖：

- Node.js 环境检测（版本 < 18 时提示升级）
- `@wecom/cli` npm 全局安装（自动识别国内网络并切换淘宝镜像）
- Skills 技能包安装（`npx skills add WeComTeam/wecom-cli -y -g`）
- 安装验证
- 初始化引导（Bot ID + Secret 配置说明）

安装完成后即可通过命令行操作企业微信的通讯录、文档、消息、会议、日程、待办等功能。

---

## 前置要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows x64 / macOS x64/arm64 / Linux x64/arm64 |
| Node.js | **≥ 18**（推荐 LTS 最新版） |
| 企业微信账号 | 目前仅对 **≤ 10 人企业**开放 |
| Bot 权限 | 需在企业微信中创建智能机器人，获取 Bot ID 和 Secret |

---

## 安装工作流

### Step 1：运行一键安装脚本

调用脚本 `scripts/install.py` 完成全部安装步骤：

```powershell
# 基础安装（自动检测环境，安装完成后显示初始化引导）
python "$env:USERPROFILE\.workbuddy\skills\wecom-cli-installer\scripts\install.py"

# 带凭证参数（在引导提示中显示 Bot ID / Secret 供参考）
python "$env:USERPROFILE\.workbuddy\skills\wecom-cli-installer\scripts\install.py" --bot-id "YOUR_BOT_ID" --secret "YOUR_SECRET"

# 仅安装，跳过 init 引导（已配置过的用户）
python "$env:USERPROFILE\.workbuddy\skills\wecom-cli-installer\scripts\install.py" --skip-init

# 国内网络强制使用淘宝镜像
python "$env:USERPROFILE\.workbuddy\skills\wecom-cli-installer\scripts\install.py" --registry https://registry.npmmirror.com
```

脚本自动完成：
1. 检测 Node.js 版本（< 18 则退出并提示升级）
2. `npm install -g @wecom/cli`（失败自动建议淘宝镜像重试）
3. `npx skills add WeComTeam/wecom-cli -y -g`
4. 验证 `wecom-cli --version`
5. 检测是否已有配置，按需引导 init

---

### Step 2：获取 Bot ID 和 Secret（首次配置）

> ⚠️ `wecom-cli init` **必须在真实交互式终端（TTY）中执行**，不能通过管道/脚本自动化传参。

1. 打开企业微信客户端
2. 进入「工作台」→「智能机器人」
3. 点击「手动创建」→ 选「API 模式创建」
4. 连接方式选「使用长连接」
5. 保存页面上的 **Bot ID** 和 **Secret**
6. 在「可见成员」中添加需要使用的成员
7. 在「授权」页面开启所需权限（通讯录/消息/文档等）

---

### Step 3：在真实终端中执行 init

```bash
wecom-cli init
```

交互步骤：
1. 方向键选「手动输入 Bot ID 和 Secret」→ 回车
2. 输入 Bot ID → 回车
3. 输入 Secret → 回车
4. 看到「初始化完成 ✅」

---

### Step 4：验证安装

```powershell
# 检查版本
wecom-cli --version

# 拉取通讯录（有数据返回即表示配置成功）
chcp 65001 | Out-Null
wecom-cli contact get_userlist '{}'
```

期望输出：
```json
{
  "errcode": 0,
  "errmsg": "ok",
  "userlist": [ ... ]
}
```

---

## 故障排查

详见 `references/troubleshooting.md`，或参考以下快速索引：

| 错误 | 快速方案 |
|------|----------|
| `wecom-cli: command not found` | 检查 npm 全局 bin 是否在 PATH |
| `not connected` / 连接失败 | 检查 Bot 状态和可见成员配置 |
| Node.js 版本过低 | 安装 nvm，执行 `nvm install --lts` |
| npm 安装超时（国内） | 加 `--registry https://registry.npmmirror.com` |
| 配置文件存在但无法连接 | 删除 `~/.config/wecom/` 后重新 init |

---

## 特殊场景

### 已安装 + 已有配置

如果用户说「已经装过了但不知道怎么用」或「wecom-cli 装好了」，直接跳转到使用文档（参见「企业微信」Skill）：

```powershell
# 快速验证配置
chcp 65001 | Out-Null
wecom-cli contact get_userlist '{}'

# 查看支持命令
wecom-cli --help
```

若遇到 `not connected` 或其他错误，按 `references/troubleshooting.md` 排查。

---

## 手动安装（备选）

```bash
# 1. 安装 CLI
npm install -g @wecom/cli

# 2. 安装 Skills 包
npx skills add WeComTeam/wecom-cli -y -g

# 3. 初始化（交互式终端）
wecom-cli init
```

---

## 配置文件位置

| 平台 | 路径 |
|------|------|
| Windows | `%USERPROFILE%\.config\wecom\` |
| macOS/Linux | `~/.config/wecom/` |

包含文件：
- `bot.enc` — 加密存储的 Bot 凭证
- `mcp_config.enc` — MCP 配置
- `.encryption_key` — 本地加密密钥

---

## 参考资料

- GitHub：https://github.com/WecomTeam/wecom-cli
- 官方文档：https://open.work.weixin.qq.com/help2/pc/21676
