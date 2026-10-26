# Dependencies / 依赖与环境要求

本文说明本技能依赖的 Ardot MCP 工具集与环境排查方式。执行前先确认 Ardot 已打开目标文件，MCP 已连接。

## 必需工具

| 工具 | 用途 | 最低要求 |
|---|---|---|
| `fetch_editor_state` | 读取当前文件、页面、selection | 能返回 `currentPage.id`；优先返回 `selection` |
| `batch_read` | 读取入口节点、子结构、生成后校验 | 支持 depth ≥ 2；能返回尺寸与 children |
| `locate_available_space` | 寻找展示区空位，避免覆盖已有画布 | 支持 `width` / `height` / `padding` / `direction` 参数 |
| `batch_edit` | 生成 outer/titlebar/group/cell 等结构 | 使用 `operations` 字符串语法；不要使用旧版 `edits[]` |
| `capture_screenshot` | 生成后截图预览 | 能按 nodeId 截取 outer frame |
| `ask_followup_question` | 分组歧义时给用户单选确认 | 支持 2-4 个选项和自定义输入；宿主若显示为等价选择题工具，按宿主工具名调用 |

## 推荐工具

| 工具 | 用途 |
|---|---|
| `get_available_fonts` | 字体不可用时查询目标文件可用字体，做可解释降级 |

## 版本与语法约束

- `batch_edit` 必须使用当前 Ardot MCP 的 `operations` 字符串语法。
- 每个 Insert/Copy 操作必须有 binding 名，便于后续引用和校验。
- 单次 batch 操作建议不超过 25 条；超过时先建外层容器，再分批生成内部节点。
- 禁止在 `locate_available_space` 失败后降级为手写坐标。

## 环境排查

| 现象 | 检查项 | 下一步 |
|---|---|---|
| 读取不到 selection | 是否在 Ardot 里选中了画板/page | 让用户选中内容或提供 nodeId |
| 读取不到 currentPage | Ardot 是否打开目标文件 | 让用户打开文件后重试 |
| 找不到空位 | 当前 page 是否空间不足 | 换页、清理画布、改矩阵降低宽度 |
| batch_edit 失败 | 是否仍使用旧 `edits[]`；单次操作是否过多 | 改 `operations`，分批写入 |
| 写入成功但看不到 | Ardot 视图未刷新 | `Cmd+R` 或点击画布空白处刷新 |

## 阻塞条件

以下情况必须停止，不要继续生成：

- Ardot MCP 断开。
- 目标文件或页面不可确定。
- 输入画板不可确定且用户未提供 nodeId。
- `locate_available_space` 失败且用户未选择换页/清理/改布局。

## 命名空间回退（NO_ADAPTER）

Ardot MCP 工具可能以多个命名空间暴露，例如 `mcp__ardot__*` 与 `mcp__ardot-design__*`。

实测遇到过：`mcp__ardot__*` 调用返回 `NO_ADAPTER: No adapter found for routeKey ...`（路由失效），但同一时刻 `mcp__ardot-design__*` 命名空间是活跃可用的。

处理顺序：

1. 某个命名空间持续报 `NO_ADAPTER`（连续 3 次重试无效）→ **先切换到另一个 ardot 命名空间重试同一调用**（如 `ardot` ↔ `ardot-design`），而不是立即判定 Ardot 不可用。
2. 用 `fetch_file_info` / `fetch_editor_state` 探测哪个命名空间能正常返回，后续全程固定用那一个。
3. 两个命名空间都不通，再走 ardot-link 自愈技能的 `diagnose.sh` 做隧道诊断。

## padding 语法约束

`batch_edit` 的 `padding` 不接受简写字符串（如 `"0 200 200 200"`），会报：

```text
Invalid padding value, expected [number] or [number, number] or [number, number, number, number]
```

正确写法二选一：

- 数组：`padding: [0, 200, 200, 200]`（T R B L）
- 或四个独立属性：`paddingTop: 0, paddingRight: 200, paddingBottom: 200, paddingLeft: 200`

四边相等时可直接用单个数字：`padding: 200`。
