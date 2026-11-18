# soia-pkm-baidu-netdisk-ops

> 百度网盘原子操作与只读 JSONL 扫描适配

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-baidu-netdisk-ops) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「看下百度网盘」「登录百度网盘」「扫描百度网盘」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 登录或检查百度网盘态 | 检查 `bdpan` 版本/登录态；支持设备码则生成授权链接与解码二维码交客户扫码 | 官方授权地址、非敏感状态与 `whoami` 核对 |
| 浏览、搜索与全盘 JSONL 扫描 | 运行 `ls --json`/`search --json` 或 `scan_drive.py` 多线程只读扫盘生成 sidecar | 远端清单、扫描统计、`.errors`/`.done` 与路径 |
| 按授权传输或建目录/移动/分享 | 先核父目录与冲突策略（`share` 单独确认），执行后回读验证 | 操作前范围确认与终态核实结果 |

### 客户如何使用

说明目标并给出远端虚拟路径（如 `/资料`）和本地路径；Agent 先查登录态，写操作/分享/覆盖先列出精确范围与冲突策略，确认后执行并回读验证。

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
npx skills add soia-team/soia-open-pkm-vault-skills -a <agent> -s soia-pkm-baidu-netdisk-ops -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
