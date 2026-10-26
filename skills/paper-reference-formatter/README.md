# 论文参考文献格式化Skill

这是一个用于整理和格式化论文参考文献的 Codex Skill。它可以把用户输入的期刊论文、学位论文、会议论文、图书、报告、预印本、网页等文献信息，转换为指定的参考文献格式。

## 支持格式

- GB/T 7714
- APA
- MLA
- Chicago

如果用户没有指定格式，Skill 会先要求用户选择一种格式。

## 主要能力

- 识别文献类型，例如期刊论文、硕士/博士学位论文、会议论文、图书、报告、网页等。
- 从用户提供的信息中提取作者、题名、年份、期刊名、卷期、页码、出版社、学校、DOI、URL 等字段。
- 按用户选择的引用格式生成参考文献条目。
- 对缺失或不确定字段进行提示，避免编造文献信息。
- 支持中英文文献信息，中文姓名和中文题名默认保持原样。

## 目录结构

```text
paper-reference-formatter/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
├── references/
│   └── style-rules.md
└── scripts/
    └── format_reference.py
```

## 文件说明

- `SKILL.md`：Skill 的核心说明文件，定义触发场景、工作流程和质量检查要求。
- `references/style-rules.md`：GB/T 7714、APA、MLA、Chicago 的格式模板和规则参考。
- `scripts/format_reference.py`：用于把结构化 JSON 文献信息格式化为指定引用格式的脚本。
- `agents/openai.yaml`：Codex App 中展示 Skill 时使用的界面元数据。

## 用户输入示例

用户可以直接输入自然语言文献信息，例如：

```text
请把下面两条文献整理成 GB/T 7714 格式：
1. 张伟、李明，Research on citation formatting，Journal of Academic Writing，2024，12(3)，45-58，DOI: 10.1234/example
2. 王明，机器学习在文本分类中的应用研究，北京大学硕士学位论文，2023，北京
```

也可以输入结构化 JSON：

```json
[
  {
    "type": "journal",
    "authors": ["Zhang Wei", "Li Ming"],
    "title": "Research on citation formatting",
    "year": "2024",
    "container": "Journal of Academic Writing",
    "volume": "12",
    "issue": "3",
    "pages": "45-58",
    "doi": "10.1234/example"
  },
  {
    "type": "thesis",
    "authors": ["王明"],
    "title": "机器学习在文本分类中的应用研究",
    "year": "2023",
    "institution": "北京大学",
    "place": "北京",
    "degree": "硕士学位论文"
  }
]
```

## 脚本用法

进入 Skill 目录后运行：

```bash
python scripts/format_reference.py --style gbt7714 --input refs.json
```

`--style` 支持：

- `gbt7714`
- `apa`
- `mla`
- `chicago`

`refs.json` 可以是单条文献对象，也可以是文献对象数组。

## 字段约定

常用字段如下：

- `type`：文献类型，例如 `journal`、`thesis`、`conference`、`book`、`report`、`preprint`、`webpage`
- `authors`：作者数组，按原始顺序填写
- `title`：文献题名
- `container`：期刊名、会议录名、网站名或其他载体名称
- `year`：年份
- `volume`：卷
- `issue`：期
- `pages`：页码
- `publisher`：出版社
- `place`：出版地或学位授予地
- `institution`：学校、机构或学位授予单位
- `degree`：学位类型
- `doi`：DOI
- `url`：网页链接
- `accessed`：访问日期

## 注意事项

- Skill 不会凭空补全文献信息；缺失的重要字段会被省略或标记为 `[missing: field]`。
- APA、MLA、Chicago 中的英文作者姓名需要根据输入判断姓和名；如果姓名顺序不明确，建议用户提供更明确的作者格式。
- GB/T 7714 会尽量添加文献类型标识，例如 `[J]`、`[D]`、`[C]`、`[M]`、`[R]`、`[EB/OL]`。
- DOI 在 APA、MLA、Chicago 中会优先规范为 `https://doi.org/...`。

## 验证

Skill 已通过官方结构校验：

```text
Skill is valid!
```
