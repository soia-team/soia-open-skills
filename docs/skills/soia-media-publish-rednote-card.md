# soia-media-publish-rednote-card

> 把成文草稿改写成 rednote（小红书）笔记：生成吸睛标题（可带 emoji）、3–5 段短文、话题标签和配图建议；获客户当次授权时可代其在创作服务平台网页端完成发布。不接平台 API、不用第三方逆向包

所属：[`soia-media-content`](https://github.com/soia-team/soia-open-media-content-skills) · [技能源码](https://github.com/soia-team/soia-open-media-content-skills/tree/main/skills/soia-media-publish-rednote-card) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「发成小红书」「小红书笔记」「改成 rednote」「rednote 这篇」「帮我发到小红书」

## 能力与用法

### 这个技能可以做什么

从文章中提炼一个明确的分享角度，组织成适合移动端快速阅读的笔记：一个有信息承诺的标题、3–5 段短文、相关话题标签，以及与内容匹配的配图建议。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 把文章发成小红书笔记 | 提炼角度、重写标题和短段落、补充标签 | 一份可复制的 rednote Markdown 文案 |
| 需要视觉素材方向 | 给出封面/配图的主体、构图、文字和比例建议 | 可执行的配图建议；需要时可衔接 `soia-media-generate-article-image` |
| 自己发布 | 只生成文本与配图建议 | 可直接复制的文案，发布动作由客户完成 |
| **代为发布**（需当次授权） | 在客户已登录的浏览器里传图、填文、加话题、挂 Red Skill 组件，停在发布前请客户确认 | 每步截图与最终状态；客户说「发布」后才点，发布后回执带笔记管理页核实结果 |

### 客户如何使用

1. 说明“发成小红书”“小红书笔记”或“rednote 这篇”，并提供成文草稿、文件内容或路径。
2. 如有要求，一并说明目标读者、账号口吻、标题禁用词、是否突出方法/清单/故事，以及想要的配图风格。
3. Agent 先确定单一分享角度，再输出标题、正文、标签和配图建议；默认不覆盖原稿，客户指定路径时才另存。
4. 客户人工复制文案、准备图片并发布到 rednote；本 skill 不代替平台后台操作。

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
npx skills add soia-team/soia-open-media-content-skills -a <agent> -s soia-media-publish-rednote-card -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
