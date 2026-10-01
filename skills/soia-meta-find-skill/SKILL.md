---
name: soia-meta-find-skill
description: 按需求查找合适的 SOIA 技能，未安装时只收集安装选择，不代替技能执行任务。触发：找个技能、有没有技能可以、发现 SOIA 能力
version: 1.2.3
created_at: 2026-07-23 10:23:03
updated_at: 2026-09-30 13:14:57
created_by: gpt-5.6-luna
updated_by: claude opus 5.5
---

# soia-meta-find-skill

按自然语言需求找最匹配的 SOIA 技能，优先当前项目已安装的；未安装时只收集安装选择，不安装、不同步、不发布。

## 客户可读说明

### 这个技能可以做什么

- 在项目 `.agents/skills`、用户全局真源或公开生态目录中发现候选技能，识别代码审查、架构评审、调用链、数据流等中文意图。
- 返回“项目/全局、目标 Agent、单技能/整域/全量”的选择意图，交给安装或同步技能执行。

### 客户如何使用

```bash
python3 scripts/find_skill.py --query <关键词> [--domain <领域>] [--project <项目路径>] [--scope auto|project|global|both] [--agent <Agent>]
```

从仓库源码调用时脚本路径为 `skills/soia-meta-find-skill/scripts/find_skill.py`。`--domain` 按领域或 `query-hints.json` 的 `domain_hints` 缩小候选。`--agent` 可重复，只记录客户选的目标 Agent，不猜宿主目录。`--scope auto` 只扫描能确定的当前项目，确定不了就让 Agent 向客户确认范围，不暗自扫全局；`project`、`global`、`both` 是显式范围。

### 依赖与安装

运行时只依赖 Python 3 标准库。本技能随 `soia-meta` 域插件提供：`claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-meta@soia`，Codex 用 `codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-meta@soia`；WorkBuddy 以角色化专家装载，见 [docs/install/workbuddy.md](https://github.com/soia-team/soia-open-skills/blob/main/docs/install/workbuddy.md)。

**安装交接边界：** 只查找时给候选即可，安装选择不是检索完成条件。客户要继续安装时才确认项目/全局、哪些 Agent、单技能/整域/全量；默认单技能，绝不默认全量，也不生成 `-g -a '*'` 命令。`npx skills add` 单技能命令由安装 owner 在客户确认后生成，本技能不构造或执行。选择字段齐全不等于写入批准；只有已展示影响并获明确批准、且含 source、具体 target、action 与删除/替换影响的完整计划，下游才可复用而不重复询问，计划字段变化时重新确认受影响部分。发布流程不顺带安装，除非客户另行选择。`--legacy-install-cmd` 只为旧消费者输出标为 deprecated 的全局全 Agent 命令，新流程不用。

### 私密信息与中间数据

- 只读候选 `SKILL.md` 的 frontmatter 与随技能发布的公开目录、同义词参考；不读私有配置、凭据或客户文件。
- 结果只输出 stdout，不写缓存、日志或运行时状态；路径只用于当前宿主读取 `SKILL.md`，回执不复制私有路径。

### 日志与完成回执

说明查询词、扫描范围、项目/全局命中、候选数、选择依据，以及是否仍需客户选择安装范围。没有候选时返回空列表，不猜造技能名。

```markdown
完成：已为“<需求>”定位 <技能名>。
日志摘要：项目/全局/生态目录命中 <数量> 个；选择依据为 <关键词或领域>。
下一步：已读取 <SKILL.md 路径> / 等待客户确认 <project|global>、<agents>、<skill|domain|all>。
```

## 检索与加载契约

1. 从需求提取 1–3 个高区分度词，可直接用中文短语；词组与同义词由 [references/query-hints.json](references/query-hints.json) 维护。
2. `auto` 下能从 `--project` 或当前目录确定项目时扫描 `<project>/.agents/skills`，否则只检索公开目录并标 `selection_required`。
3. `global` / `both` 仅在显式请求时扫描用户全局真源；项目与全局命中同一技能时按 realpath + skill name 去重，项目优先。
4. 本地与公开目录候选一起排序，本地命中不短路隐藏其他高相关候选。
5. 只对已安装候选返回优先 `path`，以 `installed_scopes`、`source_scope` 表示来源；实际读取该 `SKILL.md` 后才算加载。
6. 未安装候选返回 `source` 与 `install_selection`，只查找时保留未选字段即可；客户要继续安装且 `scope` 或 `agents` 未选时再问，然后按上面的安装交接边界交给下游 owner。
7. `install_selection.target.kind` 默认 `skill`，同时声明可选的 `domain` 和 `all`。

## 输出契约

stdout 为最多 3 项的 JSON 数组，默认不含可执行安装命令：

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

## 维护本技能时

`references/skill-directory.json` 由元仓根目录 `scripts/generate_router_index.py` 从只读 `routing/routing-manifest.json` 生成，只存公开来源标识、不存安装命令；普通查询不刷新它。改检索实现或目录后在元仓根跑：

```bash
python3 -m unittest tests.test_find_skill_router tests.test_generate_router_index
python3 scripts/generate_router_index.py --check
python3 scripts/generate_skill_pages.py --check
```

真实输出验收：夹具覆盖项目优先、项目/全局合并与 realpath 去重、未选范围时的 `selection_required`、多 Agent 意图、中文审查短语与显式 legacy 命令，逐项断言 JSON 字段和值。
