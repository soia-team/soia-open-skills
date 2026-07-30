# SOIA 技能生态学习指南

[English](learning-guide.en.md) · 中文

这份文档回答「**这套东西是怎么运转的**」。[安装指南](install/README.md) 回答「怎么装」，两者互补：装之前读这里建立心智模型，装的时候查那里抄命令。

读完你应该能自己判断：一个新需求该做成技能还是脚本、该放哪个仓、装哪个插件、以及技能没触发时该往哪查。

---

## 一、五个名词，先分清

整套生态只有五个概念，混淆它们是绝大多数困惑的来源。

| 名词 | 是什么 | 在磁盘上 | 谁消费 |
|---|---|---|---|
| **技能（skill）** | 一个目录，含 `SKILL.md` 加可选的 `scripts/` `references/` `templates/` | 仓库的 `skills/<名>/` | Agent |
| **域插件（plugin）** | 一个仓库对外的打包单位，等于该仓全部技能 | 仓根的 `.claude-plugin/plugin.json` | 宿主的插件系统 |
| **市场（marketplace）** | 插件的索引清单，一个 URL 换来一批插件 | 元仓的 `.claude-plugin/marketplace.json` | `plugin marketplace add` |
| **触发词（trigger）** | 写在 `SKILL.md` frontmatter `description` 里的自然语言 | frontmatter | Agent 的路由判断 |
| **常驻成本（always-on）** | 技能的 name+description 占用的上下文 | —— | 你的上下文预算 |

**一句话串起来**：技能是原子，域插件是包装，市场是货架，触发词是标签，常驻成本是货架费——最后这一项决定了前面所有设计。

---

## 二、一张图看懂全生态

```text
真源：10 个 Git 仓库，共 100 个技能（开源 74 + 私有 26）
        │
        │   routing/routing-manifest.json（机器可读索引，生成物）
        ▼
元仓 soia-open-skills 的生成器 scripts/generate_marketplaces.py
        │
        ├─→ .claude-plugin/marketplace.json    ← Claude Code / Qwen / agy 消费
        ├─→ .agents/plugins/marketplace.json   ← Codex 原生消费
        └─→ 私有仓自指市场（source: "./"，走本机 gh 凭证）
        │
        ▼
宿主装载：claude plugin install soia-pkm-vault@soia
        │
        ▼
你说「把这个网页存进知识库」→ Agent 按 description 命中 soia-pkm-clip-web
```

三条铁律贯穿全图：

1. **单一真源，多面派生**。三份市场清单永远由生成器从仓库内容派生，CI 跑 `--check` 校验，手改即红。杜绝多份清单各自漂移。
2. **域仓 = 域插件 = 开关单位**。`plugin disable soia-pkm-vault@soia` 一次摘掉 26 个知识库技能的索引，上下文降到零成本；写作日再 `enable` 回来。
3. **正式通道 pin sha**。市场条目锁定 commit，防上游挪 ref 换内容——这是供应链基线，不是洁癖。

---

## 三、为什么是「多仓 + 域插件」，而不是一个大仓

因为**常驻成本按域收敛**。

技能的正文（`SKILL.md` 主体、`references/`、`scripts/`）只在触发后才进上下文，但 name + description 是**常驻**的——只要技能在索引里，每一轮对话都在付这份钱。官方口径：Claude 的技能列表预算约为上下文的 1%，description 超 1536 字符截断；Codex 约 2% 或 8000 字符。

所以真正的设计约束是：**如何让你只为今天用得上的域付费**。

一个大仓做不到——装了就是全量。切成域仓之后，「今天写文章」只需 `soia-media-content` + `soia-pkm-vault`，编码域整体不在索引里。这就是把 12 个仓收敛到 8 个、但坚决不合并成 1 个的原因：**仓的边界就是开关的粒度**。

推论：**新技能该放哪个仓，取决于「它和谁一起被打开」**，不取决于代码相似度。

---

## 四、交付方式的演进（以及已废弃的做法）

这一节比其他章节都重要——生态里的老文档和老命令仍在流传，照着做会踩坑。

| 时期 | 交付方式 | 现状 |
|---|---|---|
| 早期 | `npx skills add ... -g` 装进共享真源 `~/.agents/skills`，各宿主软链过去 | **已废弃为反模式** |
| 现在 | 插件市场，域粒度装载与启停 | 唯一推荐路线 |

