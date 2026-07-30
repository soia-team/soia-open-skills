# soia-env-storage-cleanup

> 面向小白统计 SOIA 受管配置、状态、缓存和临时目录的空间占用，生成可清理清单并提醒删除风险；只有客户看过最新清单并明确授权后才执行删除，随后复核实际释放空间

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-storage-cleanup) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「检查 SOIA 占用」「统计缓存大小」「清理临时文件」「清理过期状态」「释放磁盘空间」；不用于未经授权的全盘清理。

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 看 SOIA 数据占了多少空间 | 只读统计配置、状态、缓存和临时目录 | 各类别大小、文件数和可清理大小 |
| 判断哪些文件能清理 | 按时效、容量、安全标记和活动状态分类 | 可清理、需授权、禁止清理及原因 |
| 清理过期数据 | 先冻结计划，提醒风险，等待明确授权后按计划删除 | 删除数量、失败项和实际释放空间 |
| 复核清理结果 | 重新检查删除结果和回执摘要 | 是否删除成功、是否有文件重新出现 |

本技能只清理 SOIA 标准受管目录，不扫描或清理整个磁盘，不删除普通下载、项目、照片、文档或其他应用数据。

### 客户如何使用

客户只需要用自然语言提出目标，不需要操作终端：

1. 客户说“检查 SOIA 占用”时，只执行扫描，不删除任何文件。
2. 客户说“清理缓存”时，先生成计划并展示风险；这句话只表示目标，不是最终删除授权。
3. Agent 必须停下来等待客户在看到最新计划后明确回复，例如“确认按计划 `<plan_id>` 删除”。
4. 只有同一份未过期计划获得授权后，Agent 才执行清理；模糊的“继续”“随便处理”不能作为授权。
5. 清理完成后重新检查，并向客户报告实际结果。

## 安装

本技能随 `soia-env` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-env@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-env@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-env-skills -g -a '*' -s soia-env-storage-cleanup -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
