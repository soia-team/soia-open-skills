# soia-media-publish-x-article

> 将 Markdown 成文上传到 X Articles 草稿箱并校验格式，只保存草稿

所属：[`soia-media-content`](https://github.com/soia-team/soia-open-media-content-skills) · [技能源码](https://github.com/soia-team/soia-open-media-content-skills/tree/main/skills/soia-media-publish-x-article) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「发成 X Article」「推到 X 文章草稿箱」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 把一篇 Markdown 长文发到 X Articles | 解析标题/封面/正文图 → 浏览器里新建草稿 → 富文本粘贴 → 按原位插图 → 机械校验 | 浏览器实时操作过程、草稿 URL、校验清单和最终回执 |
| 文章没有封面图 | 停下来提醒（X Article 无封面观感差），明确同意后才无封面继续 | 提醒与确认问题 |
| 缺依赖/未登录/无 Premium+ | 停止并明确指出缺什么 | 登录/开通指引，不代填任何凭据 |

**安全底线**：只保存草稿，**绝不点击「发布/Publish」**；登录态只留在浏览器里，不导出 cookie、不写任何凭据到磁盘。

### 客户如何使用

其他可识别说法包括「上传到 X 文章」「X Articles draft」「把这篇发 X 长文」；只有普通短帖或 thread 时转交 `soia-media-publish-x-thread`。

1. 说「把 <文件> 发成 X Article」。首次使用需要登录一次：脚本弹出浏览器窗口，人工登录后长期复用（与 `soia-media-publish-x-thread` 共用同一份登录态，任一技能登录过就都不用再登）；账号需订阅含「撰写文章」权益。
2. Agent 先 dry-run 解析并汇报：标题、封面、正文图数量、缺图清单；封面缺失时先问你。
3. 浏览器阶段全程可见（默认走宿主无关的 Playwright 脚本，任何能跑 Python 的环境都一样）；完成后给草稿 URL 和校验清单，由你人工审阅并发布。

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
npx skills add soia-team/soia-open-media-content-skills -a <agent> -s soia-media-publish-x-article -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
