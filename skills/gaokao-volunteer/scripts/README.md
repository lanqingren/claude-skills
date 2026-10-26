# 脚本目录索引

## Agent 日常使用（只需要这2个）

| 脚本 | 用途 | 调用方式 |
|------|------|---------|
| **gaokao_tools.py** | 主工具：位次查询、院校匹配、方案生成 | `python scripts/gaokao_tools.py` |
| **backtest_v19.py** | 回测校准（如需重新计算阈值） | `python scripts/backtest_v19.py` |

## 数据获取

| 脚本 | 用途 |
|------|------|
| extract_guizhou_2025.py | 解析贵州省考试院PDF |
| fetch_all_provinces_v4.py | 批量获取各省投档数据 |
| extract_all_provinces.py | 从大学生必备网提取HTML表格 |
| ocr_fujian.py | 福建省OCR数据提取 |

## 历史迭代（审计用，不要调用）

以下为回测脚本的迭代历史，**最终版为 backtest_v19.py**：

| 版本 | 关键改进 | 产出 |
|------|---------|------|
| backtest_v2~v5 | 贵州单省回测 | 发现位次法可行性 |
| backtest_v6~v9 | 扩展到全国4-22省 | 双模式（位次/分数） |
| backtest_v10~v15 | 多源融合+五维度分析 | 12,266校覆盖 |
| backtest_v16~v18 | IQR自适应阈值+省份分档 | 9,590对校准 |
| **backtest_v19** | **分科类精细化回测** | **14,008对，最终版** |

> 对应回测结果在 `~/.hermes/workspace/gaokao-data/backtest_results/`
> 最终结果文件：`backtest_v20.json`（v19脚本输出，v20命名因数据源版本）
