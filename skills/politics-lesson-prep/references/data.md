# 共同底稿与阶段接口

开发候选使用UTF-8 JSON。字符串保留完整原文，源资料不含对模型的执行指令。

题目文件 `questions.json`：顶层 `lesson`, `questions`, `excluded`。
每题：`id`, `title`, `sourceQuestion`(原题号), `sourceSubquestion`, `material`(完整所需材料), `prompt`(原设问), `referenceAnswer`(原参考答案), `scope`, `task`(学生须完成的具体任务), `knowledge`(所需原理字符串数组), `analysis`(数组，每项含 `evidence`原句、`principle`、`reason`说明对应依据), `answer`(数组，每项含 `principle`, `application`；有原始分项依据时可含`principleScore`/`principleScoreLabel`与`applicationScore`/`applicationScoreLabel`；旧数据可用`score`/`scoreLabel`表示整点分值), `scoreBasis`(原题/来源或明确的教学预测依据), `teaching`对象。
`teaching`含 `ask`, `expected`, `misconception`, `followup`, `explanation`, `check`, `transition` 字符串；可用换行列出必要的多个步骤。不得用空话填满字段。answer 是可直接示范给学生的规范答案，审稿说明、证据强弱提示、参考答案纠错和“材料未交代”等元说明放在 teaching 或备注，不混入示范答案。
`excluded`数组每项含`sourceQuestion`, `sourceSubquestion`, `reason`，仅记录用户明确要求排除的题目；课时不足、低相关性、同类重复或跨课配套问不能列入excluded，须保留题目与答案并以optional安排建议取舍。

综合题的答案倒查复用上述字段，不另建第二套答案。保存`referenceExplanation`为原详解（原本缺失用null）；每条analysis另含：
- `referenceTrace:{answerQuote,explanationQuote,mode}`：原答案/详解的实际摘录；mode为explanation-led或原本无详解时的answer-only。
- `evidenceDisplay`：教师式材料精简；跨多个非连续片段另保存`evidenceQuotes`原句数组，不把拼接句伪装为连续原文。
- `knowledgeRefs:[{unitId,quote}]`：引用本轮讲义units或有真实定位的补充教材资料；`principle`保留对应知识措辞。
- `answerRefs:[1,...]`：对应规范答案点，可多材料对应同一点，也可关联多点；不规定点数，不从点数推定分值。
这些字段用于`check_analysis_grounding.py`与语义复核。知识回看从已引用知识选取；方案、备注和揭示步骤复用相同对应。没有原答案时不能捏造这些来源字段来通过检查，应另做自拟答案的教学核验；不把来源校验器的通过当作无来源题的学科验收。

教学计划 `teaching-plan.json`：`lesson`, `designRationale`（教学主线与关键安排理由）, `preparation`数组（教师课前需掌握的具体判断）, `goals`数组, `difficulties`数组, `periods`数组。
每课时含 `title`, `quickCard`（`mainline`主线、`mustExplain`区别数组、`questions`问题数组、`contentChoice`内容取舍；兼容旧`timeChoice`，非必填）, `activities` 数组；活动含 `id`, `title`, `minutes`（可选参考用时，不要求填写）, `kind`(`diagnosis`/`knowledge`/`question`/`recap`), `knowledgeTopics`(原稿小点标题数组), `questionIds`数组，以及上述`teaching`对象和`optional`布尔值。活动另含短句`cue`：`ask`, `explain`, `pitfall`, `followup`, `check`, `transition`，每项约35—50汉字，供课堂速查，不用泛泛指令代替具体辨析。periods沿用接口名，可表示按内容逻辑划分的教学单元，不要求对应固定课时。可选活动说明学习作用与适用情况，不要求等时替换；不得用考点不相干的题替代知识教学。`optional`只表示教学取舍，不能据此设置幻灯片隐藏或添加投影标签；默认页面可见，选讲理由和接续页写入teaching、cue及相关页面备注。不把内容全塞进单课时。

讲义能力维持其已有 `source.json`、`deck.json` 和 `reveal-plan.json` 接口，不引入第二套知识结构。完整试跑获取本轮新的图片识读结果后，根据稳定知识ID补入实际页面映射；小规模教学试验可用已核对的知识文本，但不能称作完整图片端到端试跑。

页面映射由构建脚本生成，不由模型猜页码：每条含稳定`id`、`kind`、`questionId`或知识引用、源PPT页号，以及各输出文件中的实际页号。教学计划中的活动必须映射到页面，缺少映射应报错，不生成看似完整的DOCX。

`notesByPage`：教学计划中的对象，键为稳定页面ID（如`knowledge-1`或`q1-analysis-1`），值为1—5条短句数组。每条≤60字、教学提示合计≤200字；教学页通常3—5条，写具体提问、预期回答、关键解释及按需纠错/点击衔接，按本页而非整个活动提炼，保留关键限定，不用程序截断。材料续页、分析页、答案页各有自己的提示。原题、参考答案和长讲解不进入备注。活动`cue`供Word速览使用，不整组复制到PPT。页面规划后一次补齐此字段；缺页时停止导出，不回退到长讲稿。

