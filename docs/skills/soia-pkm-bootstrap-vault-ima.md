# soia-pkm-bootstrap-vault-ima

> 把已有本地 Markdown vault 接入腾讯 ima 知识库消费端：安装客户端、建立目录映射、用 ima 官方 Skills 配置本地文件夹监控同步并验证检索

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-bootstrap-vault-ima) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「接入 ima」「同步到 ima 知识库」「配置 ima」「让 ima 监控 vault」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 在 ima 中检索 vault 内容 | 建立同步范围和目录映射，接入指定 ima 知识库 | 映射表、同步范围和验证结果 |
| 新文章自动进入 ima | 引导使用 ima 官方 Skills 的本地文件夹监控能力 | 监控源目录、目标知识库和首次同步回执 |
| 保持本地内容为真源 | 明确单向同步与排除项 | 不会执行 ima → vault 反向同步 |

本 skill 不负责从零创建 vault，也不编造 ima 客户端的按钮名称、菜单路径或未公开 API。ima 具体 UI 操作未经本次实测，首次执行时必须以客户端实际界面为准并校正本文档。

### 客户如何使用

1. 提供已有 vault 路径、希望同步的相对目录、目标 ima 知识库和一篇用于验证的文章标题。
2. 安装并登录 ima 客户端。
3. 先确定 allowlist 形式的本地同步范围，再在 ima 官方 Skills 中配置本地文件夹监控。
4. 首次同步只选一篇或一个小目录，确认层级、标题和正文后再扩大范围。
5. 在 ima 搜索验证文章；任何冲突都以本地 Markdown 为准，不从 ima 反向写回。

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
npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -s soia-pkm-bootstrap-vault-ima -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
