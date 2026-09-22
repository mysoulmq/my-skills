# 数据格式与运行

本页介绍从 source.json 与 deck.json 新建 PPT 的渲染器。开发时按 [从人工样本提炼生成规则](sample-learning.md) 校准生成效果；固定坐标和字号下限不是样本验收标准。遇到能力不足，应修正配置或脚本，不能导入已有课件替代生成。

先调用 `load_workspace_dependencies` 获取 Node、Python 和 node_modules。设置：

- `LESSON_NODE_MODULES`：捆绑 node_modules 绝对路径（含 @oai/artifact-tool 与 @napi-rs/canvas）。
- `LESSON_FONT_FILES`：本机合法可用的字体路径 JSON 数组，微软雅黑常规和粗体均注册。macOS 可查已装 PowerPoint 的 Contents/Resources/DFonts/msyh.ttc、msyhbd.ttc。勿复制字体进 skill。
- `LESSON_FONT_FAMILY`：默认 `Microsoft YaHei`；替换字体须先验证简体字形和实际排版。

```sh
"$LESSON_PYTHON" /absolute/skill/scripts/check_plan.py /absolute/source.json /absolute/deck.json --report /absolute/plan-check.json
"$LESSON_PYTHON" /absolute/skill/scripts/prepare_marks.py /absolute/source.json /absolute/deck.json /absolute/styled-deck.json --report /absolute/highlight-review.json
"$LESSON_NODE" /absolute/skill/scripts/render.mjs /absolute/source.json /absolute/styled-deck.json /absolute/run
"$LESSON_PYTHON" /absolute/skill/scripts/check_pptx.py /absolute/source.json /absolute/run/candidate.pptx --report /absolute/run/content-check.json
```

先按[识读复核与知识组分页](transcription-and-grouping.md)完成直接识图及重要内容复核。所有渲染须声明 `knowledgeGroups` 并通过计划检查；旧计划重新生成时也要先补录语义分组。`render.mjs` 会强制调用计划检查，不能只依赖 source→PPT 覆盖检查。

## source.json

```json
{"units":[
 {"id":"lesson","kind":"heading","page":"3","text":"第四课　探索认识的奥秘"},
 {"id":"frame1","kind":"heading","page":"3","text":"第一框　人的认识从何而来"},
 {"id":"topic1","kind":"heading","page":"3","text":"一、认识和实践"},
 {"id":"point1","kind":"body","page":"3","text":"1、含义：是主体对客体的能动反映。"}
],"knowledgeGroups":[{"id":"recognition-definition","members":["point1"]}]}
```

`text` 是核定授课文字；确认的最小笔误修正、用户指定的标题末尾悬空破折号省略，均保留 `originalText` 与 `editReason`，不能变成知识改写。

原子单元按原图顺序排列；表格按行拆为单元格，包含原表列名/行名。标题和重复表头 kind=heading；正文 kind=body。每个单元独立记录，禁止把很多段粘成一个单元。跨页句子按实际完整语义接续，不丢页首尾。

## deck.json

所有文字引用使用 `{ "ref":"point1" }` 或简写 `"point1"`。不要在排版阶段改写核定稿。只用于框图的重复概念标签可用 `{ "text":"实践" }`，脚本要求标签来自原文。要手动断行可加 `text`，其去空白内容必须与引用原文完全一致。新标注使用 [marks格式](highlighting.md)，先判教学角色再编译样式；旧 `emphasis/focus/contrast` 数组兼容保留，但不能代替标注理由。

```json
{"lesson":"lesson","slides":[
 {"type":"overview","page":"3—4","root":{"text":"探索认识的奥秘"},
  "groups":[{"title":"frame1","items":["topic1"]}]},
 {"type":"content","page":"3","frame":"frame1","title":"topic1",
  "blocks":[{"type":"paragraphs","items":["point1"]}]}
]}
```

`overview` 是兼容旧稿的三层目录树，最多3个框；不能替代下文 `knowledge-map` 的四层知识导航。新课首页优先采用单页四层整课导航，先精简有证据的记忆线索及调节列宽、间距。可用 kicker 引用原文“【知识点突破】”，原图没有则不加。

content 页标题为原稿目标题，topic 可放原稿次级标题或当前小点。全部元素按引用顺序显示。默认正文从 y=238 排到650；可设 bodyTop（218—500）匹配页型起点，左下角讲义来源标识不占正文；不生成右下角幻灯片页码角标。

