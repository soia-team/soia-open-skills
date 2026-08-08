# soia-meta-publish-market

> 把已正式发版的技能上架到外部市场（腾讯 SkillHub、小红书 Red Skill）：筛选可独立运行的技能、叠加平台 frontmatter、预检后交由客户提交

所属：[`soia-meta`](https://github.com/soia-team/soia-open-skills) · [技能源码](https://github.com/soia-team/soia-open-skills/tree/main/skills/soia-meta-publish-market) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「上架 SkillHub」「发到 Red Skill」「上架技能市场」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 看哪些技能能上架 | 扫全仓，按 hard 依赖筛选 | 逐技能的可否上架与原因 |
| 上架某个技能到 SkillHub | 打包 → 叠加平台字段 → `--dry-run` 预检 → 交客户提交 | 暂存路径、预检结果、待执行命令 |
| 发到小红书 Red Skill | 打包并给出上传指引 | 暂存路径与上传入口说明 |
| 更新已上架的技能 | 保持 slug 不变重新打包，提示填写变更说明 | 版本对比与 changelog 建议 |
| 上架前检查技能是否就绪 | 打包并对暂存产物跑 R1-R6 就绪门禁 | 逐项通过/警告/硬缺口报告，硬缺口拒绝打包 |

### 客户如何使用

```bash
# 1. 看这个仓哪些技能可以上架
python3 scripts/stage_for_market.py --repo-dir <域仓路径> --list-eligible

# 2. 打包某一个（不会上传；按渠道过滤文件）
python3 scripts/stage_for_market.py --repo-dir <域仓路径> \
  --skill <技能名> --out <暂存目录> --channel skillhub|redskill \
  --display-name "<中文展示名>"

# 3. 发版前咨询：对工作树跑一遍就绪门禁，不留产物（见「上架就绪门禁」）
python3 scripts/stage_for_market.py --repo-dir <域仓路径> \
  --skill <技能名> --out <暂存目录> --allow-unreleased --check-only
```

**打包内容直接从 `origin/main` 导出**，不读工作副本——本地检出在哪个分支都不影响
结果，也就不会因为有人切走分支而误打包未发布内容（多 AI 共用检出时这是常态）。
`main` 上没有该技能、或 main 版本带 `-SNAPSHOT`，一律拒绝打包。

`--channel redskill` 时 **`--display-name` 是必填**，缺省直接拒跑，原因见
[展示名与平台主键](#展示名与平台主键必填)。

打包后由**客户本人**执行投递命令——见下方两个渠道。

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
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-publish-market -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
