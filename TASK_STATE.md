# paper-daily 本地发布准备状态

更新日期：2026-09-20。范围仅为本仓库；不自动 commit、push 或创建 PR。

## 本次发布授权（2026-09-20）

用户在本地版本与新版操作演示交付后明确要求「帮助我 gitpush 上去」，授权提交并推送下列 36 个已审计文件到自己的 `zhangyao23/paper-daily`，目标为 `myfork/main`；不向上游推送，不创建 PR，不强制推送。下文“未提交/未推送”描述的是此前本地交付阶段，不再表示当前禁止执行本次已授权操作。

发布前实时核验：fork 默认分支为 main，远端 SHA 为 `5b10d5891069f1957e1fb44cc6203c5e62d33416`，与本地提交起点一致；51 项测试与 Ruff 再次通过。提交 SHA 与远端校验结果以 Git 历史和发布后的只读核验为准，本地执行回执保存在忽略目录 `.local-audit/publish-result.json`。本次未包括 `config.py`，其内容仍与原 HEAD 一致。

## 起点与事实边界

- 已完整读取个人 CV、learning_skills、paper-daily 的 AGENTS.md。
- 本地 `main` HEAD：`5b10d5891069f1957e1fb44cc6203c5e62d33416`。
- `myfork`：`git@github.com:zhangyao23/paper-daily.git`，实时 HEAD 同上。
- `origin`：`https://github.com/Lin5412/paper-daily.git`。HTTPS 两次连接失败，改用同一仓库的 SSH 只读查询确认实时 HEAD：`f69b5552f95bf3f21967e0e87e343499f9b4c163`；未改变远端配置。
- 初始 `git status` 报 `.gitignore`、`src/paper_daily/config.py`、`src/paper_daily/ui/screens/results.py` 为修改状态；初始 `git diff` / `--stat` / `--numstat` 均无内容差异，暂存区无差异。未 reset、checkout、stash、覆盖已有文件版本。config.py 未修改。
- 上游基础：`7a57a4e` → `4e25432` → `0d33312` → `f69b555`。
- 已有 fork 扩展：`90a1299` 的复制、PDF 提取、深度分析与 Markdown 格式化；`5b10d58` 后续调整。它们不能列为本轮首创。

## 已实现

1. 基础 ID/URL/版本规范化；按 work 去重，最高显式版本胜出，同版本 first-wins；不拼接跨版本元数据。
2. 无 LLM 的 BibTeX 导出，字段白名单、特殊字符转义、稳定 citation key 与冲突后缀；不补写缺失作者、年份或期刊。
3. 本地 JSON 阅读列表：收藏、已读、导入导出、原子写入、写锁、坏文件保护，正向状态合并。
4. Textual 结果页保存按钮、主菜单阅读列表、列表操作；Typer 无 key 列表入口与 add/import-list/export-list。
5. 摘要/PDF 提取文本/未知来源标签；下载、解析、空文本显式降级；80,000 字符截断记录；报告确定性证据清单与本地 Markdown 保存。
6. 离线 fixture、mock 与真实 Textual Pilot 交互测试。

## 最终状态与验证

本地可发布源码版本已完成，未暂存、commit、push、创建 PR。英文 README 与中文贡献说明已完成；英文简历候选位于 `CONTRIBUTIONS.zh-CN.md`。未修改个人 CV 或其他项目。

| 检查 | 结果与边界 |
| --- | --- |
| `uv sync --extra dev` | 成功；运行环境 Windows / CPython 3.13.9，锁定 Textual 8.0.2、PyMuPDF 1.27.2、HTTPX 0.28.1、pytest 9.1.1 |
| `uv run --extra dev pytest -q --tb=short` | 演示更新后复跑 **51 passed**，4.67 秒；无真实 LLM 调用、无付费 API |
| 真实 Textual 交互 | Pilot 运行实际 App/Screen，按键与点击覆盖主菜单→结果→收藏→阅读列表→状态切换→JSON/BibTeX 导出→重新导入；检索→评分→摘要→报告流程的外部服务 mock；含剪贴板不可用分支 |
| 核心失败路径 | HTTP 503、超时、非 PDF、解析异常、空文本、80,000 字符截断；JSON 非法状态/坏记录、坏本地文件、写锁、原子替换失败保留原文件 |
| BibTeX | 用独立 BibTeX parser 解析导出；检查特殊字符、Unicode、缺失字段、版本去重与 citation key 碰撞 |
| `uv run --extra dev ruff check src tests tools` | E4/E7/E9/F 全部通过，包含新增录制脚本 |
| `uv run paper-daily --help` | 成功，列出 library / add / import-list / export-list |
| `git diff --check` | 通过，无空白错误；Git 的 LF/CRLF 提示不等于内容差异 |
| `uv build` | sdist 与 wheel 构建成功；wheel 含新模块及 `app.tcss`；两个包均保留 LICENSE |
| 真实 arXiv 烟雾请求 | 公开 ID `1706.03762v1`，普通请求及显式 User-Agent/Accept 请求均返回 **HTTP 406**；未写入私人列表，不宣称现场在线检索成功 |
| 真实 LLM / 性能 | 未进行真实 LLM 质量测试，未进行性能 benchmark，未测试全部 Python/依赖版本组合 |

使用 code-simplification Skill 对当前改动审查，仅展开 CLI/UI 导出和报告清单中的少量密集表达式，没有无关重构；修改后 51 项测试通过。人工核对没有因表达式展开改变算法复杂度或增加网络/I/O 调用。JSON 导入的小集合适用范围已写入 README。

## 发布文件与隐私审计