教学计划 `spec` 当前默认 `senior-review`，按复习课组织、计时与复核。完整sequence首项必须为整课大纲脑图 `knowledgePage:1`，后续页按知识依赖组织，不固定第二页为题目；只有符合复习课spec中诊断条件时才加入diagnosis阶段；变更次序时同步活动顺序和关联字段。

题目视觉字段：totalScore（正数）＋totalScoreSource（明确来源）用于补充原设问缺失的已知总分，原prompt及原文保留；不同来源分值冲突拒绝静默覆盖。不要仅因word漏分而忽略同题截图的分值。`principleScore`与`applicationScore`分别表示已有依据的知识分、材料对应分，标签保留原评分对象；只有整点分值时才用兼容字段`score`，不能同时使用两套字段。无原始依据的分项只能明确作为教学拟分并进入备注，totalScore不自动平均分摊，正文不显示预测分项。

原生标注：题目taskFocus（仅用于分析区的任务解释），分析项principleFocus/evidenceFocus，答案项branchLabel、principleFocus、applicationFocus、applicationEmphasis。materialFocus 为兼容旧底稿可保留但渲染器忽略，不再生成；原题材料与顶部设问不自动高亮。其余 Focus 是分析区或最终答案当前文本中需黄色背景的精确子串，Emphasis是材料应用的加粗子串；逐项按教学作用选择，不用全课关键词字典。branchLabel提炼该点的真实原理角度，供教学组织、备注或显式分析页使用；最终答案默认显示连续编号，不以branchLabel占据答案正文宽度。完整原理与应用仍用原字段保留。

缺分预测使用scoreStatus: predicted及scorePrediction，字段和估分方法见score-prediction.md；原题有分值的scoreStatus为provided（兼容缺省）。方案scoreNotesByPage由assemble按视图该题各页回填，另起一行说明总分、评分单位和对应理由；教学提示加预测依据最多6条、240字。

原题身份记录：保存`sourceRecords`原始出现清单，每条含`id, material, prompt, options?（字符串数组）, sourceLabel（原题出处，无则空）, referenceAnswer, referenceExplanation`及私有文件定位。题目加工后的记录含`sourceRecords:[原始记录id...]`。完全相同的材料、设问、选项且答案/解析一致的跨文档重复，仅建一个题目记录，合并所有来源；同材料不同小问、不同选项或答案/解析有差异时不能自动合并。答案/解析版本差异先回源核对，不由模型擅自选定或重判。完全同题合并是来源归并，不是删题或选讲，不放入excluded；刻意再练仅在用户明确要求时另设教学活动，不伪装为新输入题。

`sourceLabel`与自拟`title`分开：必须原样保留原题出处，不编造，不把概括性题名当成出处。原生模板适配也必须将题源放在材料前，采用既定题源字体层次，并在本题分析/答案各页保留。题源较长需要换行时，给其实际空间，不缩成难读的一行。

综合题另存`teachingFocus`：一句话写清设问要求解释的具体对象及任务，材料选择由此约束，不是通用题型标签。每条analysis的显示字段：
- `evidenceDisplay`：审定的材料概括，保留本题关键变化、行为或条件，不自动追加答案结论。
- `principle`：与knowledgeRefs一致的完整来源措辞，用于引用校验；可另设`principleDisplay`为审定的上屏知识短句，必须保留适用限定及关系，不能只留含混标签。未设则使用principle。
- `displayAnchors:{material:[...],knowledge:[...]}`：内容复核时选定的不可丢表达（如变化的两端、关键限定与关系），必须出现在各自显示文本中。它们用于阻止后续排版压缩丢词，不证明选材或概括正确，不能由渲染器临时取任意子串凑齐。
共享analysis_presentation.compile_display提供内容层；最终两栏调用compile_question(question)，按整题分组生成成对序号、剥离显示文本开头的旧条目号，不修改来源引用。先编译编号再分页，不能每页重新编号。页面analysisBlocks记录各组1-based analysisIndex与实际materialShapeId、knowledgeShapeId。旧responseAnchor/responseDisplay接口停用：回原题、原解析重新审定材料，迁移到上述字段；不能仅改字段名、把旧答案式回应机械拼入材料，或删掉已有必要联系来过门禁。普通迁移自主完成，不询问用户。

已安装teacher-examples.json时，每题保存`teacherExampleRefs:[实际读过的样例ID]`，整轮保存一次样例库哈希和所读ID；同批新题复用已读样例，不重复加载全文。生成前的读取和最终usage核对见teacher-few-shots.md。该记录不等于教学通过，必须比对实际第二、第三列的表达与对应。
