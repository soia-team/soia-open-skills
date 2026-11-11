# soia-media-publish-x

> 成文发 X：拆成编号 thread 并按授权存草稿，或把 Markdown 传到 X Articles 草稿箱并校验

所属：[`soia-cwork-office`](https://github.com/soia-team/soia-open-cwork-office-skills) · [技能源码](https://github.com/soia-team/soia-open-cwork-office-skills/tree/main/skills/soia-media-publish-x) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「发成 X thread」「拆成推文串」「thread 这篇」「发成 X Article」「推到 X 文章草稿箱」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 走哪个子任务 | 技能会做 | 客户能看到 |
|---|---|---|---|
| 把文章发成 X thread、拆成推文串、发条 X / 发个推 | [references/thread.md](references/thread.md) | 提取主线、拆分论证、编号并控制每条 ≤280 字符；代码与链接保持原样 | 一组可复制的 Markdown 推文条目与长度检查 |
| 把 thread 填进 X、存到 X 草稿、直接发 | [references/thread.md](references/thread.md) 的「浏览器直填模式」 | 用 `scripts/x_post.py` 填入并存草稿；满足发布档条件才发布 | 单行 JSON 回执：草稿位置或推文 URL |
| 把 Markdown 长文发成 X Article、推到 X 文章草稿箱 | [references/article.md](references/article.md) | 解析标题/封面/正文图 → 新建草稿 → 富文本粘贴 → 按原位插图 → 机械校验 | 草稿 URL、校验清单和回执 |
| 先看看这篇能不能发 X Article | [references/article.md](references/article.md) 第 1 步 | 只跑解析 dry-run，不动浏览器 | 标题、封面、图片数量与缺图清单 |

按请求只读对应的一份参考：做 thread 不必读 article，反之亦然。分不清是短帖/thread 还是 Articles 长文时先问一句。

### 客户如何使用

- thread：说“发成 X thread”“拆成推文串”或“thread 这篇”，并提供成文草稿、文件内容或路径；可一并说明目标读者、口吻、CTA 方向和需要保留的代码/链接。默认只在回复里交付文本，由客户人工复制发布。
- X Articles：说“把 <文件> 发成 X Article”“上传到 X 文章”“推到 X 草稿箱”。Agent 先 dry-run 解析并汇报，封面缺失时先问；浏览器阶段全程可见，完成后给草稿 URL，由客户人工审阅并发布。账号需订阅含「撰写文章」权益。
- `soia-media-compose-article-draft` 是常见上游产物，但不是安装级强依赖；也可以直接提供任意成文草稿。

### 授权档位与安全底线

| 场景 | 默认 | 何时可以更进一步 |
|---|---|---|
| thread 文本 | 只产出回复文本，不动浏览器 | 客户说「填进 X」「存到 X 草稿」才启用浏览器直填，默认存草稿 |
| thread 发布 | 不发布 | 客户**在本次会话中逐字给出内容或确认最终文案，并明确说「发」**，才可 `send --yes`；AI 改写产物必须先展示最终文案并得到确认，逐字使用确认过的文案 |
| X Articles | 只保存草稿 | 没有更进一步：**任何情况下不点「发布/Publish」**，`x_article_post.py` 里没有发布代码路径 |

不代输凭据、不代为订阅 Premium；登录态只留在本地浏览器 profile，不导出 cookie、不进仓库和日志。不把“已生成”“已存草稿”说成“已发布”。

### 登录态与旧 profile

thread 与 Articles 共用一份本地浏览器 profile，登录一次两边都能用：

```bash
python3 <skill-path>/scripts/x_post.py login     # 弹窗人工登录，登录态存本地 profile
python3 <skill-path>/scripts/x_post.py status    # 检查登录态
```

profile 目录优先级：`--profile-dir` → `SOIA_X_PROFILE_DIR` → `~/.config/soia-skills/soia-media-publish-x/x-profile`。新位置不存在时，脚本按顺序原地复用旧技能名下已有的 profile：`~/.config/soia-skills/soia-media-publish-x-thread/x-profile`，再到更早的 `~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-publish-x-thread/x-profile`。旧目录不搬移、不删除，已登录的不用重新登录；浏览器会照常在被复用的目录里更新登录态。本技能没有私有 `config.yml`。

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
npx skills add soia-team/soia-open-cwork-office-skills -a <agent> -s soia-media-publish-x -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
