# My Skills

个人 Agent Skills 集合。每个 skill 独立存放，后续新增能力继续加入 `skills/`。

| Skill | 用途 |
| --- | --- |
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

本仓库保存可维护的源码与模板，不包含原始试卷、学生材料、交付 ZIP 或商业字体。现有人工定稿的一次性修复不属于通用 skill。

## 维护约定

本地开发和发布源码统一维护在 `skills/`。工作区 skill 入口是指向源码的相对软链接，无需复制同步；本地修改或 `git pull` 更新源码后，入口读取同一份文件。已加载旧指令的会话应重新读取 skill，必要时重新打开会话。Git 记录该软链接，其他本地 `.agents/` 内容、原始文档、临时文件和输出结果不纳入 Git。新增 skill 时创建 `skills/<skill-name>/SKILL.md`，补充对应测试并更新上方目录表。
