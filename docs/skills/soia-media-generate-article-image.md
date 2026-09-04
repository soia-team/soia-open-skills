# soia-media-generate-article-image

> 将文章、开源项目、品牌 Logo 或公开 X Prompt Deck 编译为可验收的图片与矢量资产，按组合轴生成 Prompt 并完成事实、文字和视觉验收

所属：[`soia-media-content`](https://github.com/soia-team/soia-open-media-content-skills) · [技能源码](https://github.com/soia-team/soia-open-media-content-skills/tree/main/skills/soia-media-generate-article-image) · [← 全部技能](README.md)

## 能力与用法

### 这个技能可以做什么

支持六类交付：文章封面/小结卡、康奈尔笔记、视觉隐喻海报、技能库宣传单图/轮播、插件图标、品牌 Logo 系统。客户只需提供来源、用途、平台、比例和必须逐字出现的文字；有参考图时说明它是风格参考、构图参考还是编辑目标。

### 客户如何使用

**方向是「客户先给需求，技能负责匹配」，不是让客户先学选型体系。**

1. 客户用自己的话给出需求（来源文章/主题、投放平台、张数、必须逐字出现的文字即可）；`image_type`、`preset`、组合轴由 Agent 从需求里推导并给出可确认的假设，不要求客户报字段名。
2. 需求已足够路由（能定用途、平台、输出形态）就直接匹配进入编译，**不把 L0 目录当仪式走**；只有请求含糊到无法路由时才展示 L0 目录反问，且不得静默套用早安、字体蒙版或某个美学 preset。
3. 选定后只加载命中的 references，编译完整 Prompt，调用 imagegen，执行 `view_image` 和对应质量门。

### 需求不明确时：先反问，不生成

当客户只说“做张好看的图”“帮我配个海报”或没有给出用途/输出形态时，先运行 L0 目录命令，再用下面的最小问题澄清；不要猜 preset，也不要先生成样图：

```text
我先确认一下需求。我们目前支持：
1. 文章封面 / 研究小结卡
2. 康奈尔笔记信息图
3. 视觉隐喻海报
4. 技能库宣传单图 / 小红书轮播
5. 插件或应用图标
6. 品牌 Logo 系统（图形标、字标、组合和变体）
7. 公开 X Prompt Deck → image 技能进化导入

请回复：
- 用途：封面、小结、笔记、海报、宣传卡、轮播、插件图标还是品牌 Logo？
- 来源：文章/仓库/X Prompt Deck，还是只给一个主题？
- 风格：从支持目录选一个 family，或描述你想要的视觉感觉？
- 版式：比例、平台、张数；有没有必须逐字出现的标题、数字、URL、字标或 Logo？
```

客户只回答部分问题时，只追问缺失且会改变路由的字段；比例、文字策略等次级轴由 Agent 给出一个可确认的默认值。客户明确说“直接生成”且用途、来源和输出形态已经足够确定时，才可跳过这段反问。

## 安装

客户明确选择安装整个 `soia-media-content` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-media-content@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-media-content@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-media-content-skills -a <agent> -s soia-media-generate-article-image -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
