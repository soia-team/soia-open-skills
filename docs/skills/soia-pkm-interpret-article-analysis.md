# soia-pkm-interpret-article-analysis

> 为 vault 长文或论文生成独立 AI 解读，帮助判断是否值得深挖，且不改原文或代写用户观点

所属：[`soia-pkm-vault`](https://github.com/soia-team/soia-open-pkm-vault-skills) · [技能源码](https://github.com/soia-team/soia-open-pkm-vault-skills/tree/main/skills/soia-pkm-interpret-article-analysis) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「解读这篇」「精读这篇」「值得细读吗」

## 能力与用法

### 这个技能可以做什么

对 vault 里 clip 进来的长文/论文，AI 直接给出解读：内容总览/核心要点/关键启发/批判视角/延伸阅读五段式。默认快读（各段 2-3 句），说"精读/深度解读"升级为逐节展开 + 论证链核查。产出独立 `<原文件名>-AI解读.md`，落原文件同目录并双链回原文，绝不碰原文、绝不写入原文的 `## 我的看法` 段。

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 快速判断一篇长文/论文值不值得细读 | 快读：五段式各 2-3 句的 AI 解读 | `<原文件名>-AI解读.md`，双链回原文 |
| 精读一篇重要文章，要逐节核查论证 | 精读：逐节展开 + 论证链核查，标出原文未明确处 | 更详细的解读文件，批判视角至少一条 |
| 批量解读同一批文章（超过 3 篇） | 先报清单（文件名 + 主题），等待确认范围 | 待解读清单 → 逐篇解读文件 + 汇总回执 |
| 想把这篇炼成自己的观点，而不是看 AI 怎么想 | 提示这不是本技能职责，指向 `soia-pkm-distill-article-opinion` | 边界说明，不会被误当成你的观点 |

### 客户如何使用

1. 提供要解读的文章：说"这篇"（=当前对话涉及的文章）或给出文件名/标题，Agent 在 `<vault-articles-dir>/` 下定位。
2. 单篇文章：Agent 直接执行，不需要额外确认。批量（同一请求涉及超过 3 篇）：Agent 先列出清单（文件名 + 大致主题），等待客户确认解读范围（全部 / 挑选几篇 / 暂停），再逐篇执行。
3. 深度默认**快读**（五段式，各段 2-3 句）；客户说"精读""深度解读""逐节核查"时升级为**精读**（逐节展开 + 论证链核查，见 [两档深度](#两档深度)）。
4. 解读永远**先落盘、后汇报**：产出 `<原文件名>-AI解读.md` 落在原文件同目录，正文双链回原文，绝不改动或覆盖原文件（含 `## 我的看法` 段）。
5. 最终回复必须给客户完整回执：深度、篇数、产出文件路径、标注了几处"原文未明确/需核对"、剩余风险。

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
npx skills add soia-team/soia-open-pkm-vault-skills -g -a '*' -s soia-pkm-interpret-article-analysis -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
