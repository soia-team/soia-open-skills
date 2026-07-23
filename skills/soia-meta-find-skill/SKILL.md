---
name: soia-meta-find-skill
description: 按需检索 SOIA 全生态技能并加载——剪藏网盘/知识提炼/新媒发布/编码审查与终端操作/设计图表/产品PRD/软件测试/软件发版/办公协作/教育课程/环境安装/生态管理。说出需求即可检索、定位并按需读入对应技能
version: 1.0.1
created_at: 2026-07-23 10:23:03
updated_at: 2026-07-23 13:49:14
created_by: gpt-5.6-luna
updated_by: gpt-5.6-luna
---

# soia-meta-find-skill

按自然语言关键词在已安装技能与全生态目录之间做两级检索，定位最匹配的技能，并指引宿主只在需要时把该技能的 `SKILL.md` 读入上下文。

## 客户可读说明

### 这个技能可以做什么

- 优先查找本机已经安装、可以立即加载的 SOIA 技能。
- 本机没有匹配项时，从随技能发布的全生态目录定位未安装技能并给出精确安装命令。
- 候选超过一个时列出相关性最高的 3 个，由当前模型结合客户原始需求选择。

### 客户如何使用

客户只需说明目标，例如“剪藏一篇网页”“起草 PRD”或“检查发版清单”。Agent 提取一个高区分度关键词和可选领域后运行：

```bash
python3 scripts/find_skill.py --query <关键词> [--domain <领域>]
```

如果从仓库源码调用，使用：

```bash
python3 skills/soia-meta-find-skill/scripts/find_skill.py --query <关键词> [--domain <领域>]
```

### 依赖与安装

运行时只依赖 Python 3 标准库。安装本路由技能：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-find-skill -y
```

目录中未安装的候选会自带对应仓库的 `npx skills add` 命令。安装会改变本机状态；先把命令展示给客户并取得授权，安装后重新检索。

### 私密信息与中间数据

- 本机扫描范围仅为 `~/.agents/skills/*/SKILL.md`；不读取技能私有配置、凭据或客户文件。
- 查询与结果只输出到终端，不写缓存或日志。结果中的本机路径仅用于宿主读取，不复制到公开交付物。
- 全生态目录是仓库内的公开生成产物，不包含账号、token、私有技能或本机路径。

### 日志与完成回执

回执必须说明查询词、是否命中本机、展示的候选数、最终选择及依据。未命中时明确返回空列表，不猜造技能名。

```markdown
完成：已为“<需求>”定位 <技能名>。
日志摘要：本机/全生态目录命中 <数量> 个候选；选择依据为 <关键词或领域>。
下一步：已读取 <SKILL.md 路径> / 等待授权执行 <安装命令> / 未找到匹配项。
```

## 检索与加载契约

1. 从客户需求中提取 1–3 个高区分度词；领域已明确时追加 `--domain`，不要把整段自然语言原样作为一个关键词。
2. 运行 `scripts/find_skill.py`。脚本先扫描 `~/.agents/skills/*/SKILL.md` 的 frontmatter `name` 与 `description`。
3. 若本机有匹配项，只返回已安装候选；若没有，查询 `references/skill-directory.json`，返回未安装候选及精确 `install_cmd`。
4. 最多向模型展示排名前 3 的候选。结合原始需求、技能边界和 description 自主选择一个；不能区分时再向客户问一个短问题。
5. 已安装候选包含 `path`。调用宿主的文件读取能力完整读取该路径的 `SKILL.md`；只有实际读入内容才算加载，不能只引用路径或凭记忆执行。
6. 未安装候选包含 `install_cmd`。展示命令并等待客户授权；安装成功后重新运行检索，再读取返回的 `path`。
7. 读取选中技能后，以该技能的依赖、安全边界、工作流和验证契约继续处理原始需求。本路由技能不替代目标技能。

## 输出契约

脚本向 stdout 输出 JSON 数组，最多 3 项：

```json
[
  {
    "name": "soia-example-skill",
    "description": "示例描述",
    "installed": true,
    "path": "<home>/.agents/skills/soia-example-skill/SKILL.md"
  }
]
```

未安装项以 `install_cmd` 替代 `path`。不要把目录内的 `repo` 等维护字段扩散为运行时契约。

## 目录维护边界

`references/skill-directory.json` 由元仓根目录的 `scripts/generate_router_index.py` 从只读 `routing/routing-manifest.json` 生成。普通客户运行路由时不刷新目录；维护者仅在公开技能描述或路由清单变化时生成并提交产物。

## 验证

```bash
python3 skills/soia-meta-find-skill/scripts/find_skill.py --query 剪藏
python3 scripts/generate_router_index.py --check
```

真实输出验收：第一条命令必须返回合法 JSON；每项必须恰含公共字段、`installed` 布尔值，以及 `path` 或 `install_cmd` 之一。第二条命令必须确认提交的全生态目录与远端公开 `SKILL.md` 描述一致。
