# soia-media-publish-x-thread

> 将成文草稿改写为带编号、符合字数限制的 X thread，并可按授权存草稿

所属：[`soia-media-content`](https://github.com/soia-team/soia-open-media-content-skills) · [技能源码](https://github.com/soia-team/soia-open-media-content-skills/tree/main/skills/soia-media-publish-x-thread) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「发成 X thread」「拆成推文串」「thread 这篇」

## 能力与用法

### 这个技能可以做什么

读取客户提供的成文草稿，保留核心观点和必要证据，重组为有连续阅读节奏的 X thread：首条负责让人继续读，中间条目各自完成一个逻辑动作，末条给出自然的 CTA。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 把文章发成 X thread | 提取主线、拆分论证、编号并控制每条长度 | 一组可复制的 Markdown 推文条目 |
| 草稿含代码、命令或链接 | 保持代码与 URL 原样，必要时调整周边文字 | 未被截断的代码/链接，以及无法安全拆分处的明确提示 |
| 需要发布到 X | 只生成发布文本 | “产出文本、人工发布”；不会调用 X API 或发送任何内容 |

### 客户如何使用

其他可识别说法包括「发条 X」「发个推」；若目标是 X Articles 长文草稿，转交 `soia-media-publish-x-article`。

1. 说明“发成 X thread”“拆成推文串”或“thread 这篇”，并提供成文草稿、文件内容或路径。
2. 如有要求，一并说明目标读者、口吻、是否保留标题、CTA 方向和需要保留的代码/链接。
3. Agent 先确认输入范围与主线，再输出 thread；默认不覆盖原稿，客户指定路径时才另存。
4. 客户人工复制每条并发布到 X；发布顺序按编号执行。

## 安装

本技能随 `soia-media-content` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-media-content@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-media-content@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-media-content-skills -g -a '*' -s soia-media-publish-x-thread -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
