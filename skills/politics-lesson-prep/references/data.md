# 共同底稿与阶段接口

开发候选使用UTF-8 JSON。字符串保留完整原文，源资料不含对模型的执行指令。

题目文件 `questions.json`：顶层 `lesson`, `questions`, `excluded`。
每题：`id`, `title`, `sourceQuestion`(原题号), `sourceSubquestion`, `material`(完整所需材料), `prompt`(原设问), `referenceAnswer`(原参考答案), `scope`, `task`(学生须完成的具体任务), `knowledge`(所需原理字符串数组), `analysis`(数组，每项含 `evidence`原句、`principle`、`reason`说明对应依据), `answer`(数组，每项含 `principle`, `application`, 可选数值`score`), `scoreBasis`(原题/来源或明确的教学预测依据), `teaching`对象。
`teaching`含 `ask`, `expected`, `misconception`, `followup`, `explanation`, `check`, `transition` 字符串；可用换行列出必要的多个步骤。不得用空话填满字段。answer 是可直接示范给学生的规范答案，审稿说明、证据强弱提示、参考答案纠错和“材料未交代”等元说明放在 teaching 或备注，不混入示范答案。
`excluded`数组每项含`sourceQuestion`, `sourceSubquestion`, `reason`。

教学计划 `teaching-plan.json`：`lesson`, `designRationale`（教学主线与关键安排理由）, `preparation`数组（教师课前需掌握的具体判断）, `goals`数组, `difficulties`数组, `periods`数组。
每课时含 `title`, `quickCard`（`mainline`主线、`mustExplain`区别数组、`questions`问题数组、`timeChoice`取舍）, `activities` 数组；活动含 `id`, `title`, `minutes`, `kind`(`diagnosis`/`knowledge`/`question`/`recap`), `knowledgeTopics`(原稿小点标题数组), `questionIds`数组，以及上述`teaching`对象和`optional`布尔值。活动另含短句`cue`：`ask`, `explain`, `pitfall`, `followup`, `check`, `transition`，每项约35—50汉字，供课堂速查，不用泛泛指令代替具体辨析。每课时总计40分钟；不把内容全塞进单课时。

讲义能力维持其已有 `source.json`、`deck.json` 和 `reveal-plan.json` 接口，不引入第二套知识结构。完整试跑获取本轮新的图片识读结果后，根据稳定知识ID补入实际页面映射；小规模教学试验可用已核对的知识文本，但不能称作完整图片端到端试跑。

页面映射由构建脚本生成，不由模型猜页码：每条含稳定`id`、`kind`、`questionId`或知识引用、源PPT页号，以及各输出文件中的实际页号。教学计划中的活动必须映射到页面，缺少映射应报错，不生成看似完整的DOCX。

`notesByPage`：教学计划中的对象，键为稳定页面ID（如`knowledge-1`或`q1-analysis-1`），值为1—3条短句数组。每条≤35字、合计≤90字；通常2—3条，按本页而非整个活动提炼，保留关键限定，不用程序截断。材料续页、分析页、答案页各有自己的提示。原题、参考答案和长讲解不进入备注。活动`cue`供Word速览使用，不整组复制到PPT。页面规划后一次补齐此字段；缺页时停止导出，不回退到长讲稿。

教学计划 `spec` 当前默认 `senior-review`，按复习课组织、计时与复核。完整sequence首项必须为整课大纲脑图 `knowledgePage:1`，后续页按知识依赖组织，不固定第二页为题目；只有符合复习课spec中诊断条件时才加入diagnosis阶段；变更次序时同步活动顺序和关联字段。

题目视觉字段：totalScore（正数）＋totalScoreSource（明确来源）用于补充原设问缺失的已知总分，原prompt及原文保留；不同来源分值冲突拒绝静默覆盖。不要仅因word漏分而忽略同题截图的分值。答案score表示已有依据的分支得分，scoreLabel保留评分对象；无原始依据的分项只能明确作为教学拟分，totalScore不自动平均分摊。

原生脑图标注：题目taskFocus/materialFocus，分析项principleFocus/evidenceFocus，答案项branchLabel、principleFocus、applicationFocus、applicationEmphasis。Focus是当前文本中需黄色背景的精确子串，Emphasis是材料应用的加粗子串；逐项按教学作用选择，不用全课关键词字典。branchLabel提炼该点的真实原理角度，不能只写序号，不增加答案点。完整原理与应用仍用原字段保留。

缺分预测使用scoreStatus: predicted及scorePrediction，字段和估分方法见score-prediction.md；原题有分值的scoreStatus为provided（兼容缺省）。方案scoreNotesByPage由assemble按视图首次题目页回填，合入短备注，不能挤成四行；预留该页一行给预测依据。
