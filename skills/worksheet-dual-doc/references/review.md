# 人工或代理审核记录

读取 verification.json，必须 errors 为空。打开所有 qa/pages 下页面，逐页检查；审阅 input.json 中全部题目的答案及解析。

审核 JSON 示例（摘要和页数必须从当前 verification.json 获取；禁止直接复制示例作为证据）：

```json
{
  "题目版": {"sha256":"当前DOC摘要", "pages_checked":[1,2,3], "issues":[]},
  "答案版": {"sha256":"当前DOC摘要", "pages_checked":[1,2,3,4], "issues":[]},
  "content_review": {"status":"passed", "notes":"说明实际审阅范围、是否有原文疑点"}
}
```

执行 `scripts/run.sh approve /absolute/run --review /absolute/review.json`，仅在通过后发布到 deliverables。出现疑点则 content_review.status 填 needs_confirmation，保留问题位置，不会发布。

注意：审核记录是审阅者的声明，脚本校验其完整性与文件摘要，不能证明审阅者真的看过页面。Skill 必须完成实际观察，不能自动制造记录。

开发兼容性验收：允许使用 computer-use 在 WPS 中打开最终 DOC，记录实际文件哈希、检查页及应用版本。日常生成仍使用脚本。WPS 与 LibreOffice 的分页可能不同，按各自实际页面检查，不把页数相同当成正确性的依据。文末不要添加仅用于撑留白的空段落，以免 WPS 出现额外空白页。

## 缩进独立检查

不能仅检查生成器写入的缩进常量。layout_audit.py 从最终 DOC 渲染的 PDF 获取句点末端、题干首字和续行起点，独立检查间距、悬挂、题号顺序及跨页续行；开头中文标点允许有限光学悬挂。题号句点后不得插空格/TAB，表格内部不得继承外层题干缩进。视觉检查同时对照样本信息栏，检查单、两位数题号和长选项。WPS 字体工具栏不作为实际字体可用的证据，应查看字体对话框；原生复核记录明确文件哈希和检查范围，不扩写为全套逐页复核。

发生删除时，审核JSON还需要 deletion_report: {"sha256":"当前删除PDF摘要","pages_checked":[实际全部页码]}。综合题空位属于有意留白，应检查原号、可编辑段落和原内容隔离；不要以恢复原题来填满页面。