**为什么废弃 `-g` 全局安装**：如果同一技能既被 npx 装进 `~/.agents/skills`、又被插件带进来，宿主会看到**两份索引**，且两份各自更新、逐渐漂移。你无法判断触发的是哪一份。

因此规则是**二选一**。本机现状可以印证这个迁移已经完成：`~/.agents/skills` 里现在只剩第三方技能（`find-skills`、`weread-skills` 等），**没有任何 SOIA 技能**——SOIA 已 100% 插件化交付。

`npx` 路线仍然可用，且是**只想要单个技能**时的合理选择，但要清楚它落在哪里：

```bash
npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -s soia-pkm-clip-web -y
```

用了它，就别再装同一个域插件。

---

## 五、按需加载：四层策略

这是整套架构要解决的核心问题，分四层处理，从粗到细：

| 层 | 手段 | 当前状态 |
|---|---|---|
| 1 常驻核心 | description 瘦身，`audit_skills.py --strict` 限制新技能 ≤150 字符 | ✅ 已生效，CI 强制 |
| 2 域级开关 | `plugin enable/disable`（Claude/Qwen/agy）；Codex 市场级；WorkBuddy 按专家召唤 | ✅ 已生效 |
| 3 机器画像 | [install-profiles.md](install-profiles.md) 四场景（写作/编码/教育/最小） | ✅ 已发布 |
| 4 长尾路由 | `find-skills` 搜公开技能 + `routing-manifest.json` 兜底 | ✅ 已启用 |

第 4 层的代价要讲清楚：**路由牺牲触发词直达**。走路由的技能不在索引里，Agent 不会自动命中，得先查清单再装。所以它只适合低频长尾，高频能力必须留在第 1 层。

---

## 六、各宿主怎么装载技能

宿主分两类，决定了你能用哪一层开关。

**有插件层**（能做域级启停）：

| 宿主 | 装载机制 | 开关手段 |
|---|---|---|
| Claude Code | name+description 索引，正文按需加载 | `plugin enable/disable`，上下文零成本 |
| Codex | 发现链五层，含 `$HOME/.agents/skills` | 市场级 enable；技能层无开关 |
| Qwen | 原生消费 Claude 市场格式（自动转换） | extension 级启停 + scope |
| agy | `plugin import claude` 通道 | plugin enable/disable |
| WorkBuddy | 专家插件携带自己的技能组合 | 召唤/切换专家 |

**无插件层**（只能靠目录内容增删）：Kimi（`--skills-dir` 显式子集，最彻底）、OpenCode、DeepCode、Gemini CLI。这些用 `soia-meta-sync-skills` 的 `--skills` 白名单与 `--exclude-skills` 做目录级增删。

WorkBuddy 是个特例，值得单独说：它的开关单位不是插件而是**专家**——一个角色化的 agent 预设，
自带人设与一组技能，召唤时才进场。这是本生态的第三个分发面，与两份市场清单并列，
由域仓的 `.codebuddy-plugin/plugin.json` 派生，仍然是**一仓一专家**。

它与 Claude/Codex 有两点不同，装之前要知道：**没有按 sha pin 拉远端仓那一层**
（市场条目的 `source` 只能是路径字符串），且自建专家**只认硬编码目录 `my-experts`**。
所以装载方式是在该目录下放一份域仓 checkout——与 Claude/Codex 各自在插件缓存里
有一份克隆是对等的。见 [WorkBuddy 安装指南](install/workbuddy.md)。

