---
name: boutique-exam-converter
description: "Use when 将学科网精品解析的原卷版与解析版 DOCX 转换为同一套综合练选择题、主观题和解析三个 DOCX，并核对两份输入题目一致性、套用校本抬头、按目标页数有条件恢复主观题详解。用于既有试题转换，不用于自由命题或普通文档排版。"
---

# 精品解析试题转换

输入同一套试卷的两个 DOCX：原卷版（题目版）和解析版（答案版）。输出三个文件：综合练选择题、综合练主观题、综合练解析。不得修改输入文件，不自行换题、改题或编造答案。

## 默认配置

读取 `assets/defaults.json`。标题、学校、届别、学段、科目、练习名称、编制人、校对人和解析目标页数均可通过 `--set key=value` 临时覆盖；只有用户明确要求改变以后默认值时，才使用 `config --save-defaults`。

默认文件名：

- `高三上 综合练2（选择题）.docx`
- `高三上 综合练2（主观题）.docx`
- `高三上 综合练2 解析.docx`

页面、校徽与题头横线、标题、信息栏、正文、材料、答案颜色、行距以及主观题答题留白，以 `assets/reference-*.docx` 三份样本为版式权威。模板中的浮动图形和空白答题段落都是版式内容，不得因“没有文字”而清理。保留题目中的图片、表格和必要的行内强调；不要复刻样本中题号与上一题粘连等明显编辑瑕疵。

当输入文件哈希与五份基准样本中的原卷版、解析版完全相同时，必须使用精确模板模式：在三份目标样本上只修改配置化文字，不得删除正文后重排。该模式用于回归测试，输出应保留样本校徽、横线、题头位置、分页和全部答题空间。其他试卷才使用通用重排模式，并仍须在 WPS 中逐页校准。

## 必做的输入一致性与教研核对

先运行 `inspect`，不得跳过：

```bash
scripts/run.sh inspect /absolute/原卷版.docx /absolute/解析版.docx --out /absolute/inspection.json
```

必须确认：

1. 两份输入的题号、题干、选项、材料、设问、图片及表格逐题一致；解析版允许在每题后新增答案与解析。
2. 每题都有可识别答案；选择题答案字母与解析结论没有明显冲突；主观题答案覆盖全部小问并对应题目指定知识范围。
3. 脚本报告的 `errors` 必须为空。`review_issues` 需要逐项阅读和教研判断；脚本的结构核对不能替代答案正确性审核。

发现不一致时停止转换，列明题号、两边原文和差异，不静默选择其中一份，也不擅自修正。

## 三份输出的内容规则

- 选择题文件：收录原卷中的全部选择题；题号前加全角括号样式的答题空位；不带答案解析。
- 主观题文件：收录原卷中的全部非选择题；不带答案解析。
- 解析文件：选择题保留答案和详解；主观题默认只保留 `【答案】`部分，删除从 `【解析】`开始的过程性详解。

主观题详解不是固定只保留最后一题。先生成仅含参考答案的解析版候选稿；若在 WPS 中未达到或未尽量填满配置的目标页数，则从最后一道主观题向前，按原顺序恢复完整详解模块。优先恢复整道题的详解；空间不足时只能按完整段落模块截取前缀，例如保留“题型说明”及连续的“有效信息①②”，不能抽取不连续段落，不能自行总结或改写。达到目标页数且继续增加会溢出时停止。恢复内容必须逐字来自输入解析版。

样本中第27题的处理是：完整保留原 `【详解】`及三组“有效信息”分析，仅删去独立的 `【解析】`标签并压缩段落；它是为填充第四页形成的实例，不是“只有最后一题可保留详解”的规则。

详细边界见 [references/content-policy.md](references/content-policy.md)。

## 执行与验收

使用 `load_workspace_dependencies` 定位捆绑 Python，必要时设置 `BOUTIQUE_PYTHON`。实际命令使用本 skill 的绝对路径：

```bash
scripts/run.sh convert /absolute/原卷版.docx /absolute/解析版.docx --out /absolute/output-root
scripts/run.sh convert /absolute/原卷版.docx /absolute/解析版.docx --out /absolute/output-root --set compiler=王老师 --set practice_number=3
scripts/run.sh convert /absolute/原卷版.docx /absolute/解析版.docx --out /absolute/output-root --detail-count 27=4
scripts/run.sh verify /absolute/run-directory
```

`convert` 创建独立运行目录，内含三份 DOCX、输入核对报告、内容清单、解析详解恢复记录，以及供辅助检查的 PDF/逐页 PNG。未传 `--detail-count` 时，脚本会根据 LibreOffice 渲染生成一个详解范围候选，但该结果不能作为分页定稿。转换后必须：

1. 阅读 `inspection.json` 与 `manifest.json`，确认题数、选择题/主观题分界、答案和恢复的详解范围。
2. 用 WPS 打开三份 DOCX，逐页检查实际页面数量、留白、标题和信息栏、题号、图片、表格、裁切、重叠及乱码。WPS 是分页和版式的最终权威。
   第一页必须与相应样本并排检查；校徽、题头横线、标题和信息栏任一缺失即为失败。主观题还必须逐题核对答题留白，不能只核对文字是否齐全。
3. 特别检查解析文件是否达到目标页数；第四页应自然饱满，但不得用空段落、异常字号、压缩行距或无关内容撑页。
4. 若 WPS 中欠填或溢出，按完整段落边界确定各题保留量，用一个或多个 `--detail-count 题号=段落数` 重新转换。未列出的主观题默认为 0；例如 `--detail-count 27=4` 表示只保留第27题详解的前4个连续段落。
5. 核对解析中恢复的文字确实来自原解析版，且是连续、完整的内容模块。PDF/PNG 和其中的页数只作辅助定位，不能代替 WPS 验收。
6. 明显格式问题修复后必须重新转换，并再次在 WPS 中逐页检查；不能只凭自动检查交付。

审核要点和交付说明见 [references/review.md](references/review.md)。正常交付三份 DOCX；JSON、PDF和PNG仅作内部审核，除非用户要求，不作为最终附件。

## 配置

```bash
scripts/run.sh config --set compiler=王老师
scripts/run.sh config --set compiler=王老师 --save-defaults
```

未知配置键必须拒绝。`target_analysis_pages` 必须为正整数；`analysis_fill_threshold` 是末页正文占可用高度的停止阈值，默认 `0.9`。临时配置不得写回默认文件。
