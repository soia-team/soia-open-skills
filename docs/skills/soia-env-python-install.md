# soia-env-python-install

> 为新手安装、验证或按授权更新 Python 与 pip

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-python-install) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「安装 Python」「更新 Python」「python 命令不存在」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 安装 Python | 识别系统/架构、选择官方稳定版本、安装并验证 | Python/pip 版本和状态 |
| 检查 Python 更新 | 识别解释器来源与项目约束，不自动更新 | 当前版本、最新版本和来源 |
| 更新 Python 到最新 | 客户明确要求最新版后沿原来源更新 | 中间状态、虚拟环境影响和验证结果 |
| pip 不可用 | 区分解释器、PATH、pip 模块和权限问题 | 安全修复方案 |
| 准备脚本或知识库工具 | 创建项目级虚拟环境并验证依赖入口 | 可交给下游技能的 readiness 摘要 |

### 客户如何使用

其他可识别说法包括「更新 Python 到最新」「安装 pip」「pip 不能用」；纯网络超时优先交给 `soia-env-network-diagnose`。

1. 说目标项目、操作系统和是否有版本要求；不确定时选择 Python 官方当前维护的稳定版本。
2. Agent 先检查 `python3`、`python`、Windows `py`、pip 和项目配置，不覆盖已有环境。
3. 发现新版本时只汇报；只说“更新 Python”时先询问是否更新到最新，明确选择最新版后才执行。
4. 展示安装源、版本和 PATH 影响；需要管理员权限或系统范围安装时单独确认。
5. 安装或明确授权的更新过程中持续显示并记录检查、计划、执行、验证和终态。

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
npx skills add soia-team/soia-open-env-skills -g -a '*' -s soia-env-python-install -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
