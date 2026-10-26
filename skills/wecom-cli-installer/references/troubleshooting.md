# wecom-cli 故障排查手册

> 本文档由 `wecom-installer` Skill 使用，记录常见安装和配置问题的排查步骤。

---

## 安装阶段问题

### ❌ `wecom-cli: command not found` / 找不到命令

**原因**：npm 全局安装路径不在系统 PATH 环境变量中。

**排查步骤**：

```powershell
# 1. 查看 npm 全局安装路径
npm config get prefix

# 2. 查看 PATH 是否包含该路径
$env:PATH -split ';'

# 3. 临时生效（当前 PowerShell 会话）
$env:PATH += ";" + (npm config get prefix)

# 4. 永久生效（当前用户）
[System.Environment]::SetEnvironmentVariable(
  "PATH",
  [System.Environment]::GetEnvironmentVariable("PATH","User") + ";" + (npm config get prefix),
  "User"
)
```

**macOS / Linux**：

```bash
npm config get prefix
# 假设输出 /usr/local
export PATH="$PATH:/usr/local/bin"
# 写入 ~/.bashrc 或 ~/.zshrc 使其永久生效
echo 'export PATH="$PATH:/usr/local/bin"' >> ~/.zshrc
```

---

### ❌ npm 安装超时 / ETIMEDOUT / 403 Forbidden

**原因**：国内网络访问 npmjs.org 不稳定。

**解决方案**：

```bash
# 方案 1：切换淘宝镜像（推荐）
npm install -g @wecom/cli --registry https://registry.npmmirror.com

# 方案 2：全局设置淘宝镜像（长期有效）
npm config set registry https://registry.npmmirror.com
npm install -g @wecom/cli

# 方案 3：使用一键安装脚本的 --registry 参数
python install.py --registry https://registry.npmmirror.com
```

---

### ❌ Node.js 版本过低（< 18）

```bash
# 使用 nvm 升级（推荐方式）
# Windows: https://github.com/coreybutler/nvm-windows
nvm install --lts
nvm use --lts
node --version   # 应显示 v18.x 或更高

# 或直接前往官网下载 LTS 版本
# https://nodejs.org
```

---

### ❌ Skills 安装失败（npx skills add 报错）

**说明**：Skills 包是 Agent 辅助增强，不影响 `wecom-cli` 命令行基本使用。

**手动安装**：

```bash
npx skills add WeComTeam/wecom-cli -y -g
```

若仍然失败，跳过此步骤，继续执行 `wecom-cli init` 即可。

---

## 配置阶段问题

### ❌ `wecom-cli init` 无交互 / 输入没反应

**原因**：init 命令需要真实的 TTY 终端，IDE 内嵌终端或管道传参不支持。

**解决方案**：
1. 打开独立终端窗口：Windows Terminal / CMD / PowerShell
2. 在该窗口中执行 `wecom-cli init`
3. 按提示完成交互

---

### ❌ `not connected` / 连接超时

**排查清单**：

- [ ] 企业微信后台「机器人状态」是否为开启
- [ ] Bot 的「可见成员」是否包含了当前登录账号
- [ ] 网络是否能访问 `work.weixin.qq.com`（防火墙 / 代理）
- [ ] Bot ID 和 Secret 是否正确（重新 init 确认）

**重新初始化**：

```powershell
# 删除旧配置
Remove-Item -Recurse "$env:USERPROFILE\.config\wecom"

# 重新 init（在真实终端中执行）
wecom-cli init
```

---

### ❌ `errcode: 60011` / 无权限

**原因**：Bot 未授权对应的接口权限。

**解决方案**：
1. 企业微信后台 → 智能机器人 → 选择你的 Bot
2. 进入「授权」页面
3. 开启所需模块的权限（通讯录 / 消息 / 文档 / 日程 / 待办等）
4. 等待 1-2 分钟后重试

---

### ❌ 配置文件存在但每次重启后失效

**原因**：可能是配置文件权限或加密密钥问题。

**解决方案**：

```powershell
# 备份旧配置
Copy-Item "$env:USERPROFILE\.config\wecom" "$env:USERPROFILE\.config\wecom_backup" -Recurse

# 删除旧配置
Remove-Item -Recurse "$env:USERPROFILE\.config\wecom"

# 重新 init
wecom-cli init
```

---

## 使用阶段问题

### ❌ 中文乱码（Windows PowerShell）

**解决方案**：执行命令前先设置 UTF-8 编码：

```powershell
chcp 65001 | Out-Null
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 然后执行 wecom-cli 命令
wecom-cli contact get_userlist '{}'
```

---

### ❌ JSON 参数报错（单引号 / 双引号问题）

**Windows PowerShell**：

```powershell
# 使用单引号包裹 JSON
wecom-cli contact get_userlist '{}'

# 复杂 JSON 使用 here-string
wecom-cli msg send --to 'userid' --text 'hello'
```

**macOS / Linux Bash**：

```bash
wecom-cli contact get_userlist '{}'
```

---

## 环境信息收集（报告问题时使用）

```powershell
chcp 65001 | Out-Null
Write-Host "=== 环境信息 ==="
Write-Host "OS: $([System.Environment]::OSVersion.VersionString)"
node --version
npm --version
wecom-cli --version
npm config get prefix
Write-Host "PATH includes npm prefix: " ($env:PATH -split ';' | Where-Object { $_ -like "*npm*" })
```

---

## 配置文件位置参考

| 平台 | 路径 |
|------|------|
| Windows | `%USERPROFILE%\.config\wecom\` |
| macOS/Linux | `~/.config/wecom/` |

文件列表：
- `bot.enc` — 加密存储的 Bot 凭证
- `mcp_config.enc` — MCP 配置
- `.encryption_key` — 本地加密密钥

---

## 相关链接

- GitHub：https://github.com/WecomTeam/wecom-cli
- 官方文档：https://open.work.weixin.qq.com/help2/pc/21676
- 企业微信开发者中心：https://work.weixin.qq.com/api/doc
