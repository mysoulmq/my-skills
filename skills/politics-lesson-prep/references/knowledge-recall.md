# 相关知识回看：来源、范围与原生呈现

在替换教师模板的知识区之前读取。原则：**设问确定范围，答案辅助定位，讲义或框架提供原文与层级。** 可以根据答案倒查、核对候选知识、选择强调；不能把答案里用到的原理拼接成一个自创的知识目录。知识回看提供本题可选择的知识，审材料再展示具体对应，两者不必相同条数。

## 按有效设问范围选择

| 有效范围 | 优先来源 | 边界 |
| --- | --- | --- |
| 具体原理或知识点 | 已核对学案的对应印刷段落 | 保留完整限定和内部关系，不只摘最终答案句 |
| 一个目或框 | 本轮首页框架的对应分支 | 视教师示范保留下一级知识线索，不机械截到目标题 |
| 整课或更大范围 | 本轮课—框—目框架 | 通常截止目标题，避免整课细节挤满知识区 |

按设问的实际任务判断，不能只按范围词长度。例如设问前面写整本书、后面限定一个具体原理，仍走具体原理路由。新题引用本轮资料，不能照搬旧课示例知识。已有标题须先完成教材目标题核定。

## few-shot与数据

先按 `teacher-few-shots.md` 的 `knowledge-recall` 路由读取真实教师案例：原设问 → 选取的学案段落/首页分支 → 实际回看区。教师使用图片时核验真实图片关系与哈希，并实际查看返回的 `verifiedImagePath`；截图只是示范证据，新输出优先原生可编辑内容。省去手写杂注，保留印刷原文及教师正式框架层级。批注遮挡造成的缺字回原资料核实，不能猜写。

每题独立保存 `knowledgeRecall`：`id / route / scopeReason / sourceScope / teacherExampleRefs / nodes`。route 为 `handout / outline-branch / outline-overview`。node 包含 `id / parentId / text / source / emphasis`；source含 `kind`、讲义`unitId`或框架`deck/page/shapeId`及`quote`。讲义节点应来自已核定的源段落；不得先改写再把改写稿登记成来源。

`knowledge_recall.compile_recall(record, catalog)`校验真实来源节点、完整文字和父子关系。catalog从已核定讲义单元及实际框架PPT独立读取，键为`unit:ID`或`ppt:DECK:PAGE:SHAPEID`，值为原文；不能从候选record反向构造catalog让它自证。校验允许排版空白变化，不允许删词或自行合并知识内容。语义范围仍由独立教研审查。

## 写入与验收

`native_recall_layout.plan_recall`提供手稿式层级或框架树的实际测量布局，保留父子关系；使用模板对应字体与有界字号，不能无差别套一个小字号。`native_text.write_text`写入可编辑段落、原生行距和已核定的标记，同时处理连续破折号。知识区和分析区联合测量：先算完整分析组的高度，再对完整知识区做有界紧凑试排，最后决定是否续页，不先把知识区无限撑大。过高时保留完整语义分支分续页，并重算对应分析容量，不能暗中删知识。

实际PPT需运行：

```sh
python scripts/check_recall_delivery.py final.pptx recall-records.json source-catalog.json recall-map.json --report recall-check.json
```

records文件为`{"records":[knowledgeRecall,...]}`。mapping是每页对象映射数组：`page / recallId / nodeShapes`；`nodeShapes`为node ID到实际shape ID。可附`emphasisShapes`（shapeId、role、focus、emphasis，第二列role为analysis-material并禁止高亮）、`unmarkedShapeIds`（材料/设问）。答案页可省略recallId，附`noHighlight`和`sectionTexts`，检查无新增黄底及原理/应用真正另起段。检查来源与落盘传递，不替代逐页视觉、范围选择或动画验收。

## 为审材料留空间的紧凑档

`native_recall_layout.fit_recall(..., max_height, base_font=13.5, min_font=12)`按完整分析组高度倒算知识区目标高度，在960×540 pt画布先试原舒适档，再试知识区专用紧凑档：行距1.10、节点间距2 pt、节点附加高度1 pt，字号每次0.5 pt降到12 pt。以上是本模板回看区的配置起点，其他画布同比缩放；不是正文/审材料的统一小字号。先压无效留白再降字号，不同时压缩所有区域。每个box返回的lineSpacing必须实际写入PPT，不能测量按紧凑档、落盘仍是旧行距。

选择满足容量的最大字号，保存profile、完整高度及fits；fits=false说明可读下限仍不够，保留源内容并分同模板续页。不能为了全塞同页继续缩字。实际渲染验收关注投屏辨认、父子分隔、连续破折号，以及下方两列能否按组完整呈现；不以页数更少自动判通过。
