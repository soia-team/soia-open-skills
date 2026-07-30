# SOIA Skills

[English](README.en.md) · 中文

一套按领域分装的 AI 工作流技能库，74 个技能覆盖开发、知识库、新媒体、办公协作、设计文档、课程与环境安装。装成插件，按需启停。

## 这是什么

「技能」是一份告诉 AI **怎么做某件具体的事**的说明书——包含步骤、边界、验收口径和踩过的坑。它不是提示词模板，而是可版本化、可测试、可组合的工程产物。

本仓库是整个生态的**门户**：规范真源、跨仓导航、市场清单，以及 4 个管理生态自身的 meta 技能。**具体领域的技能在各自的仓库里**，通过插件市场统一分发。

```text
soia-open-skills（你在这里）
    ├── 规范    SKILL_SPEC.md · DATA_STORAGE_SPEC.md · CONTRIBUTING.md
    ├── 市场    一次注册，8 个领域插件按需安装
    └── meta    检索、同步、发布、提示词起草
                    ↓
        7 个领域仓（dev · pkm-vault · media · cwork · design · edu · env）
```

### 适合什么场景

- 「让 AI 帮我改代码，但它老是改完说『应该没问题』就交差。」
- 「网上剪藏的文章散在各处，想收进一个能搜的本地知识库。」
- 「写完文章要发公众号、X、小红书，每个平台格式都不一样。」
- 「团队资料锁在飞书和 ProcessOn 里，想导出成本地文件。」
- 「新机器要装一堆 AI CLI，每次都踩坑。」

### 不负责什么

- 不是 AI 客户端。它扩展你已有的 Claude Code / Codex，不替代它们。
- 不托管你的数据。所有内容留在你自己的机器上，技能只提供操作方法。
- 不保存凭据。各平台登录态由官方流程持有，不进仓库、不进日志。
- 不含公司内部流程。行业特定的需求、测试、发版规范在私有仓，不开源。

## 从哪里开始

**第一次用，两条命令：**

```bash
claude plugin marketplace add soia-team/soia-open-skills
```

```bash
claude plugin install soia-meta@soia
```

装完对 AI 说「**找个技能**」，`soia-meta-find-skill` 会按你的需求检索全生态 74 个技能并告诉你装哪个——不必先读完下面的表。

**已经知道要什么，直接装对应领域：**

| 我要做的 | 装这个 | 技能数 | 常驻成本 |
|---|---|---|---|
| 写代码、审代码、管 PR | `soia-dev` | 12 | ~971 tok |
| 建知识库、剪藏、整理、转换 | `soia-pkm-vault` | 26 | ~2.8k tok |
| 配电脑、装 AI CLI、诊断网络 | `soia-env` | 15 | ~1.5k tok |
| 写文章、配图、多平台发布 | `soia-media-content` | 6 | ~691 tok |
| PRD、原型、架构图、Office | `soia-dev-design` | 6 | ~548 tok |
| 飞书、ProcessOn 资料导出 | `soia-cwork-office` | 3 | ~309 tok |
| 课程大纲与教案 | `soia-edu-course` | 2 | ~140 tok |
| 管理技能生态本身 | `soia-meta` | 4 | ~396 tok |

> **常驻成本**指该插件的技能索引每次会话占用的上下文；技能正文只在命中时才载入。
> 暂时不用的领域用 `claude plugin disable <插件名>` 关掉，成本归零，随时开回来。

Codex 用户把 `claude` 换成 `codex`、`install` 换成 `add` 即可，其余相同。
其他 60+ 宿主（Cursor、Zed、Windsurf 等）见 [安装指南](docs/install/README.md)；
按机器用途组织的安装组合见 [install-profiles.md](docs/install-profiles.md)。

## 生态拓扑

