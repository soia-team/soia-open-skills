# soia-pkm-bootstrap-vault-obsidian

> 将已有 Markdown vault 配置为 Obsidian 消费端，并衔接通用 vault 基座

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-bootstrap-vault-obsidian) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「配置 Obsidian vault」「启用 Obsidian Bases」「接入 Obsidian 消费端」

## 能力与用法

### 这个技能可以做什么

- 安装或检查 Obsidian 1.9+。
- 启用核心插件 **Bases**，用于书库、文章库等数据库视图。
- 检查 `.obsidian/` 与 `snippets/wide-page.css` 是否已由 base 脚本生成，并说明手动启用步骤。
- 提供 Tars、Terminal、Obsidian Git 等可选配置边界。

本 skill 不创建 PARA 骨架、不替代 base，也不把 Obsidian 数据反向写回其他云端知识库。

### 客户如何使用

其他可识别说法包括「配置 Obsidian」「装 Obsidian 插件」「Obsidian 特化配置」「启用 Bases」；从零建立通用 vault 骨架时先使用 `soia-pkm-bootstrap-vault-base`。

1. 先安装并运行 `soia-pkm-bootstrap-vault-base`，通用初始化使用 `--no-obsidian`；如果要让脚本同时生成 CSS snippet，则按下方命令不带该参数运行。
2. 提供已有 vault 路径，确认 Obsidian 是否已安装及版本。
3. 按本 skill 完成核心插件和可选插件配置。
4. 在 Obsidian 中打开目标 vault，确认规则、模板和文章能正常显示。

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
