# 执行与验证

先通过 `load_workspace_dependencies` 定位捆绑 Node/Python 与依赖。按 lesson-image-ppt 的 runtime-and-schema 设置 `LESSON_NODE_MODULES`、`LESSON_FONT_FILES`、`LESSON_PYTHON`；字体来自本机合法安装，不打包进入skill。

用 `check_dependency.py --workspace /absolute/workspace --record private-build/dependency.json` 检查并记录实际依赖。依赖版本必须包含知识组校验脚本 check_plan.py；仓库旧版或另一个安装副本不一定具备此接口，不凭技能同名假定版本满足要求。

1. `python extract_docx.py input.docx extracted.json` 生成原序段落和表格，由指定模型一次解释题目结构。重要文字识别问题回原文件核对。
2. 建立 questions.json 和 teaching-plan.json 后，运行 `python check_teaching.py questions.json teaching-plan.json --report check.json`。脚本核对连续材料引用、字段、活动题号及40分钟合计，不判断学科或教学含义。
3. 使用 `node render_questions.mjs questions.json /absolute/lesson-image-ppt build sequence.json teaching-plan.json` 创建题目页、经教学设计明确需要的可选诊断页、本页讲授卡和稳定页面列表，随后调用依赖的 add_reveals.py 写入原生动画。第一次创建文件前，按 Presentations 技能执行其 operation marker。读取其终检要求，不以生成成功代替验收。
4. `pptx_views.py manifest.json candidate.pptx --mapping mapping.json` 根据教学序列复制原生页面及其资源关系，保持页面XML和动画。manifest 包含 `decks:{key:absolutePptxPath}` 与 `slides:[{id,deck,sourceSlide,activityIds,clicks}]`。sourceSlide 按实际播放顺序、从1开始，不能根据slide文件名推断。不得重复引用同一源页；需要重复显示时先明确生成独立页实例。复用已有讲義产物只用于日常缓存或接口验证，独立完整试跑必须从原图开始。
5. `write_plan.py teaching-plan.json mapping.json candidate.docx` 按真实页码生成方案；每个活动须有页面映射，拒绝缺失引用。采用 Documents 技能捆绑 Python、python-docx，渲染并检查全部页面后再交付。

统一教学计划确定后，创建 sequence.json 数组，每项为 `{knowledgePage:1,activityIds:[...]}` 或 `{questionId:"q1",stage:"teaching",activityIds:[...]}`。精选代表题可另有`stage:"diagnosis"`，生成独立材料设问页并前置；不提前展示答案。knowledgePage按讲义实际顺序从1开始，必须完整保序；每题每阶段只插入一次，脚本展开该阶段页面。回顾活动可关联正在显示的既有页面，不必另造空泛回顾页。

`add_knowledge_notes.py input.pptx source.json deck.json sequence.json teaching-plan.json noted.pptx` 按notesByPage给讲义页补充临场短提示；不改正文或动画。随后 `assemble.py noted.pptx questions-animated.pptx question-build/slides.json questions.json teaching-plan.json sequence.json bundle-build` 生成三份候选PPTX、映射和授课方案。输出目录必须是新目录；构建映射留在私有目录，主交付为四份文件；如需保留编辑依据，附独立原始资料底稿，不把原文塞入备注。

仅有一种资料时，缺少的源PPT参数传 `-`，相应题目/页面数组为空。只输出有实际内容的视图，不生成空白课件。

脚本不判断教学顺序是否合理，不能把任意sequence当作教研通过。讲义覆盖使用依赖检查器仅检查讲义正文；题目和方案的语义复核独立执行。对合并候选用 Presentations 的包完整性、布局检查与终检，然后在WPS验证静态、动画对象初始隐藏、点击顺序和最后一步（动画对象隐藏不等于整张幻灯片隐藏）。终检输出父目录须预先存在；临时目录路径使用realpath，避免macOS /tmp别名误判。

