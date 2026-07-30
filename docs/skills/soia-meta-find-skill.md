# soia-meta-find-skill

> 按需检索 SOIA 全生态技能并加载——剪藏网盘/知识提炼/新媒发布/编码审查与终端操作/设计图表/产品PRD/软件测试/软件发版/办公协作/教育课程/环境安装/生态管理。说出需求即可检索、定位并按需读入对应技能

所属：[`soia-meta`](https://github.com/soia-team/soia-open-skills) · [技能源码](https://github.com/soia-team/soia-open-skills/tree/main/skills/soia-meta-find-skill) · [← 全部技能](README.md)

## 能力与用法

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

## 安装

本技能随 `soia-meta` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-meta@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-meta@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-find-skill -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
