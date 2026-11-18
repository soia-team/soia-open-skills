# soia-pkm-alipan-drive-ops

> 执行阿里云盘登录、浏览与文件操作，并为资源整理提供底层能力

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-alipan-drive-ops) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「登录阿里云盘」「下载阿里云盘文件」「全盘扫描阿里云盘」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 安装、登录或远程续期阿里云盘 | 用包装器 `run_with_env.py` 检查状态；支持非交互 pty 拉出 5 分钟扫码链接远程恢复 | UID、容量配额与双盘空间摘要 |
| 只读浏览或全盘 JSONL 扫描 | 显式 `--driveId` 列目录，或跑 `scan_drive.py` 输出断点续扫 JSONL 与 sidecar | JSONL 快照、目录/文件数与同名歧义告警 |
| 按批准计划执行安全读写与下载 | 在批准清单内限流节拍运行 `mv`/`rename`/`mkdir`/`download`/`rm` 并回读验证 | 账本记录、逐项 `✓/✗` 回读与交付路径 |

### 客户如何使用

- 「只读扫描阿里云盘备份盘的 `/某个目录`，输出 JSONL 快照。」
- 「按已批准的迁移清单预览 `mv`/`rename`，不要删除任何文件。」
- 「从资源库把 `<远端路径>` 下载到指定本地目录。」

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-alipan-drive-ops -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
