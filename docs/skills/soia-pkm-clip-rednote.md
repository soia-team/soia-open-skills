# soia-pkm-clip-rednote

> 将单篇小红书图文或视频笔记归档到 Obsidian vault

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-clip-rednote) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「归档这条小红书」「clip 小红书笔记」「存这篇 rednote」

## 能力与用法

### 这个技能可以做什么

归档小红书单篇笔记（图文或视频）到 Obsidian vault：抓取标题、正文、作者、发布时间、互动数据、话题标签，并把视频/图片下载到本地；vault 内生成一份轻量 Markdown 笔记。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 归档一篇小红书笔记 | 解析分享链接 → 抓取笔记详情页 → 提取元数据和正文 → 写入 vault | 一份带 frontmatter 的 Markdown 笔记 + 终端回执 |
| 保留笔记里的视频/图片 | 下载到本地 `~/Downloads/soia-pkm-clip-rednote/<note_id>/` | 本地文件路径（记在笔记 `media_local_path` 字段里，vault 本身不存二进制） |
| 先看看链接能不能解析 | 加 `--metadata-only`，只写元数据+正文，不下载媒体 | 笔记文件仍会生成，媒体候选直链列在文件里，供之后手动/重跑下载 |
| 已经归档过的笔记 | 按 `url:` 中的 note_id 去重，默认跳过 | `SKIP: <路径>` 提示，不覆盖 |

### 客户如何使用

1. 从小红书 App 打开目标笔记 →「分享」→「复制链接」，得到完整分享链接（**必须包含 `xsec_token` 参数**，手打或截断的链接无法正常渲染笔记内容）。
2. 把链接发给 Agent，说「归档这条小红书」或直接调用 `python3 scripts/archive_rednote.py <URL>`。
3. Agent 在 vault 根目录（或指定 `--vault`）运行脚本；脚本先查重，再抓取、下载媒体、写入 Markdown。
4. 执行后 Agent 补全 `## 摘要`、`topics`/`people` 双链；`## 我的看法` 永远留空给用户。

## 安装

本技能随 `soia-pkm-vault` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-pkm-vault@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-pkm-vault@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -s soia-pkm-clip-rednote -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
