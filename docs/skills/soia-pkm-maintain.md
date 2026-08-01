# soia-pkm-maintain

> 旧版 vault 维护技能的兼容路由，将健康检查、工作台生命周期和 AI 会话日志请求转到职责明确的新技能

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-maintain) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「vault 周维护」「重建全库地图」「整理工作台」「接入会话日志」

## 能力与用法

### 这个技能可以做什么

| 旧请求 | 新技能 |
|---|---|
| vault 周维护、死链/标签/过期检查、重建地图 | `soia-pkm-maintain-vault-health` |
| 整理工作台、清 Inbox、冻结证据、归档历史 | `soia-pkm-manage-vault-lifecycle` |
| Claude/Codex 会话日志、SessionEnd、notify | `soia-pkm-log-agent-sessions` |

只读搜索不属于旧 maintain 的实现，直接使用 `soia-pkm-query-vault`。

### 客户如何使用

旧提示词仍可触发本技能；Agent 必须立即说明实际路由到哪个新技能，并遵循目标技能的 dry-run、授权、日志与验收规则。不要继续在本文件拼装新的“万能维护”工作流。

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
npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -s soia-pkm-maintain -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
