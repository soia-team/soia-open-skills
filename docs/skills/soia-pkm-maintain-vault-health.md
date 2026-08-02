# soia-pkm-maintain-vault-health

> 只读检查整个 Markdown/Obsidian 知识库或指定模块的健康状态，审计死链、歧义文件名、标签策略与过期内容，并按授权重建地图或健康简报

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-maintain-vault-health) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「检查知识库健康」「检查知识库某个模块」「维护知识库」「重建知识库地图」「vault 周维护」

## 能力与用法

### 这个技能可以做什么

| 客户目标 | 技能行为 | 默认是否写文件 |
|---|---|---|
| 检查 vault 健康 | 扫描死链、重复文件名、主标签漂移、未打标、过期文章、读取失败，并报告 20 区目录编号漂移 | 否 |
| 重建知识库地图 | 先生成临时预览；用户明确要求后覆盖配置的地图文件 | 预览否，确认后是 |
| vault 周维护 | 运行健康检查，汇总近 7 天变化；按授权写周简报 | 默认否 |

### 客户如何使用

提供 vault 路径；若要检查主标签，再提供白名单或在私有配置中设置。只说“检查”时输出 stdout/JSON，不落盘。只有用户明确要求“保存周报”或“重建地图”才写对应产物。

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
npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -s soia-pkm-maintain-vault-health -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