blocks 支持：

- `paragraphs`：`items:[{ref,emphasis,bold,color,size,bullet,indent,gap}]`。默认字号32、段后15；正文建议32–36。`bullet:true` 表示该原文是上条的从属解释，会缩进并添加圆点。原编号保留。原文小标题用 bold=true。不要让圆点代替原图编号。
- `branches`：`root:{text:"原文概念"}`、`items:[引用…]`；默认根框宽230、字号30、叶正文32。只给具有明确层级/并列关系的内容用框图。不得用空泛“注意”作为一切内容的万能根节点。默认根框居中，叶左对齐。
- `table`：`rows:[[引用…],…]`，`widths:[…]`总和1168，默认字号27。第一行视为表头，可跨页重复原表头。渲染器不合并单元格；原稿合并项通过重复其原有标签呈现，不增加不同含义。
- `arrow`：确有推导关系时放在两个段落块之间，默认在 x=366 显示短实心向下箭头；可设置 x。正文不变。

每块可设 before/after 增加前后距，以知识组整体的位置和留白贴近样本。不要负间距。段落、分支、表格不足以表达时，可在独立构建脚本中使用同目录 graphics.mjs 的可编辑图形方法；保持全部原文映射和相同验收，不能靠隐藏文字骗过覆盖检查。

标题过长或正文溢出会报错。拆页是正常步骤，正文通常30–34px（下限26）、表格通常24–27px（下限24）、参考式导航叶通常22–26px（下限21）；不要删原文或改成截图。重复上层标题保持导航；一个原文单元过长可在 source.json 按语义拆成连续子单元。

## 输出与终检

render.mjs 生成 candidate.pptx、previews/、coverage.json 和 reveal-plan.json；按 [播放节奏](reveals.md) 加入原生出现动画后再终检。覆盖只是已排版证明，不是图片识别正确证明。check_pptx.py 读取实际 PPTX 并检查 body 原文顺序，报告必须保留。

文件终检可用 `finalize.mjs`，需要已安装 presentations skill：设置 `PRESENTATIONS_SKILL` 为其目录，`LESSON_PYTHON` 为 Python，`RUNTIME_NODE_MODULES=$LESSON_NODE_MODULES`。参数是4个绝对路径：工作目录、candidate.pptx、交付.pptx、独立receipt.json。交付和receipt禁止覆盖，用新版本名；receipt放在工作目录的records/等私有目录，不能放在交付文件所在目录或其子目录。该检查不证明 WPS 实际字体或显示；WPS 抽查另行记录。

## 四层知识导航图（新）

`type:"knowledge-map"` 将课→框→目→知识点/记忆线索同时展开。与仅列课、框、目标题的 overview 不同；首页优先保留整课结构，不能因为通用字号造成的假性溢出拆成分目目录。`mapStyle:"reference"` 为默认：贴近人工样本的白底黑字、无填充细黑框、窄竖向课题与外橙内蓝括线。`mapStyle:"teal"` 兼容旧浅蓝节点风格。参考式图以26px起步，按实测高度在22–26px范围内适配，标题默认不低于24px，密集页可用 `mapLayout.headingSize` 单独调整（21–36px），须以分点可辨为验收依据；这对应样本约16–18pt的密集导航，不使用正文大字号约束。

```json
{"type":"knowledge-map","page":"3—4","root":{"text":"探索认识的奥秘"},
 "groups":[{"title":"frame1","topics":[
   {"title":"topic1","leaves":[
      {"label":{"ref":"recognitionHeading","quote":"认识"},"segments":[{"ref":"point1","quote":"主体对客体的能动反映"}],"emphasis":["能动反映"]}
   ]}
 ]}]}
```

每个叶节点必须有 `label:{ref,quote}` 标明所属知识点，再用 `segments:[{ref,quote}]` 摘录记忆线索；标签同样须在原文中有证据。示例中的 recognitionHeading 指向原稿“（一）认识”，实际数据必须先登记该ID。同一知识点的多条线索在一个叶内合并，不混成多个无名同级条目。quote 必须在该 ref 原文中存在；多段默认以“；”相接，可设 join。可用完整原文引用，但通常过长。导航摘录只用于建立结构，不计入全文覆盖，因此每个原文单元仍须在讲解页完整呈现。不得从示例脑图抄出原教案没有的学科提示。原稿有三条就保留三条，不能因为参考图写四个就改四个。

