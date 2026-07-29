# WorkBuddy 专家定义

WorkBuddy 的「专家」是**角色化的 agent 预设**：一份人设 MD + 一组技能 + 展示元数据。
它是 WorkBuddy 自己的插件格式，与 Claude 市场清单、Codex 市场清单并列，是本生态的第三个分发面。

召唤一个专家，等于同时拿到「这个角色怎么干活」和「它手上有哪些技能」——
这也是 WorkBuddy 侧的域级按需加载：不召唤就不在场。

## 现有专家

| 专家 | 花名 | 技能来源 | 技能数 |
|---|---|---|---|
| 知识库管家 | 阿藏 / Archie | `soia-open-pkm-vault-skills` | 26 |
| 新媒体运营 | 阿墨 / Inky | `soia-open-media-content-skills` | 6 |
| 办公资料助手 | 阿档 / Filo | `soia-open-cwork-office-skills` | 3 |

## 目录里放什么

每个专家一个目录，只放**定义**，不放技能副本：

```text
<专家名>/
  expert.json   展示元数据：花名、职业、分类、标签、推荐提示词、技能来源仓
  agent.md      人设：核心能力、工作流程、输出规范、注意事项
  avatar.png    头像，1024×1024，≤500KB
  avatar.svg    头像母版，由 scripts/generate_icons.py 确定性生成
```

技能不提交进本目录。原因是两边都有约束：WorkBuddy 校验器要求 `plugin.json` 里
`skills` 声明的每个路径下都有 `SKILL.md`，即技能必须实体存在于专家包内；
但把 26 个知识库技能的副本提交进本仓会造成双份真源，改一处要改两处。
取舍是**仓里只存定义，副本在本机生成**。

## 生成到 WorkBuddy

```bash
python3 scripts/generate_workbuddy_experts.py --dry-run
```

```bash
python3 scripts/generate_workbuddy_experts.py
```

生成器会从各域仓拷贝技能、组装 `plugin.json`，再调用 WorkBuddy 官方
`expert-manager` 的 `validate_expert.py` 与 `register_expert.py` 完成校验与注册——
不自己写 `marketplace.json`，官方规范明确禁止绕过注册脚本。

默认从本仓上级目录找各域仓，域仓在别处时用 `--skills-root` 指定。
生成后重启 WorkBuddy，在【专家中心 - 我的专家】可见。

## 新增一个专家

1. 建 `experts/<kebab-case-名>/`，照现有专家写 `expert.json` 与 `agent.md`。
2. 在 `scripts/generate_icons.py` 的 `EXPERTS` 表里加一条，指明借用哪个域插件的配色
   （需要换字形时给出覆盖），跑 `python3 scripts/generate_icons.py` 生成头像。
   头像与该域的插件图标同源于一张表，不要另建配色。
3. 跑 `python3 -m unittest tests.test_workbuddy_experts` —— 官方的硬约束在这里复刻了一份，
   写坏的定义会在提交前被拦下，而不是等到用户机器上生成失败。
4. 跑生成器验证官方校验器也放行。

写 `expert.json` 时注意几条官方硬性规则：`tags` 与 `quickPrompts` 各**正好 3 条**，
`displayDescription.zh` **40–50 字**，`agentName` 必须等于目录名，
`defaultInitPrompt` 由生成器取 `quickPrompts` 第一条，不用手写。
