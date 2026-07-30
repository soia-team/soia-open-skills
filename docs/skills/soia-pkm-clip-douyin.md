# soia-pkm-clip-douyin

> 归档单条抖音视频到 Obsidian vault，并保留本地媒体索引

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-clip-douyin) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「归档这条抖音」「clip 这个抖音视频」「只要抖音文案」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 归档一条抖音视频链接 | 用 Playwright 打开视频页拦截签名 API，拿到作者/文案/时长/互动数和可下载直链；下载 MP4 到本地；在 vault 写一篇轻量 Markdown 笔记（含 `media_local_path`） | vault 里新增一个 `.md` 文件，终端打印文件路径、作者、发布时间、下载路径、互动数据 |
| 只想先看这条链接能不能解析，暂不下载视频 | 加 `--metadata-only`：只抓元数据和文案写笔记，跳过视频下载 | 笔记里 `media_local_path` 为空、`media_fetched: false`，日志提示候选直链数量 |
| 同一条视频重复归档 | 按 vault 内已有笔记的 frontmatter `url:` 做去重 | 打印 `⚠️ Already archived` 并退出，不重复下载/不重复写笔记 |
| 缺少 Playwright 依赖 | 停止并给出安装命令，不猜测降级方案 | `❌` 开头的错误信息 + `pip install playwright && python -m playwright install chromium` |

### 客户如何使用

1. 给出一条抖音视频链接（`https://www.douyin.com/video/<id>`、带 `modal_id=`/`resource_id=` 参数的链接，或 `v.douyin.com` 短链）。
2. 在 vault 根目录运行 `python3 scripts/archive_douyin.py <URL>`；不在 vault 内时加 `--vault <path>`。
3. 脚本自动去重、抓取、下载、写笔记；全过程失败会用 `❌` 报出具体原因，不会留下半成品笔记。
4. 归档完成后，按回执里的「Next step」提示补 `## 摘要`、`topics`、`people`。

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
npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -s soia-pkm-clip-douyin -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
