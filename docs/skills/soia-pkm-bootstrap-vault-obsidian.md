# soia-pkm-bootstrap-vault-obsidian

> 以 dry-run 和保留未知配置的结构化合并方式，把已有 Markdown vault 配置为 Obsidian 消费端，启用 Bases 与可选宽页 CSS

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-bootstrap-vault-obsidian) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「配置 Obsidian vault」「启用 Obsidian Bases」「接入 Obsidian 消费端」

## 能力与用法

### 这个技能可以做什么

- 检查 Obsidian 客户端是否可用；版本信息需以本机或官方当前信息为准。
- dry-run 预览并结构化合并 `core-plugins.json`、`appearance.json` 与可选 `app.json`，兼容新版对象和旧版列表两种核心插件格式。
- 保留未知核心插件、主题、snippet 和 JSON 键；启用 Bases 与宽页 CSS 时不覆盖客户现有配置。
- 为工作台和工作台历史补充两个 create-only `.base` 视图；已有视图始终保留。
- apply 前备份将修改的现有文件；支持 `--check` 验收。

本 skill 不创建 PARA 骨架、不替代 base，也不把 Obsidian 数据反向写回其他云端知识库。

### 客户如何使用

其他可识别说法包括「配置 Obsidian」「装 Obsidian 插件」「Obsidian 特化配置」「启用 Bases」；从零建立通用 vault 骨架时先使用 `soia-pkm-bootstrap-vault-base`。

1. 先用 base 初始化或确认已有 Markdown vault；base 不写 `.obsidian`。
2. 提供 vault 路径，先运行脚本默认 dry-run。
3. 展示 JSON 合并和 CSS create/drift 清单，客户确认后加 `--apply`。
4. 运行 `--check`，再在 Obsidian 中打开 Bases 和普通笔记验证。

## 安装

本技能随 `soia-pkm-vault` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-pkm-vault@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-pkm-vault@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -s soia-pkm-bootstrap-vault-obsidian -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
