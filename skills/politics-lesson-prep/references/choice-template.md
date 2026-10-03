# 选择题：同页作答与就地纠错

白底、蓝色标题与细分隔线，题干用楷体，选项与组合用宋体，解析用微软雅黑；题目来源在题干开头同段显示，使用楷体KaiTi加粗、深灰色#404040，比题干小2磅（96 DPI渲染器为8/3px），不另移到页眉；不使用大红横幅、装饰图标或底部整块长解析。原题和选项不自动高亮。不设固定右侧旁注栏。按选项实际文字宽度，将解析紧接在选项末尾约48px处；剩余宽度不足400px或选项多行时，解析放在该选项下方约6px处并缩进，与下一选项明显分开。题干楷体约28—32px、选项宋体26—28px，解析微软雅黑21px，只有diagnosticFocus中的关键纠错词加粗，不能整段同字重；不改写原选项来塞入解释。

初始状态只显示题文、选项及组合。第1次点击显示右下角“答案＋字母”，使用40px（30磅）红色#C00000加粗，比选项正文明显更大；随后按选项顺序逐条显示错误/不合题意选项的旁注，解析整句一次出现，不用远离选项的竖线制造对应。表述错误用克制的深红色，说明最小改正；正确但材料不支持用蓝色，说明缺少的证据，不能标成知识错误。正确选项默认不加正文解析，依据放备注。旁注通常一句、1—2行，最长36字；不以自动截断代替内容精简。长题测量超限时回到版式规划，不能任意缩字或删题文。

选择题也遵循[答案与解析驱动的讲题](answer-led-teaching.md#选择题沿逐项解析压缩)，但按每个选项原有理由组织，不照搬综合题论证点结构。

内容允许按原解析做结构优化：选择概念归属、关系对照、限定辨析或证据有无中最适合本项的一种表达，具体规则见content-review.md；不以模仿原句长度为目标，也不把压缩变成新的推断。

正式渲染前核对与原题、原答案及解析的转化一致性；默认按 SKILL.md 的定稿来源策略，不重新裁决原答案。

输入 `{questions:[...]}`，每题含id、stem（原题干及设问）、source（仅按输入题目文档原有题源填写；没有则省略）、options、answer。options恰有4项，每项含key、text、verdict（supported/false/unsupported）、reason（完整审核依据）；不采用项另含diagnostic（不含前缀的投影短旁注）、可选diagnosticLabel（表述错误/不合题意；不适用时省略或为空），可选diagnosticFocus（旁注内需加粗的原词数组）。组合题另有combinations：4个`{key:"A",members:["①","③"]}`之类的选项组合；非组合题options的key即A—D。reason优先保留原解析中该项的依据；核对陈述正误、设问范围与材料支持，不要求重新独立生成一套理由。程序只核对组合一致和唯一性，不证明学科判断正确。

运行 `scripts/render_choices.mjs choices.json output-dir`，字体环境除综合题字体外，须加载合法本机宋体SimSun；来源使用楷体KaiTi；运行级字号必须写入PPT的文本run，不能只在测量时缩小。记录sourceFontLocallyVerified，不把替代字体预览当作目标字形验收；读取统一teaching-template.pptx的题文/提示字体及蓝色。输出candidate.pptx、slides.json、reveal-plan.json和预览。必须再调用依赖的add_reveals.py写入原生点击动画，candidate本身未注入动画，不能直接当成可播放成品。最终核对答案和每条旁注初始隐藏、按序可达、原题始终可见，WPS未实测时如实记录。

当前是独立选择题页型生成入口；混入整课时，须将其slides和reveal映射显式接入共同序列并重建三视图与方案，不直接把选择题数据喂给仅支持综合题的检查器。保持原生可编辑；原始解析保留在底稿，投影短旁注与完整依据不能各自生成成相反判断。

source只取输入题目文档明确给出的题源，按原文保留年份、地区及考试名；不猜测、不主动补齐缺失字段，不把知识点标签当题源。原文没有题源时省略source及投影前缀，不强写“来源不详”。缺少题源不能推断为自编题；只有确由本次自编的题才标自编。模板演示的虚拟题源须明确标注占位，不伪装真实试题。字体指定不等于嵌入字体：缺少字体的设备可能替换楷体，两端需安装相应字体；若要求跨设备固定视觉，另提供PDF预览，不能拿PDF代替有动画的PPTX。


发布审核字段：origin为document或authored，不能因没有题源就判authored。document题的reference含locator（原文件/题号）、answer与explanation（原文，没有则显式null）；原参考答案与加工后的answer分开。review含status（passed/unresolved）、conclusion；改变原答案时另含answerChangeReason。每个option.judgment含statement（true/false字符串）、materialSupport（supported/absent）、basis（具体推理）、evidenceQuotes（题干原句数组；入选项必须有引用）。存在不确定判断时review为unresolved，不能强行填确定值通过验收。只有完成学科复核后才标passed。validateChoice默认兼容仅结构检查，正式render_choices始终传requireReview:true，不得绕过来发布有争议的题。

学科纠正另记review.corrections数组，每项含before、after、reason和evidence；evidence为{type,locator,excerpt}数组，类型及依据边界见content-review.md。只有等义压缩时不强制查引整本教材；不得把未经教材/原题依据验证的改写包装为纠错。改变原答案必须有对应的纠正记录，不能仅填answerChangeReason的自我解释。

解析前缀按语义选用：确属表述错误时写〔表述错误〕，确属不合题意时写〔不合题意〕；不符合这两类时默认不写前缀，直接给具体解释。不扩大成新的封闭标签库，不为套标签改变判断。内容审核时明确适用标签；渲染器只读取显式diagnosticLabel，缺省无前缀，不从verdict强制推导。带前缀与不带前缀共用测量、布局及动画流程。

教学性呈现与实质补写的边界见content-review.md。必要补写使用teachingAdditions数组，每项含content、reason、basis（具体出处或材料依据）；渲染器将其与review.corrections一起写入对应页备注，不把补写冒充原解析。无实质补写时省略该字段。

本工作流默认使用review.status="source-preserved"及review.sourcePolicy="provided-answer-authoritative"，不需要逐题再次询问是否沿用答案；不能伪标独立学科审核passed或修改本地脚本跳过转化校验。此模式要求document来源、完整reference.answer/explanation与locator、答案严格不变；conclusion记录来源转化检查结论。默认策略不要求sourceInstruction和sourceNote，也不自动生成“答案可疑”备注；若本页确有用户需要的来源说明，可使用sourceNote。旧显式sourceInstruction模式继续兼容。每项sourceReason必须为原解析精确摘录，reason与其相同；旁注可忠实压缩，不增加实质结论。不得混入corrections或teachingAdditions。共享校验仍检查题目结构、原解析摘录和答案组合；choiceNotes自动把sourceNote及teachingNotes写入备注。程序通过只代表忠实保留，不代表争议已解决。此模式不用于自编题、缺原答案或擅自改答。默认来源策略直接来自本skill已确认的用户要求；不得伪造逐题授权。