| 仓库 | 职责 | 插件 |
|---|---|---|
| [soia-open-skills](https://github.com/soia-team/soia-open-skills) | 门户、规范真源、市场清单、meta 技能 | `soia-meta` |
| [soia-open-dev-skills](https://github.com/soia-team/soia-open-dev-skills) | 工程契约：任务执行、修复闭环、评审、GitHub 运维 | `soia-dev` |
| [soia-open-dev-design-skills](https://github.com/soia-team/soia-open-dev-design-skills) | 设计与文档产线：PRD、原型、架构图、Office | `soia-dev-design` |
| [soia-open-pkm-vault-skills](https://github.com/soia-team/soia-open-pkm-vault-skills) | 知识库全生命周期：剪藏、整理、提炼、转换 | `soia-pkm-vault` |
| [soia-open-media-content-skills](https://github.com/soia-team/soia-open-media-content-skills) | 内容生产最后一公里：成文、配图、分平台发布 | `soia-media-content` |
| [soia-open-cwork-office-skills](https://github.com/soia-team/soia-open-cwork-office-skills) | 把 SaaS 平台里的资料导出成本地文件 | `soia-cwork-office` |
| [soia-open-edu-course-skills](https://github.com/soia-team/soia-open-edu-course-skills) | 课程大纲与教案设计 | `soia-edu-course` |
| [soia-open-env-skills](https://github.com/soia-team/soia-open-env-skills) | 环境就绪：网络诊断、运行时与 AI CLI 安装 | `soia-env` |

机器可读的全生态技能目录见 [routing-manifest.json](routing/routing-manifest.json)。

## WorkBuddy 专家

除 Claude 与 Codex 两份市场清单外，域仓还派生第三张清单 `.codebuddy-plugin/plugin.json`，
把该域封装成 WorkBuddy 的**角色化专家**（人设 + 技能组合 + 展示元数据），不召唤就不在场。

**一个域仓 = 一个插件 = 一个专家**，与 Claude/Codex 同一条粒度规则。技能不复制——
清单直接引用本仓 `skills/`，`avatar` 直接用本仓 `assets/icon.png`（与 Codex 的 logo 同一个文件）。

专家定义放在各域仓，不在本仓。已就绪：`soia-pkm-vault`（知识库管家 / Soia Vault）。

装载与限制见 [WorkBuddy 安装指南](docs/install/workbuddy.md)——WorkBuddy 的自建专家
只认硬编码目录 `my-experts`，没有按 sha pin 拉远端仓那一层，这点与 Claude/Codex 不同。


## 本仓技能

| 技能 | 一句话职责 |
|---|---|
| [`soia-meta-find-skill`](skills/soia-meta-find-skill/) | 按需求检索全生态技能并加载，不必预先知道技能名。 |
| [`soia-meta-skill-release`](skills/soia-meta-skill-release/) | 技能改动合并后完成市场发布、客户端更新与缓存回收。 |
| [`soia-meta-sync-skills`](skills/soia-meta-sync-skills/) | 把共享技能源软链同步到你明确选择的 AI 工具目录。 |
| [`soia-meta-prompt-clarity`](skills/soia-meta-prompt-clarity/) | 起草、诊断并规格化中英文提示词，保留原意与安全边界。 |

## 规范文档

| 文档 | 说明 |
|---|---|
| [docs/learning-guide.md](docs/learning-guide.md) | **先读这份**：整套生态怎么运转、为什么这么设计、常见疑问 |
| [SKILL_SPEC.md](SKILL_SPEC.md) | 技能结构、命名、frontmatter 与验证要求 |
| [DATA_STORAGE_SPEC.md](DATA_STORAGE_SPEC.md) | 配置、凭据、状态、缓存与输出的存储边界 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 外部贡献者指南 + 维护者手册 |
| [docs/install/](docs/install/README.md) | 60+ AI 宿主的安装指南 |
| [docs/plugin-dev.md](docs/plugin-dev.md) | 本地插件迭代与发版后的元仓刷新流程 |

## License

[MIT](LICENSE)
