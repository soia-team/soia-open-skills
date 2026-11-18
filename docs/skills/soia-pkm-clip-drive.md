# soia-pkm-clip-drive

> 把云盘/本地文档或受控 PDF URL 导入 Obsidian vault，提取可搜索正文并接入整理

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-clip-drive) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「导入云盘资料」「下载这些 PDF」「clip 这个文档」「OCR 这批图片」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 导入本地/云盘 PDF、Word、PPT、表格 | 计算 SHA-256、提取可搜索文本并生成带来源元数据的资料/摘抄笔记 | `<vault-resources-dir>/<主题>/` 或文章区 Markdown 与哈希回执 |
| 归档并深度提取受控 PDF URL | `archive_pdf.py --deep --extract` 校验魔数/哈希，发现 arXiv/HTML 论文 PDF 并抽文本 | 原 PDF、`-extracted.txt` 与逐条状态 |
| 处理图片或扫描版 PDF | 严格区分文件名命中与正文命中；仅显式运行 OCR 后标 `ocr` 正文状态 | 提取限制说明或带来源/工具标签的正文笔记 |

### 客户如何使用

- 「把这个文件夹里的 PDF 和 Word 批量提取成知识库笔记，先列清单确认。」
- 「把这个论文链接列表通过 `archive_pdf.py --deep --extract` 归档进知识库。」

## 安装

客户明确选择安装整个 `soia-pkm-vault` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-pkm-vault@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-pkm-vault@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-clip-drive -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
