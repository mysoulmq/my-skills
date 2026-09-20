# 课堂播放节奏

人工参考显示，静态同一页也可能经过重要加工：按讲解次序单击出现。默认以原生“出现”实现，不用炫技飞入、自动计时、逐字动画。

- 课/框/目标题、必要根节点先可见。
- 定义、属性、解释各按一个教学单元出现；同一单元的原编号、正文、从属圆点和解释一起出现。
- 并列依据分次出现；“因此”结论最后出现。
- 原理总结先显示原理，下一次单击显示方法论要求。
- 四层导航先框架，再分组目标题/括线，再各知识点及其记忆线索。无需把细碎词语拆为几十个动作。
- 表格可保持整体可见或整表一次出现；不自动为每个单元格单独加动画。

## 数据和运行

content 页可设 `revealSteps:[["point1"],["point2","detail2","detail2--bullet"]]`。字符串是源ID对应的原生形状名称；同一个数组中的目标同次单击出现。圆点单独为 `源ID--bullet`，必须与正文同组。同页不能重复放置同名源ID后再模糊指定目标；消除不必要的重复标题，或用不同的明确形状名。

knowledge-map 自动生成按目/叶展开的步骤。名称为 `map-topic-框序号-目序号`、`map-brace-leaves-框序号-目序号`、`map-leaf-框序号-目序号-叶序号`（均从1起）。单框单目紧凑图保持目框可见，仅按叶展开。`reveal:false` 可关闭单张导航图的动画。

render.mjs 生成 `reveal-plan.json` 后运行：

```sh
"$LESSON_PYTHON" /absolute/skill/scripts/add_reveals.py /absolute/run/candidate.pptx /absolute/run/reveal-plan.json /absolute/run/animated.pptx --report /absolute/run/reveal-check.json
```

工具只增添原生出现时间轴，不改文字、坐标、字体或其他包内对象；拒绝未知/重名/重复目标、覆盖现有动画或输入/输出。完成后对 animated.pptx 重跑原文检查，以它为 candidate 做终检。不要先终检再偷偷加动画，使验收哈希失效。

## 复核

静态PNG只能检查所有内容展开后的版式。必须在WPS放映中检查初始状态、至少两次单击、最后一步，确认顺序与组正确；最好逐页检查所有组。只确认XML存在不能声称播放验证通过。无法控制WPS时写明“原生动画已写入；WPS播放未验证”。

修改已有PPT先检查是否已有 timing / animation / transition，再决定保留或修改；不能在导入导出时默默丢失人工动画。
