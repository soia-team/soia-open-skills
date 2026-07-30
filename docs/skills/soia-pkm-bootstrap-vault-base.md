# soia-pkm-bootstrap-vault-base

> 初始化知识库中立的 Markdown vault 骨架、多 AI 入口与 PKM 闭环，不包含平台特化配置

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-bootstrap-vault-base) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「初始化知识库」「从零建 Markdown 知识库」「搭通用 vault 骨架」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 从零开始建本地 Markdown 知识库 | 按配置创建 PARA 骨架、各区规则、模板和使用手册 | 目录、规则文件、模板及终端摘要 |
| 让多个 AI 共用一套规则 | 创建多 AI adapter，并让 `AGENTS.md` 保持唯一真源 | 各入口文件和规则路由 |
| 接入 PKM 闭环 | 安装或检查 SOIA 的 clip、organize、distill、compose、publish 等技能 | 安装结果、缺失依赖和后续命令 |

本 skill 不负责安装或配置 Obsidian，也不负责把内容上传到 ima。需要这些能力时，继续使用 `soia-pkm-bootstrap-vault-obsidian` 或 `soia-pkm-bootstrap-vault-ima`。

### 客户如何使用

1. 提供目标 vault 路径，并说明是否使用默认 JSON 配置或自己的 JSON/YAML 配置。
2. 对通用 Markdown 知识库运行初始化脚本时使用 `--no-obsidian`，跳过默认配置中的 `.obsidian/**` 产物。
3. 检查生成的目录、规则和模板，再接入需要的 AI 与 PKM 技能。
4. 需要 Obsidian 时，让 `soia-pkm-bootstrap-vault-obsidian` 在 base 完成后处理平台配置；需要 ima 时，让 `soia-pkm-bootstrap-vault-ima` 处理云端消费端接入。
5. 执行后核对真实文件和闭环示例，不以命令退出码单独宣称完成。

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
npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -s soia-pkm-bootstrap-vault-base -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
