# 数据格式与运行

先调用 `load_workspace_dependencies` 获取 Node、Python 和 node_modules。设置：

- `LESSON_NODE_MODULES`：捆绑 node_modules 绝对路径（含 @oai/artifact-tool 与 @napi-rs/canvas）。
- `LESSON_FONT_FILES`：本机合法可用的字体路径 JSON 数组，微软雅黑常规和粗体均注册。macOS 可查已装 PowerPoint 的 Contents/Resources/DFonts/msyh.ttc、msyhbd.ttc。勿复制字体进 skill。
- `LESSON_FONT_FAMILY`：默认 `Microsoft YaHei`；替换字体须先验证简体字形和实际排版。

```sh
"$LESSON_PYTHON" /absolute/skill/scripts/prepare_marks.py /absolute/source.json /absolute/deck.json /absolute/styled-deck.json --report /absolute/highlight-review.json
"$LESSON_NODE" /absolute/skill/scripts/render.mjs /absolute/source.json /absolute/styled-deck.json /absolute/run
"$LESSON_PYTHON" /absolute/skill/scripts/check_pptx.py /absolute/source.json /absolute/run/candidate.pptx --report /absolute/run/content-check.json
```

## source.json

```json
{"units":[
 {"id":"lesson","kind":"heading","page":"3","text":"第四课　探索认识的奥秘"},
 {"id":"frame1","kind":"heading","page":"3","text":"第一框　人的认识从何而来"},
 {"id":"topic1","kind":"heading","page":"3","text":"一、认识和实践"},
 {"id":"point1","kind":"body","page":"3","text":"1、含义：是主体对客体的能动反映。"}
]}
```

原子单元按原图顺序排列；表格按行拆为单元格，包含原表列名/行名。标题和重复表头 kind=heading；正文 kind=body。每个单元独立记录，禁止把很多段粘成一个单元。跨页句子按实际完整语义接续，不丢页首尾。

## deck.json

所有文字引用使用 `{ "ref":"point1" }` 或简写 `"point1"`。不要重写原文。只用于框图的重复概念标签可用 `{ "text":"实践" }`，脚本要求标签来自原文。要手动断行可加 `text`，其去空白内容必须与引用原文完全一致。新标注使用 [marks格式](highlighting.md)，先判教学角色再编译样式；旧 `emphasis/focus/contrast` 数组兼容保留，但不能代替标注理由。

```json
{"lesson":"lesson","slides":[
 {"type":"overview","page":"3—4","root":{"text":"探索认识的奥秘"},
  "groups":[{"title":"frame1","items":["topic1"]}]},
 {"type":"content","page":"3","frame":"frame1","title":"topic1",
  "blocks":[{"type":"paragraphs","items":["point1"]}]}
]}
```

`overview` 是兼容旧稿的三层目录树，最多3个框；不能替代下文 `knowledge-map` 的四层知识导航。新课首页优先采用四层导航，过密时按框拆页。可用 kicker 引用原文“【知识点突破】”，原图没有则不加。

content 页标题为原稿目标题，topic 可放原稿次级标题或当前小点。全部元素按引用顺序显示。默认正文从 y=238 排到650，页脚不占正文。

blocks 支持：

- `paragraphs`：`items:[{ref,emphasis,bold,color,size,bullet,indent,gap}]`。默认字号32、段后15；正文建议32–36。`bullet:true` 表示该原文是上条的从属解释，会缩进并添加圆点。原编号保留。原文小标题用 bold=true。不要让圆点代替原图编号。
- `branches`：`root:{text:"原文概念"}`、`items:[引用…]`；默认根框宽230、字号30、叶正文32。只给具有明确层级/并列关系的内容用框图。不得用空泛“注意”作为一切内容的万能根节点。默认根框居中，叶左对齐。
- `table`：`rows:[[引用…],…]`，`widths:[…]`总和1168，默认字号27。第一行视为表头，可跨页重复原表头。渲染器不合并单元格；原稿合并项通过重复其原有标签呈现，不增加不同含义。
- `arrow`：确有推导关系时放在两个段落块之间，默认在 x=366 显示短实心向下箭头；可设置 x。正文不变。

每块可设 after 增加后距。不要负间距。段落、分支、表格不足以表达时，可在独立构建脚本中使用同目录 graphics.mjs 的可编辑图形方法；保持全部原文映射和相同验收，不能靠隐藏文字骗过覆盖检查。

标题过长或正文溢出会报错。拆页是正常步骤，正文不低于30、表格不低于27、导航叶不低于26；不要删原文或改成截图。重复上层标题保持导航；一个原文单元过长可在 source.json 按语义拆成连续子单元。

## 输出与终检

render.mjs 生成 candidate.pptx、previews/、coverage.json 和 reveal-plan.json；按 [播放节奏](reveals.md) 加入原生出现动画后再终检。覆盖只是已排版证明，不是图片识别正确证明。check_pptx.py 读取实际 PPTX 并检查 body 原文顺序，报告必须保留。

文件终检可用 `finalize.mjs`，需要已安装 presentations skill：设置 `PRESENTATIONS_SKILL` 为其目录，`LESSON_PYTHON` 为 Python，`RUNTIME_NODE_MODULES=$LESSON_NODE_MODULES`。参数是4个绝对路径：工作目录、candidate.pptx、交付.pptx、独立receipt.json。交付和receipt禁止覆盖，用新版本名；receipt放在工作目录的records/等私有目录，不能放在交付文件所在目录或其子目录。该检查不证明 WPS 实际字体或显示；WPS 抽查另行记录。

## 四层知识导航图（新）

`type:"knowledge-map"` 将课→框→目→知识点/记忆线索同时展开。与仅列课、框、目标题的 overview 不同；一课可分成按框划分的若干导航页，避免强挤全课。`mapStyle:"reference"` 为默认：贴近人工样本的白底黑字、无填充细黑框、窄竖向课题与分级括线。`mapStyle:"teal"` 兼容旧浅蓝节点风格。正文默认26以上。

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
