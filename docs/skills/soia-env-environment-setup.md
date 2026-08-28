# soia-env-environment-setup

> 从零规划并验证面向新手的开发环境，协调所需安装技能

所属：[`soia-env`](https://github.com/soia-team/soia-open-env-skills) · [技能源码](https://github.com/soia-team/soia-open-env-skills/tree/main/skills/soia-env-environment-setup) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「从零配置开发环境」「准备 AI CLI 环境」「新电脑开发环境搭建」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 从零配置开发环境 | 检查系统、网络、运行时，再按依赖顺序安装 | 每一步计划、权限请求和验证结果 |
| 准备知识库或 PKM 工作 | 先确认 Node/Python、网络和登录状态 | 可交给其他 SOIA 技能库的就绪摘要 |
| 不知道缺什么 | 只读盘点命令、版本和常见阻塞 | 缺什么、为什么缺、下一步怎么补 |

### 客户如何使用

用自然语言说目标，例如“帮我把这台电脑准备好使用 Codex”和系统类型；Agent 先读取当前系统与工具状态，生成安装计划，安装、PATH/profile 修改、管理员权限或网络设置变更前展示影响并确认。客户只在官方图形界面完成登录、验证码、系统安全提示和产品授权；每一步独立验证后再进入下一步，失败时停止在当前步骤。只安装单个运行时或 CLI 时交给对应安装技能。

### 已安装工具的生命周期

先盘点版本、来源、配置目录/文件和项目约束，再归入 `missing`、`needs_configuration`、`ready`、`update_available` 或 `blocked`。`ready` 必须同时满足：命令/应用存在、版本验证通过、首次登录或 API 配置完成、无副作用启动/认证验证通过；“已安装”不等于“ready”。默认只检查并汇报当前版本和可用版本，不自动更新；客户只说“更新”时，先展示两个版本并询问是否“更新到最新版本”，没有这句明确选择，不调用更新器。完整状态语义见 [lifecycle.md](references/lifecycle.md)。

### 安装与更新的中间状态

真正开始安装或更新后，必须在对话中持续追加阶段状态：检查、计划/等待确认、安装或更新、验证、完成/失败/被阻塞；不能只给最终表。各专门安装技能使用自己的 `scripts/record_install_progress.py` 写入私有 state；编排技能只汇总子技能的阶段和 `run_id`，不重复保存第二份完整日志。只读盘点不创建中间状态文件。细则见 [lifecycle.md](references/lifecycle.md)。

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
npx skills add soia-team/soia-open-env-skills -g -a '*' -s soia-env-environment-setup -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
