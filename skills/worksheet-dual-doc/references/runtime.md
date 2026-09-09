# 环境和自动修复

使用 Codex `load_workspace_dependencies` 返回的 Python。依赖：python-docx、lxml、Pillow、pdfplumber、pypdfium2；soffice 为同一运行时中的无界面 LibreOffice。不要默认调用系统 Python 或临时安装另一套转换引擎。

`run.sh` 先使用 WORKSHEET_PYTHON，再尝试当前用户下的 Codex 捆绑运行时。不同环境下入口代理应先通过依赖加载工具定位，设置环境变量后执行。soffice 在对应运行时 bin/override、bin/fallback、PATH 中自动查找。

字体解析自动搜索配置目录、系统字体、Microsoft Office 字体、WPS缓存和本地缓存，并读取字体内部 family 确认宋体。为无界面 LibreOffice 创建临时 fontconfig，macOS 另按下文准备用户字体，不把版权字体打包进 skill。

可选环境变量：
- WORKSHEET_FONT_DIR：已有合法字体所在目录，优先查找。
- WORKSHEET_FONT_CACHE：字体缓存位置。
- WORKSHEET_FONT_URL 与 WORKSHEET_FONT_SHA256：管理员配置的合法 HTTPS 字体源及固定摘要；两者齐全才下载并校验。

没有查到宋体时先扩大已安装目录和缓存搜索；不将 Linux 替代字体或其他宋体风格字体自动声明成 SimSun。只有自动发现、已配置可信源都不可用才需要用户提供资源。下载失败或校验失败不得继续使用不可信文件。

转换在独立临时 Office profile 中运行，避免影响用户打开的 WPS/Word。保留输入与失败日志；转换超时不要无限重试。整个生成与日常验收无需 UI；开发时可用 WPS 原生打开候选 DOC 检查兼容性。

## 原生办公软件字体

找到 Office 私有字体只证明渲染器可访问，不等于 WPS 已安装。macOS 通过用户字体目录准备本地合法宋体并查询 CoreText；报告分别记录字体文件和 native_registered。其他系统 native_registered 为 null，不能据此宣称原生软件已验证。日常 LibreOffice 仍使用独立字体配置。不得打包或传播本地商业字体。已运行 WPS 可能缓存字体列表，开发检查需保存工作后重新打开，并在字体对话框确认没有缺失字体提示。

题源字体指定为隶书LiSu。自动发现之外，可配置WORKSHEET_SOURCE_FONT_FILE或WORKSHEET_SOURCE_FONT_URL与WORKSHEET_SOURCE_FONT_SHA256（合法可信HTTPS源、摘要必填），自动下载校验后准备用户字体。不以华文隶书、傈僳文Lisu字体替代。

题源字体验收按用户新确认执行：最终DOC重开后的题源字体属性必须为隶书/LiSu、五号；本机缺少真实隶书时允许渲染器替代显示，不阻止交付。记录预览替代警告，不能宣称已验证真实隶书的字形和换行。正文宋体的实际渲染检查保持不变。自动查找可用隶书，但不再要求用户补齐才能生成。
