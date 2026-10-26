---
name: code-reviewer
description: 对指定文件夹内的代码进行全面审查，包含规范性检查、Bug检测、性能优化建议和可读性评估；当用户需要审查代码质量、发现潜在问题或生成代码审查报告时使用
---

# 代码审查工具

## 任务目标
- 本 Skill 用于：对指定文件夹内的代码进行全面的质量审查和问题检测
- 能力包含：代码规范性检查、潜在Bug检测、性能优化建议、代码可读性评估、生成结构化审查报告
- 触发条件：用户需要审查代码质量、发现潜在Bug、优化代码性能或生成代码审查报告时

## 前置准备
- 依赖说明：无额外Python包依赖，使用Python 3标准库
- 非标准文件/文件夹准备：无需额外准备

## 操作步骤

### 标准流程

1. **执行代码审查**
   - 调用 `scripts/code_reviewer.py` 对目标文件夹进行审查
   - 参数：
     - `--input-dir`：要审查的文件夹路径（必填）
   - 输出：在当前目录生成 `review_results.json` 文件
   - 示例：
     ```bash
     python scripts/code_reviewer.py --input-dir ./my-project
     ```

2. **生成审查报告**
   - 调用 `scripts/report_generator.py` 将审查结果转换为Markdown报告
   - 参数：
     - `--review-json`：审查结果JSON文件路径（默认为 `./review_results.json`）
     - `--output-dir`：报告输出文件夹路径（默认为当前目录）
   - 输出：在指定目录生成 `code_review_report.md` 文件
   - 示例：
     ```bash
     python scripts/report_generator.py --review-json ./review_results.json --output-dir ./reports
     ```

3. **查看审查报告**
   - 打开生成的 `code_review_report.md` 文件
   - 报告包含：
     - 概览统计（文件数量、问题总数、各严重性问题分布）
     - 严重问题列表（需立即修复）
     - 一般问题列表（建议修复）
     - 优化建议列表（性能和可读性提升）
     - 文件级别的详细分析

### 可选分支

- 当只需快速检查问题：执行步骤1后直接查看 `review_results.json` 文件
- 当需要审查特定类型代码：使用 `--file-ext` 参数指定文件扩展名，如 `--file-ext .py`

## 资源索引

- 必要脚本：
  - `scripts/code_reviewer.py`（用途：核心审查逻辑，支持多语言代码静态分析）
  - `scripts/report_generator.py`（用途：将审查结果转换为Markdown格式报告）
- 领域参考：
  - `references/review-guidelines.md`（用途：详细的审查规则、严重性分级标准和各语言特定检查项）

## 注意事项

- 审查工具使用静态分析方法，可能无法检测到运行时问题
- 建议结合单元测试和集成测试进行全面质量保障
- 不同编程语言的检查规则可能有所差异，详见 `review-guidelines.md`
- 报告中的"严重"问题建议优先处理，"一般"问题在代码重构时处理，"优化"问题可根据项目进度安排

## 使用示例

### 示例1：审查Python项目
```bash
# 对Python项目进行审查
python scripts/code_reviewer.py --input-dir ./python-project

# 生成报告
python scripts/report_generator.py --review-json ./review_results.json
```

### 示例2：审查特定类型文件
```bash
# 只审查JavaScript文件
python scripts/code_reviewer.py --input-dir ./web-app --file-ext .js

# 生成报告到指定目录
python scripts/report_generator.py --output-dir ./audit-reports
```

### 示例3：快速查看问题
```bash
# 执行审查后直接查看JSON结果
python scripts/code_reviewer.py --input-dir ./src && cat review_results.json | jq '.issues | group_by(.severity)'
```