首次功能交付已审计实际 diff、全部跟踪文件与非忽略新增文件，以及 wheel/sdist，未发现私人配置、PDF、阅读记录、缓存或常见密钥模式。演示更新后的素材额外检查了录制 SVG 源文本，不含个人路径、用户名、邮箱或 API 占位值；生成的私人工作文件继续位于忽略目录。此为当前文件与已知模式审计，不代表通用秘密检测的绝对保证。

- 原作者 LICENSE 内容未变（比较时规范化 CRLF）；原始截图/动画未改动，README 明确标为上游旧演示。新增当前功能演示作为 README 主展示。
- `config.py` 与 HEAD **逐字节相同**，但沿用初始 Git 的修改状态；它不是本轮待提交文件。未通过 reset/checkout/index 刷新抹除初始状态。
- 本地构建产物 `dist/`、测试产物 `.test-tmp/`、审计结果 `.local-audit/release-audit.json` 和归档清单均被忽略，不提交。
- AGENTS.md、个人配置、环境文件、缓存、PDF、阅读列表与导出目录均有忽略规则。任意自定义导出路径仍需由使用者检查，不能认为 `.gitignore` 自动识别所有私人文件。

**准确待提交文件：36 个**（基于实际内容差异与非忽略新增文件，含本轮新增 4 个演示素材和 1 个录制脚本，未执行 git add）：

```text
.gitignore
CONTRIBUTIONS.zh-CN.md
README.md
TASK_STATE.md
assets/demo-library.gif
assets/reading-list.png
assets/report-evidence.png
assets/results-library.png
pyproject.toml
src/paper_daily/cli.py
src/paper_daily/core/bibtex.py
src/paper_daily/core/exports.py
src/paper_daily/core/identifiers.py
src/paper_daily/core/reading_list.py
src/paper_daily/pipeline/arxiv.py
src/paper_daily/pipeline/deep_reviewer.py
src/paper_daily/pipeline/evidence.py
src/paper_daily/pipeline/formatter.py
src/paper_daily/pipeline/pdf_fetcher.py
src/paper_daily/pipeline/scorer.py
src/paper_daily/pipeline/summarizer.py
src/paper_daily/prompts/deep_review.py
src/paper_daily/prompts/formatter.py
src/paper_daily/ui/app.py
src/paper_daily/ui/screens/library.py
src/paper_daily/ui/screens/main_menu.py
src/paper_daily/ui/screens/report_running.py
src/paper_daily/ui/screens/results.py
tests/conftest.py
tests/fixtures/arxiv.xml
tests/test_cli.py
tests/test_library.py
tests/test_pipeline.py
tests/test_ui.py
tools/record_demo.py
uv.lock
```

## 操作演示更新（2026-09-20）

- 主演示：`assets/demo-library.gif`，1200×1020，13 帧/步骤，36.2 秒，477,372 字节。每帧有英文操作字幕和离线 fixture 标识。
- 静态截图：`assets/results-library.png`、`assets/reading-list.png`、`assets/report-evidence.png`；分别展示摘要依据、已读状态、报告降级证据。
- 录制范围：选择关键词→真实结果页→保存→BibTeX 导出与文件预览→阅读列表→已读/取消收藏→JSON 备份→重复导入合并→Markdown 报告与文件预览。
- 通过 Textual Pilot 操作实际 App/Screen；保存、切换状态、导入导出调用真实代码并逐步断言。仅检索、评分、摘要、LLM review/formatter 和 PDF 失败采用 synthetic fixture/mock。文件预览明确标识为导出文件，不暗示应用新增了查看器。
- 录制不加载个人配置、不使用真实 API key、不触碰真实剪贴板、不把个人阅读列表写进素材；源码 SVG 内容检查通过。全部帧做概览检查，结果页/阅读页/报告页已目视检查。
- `tools/record_demo.py` 可复现；`pyproject.toml` / `uv.lock` 新增可选 `demo` 依赖组（Pillow、Playwright），不增加应用运行必需依赖。实际使用已安装 Edge 的 headless 模式渲染 Textual SVG 并组合 GIF。
- 验证：录制脚本成功跑通全部 13 步；现有 51 测试通过；Ruff 包含 tools 后通过；diff whitespace 检查通过。未自动提交/推送。

```bash
uv run --group demo tools/record_demo.py --browser-channel msedge
# 未安装 Edge/Chrome 时，可安装 Playwright Chromium 后省略 browser-channel。
```

## 文档核对

本轮已读取官方文档，未依赖第三方教程确定协议行为：

- arXiv ID/version：https://info.arxiv.org/help/arxiv_identifier.html
- arXiv Atom API/metadata：https://info.arxiv.org/help/api/user-manual.html
- Textual 无头真实 UI 测试：https://textual.textualize.io/guide/testing/
- PyMuPDF 文本提取局限：https://pymupdf.readthedocs.io/en/latest/recipes-text.html
- HTTPX HTTP 错误与 timeout：https://www.python-httpx.org/quickstart/
- uv 锁定与同步：https://docs.astral.sh/uv/concepts/projects/sync/

后续若发布，只提交上述审阅后的源码/文档/测试；现场 arXiv 406 与真实 LLM 效果仍需在目标环境另行验证，不自动产生新的远程操作。

## 恢复与验证命令

```bash
uv sync --extra dev
uv run --extra dev pytest -q
uv run --extra dev ruff check src tests
uv run paper-daily --help
git diff --check
```

测试数据在被忽略的 `.test-tmp/`；所有 LLM 调用 mock，外网 socket 被禁止，Windows asyncio 所需 loopback 例外。开发缓存与本地审计放 `.local-audit/`，不纳入发布。
