# soia-media-publish-rednote-card

> 把成文草稿改写成小红书（rednote）笔记：标题、3–5 段短文、标签与配图建议；获当次授权可驱动已登录浏览器在网页端完成发布，不用逆向包

所属：[`soia-cwork-office`](https://github.com/soia-team/soia-open-cwork-office-skills) · [技能源码](https://github.com/soia-team/soia-open-cwork-office-skills/tree/main/skills/soia-media-publish-rednote-card) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「发成小红书」「小红书笔记」「改成 rednote」「帮我发到小红书」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 把文章改成小红书笔记文案 | 提炼单一分享角度，生成承诺明确的标题、3–5 段短文、相关话题标签与配图建议 | 一份可直接复制的 rednote Markdown 文案（不覆盖原稿） |
| 处理 >1000 字长文 | 推荐走官方「写长文」富文本/一键排版通道，或仅在跨平台复用时拆成 4–8 张自产文字卡 | 合规的长文排版路线、≤20 字标题与导读描述 |
| **代为网页端发布**（需当次授权） | 在客户已登录浏览器传图、填文、逐个点选蓝色标签、按需挂 Red Skill 组件，发布前停下确认 | 最终确认截图与笔记管理页/正式链接核实回执 |

### 客户如何使用

- 「把这篇文章发成小红书，目标读者是独立开发者，不要夸大效果。」
- 「原稿超过 1500 字，按写长文形态整理标题、描述框导语和配图建议。」
- 「我已经登录小红书创作服务平台，把图和这套文案代我传上去，最后点发布前给我确认。」

## 安装

客户明确选择安装整个 `soia-cwork-office` 领域插件时：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-cwork-office@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-cwork-office@soia
```

客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。

安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。默认是当前项目、明确 Agent、单个技能：

```bash
npx skills add soia-team/soia-open-cwork-office-skills -a <agent> -s soia-media-publish-rednote-card -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