原文正文和导航叶均可使用：

- `emphasis:["概念/结论短语"]`：青蓝加粗，供讲解页的定义核、限定、机制、结论及要求使用。
- `focus:["对象","主体","基础"]`：黄色底纹，保留所在文字的字重与字色。参考脑图基底为黑色粗体；讲解页的“对象/主体/基础”沿用普通正文的字重，黄底本身不额外加粗。导航页还可标知识点入口和关键线索。
- `contrast:["标题核心词"]`：红色，导航的层级标题中少量使用；字段名为兼容旧版保留，不代表只有对比才允许红字。

颜色必须承担当前页型下稳定的教学角色。不能把所有原有粗体都改黄，不能满页红字。无需每页三种颜色都用。`prepare_marks.py` 会生成样式数组与审稿表；编译只是执行标注计划，教学理由须由模型按原文和学科关系复核。

## 紧凑参考式脑图参数

`mapStyle:"reference"` 从图片来源数据新建对象，不导入样本页。整课图右侧叶区默认x=650、宽600，顶部/底部留白内可用684px；不加底部页码和来源脚注挤占导航区。`size` 是尝试的最大叶字号，默认26；`mapLayout:{minSize:22,lineSpacing:1.04,groupGap:18,topicGap:10,leafGap:3,frameWidth:230,topicWidth:184}` 可调整。多框导航的框/目列宽可按标题长度调整，叶区与括线随动；框/目至少180/160px，叶区至少400px。标题断词时先调列宽或使用保序换行，再测整页；不能只增大字号或截去标题。渲染器按实测富文本换行选择能放下的字号，不能低于21px；仍放不下时报错，先回到原文摘要与关系聚合，不删知识点，也不自动拆图。`layout-review.json` 记录实际字号、框/目/叶数量和占用高度。

正文与导航的高度测量使用实际富文本字重、换行和行距；不要再按固定1.3倍行高推断必须拆页。知识点入口与完整从属解释应合在同一页，先检验真实占用；定义—形式、三条并列原因等能同页读清时不要分散。

### 用户指定的编号呈现例外

原始转录保留编号。仅当用户已经要求省略某个孤立编号时，在 `source.json` 顶层记录 `displayOmissions`：

```json
{"displayOmissions":[{"id":"原文单元ID","prefix":"①","reason":"并列分支仅首项带编号，呈现突兀","authorization":"用户本轮明确要求省略该编号"}]}
```

`deck` 仍使用该单元的 `ref`，不要覆写正文。编译、渲染和内容检查使用省略该前缀后的文字，报告保留例外记录。只支持首部编号，不允许通过此机制删除知识内容。不要自行填写授权、默认清除全部编号，或把一次具体反馈扩大到其他段落。例如对象／主体／基础并列图中用户指定的孤立①可以省略；其他层级编号、题号仍按原图保留。

`mapLayout.frameLineColor/topicLineColor/leafLineColor` 分别控制课→框、框→目、目→叶括线，默认 `#ED7D31/#4472C4/#4472C4`，值须为 `#RRGGBB`。紧凑单框单目图使用 `leafLineColor`。颜色及实际字号、间距写入 `layout-review.json` 供复核；节点边框颜色不随括线改变。`headingSize` 不改变叶字号范围，勿仅缩叶字而让中间标题仍挤在一起。

## 自动舒展预设

正文默认 `spacingProfile:"comfortable"`（deck级，可由单页覆盖）；只有保留人工精调距离时用 `preserve`。渲染器按实际字体换行测量本页全部板块，再应用段落2/3/4/更多项的44/36/28/24px目标间距、分支48px、少量板块前留白。空间不足时只按比例收回新增间距，不缩字号、不改原文、不改页序；已有内容本身超高仍报告溢出。整课首页与知识脑图不套正文预设。

默认不再为每页写试探性的 `gap/before/after`。有语义依据的自定义间距仍作为基线，`layout-review.json` 的 `content-spacing` 记录基线、目标、最终高度及分配比例。仅失败页或明显不均衡页需人工/模型复核；不能重复调用模型计算像素。参数保留在模板脚本，不把第五课题名、页码或原文写入通用规则。