中文DOCX预览若出现空白或方块，先核对实际OOXML中文字是否齐全。可在构建目录创建临时fontconfig配置，指向本机已经安装的中文字体目录，使用 `FONTCONFIG_FILE` 运行捆绑render_docx.py；不安装字体、不修改系统字体配置，也不把缺字预览当作已完成视觉验收。

成本记录不要求新模型调用或日志分析。可直接保存工具返回值；试跑报告只写pass/fail与具体问题。

仅修改备注时，可用 `compact_notes.py input.pptx view-mapping.json teaching-plan.json output.pptx`，不重新生成正文、动画或调用教学模型。脚本只改原生备注正文；验证其余ZIP成员字节不变。修改前的完整原始资料留在私有底稿，可整理为带页面ID的附属编辑参考文件。

题目覆盖检查 `check_question_slides.py` 的 mapping 参数必须是当前课件的页面数组，不是 assemble 输出的三视图对象。先从 page-mapping.json 选取相应视图（如“完整授课”）写入私有 view-mapping.json，再运行检查。错误的映射结构属于程序调用问题，不当作教学模型失败。

独立教学复核至少留一份简短记录：实际模型与强度、结论、失败活动/页面ID及字段、原断言与依据。复核范围包括 questions、teaching-plan 的详细讲法/速览、notesByPage；不能只读最终示范答案。发现教学失败时保留简短记录，原模型自主局部修订并独立复核，通过后继续；无需逐错审批。仅在SKILL.md规定的真实阻塞条件下询问。结构检查通过不代表教学复核通过，最终报告区分首轮问题、已修正问题和未解决项。

不要为保持旧页数而保留无教学依据的diagnosis阶段。取消前置诊断时同步移除sequence条目、独立诊断页与相应活动/备注，保留该题正式材料和解析；重新分配课时、生成三视图及方案映射。原题不因取消重复诊断页而丢失。

题目模板更新后先读question-template.md。确保LESSON_FONT_FILES同时加载楷体与微软雅黑（含粗体）。必要时先用相同参数加--layout-only只写slides.json/reveal-plan.json，按实际分页更新notesByPage，再正常渲染到新构建目录。模板分页可能不同于旧列表页；重建教学映射、原生动画和DOCX页码，不能继续沿用旧页数。脑图标注是教学底稿的局部加工，不要求重新理解所有题目。

题目加工同轮完成缺分预测，先运行check_teaching.py核对scorePrediction的分组、来源标识和总和；所有显示分值仍通过check_question_slides.py。assemble.py在每个视图的该题各页附加简短预测说明；若提示超长，局部缩写其他教学提示后重新导出，不放宽备注限制。

交付前检查三视图的幻灯片可见性：没有用户明确隐藏要求时，不应存在slide级show="0"，也不应出现新增的“备用题／不进入默认放映”正文标签。修订旧文件时清除遗留隐藏与标签，但保留原生对象动画；同步选讲备注、建议取舍、接续页与方案映射。独立复核必须执行spec-senior-review的教学质量检查，文件结构或总时长通过不能替代课堂讲法与节奏通过。

题目生成必须使用当前共享render_questions.mjs的同页默认模式；旧任务本地renderer可能仍无条件生成material/analysis/answer多组页面，不可直接复用。先比较其与共享脚本差异，移除旧的强制分析分页和按题号阈值，保留有证据的容量处理。读取layout-decisions.json核实续页依据；同页后重建notesByPage、动画与三视图页码，逐问核实全部原理和材料应用都在实际答案页、每个动画目标确实存在且可到达。

收录验收从原始提取的小问清单逐项对照完整PPT和大题PPT两份实际文件，检查材料、设问、全部答案点与映射；不能只核对已筛选的questions.json而漏掉上游被删小问。仅用户明确排除项可不收录。课时不足、optional、重复训练及跨课配套问均不构成少收录的理由。
