# 跨领域综合诊断决策树

> **版本**：v1.0 (2026-06-01)
> **用途**：单一文档无法定位问题时，用此决策树跨领域排查
> **原则**：从最常见原因开始，逐层深入，不跳步骤

---
## 一、诊断总流程

```
遇到问题
    │
    ▼
[收集信息]
├─ 精确描述现象（"XX连接器调用失败" →
│  具体是 401? 404? 超时? 返回空?）
├─ 记录报错信息（完整复制错误文本）
├─ 确认是偶发还是必现
└─ 确认最近是否有任何变更
    │
    ▼
[按优先级排查]
├─ P0: 连接器层（最常出问题）
├─ P1: 专家/技能层（配置问题）
├─ P2: 自动化层（调度/时区问题）
├─ P3: 模型层（回答质量问题）
└─ P4: 基础设施层（网络/代理/权限）
    │
    ▼
[验证修复]
├─ 每改一处就验证一次
├─ 不要一次改多个地方
└─ 修复后检查是否引入新问题
```

---
## 二、领域诊断树

### 2.1 连接器诊断

```
连接器问题
│
├─ 症状：所有连接器都不工作
│   ├─ 检查代理 → curl http://127.0.0.1:51103/health
│   │   ├─ 无响应 → 代理挂了 → 重启WorkBuddy
│   │   └─ 有响应 → 继续检查
│   ├─ 检查网络 → ping api.mail.qq.com
│   │   ├─ 不通 → 网络/代理/VPN问题
│   │   └─ 通 → 继续检查
│   └─ 检查配置 → 所有连接器disabled?
│
├─ 症状：单个连接器不工作
│   ├─ 检查认证 → curl + Authorization header
│   │   ├─ 401 → token过期 → 重新登录
│   │   └─ 200 → 认证OK
│   ├─ 检查传输类型 → 是stdio?
│   │   └─ 是 → 代理不支持 → 走原生通道
│   └─ 检查多session → 是否配置冲突?
│
└─ 症状：时好时坏
    ├─ 网络不稳定 → 增加timeout
    ├─ 服务限流 → 降低频率
    └─ 多session覆盖 → 统一配置
```

### 2.2 专家诊断

```
专家问题
│
├─ 症状：找不到专家
│   ├─ 是否注册成功? → 检查register输出
│   └─ 目录路径正确? → 确认在my-experts/plugins/下
│
├─ 症状：专家调用但不回答
│   ├─ prompt文件存在? → 检查 agents/<name>.md
│   └─ JSON格式正确? → 用 jsonlint 检查 plugin.json
│
├─ 症状：回答不符合预期
│   ├─ prompt太简略? → 补全4要素
│   ├─ prompt太长? → 压缩到800字
│   ├─ 缺少输出格式? → 指定表格/Markdown
│   └─ 约束不明确? → 写清楚"不要做什么"
│
└─ 症状：Team型不协作
    ├─ memberAgents列表正确? → 与文件名核对
    ├─ SOP够具体? → 每步写 receiver+action+output
    └─ 成员prompt有接收/返回规则? → 补全交互说明
```

### 2.3 自动化诊断

```
自动化问题
│
├─ 症状：定时任务不执行
│   ├─ status="PAUSED"? → 改成ACTIVE
│   ├─ 刚创建不到5分钟? → 等调度器轮询
│   ├─ 过了有效期? → 检查validFrom/validUntil
│   └─ cwds不存在? → 检查工作目录
│
├─ 症状：执行了但结果不对
│   ├─ prompt不够具体? → 补全4要素
│   ├─ 依赖的工具不可用? → 检查prompt中的工具名
│   └─ 时区问题? → BYHOUR是本地时间吗
│
└─ 症状：想删除自动化删不掉
    └─ 是否用了rm/sqlite3? → 只能用automation_update delete
```

### 2.4 模型/回答质量诊断

```
回答质量问题
│
├─ 症状：回答不对题
│   ├─ 上下文太长? → 分多轮对话
│   ├─ 选错专家? → 切换合适的专家
│   └─ 提示词太模糊? → 具体化角色+任务+格式+约束
│
├─ 症状：回答太长/太短
│   ├─ 没指定输出长度? → 加"用3句话总结"或"详细展开"
│   └─ 没指定输出格式? → 指定表格/列表/段落
│
└─ 症状：AI编造内容
    └─ 没设置边界? → 加"不确定就说不知道"
```

---
## 三、一键诊断命令

```bash
# === 环境总检查 ===
echo "===== 1. 代理状态 ====="
curl -s http://127.0.0.1:51103/health || echo "代理未运行"

echo "===== 2. 连接器状态 ====="
for f in ~/.workbuddy/connectors/*/connector-states.json; do
  echo "--- $(dirname $f | xargs basename) ---"
  python -c "import sys,json; d=json.load(open('$f')); print('Enabled:', d.get('enabled',[]))" 2>/dev/null || echo "无法读取"
done

echo "===== 3. 配置完整性 ====="
for f in ~/.workbuddy/connectors/*/mcp.json; do
  echo "--- $(dirname $f | xargs basename) ---"
  python -c "
import sys,json
d=json.load(open('$f'))
disabled = [k for k,v in d.items() if v.get('disabled')]
active = [k for k,v in d.items() if not v.get('disabled') and k.startswith('connector:')]
print(f'  Active: {len(active)}  Disabled: {len(disabled)}')
" 2>/dev/null || echo "无法读取"
done

echo "===== 4. 专家注册状态 ====="
ls ~/.workbuddy/plugins/marketplaces/my-experts/plugins/ 2>/dev/null || echo "无自定义专家"

echo "===== 5. 最近错误日志 ====="
grep -i "error\|fail" ~/.workbuddy/logs/*.log 2>/dev/null | tail -10 || echo "无日志或日志无错误"
```

---
## 四、快速修复速查

| 问题 | 最常见原因 | 最快修复 |
|------|-----------|---------|
| 连接器disconnected | token过期 | 通过WorkBuddy UI重新登录 |
| MCP调用返回401 | Bearer token过期 | 更新Authorization头 |
| 专家不回答 | 没执行register | 重新执行validate+register |
| 自动化不执行 | status=PAUSED | 改成ACTIVE |
| 回答质量差 | prompt太模糊 | 补全角色+任务+格式+约束 |
| 所有连接器down | 代理未启动 | 重启WorkBuddy |
| 修改不生效 | 缓存 | 重启WorkBuddy |
| 工具返回空 | tool名大小写错 | 用ListMcpResources确认名称 |

---
## 五、无法解决时的上报信息

如果以上全部排查后仍无法解决，收集以下信息：

```markdown
## 问题描述
[精确描述现象和复现步骤]

## 环境信息
- WorkBuddy 版本：
- 操作系统：Windows/Mac
- 模型：

## 已排查项
- [x] 代理状态（端口51103）
- [x] 连接器认证（curl测试）
- [x] 配置文件完整性
- [x] 日志检查

## 相关日志
[粘贴相关错误日志，去除敏感信息]

## 最近变更
[最近是否有系统更新、配置修改、token更换等]
```
