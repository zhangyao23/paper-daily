# 贡献说明与简历候选

本文件按可核验 Git 历史和本轮实际代码区分贡献，不把 fork 写成独立开发整个项目。

## 归属边界

| 层次 | 事实与证据 | 合理表述 |
| --- | --- | --- |
| 原作者与上游 | LICENSE 保留 Jiaming Lin 署名；上游至 f69b555 已有检索、七维评分、摘要生成、Textual UI、设置和日历 | 使用并扩展原作者的开源终端工具 |
| 历史 fork 扩展 | 90a1299 的 Git 作者为 zhangyao；加入复制、PDF 下载/提取、deep-review 与 Markdown 格式化；5b10d58 后续调整 | 历史 fork 已有 PDF 分析与报告流程；不能全算作本轮新增 |
| 本轮协作完成 | 当前 ID、BibTeX、reading-list、来源标签与测试，以及现有交互的增量接入 | 在既有 fork 上新增文献管理与导出，修复证据标注，补齐离线及 UI 测试 |

本轮由用户明确需求驱动，通过 Codex 协作实现。代码与测试可证明功能存在，不能据此声称用户逐行手写、独立设计全部上游架构，或证明部署规模与收益。

## 为什么这样实现

- **分开基础 ID 和版本号**：同一论文的 URL、v1、v2 不应占多个条目；但不能把 v1 正文分析冒充 v2。最高显式版本胜出，整条替换元数据，不跨版本拼字段；未注明版本时不猜版本号。
- **BibTeX 绕开 LLM**：作者、标题和 DOI 是引用事实。仅使用 API/用户导入字段，缺失省略，保留 canonical arXiv URL；期刊引用字符串只放 note，不解析成未经核实的 venue/pages。
- **JSON 阅读列表**：个人小型收藏不需要数据库服务。原子替换防止半写文件，写锁拒绝并发覆盖；导入前整批校验，坏记录不会造成部分导入。
- **来源标签由代码生成**：原实现 PDF 失败后仍把摘要称为 Full text。本轮将来源、降级原因、截断长度传入 review/formatter，并在报告加入不会被模型遗漏的证据清单。不保证模型正文永远正确，也不把文本提取说成看过图表。
- **保留既有交互**：继续使用 Textual 和原检索/排序/报告入口，只增加保存按钮、阅读列表和导出按键；另加无需 key 的 CLI 入口。

## 能主张与不能主张

可以主张：版本规范化、去重、BibTeX 导出、JSON 状态持久化、导入导出、证据标注、终端流程集成，以及离线/无头 UI 验证。

不能主张：独立开发整个 Paper Daily；原创上游七维评分方法；真实用户量；某个百分比的效率/准确率提升；真实 LLM 质量评估；验证全部平台与模型；通过 PDF 提取就全面核验论文。

## 英文简历候选

> Extended an existing open-source arXiv digest tool with version-aware deduplication, deterministic BibTeX export, and a local JSON reading list; integrated the features into its Textual interface and added offline regression tests for persistence, exports, and explicit PDF-to-abstract fallback provenance.

仅覆盖可核实扩展，未将原始检索、评分系统和 UI 归为独立开发，未使用未经测量的收益数字。需要体现协作方式时，可将开头改成 “Extended an existing open-source arXiv digest tool through AI-assisted development ...”。未自动写入个人 CV。

## 验证边界

- 测试使用 fixture 和 mock，不需要付费 API；真实 Textual App 通过 Pilot 键鼠事件运行。
- PDF 提取使用临时生成的真实 PDF；失败路径包括 HTTP 错误、超时、非 PDF 内容、解析异常和空文本。
- 真实 arXiv API 烟雾请求返回 HTTP 406；不宣称现场网络检索成功。未用真实 LLM 验证质量或付费调用。
- code-simplification Skill 只审查当前修改，展开少量密集表达式，不进行无关大改。未做性能 benchmark，不声称性能实测保持不变；人工检查表达式展开未增加网络/I/O 次数，JSON 导入规模限制已写入 README。
- 精确通过数、构建情况和待提交文件以 [TASK_STATE.md](TASK_STATE.md) 的最终记录为准。
