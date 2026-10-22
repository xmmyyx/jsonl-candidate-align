# JSONL Candidate Align

面向结构化JSONL记录的词法候选检索与精确分数校验工具。由Qi Zheng维护的个人开源项目，采用MIT许可证。

[English](README.md)

`jsonl-candidate-align`根据字符三元组与数字重合对候选记录排序，并按同一词法规则检查候选输出。Python模块名称为`jsonl_candidate_align`，命令名称为`jsonl-align`。

输入须由调用者预先完成结构化和类型标注。程序不解析PDF或Word文件，不进行OCR，不从文档生成需求对象，不判断语义合规，也不作招投标决策。文本相似和数字重合只是检索信号，不能证明需求已经得到满足。

## 环境与安装

要求Python >=3.11。运行源码仅使用Python标准库。源码构建需要`setuptools>=77`和`wheel`。

在包含`pyproject.toml`的源码目录中安装：

```powershell
python -m pip install .
```

安装时需要能够取得声明的构建工具。安装后的命令为`jsonl-align`，等价的模块入口为`python -m jsonl_candidate_align`。使用`--help`查看用法，使用`--version`查看版本。

## 快速开始

安装本项目后，激活安装时使用的Python环境，在新的工作目录中打开终端。无需下载任何数据：以下记录、ID和页码均为完全合成的示例。

使用文本编辑器，在该工作目录中将以下两个文件保存为UTF-8编码，每个文件仅有一行，该行包含一个JSON对象。

`queries.jsonl`：

```json
{"blind_id":"DEMO-Q1","blind_type":"SC","comparable_text":"cobalt sensor 314159"}
```

`candidates.jsonl`：

```json
{"holdout_unit_id":"DEMO-C1","holdout_unit_type":"M3_AUTO_KEEP","comparable_text":"cobalt sensor 314159","pages":[1]}
```

在已安装本项目的Python环境中执行以下命令。两个输出目录均须此前不存在。再次运行时，请使用新的输出目录名称，并将`--actual`改为指向新的候选输出文件。

```powershell
jsonl-align align --queries queries.jsonl --candidates candidates.jsonl --output-dir alignment-output
jsonl-align validate --queries queries.jsonl --candidates candidates.jsonl --actual alignment-output/candidate_alignment_rows.jsonl --output-dir validation-output
```

该示例在`alignment-output/candidate_alignment_rows.jsonl`中生成一条候选记录。两个命令的退出码均为`0`；`validation-output/validation_summary.json`内容如下：

```json
{
  "status": "PASS",
  "queries_checked": 1,
  "candidate_rows_checked": 1,
  "failed_queries": [],
  "comparison_scope": "LEXICAL_CANDIDATE_OUTPUT_ONLY",
  "semantic_gold_or_external_accuracy_evaluated": false
}
```

`PASS`表示这些输入的输出符合词法契约，不代表语义匹配正确、需求已满足或招投标合规。

## 技术文章

