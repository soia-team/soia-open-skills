# SOIA Skills 生态门户

[English](README.en.md)

SOIA Skills 的公开生态门户：提供共享规范、跨仓导航、公开路由清单和生态级 meta 技能。

## 技能目录

| 技能名 | 一句话简介 |
|---|---|
| [`soia-meta-prompt-clarity`](skills/soia-meta-prompt-clarity/) | 起草、诊断并规范化中英文提示词，同时保留原有语言与边界。 |
| [`soia-meta-skill-release`](skills/soia-meta-skill-release/) | 协助完成技能发布后的安装、旧名清理和版本状态核对。 |
| [`soia-meta-sync-skills`](skills/soia-meta-sync-skills/) | 将共享技能安全同步至用户明确选择的 AI 工具目录。 |

## 生态拓扑

| 仓库 | 职责 |
|---|---|
| [`soia-open-skills`](https://github.com/soia-team/soia-open-skills) | 生态门户、共享规范、公开路由和 meta 技能。 |
| [`soia-open-env-skills`](https://github.com/soia-team/soia-open-env-skills) | 开发环境的诊断、安装与升级支持。 |
| [`soia-open-pkm-clip-skills`](https://github.com/soia-team/soia-open-pkm-clip-skills) | 网页、社交内容和云盘资料的剪藏与导入。 |
| [`soia-open-pkm-vault-skills`](https://github.com/soia-team/soia-open-pkm-vault-skills) | Markdown 知识库的初始化、整理、提炼、转换和书库维护。 |
| [`soia-open-media-content-skills`](https://github.com/soia-team/soia-open-media-content-skills) | 文章创作、封面制作与多平台内容发布。 |
| [`soia-open-cwork-office-skills`](https://github.com/soia-team/soia-open-cwork-office-skills) | 协作办公工具与文档服务的集成操作。 |
| [`soia-open-dev-coding-skills`](https://github.com/soia-team/soia-open-dev-coding-skills) | 编码、任务执行、代码评审、修复和 GitHub 操作。 |
| [`soia-open-dev-design-skills`](https://github.com/soia-team/soia-open-dev-design-skills) | Open Design、架构图、图表和 Office 设计工作流。 |
| [`soia-open-dev-infra-skills`](https://github.com/soia-team/soia-open-dev-infra-skills) | 基础设施、终端操作和运行维护能力。 |
| [`soia-open-safe-skills`](https://github.com/soia-team/soia-open-safe-skills) | 代码安全审计与公开漏洞情报跟踪。 |
| [`soia-open-edu-course-skills`](https://github.com/soia-team/soia-open-edu-course-skills) | 课程大纲、教学材料和测评设计。 |
| [`soia-open-dev-product-skills`](https://github.com/soia-team/soia-open-dev-product-skills) | 产品需求、用户故事和需求评审工作流。 |
| [`soia-open-dev-testing-skills`](https://github.com/soia-team/soia-open-dev-testing-skills) | 测试用例、测试文档和质量保障工作流。 |
| [`soia-open-dev-release-skills`](https://github.com/soia-team/soia-open-dev-release-skills) | 软件发布清单、预检和发布验证。 |

完整的机器可读技能目录见 [`routing/routing-manifest.json`](routing/routing-manifest.json)。

## 安装

### 插件方式（推荐）

插件方式按领域安装和开关整组技能；例如安装知识剪藏插件：

```bash
claude plugin marketplace add soia-team/soia-open-skills
/plugin install soia-pkm-clip@soia

codex plugin marketplace add soia-team/soia-open-skills
codex plugin add soia-pkm-clip@soia

qwen extensions install https://github.com/soia-team/soia-open-skills:soia-pkm-clip
```

Claude 可用 `claude plugin enable`、`claude plugin disable` 和 `claude plugin update` 管理已安装插件。

### npx 方式

npx 方式保留单技能粒度，适合只安装某一个明确技能。

按需安装单个技能：

```bash
npx skills add soia-team/<仓库名> -g -a '*' -s <技能名> -y
```

例如，安装提示词澄清技能：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-prompt-clarity -y
```

更多按机器用途组织的安装组合，见 [`docs/install-profiles.md`](docs/install-profiles.md)。

## 规范文档

- [`SKILL_SPEC.md`](SKILL_SPEC.md)：技能结构、命名、frontmatter 和验证要求。
- [`DATA_STORAGE_SPEC.md`](DATA_STORAGE_SPEC.md)：配置、凭据、状态、缓存和输出的存储边界。
- [`docs/install-profiles.md`](docs/install-profiles.md)：按使用场景组织的安装方案。

## 生态导航

规范真源与全生态目录均位于 [`soia-team/soia-open-skills`](https://github.com/soia-team/soia-open-skills)。

## License

[MIT](LICENSE)
