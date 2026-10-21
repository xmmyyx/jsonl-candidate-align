# JSONL Candidate Align

版本0.1.0的非公开本地源码候选。MIT版权署名已确认为Qi Zheng；源代码权利审查仍待完成，尚未授权或进行GitHub公开发布。

## 用途

`jsonl-candidate-align`从已经结构化的JSONL记录中检索词法候选，并按同一词法规则检查候选输出。Python模块名称为`jsonl_candidate_align`，命令名称为`jsonl-align`。

输入中的对象类型由调用者提供。程序不解析PDF或Word文件，不进行OCR，不从文档生成需求对象，不判断语义合规，也不作招投标决策。文本相似和数字重合只是检索信号，不能证明需求已经得到满足。

## 环境与安装

声明支持Python >=3.11。未声明第三方运行包，运行源码使用Python标准库。源码构建通过已声明的后端使用`setuptools>=77`和`wheel`。

以下是声明的源码安装方法，适用于包含`pyproject.toml`和英文`README.md`的源码目录。源代码权利审查及任何公开分发的授权仍待完成：

```powershell
python -m pip install .
```

这是声明的源码安装方法，不是拟公开集合已经安装成功的记录。本草稿不提供公开下载地址或预构建归档。安装需要能够取得声明的构建工具，不保证离线安装。

安装后的命令为`jsonl-align`。模块入口为`python -m jsonl_candidate_align`。顶层帮助和版本选项分别为`--help`和`--version`。

## 命令接口

调用者自行提供有权使用的输入文件。拟公开源码范围不附带演示数据集或测试样本。下表是接口规范，不是可执行演示，也不是运行记录。

| 子命令 | 必填选项 | 可选选项 | 写入指定输出目录的文件 |
|---|---|---|---|
| `align` | `--queries`、`--candidates`、`--output-dir` | `--blind-ids`，后接一个或多个精确查询ID | `candidate_alignment_rows.jsonl`、`candidate_alignment_summary.json` |
| `validate` | `--queries`、`--candidates`、`--actual`、`--output-dir` | 无 | `object_comparison.jsonl`、`validation_summary.json` |

查询和候选选项指向输入JSONL文件。`--actual`指向待检查的候选行文件。`--output-dir`必须为新目录，已有目录会被拒绝；输入文件也不能位于该输出目录内。相对路径按调用者当前工作目录解释。

`validate`检查所提供查询文件中的全部查询，没有`--blind-ids`选项。为部分查询生成的结果，不会自动被认定为原完整查询文件的完整结果。

退出码：0表示生成成功或校验通过；1表示成功解析的输出未通过校验；2表示CLI、输入或路径错误。

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

此文档不附输入样本行或预期结果行。

## 输出与校验

每条候选行包含11个字段：`blind_id`、`blind_type`、`holdout_unit_id`、`holdout_unit_type`、`holdout_pages`、`score`、`jaccard`、`containment`、`number_overlap`、`shared_trigrams`和`rank`。

排名从1开始，每个查询最多返回8个候选。最终同分按持久候选ID排序。页码来自调用者输入的候选记录。分数和重合比例范围为[0,1]，`shared_trigrams`为非负整数。校验要求指标为有限数值、排名为正整数，且ID、类型及页码列表与输入相符。

生成摘要包含`version`、`mode`、`blind_ids`、`candidate_alignment_rows`、`top_k`、`zero_candidate_blind_ids`、`semantic_gold_or_external_accuracy_evaluated`、`queries_sha256`和`candidates_sha256`。

校验会重新计算词法参考，独立检查所提供的指标和准入条件，再使用精确Decimal分数比较候选集合与排名。满足明确条件的同分换序或满容量边界替换可以被接受；同分本身不能授权未知候选。

校验摘要包含`status`、`queries_checked`、`candidate_rows_checked`、`failed_queries`、`comparison_scope`和`semantic_gold_or_external_accuracy_evaluated`。逐查询比较记录描述候选集合变化、排名及分数变化、同分等价、准入检查和指标不匹配。校验PASS仅表示对给定输入满足词法契约，不代表语义准确率或招投标合规结论。

## 限制与本地数据处理

评分器采用固定的80成员字符三元组预池，数字回退最多40个，最终最多8个。预池边界不保证任意输入顺序或哈希种子下完全稳定。输入整体加载到内存；尚未确认大规模性能或恶意输入的资源限制保障。

运行时处理本地JSONL，写入明确指定的新目录，不依赖网络服务、模型或原始文档库。输出包含传入的ID、页码和指标；错误信息可能包含输入文件名及ID。应按数据敏感程度管理输入、输出与日志。

## 版本与证据边界

此前的非公开本地候选已有历史技术验收。该历史验收与本次隔离的本地源码候选及文档分别成立。本次已在独立本地目录组装源码集合并完成静态检查，没有构建、安装或运行，也没有执行测试。静态依赖完整不能证明实际安装成功、跨平台验收或获得公开许可。

## 许可证与发布状态

本地候选已选择MIT。标准文本见[LICENSE](LICENSE)，版权行为`Copyright (c) 2026 Qi Zheng`，该署名已由项目发起人确认。包元数据仍为`license = "MIT"`和`license-files = ["LICENSE"]`。相关源代码权利，包括第三方、合同及必要声明义务，仍待审查；署名确认不代表所有相关法律权属已经最终确权。尚未授权或进行GitHub公开发布。
