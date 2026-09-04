---
name: soia-meta-find-skill
description: 按需发现 SOIA 技能并收集安全安装选择。触发：技能检索、代码审查、环境安装
version: 1.1.0
created_at: 2026-07-23 10:23:03
updated_at: 2026-09-04 16:54:39
created_by: gpt-5.6-luna
updated_by: gpt-5.6-terra
---

# soia-meta-find-skill

按自然语言需求发现最匹配的 SOIA 技能，优先识别当前项目已安装的技能；未安装时只收集安装选择，不安装、不同步、不发布。

## 客户可读说明

### 这个技能可以做什么

- 在项目 `.agents/skills`、用户全局真源或公开生态目录中发现候选技能。
- 识别代码审查、架构评审、调用链、数据流、模块边界等中文意图。
- 返回“项目/全局、目标 Agent、单技能/整域/全量”选择意图，交给安装或同步技能执行。

### 客户如何使用

先从当前项目查找；若当前目录不能确定项目，脚本不会暗自扫描全局目录，而会让 Agent 向客户确认范围。

```bash
python3 scripts/find_skill.py --query <关键词> [--project <项目路径>] [--scope auto|project|global|both] [--agent <Agent>]
```

从仓库源码调用：

```bash
python3 skills/soia-meta-find-skill/scripts/find_skill.py --query <关键词> --project <项目路径> --agent claude --agent codex
```

`--agent` 可重复，仅保留客户的目标 Agent 选择，不猜测任何宿主目录。`--scope auto` 仅扫描可确定的当前项目；`project`、`global`、`both` 是显式范围。`--skills-dir` 与 `--directory` 保留给旧离线调用和测试。

### 依赖与安装

运行时只依赖 Python 3 标准库。本路由技能可随 `soia-meta` 领域插件提供给 Claude Code 或 Codex：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-meta@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-meta@soia
```

WorkBuddy 以角色化专家装载，见 [docs/install/workbuddy.md](https://github.com/soia-team/soia-open-skills/blob/main/docs/install/workbuddy.md)。

本技能不会默认生成 `-g -a '*'` 命令。未安装候选必须先让客户确认：安装到项目还是全局、哪些 Agent、单技能/整域/全量；默认是单技能，绝不默认全量。确认后把结构化选择交给安装或同步技能；发布流程也不得顺带安装，除非客户另行选择。

`npx skills add` 仍是单技能安装路线，但它的具体参数只能由安装 owner 在客户确认选择后生成；本 finder 不构造或执行该命令。

仅为旧消费者提供 `--legacy-install-cmd`：它会额外输出标为 deprecated 的旧全局全 Agent 命令，不能用于新流程。

### 私密信息与中间数据

- 只读取候选 `SKILL.md` 的 frontmatter 与随技能发布的公开目录、同义词参考；不读私有配置、凭据或客户文件。
- 查询结果只输出 stdout，不写缓存、日志或运行时状态。
- 路径仅用于当前宿主读取 `SKILL.md`；回执不复制私有路径。

### 日志与完成回执

回执说明查询词、扫描范围、项目/全局命中、候选数、选择依据，以及是否仍需客户选择安装范围。没有候选时明确返回空列表，不猜造技能名。

```markdown
完成：已为“<需求>”定位 <技能名>。
日志摘要：项目/全局/生态目录命中 <数量> 个；选择依据为 <关键词或领域>。
下一步：已读取 <SKILL.md 路径> / 等待客户确认 <project|global>、<agents>、<skill|domain|all>。
```

## 检索与加载契约

1. 从客户需求提取 1–3 个高区分度词；可直接使用中文短语。词组与同义词由 [references/query-hints.json](references/query-hints.json) 维护。
2. `auto` 范围下，若 `--project` 或当前工作目录可确定项目，扫描 `<project>/.agents/skills`；否则只检索公开目录，并标记 `selection_required`。
3. `global` 或 `both` 只在显式请求时扫描用户全局真源。项目与全局同时命中同一技能时按 realpath + skill name 去重，项目优先。
4. 本地与公开目录候选一起排序；本地匹配不再短路隐藏其他高相关候选。
5. 只对已安装候选返回优先 `path`；以 `installed_scopes`、`source_scope` 表示来源。实际读取该 `SKILL.md` 后才算加载。
6. 未安装候选返回 `source` 和 `install_selection`。如果 `scope` 或 `agents` 未选，Agent 必须问客户；不能执行安装、同步或发布。
7. `install_selection.target.kind` 默认 `skill`，同时声明客户可选的 `domain` 和 `all`。全量仅在客户明确选择后交给对应 owner 处理。

## 输出契约

stdout 为最多 3 项的 JSON 数组。默认不包含可执行安装命令：

```json
[
  {
    "name": "soia-example-skill",
    "description": "示例描述",
    "installed": false,
    "installed_scopes": [],
    "source_scope": "directory",
    "requested_agents": ["claude", "codex"],
    "source": {"repository": "soia-open-example-skills"},
    "install_selection": {
      "scope": "project",
      "agents": ["claude", "codex"],
      "target": {"kind": "skill", "name": "soia-example-skill"},
      "available_target_kinds": ["skill", "domain", "all"],
      "selection_required": false,
      "pending": []
    }
  }
]
```

## 目录维护边界

`references/skill-directory.json` 由元仓根目录的 `scripts/generate_router_index.py` 从只读 `routing/routing-manifest.json` 生成。它只保存技能的公开来源标识，不保存默认安装命令。普通客户运行路由时不刷新目录。

## 验证

```bash
python3 -m unittest tests.test_find_skill_router tests.test_generate_router_index
python3 scripts/generate_router_index.py --check
python3 scripts/generate_skill_pages.py --check
```

真实输出验收：测试夹具分别覆盖项目优先、项目/全局合并与 realpath 去重、未选范围时的 `selection_required`、多 Agent 意图、中文审查短语，以及显式 legacy 命令；每项断言 JSON 字段和值，不只检查退出码。