各宿主的具体命令见 [安装指南的分宿主页](install/README.md#按-ai-工具查看)。

---

## 七、frontmatter：七字段与 Codex 折叠

SOIA 技能的 frontmatter 用七个字段（`name` `description` `version` `created_at` `updated_at` `created_by` `updated_by` 等），但 Codex 官方的 `quick_validate.py` 只认五键白名单（`name` `description` `license` `allowed-tools` `metadata`）。

**结论是分层解决，而不是改真源**：

- 生态真源保持七字段不动（零 churn，88+ 技能不用重写）。
- 发布管线在产出 Codex 包时，把扩展字段自动折进 `metadata:`——`metadata` 是白名单键且内部形状不检查，OpenAI 官方自己就用 `metadata.short-description`。

实测三层行为：**运行时完全容忍七字段**（连中文 `name` 都能加载），**插件打包 ingestion 容忍未知键**，只有 skill-creator 的校验器会打回。所以冲突面比看上去小得多。

---

## 八、供应链安全基线

技能是纯文本，但纯文本一样能投毒——社工 Agent 去执行安装命令即可。业界实证：postmark-mcp 后门、mcp-remote CVE-2025-6514（RCE）、Shai-Hulud npm 蠕虫、ClawHub 2857 个技能中 11.9% 恶意。

八条基线：

1. 市场条目正式通道一律 pin `sha`；开发通道才追分支。
2. MCP 注册禁 `@latest`，pin 精确版本。
3. 技能发布前全文评审（`soia-dev-review-panel`），已批准的 MCP server 做描述版本 diff，防 rug-pull。
4. 最小权限：frontmatter 用 `allowed-tools` 窄集。
5. 第三方市场自动更新保持默认关闭。
6. 不受信 stdio server 沙箱运行；远程 server 仅 HTTPS + OAuth。
7. 明文密钥治理：AI 配置文件（`models.json`、`opencode.json` 等）常明文存 API key，迁 Keychain 或环境变量。
8. 双层脱敏门禁覆盖私有→开源的内容提炼。

完整策略见 [SECURITY.md](../SECURITY.md)。

---

## 九、常见疑问

**Q：插件启用后，是整个插件的技能都进索引，还是按需？**
整个插件的技能都进索引（这是常驻成本的来源）；但**触发仍是技能级**——靠 description 自动命中，或 `/插件名:技能名` 手动调用。`disable` 是域级整体摘除，上下文零成本。

**Q：`routing-manifest.json` 是干嘛的？**
技能→仓→路径的机器可读真源，服务五件事：① `find-skills` 路由查询 ② 全生态重名 CI 检查 ③ 跨仓硬依赖闭包 ④ 市场清单生成器的数据源 ⑤ 安装文档生成。任一仓发布后由 CI 重新生成。

**Q：为什么 `plugin.json` 里列 `skills` 数组不能只暴露技能子集？**
两个宿主都不行，原因不同。**Codex**：官方校验器要求 `skills` 必须是字符串且规范化后等于 `"skills"`，传数组直接判错。**Claude**：官方字段表写明 `skills` 是「**Adds to** the default `skills/` scan」——同表 `commands`/`agents`/`workflows` 都是 "replaces"，唯独 `skills` 是叠加。实测证实数组是 no-op。**只有目录分隔能真正拆分插件内容**，这也是 `soia-private-skills` 一仓三插件（`skills/`、`workspace/skills/`、`harness/skills/`）的做法。

**Q：技能没触发怎么查？**
按序：① 插件装了吗（`claude plugin list`）② 启用了吗 ③ description 里的触发词和你说的话对得上吗 ④ 是不是同名技能有两份（npx 与插件并存）。第 ④ 项是最隐蔽的，检查 `~/.agents/skills` 里有没有同名目录。

**Q：`plugin update` 说「已是最新」，但我明明改了代码？**
Claude Code 比对的是 `plugin.json` 的 `version` 字段，**不是 sha**。改了内容不 bump 版本号，客户端就认为无事发生。发版流程见 [plugin-dev.md](plugin-dev.md)。

**Q：私有仓怎么分发？**
两个私有仓建**自指市场**（`source: "./"`），走本机 `gh` 凭证，只有仓库授权者装得上。公开市场清单不含任何私有条目。

---

## 十、接着读什么

| 你想做的事 | 去哪 |
|---|---|
| 把技能装到某个 AI 工具 | [安装指南](install/README.md) |
| 按场景选装哪些域 | [install-profiles.md](install-profiles.md) |
| 写一个新技能 | [SKILL_SPEC.md](../SKILL_SPEC.md) |
| 改完技能怎么发版 | [plugin-dev.md](plugin-dev.md) · [CONTRIBUTING.md](../CONTRIBUTING.md) |
| 技能怎么存数据、放哪 | [DATA_STORAGE_SPEC.md](../DATA_STORAGE_SPEC.md) |
| 安全边界与脱敏 | [SECURITY.md](../SECURITY.md) |
