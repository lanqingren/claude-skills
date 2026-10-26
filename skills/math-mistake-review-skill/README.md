# math-mistake-review-skill

将初中数学错题照片转化为结构化复习素材的 AI 技能。上传错题图片，自动生成包含原题还原、考点分析、破题关键、答案解析、变式训练和 SVG 几何示意图的完整复习文档。

## 功能

- 从错题图片中识别并还原题目（LaTeX 公式排版）
- 基于 2025-2026 中考数学考纲分析核心考点
- 指出解题的"题眼"和关键逻辑转换步
- 还原完整答案解析
- 生成 2 道同维度、同难度的变式训练题
- 为几何/函数题目自动生成 SVG 示意图
- 输出以考点命名的 Markdown 文件

## 安装

### 使用 install.sh（推荐）

```bash
chmod +x install.sh
./install.sh                          # 自动检测平台
./install.sh --platform claude-code   # Claude Code
./install.sh --platform cursor        # Cursor（自动生成 .mdc）
./install.sh --platform copilot       # GitHub Copilot
./install.sh --all                    # 安装到所有检测到的平台
./install.sh --dry-run                # 预览安装路径
```

### 各平台手动安装

| 平台 | 安装命令 |
|------|---------|
| Universal | `cp -R ./math-mistake-review-skill ~/.agents/skills/` |
| Claude Code | `cp -R ./math-mistake-review-skill ~/.claude/skills/` |
| GitHub Copilot | `cp -R ./math-mistake-review-skill .github/skills/` |
| Cursor | `cp -R ./math-mistake-review-skill .cursor/rules/` |
| Windsurf | `cp -R ./math-mistake-review-skill .windsurf/rules/` |
| Cline | `cp -R ./math-mistake-review-skill .clinerules/` |
| Gemini CLI | `cp -R ./math-mistake-review-skill ~/.gemini/skills/` |
| Kiro | `cp -R ./math-mistake-review-skill .kiro/skills/` |
| Trae | `cp -R ./math-mistake-review-skill .trae/rules/` |
| Goose | `cp -R ./math-mistake-review-skill ~/.config/goose/skills/` |
| OpenCode | `cp -R ./math-mistake-review-skill ~/.config/opencode/skills/` |
| Roo Code | `cp -R ./math-mistake-review-skill .roo/rules/` |

## 前提条件

- **无需外部 API** — 此 skill 不需要任何 API 密钥
- **无需特定 Python 包** — 辅助脚本仅使用 Python 标准库
- Python 3.8+（仅用于保存输出文件）
- 需要支持图片识别（vision）的 LLM

## 使用示例

### 示例 1：上传几何错题

```
用户: /math-mistake-review-skill [上传圆的切线证明题照片]

输出: 生成以"圆的切线性质与勾股定理综合"命名的 .md 文件，包含：
  - 原题还原 + SVG 示意图
  - 核心考点：圆的切线性质、勾股定理
  - 破局关键：连接切点与圆心构造直角三角形
  - 答案解析（完整步骤）
  - 2 道变式题 + SVG + 折叠解析
```

### 示例 2：上传函数错题

```
用户: /math-mistake-review-skill [上传二次函数最值题照片]

输出: 生成以"二次函数区间最值问题"命名的 .md 文件，包含：
  - 原题还原 + 函数图像 SVG
  - 核心考点：二次函数顶点式、对称轴、区间最值
  - 破局关键：判断对称轴是否在给定区间内
  - 答案解析 + 2 道变式题
```

### 示例 3：上传代数计算错题

```
用户: /math-mistake-review-skill [上传分式方程错题照片]

输出: 生成以"分式方程的解法与增根检验"命名的 .md 文件，包含：
  - 原题还原（本题无需SVG示意图）
  - 核心考点：分式方程解法、增根概念
  - 破局关键：去分母后验证解是否使分母为零
  - 答案解析 + 2 道变式题
```

## 文件结构

```
math-mistake-review-skill/
├── SKILL.md                      # 主技能文件
├── scripts/
│   └── generate_review.py        # 保存生成内容为 .md 文件
├── references/
│   └── curriculum-guide.md       # 2025-2026中考数学考纲速查手册
├── assets/
│   └── config.json               # 配置文件
├── install.sh                    # 跨平台安装脚本
└── README.md                     # 本文件
```

## 故障排除

### Skill 未被激活
- 确保 skill 安装在正确的目录中
- 在新的对话会话中尝试
- 使用明确的触发短语，如"帮我把这道错题整理成复习素材"

### 生成的 SVG 不显示
- 确保 Markdown 渲染器支持内联 SVG
- 在支持 SVG 的 Markdown 预览器中查看（VS Code、Typora 等）

### 变式题计算无解
- 变式题经数值验证后生成，如遇问题可重新运行 skill

## 许可

MIT License
