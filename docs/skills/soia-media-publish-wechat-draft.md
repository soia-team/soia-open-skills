# soia-media-publish-wechat-draft

> 把成文草稿排版成符合微信公众号限制的内联样式 HTML，机械校验通过后推入微信公众号草稿箱；只建草稿，绝不自动群发

所属：[`soia-cwork-office`](https://github.com/soia-team/soia-open-cwork-office-skills) · [技能源码](https://github.com/soia-team/soia-open-cwork-office-skills/tree/main/skills/soia-media-publish-wechat-draft) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「把这篇发成公众号」「排版这篇公众号」「推到公众号草稿箱」「公众号 draft」

## 能力与用法

### 这个技能可以做什么

对成稿**默认不改正文、不重写标题**，接管配图衔接、内联 HTML 排版、三级草稿投递与发布后归档：

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 本地排版并预览 / 一键复制（零配置最稳） | 运行 `render_wechat.py` 或 `publish.py --dry-run`，通过红线校验生成 `<stem>.html` 与 `<stem>.copy.html` | 带「复制公众号富文本」按钮、标题/作者/摘要栏、`2.35:1` 首图与中央 `1:1` 分享安全框、`5:2` X 封面、`390px` 手机视口预览与 7 项检查清单的 `.copy.html` |
| 推入公众号草稿箱（新建或原地更新） | 按 `--account` 解析凭据、传本地正文图换 CDN URL、传封面取 `thumb_media_id`；新建调 `draft/add`，已有 `wechat_draft_media_id` 调 `draft/update` | 草稿 `media_id`、上传图片数、排版 HTML 路径与后台预览提醒 |
| 浏览器辅助存草稿（无 API 权限时） | 在客户已扫码登录的公众号后台填入标题、作者、摘要、封面与内联 HTML 并保存草稿 | 草稿箱保存状态（停在草稿箱，绝不点发表/群发） |
| 正式发表后归档留底 | 运行 `archive.py --move` 更新 `status: 已发布`、`published_at`、`url`，连同源 `.md` 与 `assets/<篇名>/` 迁入发布归档区并清理临时 `.html`/`.copy.html` | 归档后的正式 Markdown 与配图路径 |

### 客户如何使用

- 「不要改这篇的正文和标题，先用 `minimal` 纯墨主题排版并生成 `copy.html` 给我预览。」
- 「把这篇推到 `<alias>` 公众号草稿箱，封面用 `01-wechat-cover.png`，开启 `--save-draft-id` 方便后续原地更新。」
- 「改了封面和两处错字，原地更新刚才那条公众号草稿，不要新建第二条。」
- 「这篇公众号已发表（附链接 `https://mp.weixin.qq.com/s/...`），帮我连同配图归档到发布目录。」

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
npx skills add soia-team/soia-open-cwork-office-skills -a <agent> -s soia-media-publish-wechat-draft -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