[这篇英文技术文章](https://dev.to/xmmyyx/why-i-added-a-validator-to-a-small-jsonl-candidate-ranker-43c7)介绍了两个 CLI 入口的分工、合成分数漂移示例，以及校验结果的能力边界。

## 使用方法

准备自己的`queries.jsonl`和`candidates.jsonl`后执行：

```powershell
jsonl-align align --queries queries.jsonl --candidates candidates.jsonl --output-dir alignment-output
jsonl-align validate --queries queries.jsonl --candidates candidates.jsonl --actual alignment-output/candidate_alignment_rows.jsonl --output-dir validation-output
```

| 子命令 | 必填选项 | 可选选项 | 写入输出目录的文件 |
|---|---|---|---|
| `align` | `--queries`、`--candidates`、`--output-dir` | `--blind-ids`，后接一个或多个精确查询ID | `candidate_alignment_rows.jsonl`、`candidate_alignment_summary.json` |
| `validate` | `--queries`、`--candidates`、`--actual`、`--output-dir` | 无 | `object_comparison.jsonl`、`validation_summary.json` |

`--queries`和`--candidates`指向输入JSONL文件，`--actual`指向待检查的候选行文件。每个`--output-dir`必须为新目录，已有目录会被拒绝；输入文件也不能位于该输出目录内。相对路径按调用者当前工作目录解释。

`validate`检查所提供查询文件中的全部查询，没有`--blind-ids`选项。校验部分查询时，应提供仅包含该部分查询的文件；部分输出不会自动被认定为原完整查询文件的完整结果。

退出码：`0`表示生成成功或校验通过；`1`表示成功解析的输出未通过校验；`2`表示CLI、输入或路径错误。

## 输入规范

采用UTF-8 JSONL，可带BOM，每个非空行包含一个JSON对象。拒绝重复JSON键、重复记录ID和`NaN`/`Infinity`常量。ID必须是非空字符串。查询文件至少包含一个对象；候选文件可以为空。`comparable_text`必须为字符串，可以为空。

| 输入 | 字段 | 要求 |
|---|---|---|
| 查询 | `blind_id` | 必填且唯一的查询ID |
| 查询 | `blind_type` | 必填：`SC`、`MRU`、`SU`或`EI` |
| 查询 | `comparable_text` | 必填字符串 |
| 候选 | `holdout_unit_id` | 必填且唯一的候选ID |
| 候选 | `holdout_unit_type` | 必填，取值见下文 |
| 候选 | `comparable_text` | 必填字符串 |
| 候选 | `pages` | 可选的正整数列表，默认为空列表 |

候选类型为`M3_AUTO_KEEP`、`M4_AUTO_KEEP`、`NARRATIVE_RESPONSE`、`TEMPLATE_COMMITMENT`、`MANUAL_RESOLVED_FACT`、`MANUAL_RESOLVED_BUNDLE`和`VISUAL_EVIDENCE`。这些只是兼容性标签，程序不证明标签是否符合记录的实际含义。任何输入对象中已有的`pages`字段都会检查其正整数列表格式，包括查询对象中的该字段。

## 评分规则

文本经过Unicode NFKC规范化、转为小写、移除空白及指定标点后，生成字符三元组集合；不足三个字符的非空文本整体作为一个词元。数字词元从原始文本中单独提取。

评分器按共享三元组数量选取最多80条记录作为预池，每条至少共享两个三元组。若预池为空且查询包含数字词元，则按输入顺序回退选择最多40条类型兼容且数字重合的记录。CLI采用词法评分，不启用上下文扩展。

各候选的指标如下：

| 指标 | 定义 |
|---|---|
| `jaccard` | 共享三元组数量除以两个三元组集合的并集大小 |
| `containment` | 共享三元组数量除以较小三元组集合的大小 |
| `number_overlap` | 共享数字词元数量除以较小数字词元集合的大小；任一集合为空时为零 |
| `score` | `0.35 * jaccard + 0.55 * containment + 0.10 * number_overlap` |

候选准入要求类型兼容、至少共享一个三元组，并满足以下任一条件：`score >= 0.10`、`containment >= 0.16`，或同时满足`number_overlap >= 0.50`和`containment >= 0.08`。这些阈值使用舍入前的数值。

`SC`和`MRU`接受除`VISUAL_EVIDENCE`外的全部候选类型；`SU`和`EI`接受除`NARRATIVE_RESPONSE`外的全部候选类型。

输出分数和重合比例保留六位小数。每个查询最多返回8个候选，先按舍入后的分数降序排序，同分时按持久候选ID排序。排名从1开始。

## 输出与校验

每条候选行包含11个字段：`blind_id`、`blind_type`、`holdout_unit_id`、`holdout_unit_type`、`holdout_pages`、`score`、`jaccard`、`containment`、`number_overlap`、`shared_trigrams`和`rank`。页码来自调用者输入的候选记录。分数和重合比例范围为[0,1]，`shared_trigrams`为非负整数。

生成摘要包含`version`、`mode`、`blind_ids`、`candidate_alignment_rows`、`top_k`、`zero_candidate_blind_ids`、`semantic_gold_or_external_accuracy_evaluated`、`queries_sha256`和`candidates_sha256`。

校验会重新计算词法参考，独立检查每个待校验候选的指标及准入条件。校验要求指标为有限数值、排名为正整数，且ID、类型及页码列表与输入相符；使用精确Decimal分数比较候选集合与排名，检查候选重复与排名断档，并限制最多8个候选。

其他检查均通过时，同分换序可以通过校验。边界替换要求两份列表均满8个候选、分数截点相同、增删候选数量相同且均位于该截点、新增候选经过独立验证，以及没有分数漂移。同分本身不能使未知或不符合准入条件的候选通过校验。

校验摘要包含`status`、`queries_checked`、`candidate_rows_checked`、`failed_queries`、`comparison_scope`和`semantic_gold_or_external_accuracy_evaluated`。逐查询比较记录描述候选集合变化、排名及分数变化、同分等价、准入检查和指标不匹配。

校验`PASS`仅表示对给定输入满足词法契约，不代表语义准确率或招投标合规结论。摘要中的`semantic_gold_or_external_accuracy_evaluated`为`false`。

## 已知限制与数据处理

预池边界不保证任意输入顺序或Python哈希种子下完全稳定。固定的80条预池记录、40条数字回退记录和8条结果上限可能排除相关候选。输入整体加载到内存；尚未确认大规模性能或恶意输入的资源限制保障。

运行时处理本地JSONL，写入明确指定的新目录，不依赖网络服务、模型或原始文档库。输出包含传入的ID、页码和指标；错误信息可能包含输入文件名及ID。请使用有权处理的输入，并按数据敏感程度管理输入、输出与日志。

## 许可证

[MIT许可证](LICENSE)。Copyright (c) 2026 Qi Zheng.
