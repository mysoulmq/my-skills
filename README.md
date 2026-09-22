# My Skills

个人 Agent Skills 集合。每个 skill 独立存放，后续新增能力继续加入 `skills/`。

| Skill | 用途 |
| --- | --- |
| [lesson-image-ppt](skills/lesson-image-ppt/SKILL.md) | 将精编教案图片转成逐字保真的可编辑授课 PPT，支持参考式四层脑图、学科标注判断、分步出现与完整讲解页。 |
| [politics-lesson-prep](skills/politics-lesson-prep/SKILL.md) | 将政治教案图片与大题文档组织成授课方案、完整课件及讲义/讲题视图，支持诊断回题、课时速览、讲授提示与原生动画。 |
| [boutique-exam-converter](skills/boutique-exam-converter/SKILL.md) | 将精品解析原卷与解析版整理为选择题、主观题、解析三个DOCX，保留校本模板并核对题目一致性。 |
| [worksheet-dual-doc](skills/worksheet-dual-doc/SKILL.md) | 将政治作业 DOCX 整理为题目、答案两个 DOC，检查格式、删除浙江选考题并生成复核 PDF。 |

## 目录

- `skills/<skill-name>/`：入口说明、脚本、模板、默认配置和规则参考。
- `tests/<skill-name或简称>/`：对应的回归测试。

## 使用作业转换 Skill

阅读 [入口说明](skills/worksheet-dual-doc/SKILL.md) 和 [运行环境](skills/worksheet-dual-doc/references/runtime.md)。当前项目通过 `.agents/skills/worksheet-dual-doc` 软链接指向 `../../skills/worksheet-dual-doc`，仅在本工作区加载，不安装到个人全局 skills 目录。

示例请求：“把这份高效作业整理成题目版和答案版，编制人用王老师。”

需要 Python、python-docx、lxml、Pillow、pdfplumber、pypdfium2、reportlab，以及 LibreOffice 和合法可用的宋体。可设置 `WORKSHEET_PYTHON` 指向准备好的 Python。此版本主要在 macOS 的文档运行环境测试；其他环境需要重新验证依赖、字体和排版。

```bash
python3 -m unittest discover -s tests/worksheet -p 'test_*.py' -v
```

编制人与校对人使用示例默认值，在 `assets/defaults.json` 修改；其余默认项是高三政治作业示例配置。临时覆盖不改变长期默认值。

字体检查区分 DOC 指定字体与实际预览字体：题源指定隶书，缺失时可替代预览；不能据此保证真实隶书环境的换行。自动验证通过后，仍须逐页视觉检查和教研复核。

本仓库保存可维护的源码与模板，校本样板作为相关 skill 的运行依赖保留；日常输入试卷、学生材料、交付 ZIP 和商业字体不纳入仓库。现有人工定稿的一次性修复不属于通用 skill。

## 维护约定

本地开发和发布源码统一维护在 `skills/`。工作区 skill 入口是指向源码的相对软链接，无需复制同步；本地修改或 `git pull` 更新源码后，入口读取同一份文件。已加载旧指令的会话应重新读取 skill，必要时重新打开会话。Git 记录该软链接，其他本地 `.agents/` 内容、原始文档、临时文件和输出结果不纳入 Git。新增 skill 时创建 `skills/<skill-name>/SKILL.md`，补充对应测试并更新上方目录表。

## 教案图片转授课 PPT

阅读 [lesson-image-ppt](skills/lesson-image-ppt/SKILL.md)。输入精编教案图片，输出一课一份可编辑 PPT；完整讲解页逐字保留，教学导航图用可追溯原文摘录展开到知识点及记忆线索。先按定义、角度、逻辑限定、机制和要求等教学功能选词，保存标注理由，再编译为贴近参考的红字、黄底及青蓝重点。渲染器使用捆绑 Node 的 `@oai/artifact-tool`，环境与数据格式见 skill 的运行参考；不包含私人图片、课堂材料或商业字体。

内容检查回归：`python3 -m unittest discover -s tests/lesson-image-ppt -p 'test_*.py' -v`。图片识别准确性和课堂图示质量仍需独立视觉复核。

## 政治整课备课

阅读 [politics-lesson-prep](skills/politics-lesson-prep/SKILL.md) 和 [执行说明](skills/politics-lesson-prep/references/running.md)。将此 skill 软链或安装到实际 workspace 的 `.agents/skills/politics-lesson-prep`，同级须能发现 `lesson-image-ppt`。依赖必须具备 `check_plan.py` 等新接口；同名旧版本可能不足，先运行依赖检查，不能假定仓库旧版已满足。

示例：“根据这些教案图片和大题文档，准备高三政治复习课，交付完整PPT和可执行授课方案。”默认每课时40分钟，Word先给速览与可点击目录，详细讲法按需查阅；PPT备注仅留逐页临场短提示，原始资料另存备查底稿。使用明确支持模型配置的执行器落实图片 Astra/low、教研 Sol/medium 的分工，脚本本身不调用或切换模型。

运行环境沿用 Codex 捆绑的 artifact-tool、Python 与 python-docx，字体由本机提供。文件检查不能替代教研及WPS播放检查；不保证任意新材料无需复核，也不支持WPS脑图节点自动重排。脱敏回归：`python3 -m unittest discover -s tests/politics-lesson-prep -v`。

