# soia-dev-officecli-ops

> 以 OfficeCLI 安全读取、复制后修改并验证 DOCX、XLSX、PPTX

所属：[`soia-dev-design`](https://github.com/soia-team/soia-open-dev-design-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-design-skills/tree/main/skills/soia-dev-officecli-ops) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

「OfficeCLI」「OpenXML 验证」「Office 文件原子修改」

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 检查 Word、Excel 或 PPT | 提取结构、文本、统计与 issues，必要时渲染 HTML/截图 | 问题清单、元素路径、预览和修复建议 |
| 精确修改现有 Office 文件 | 优先用稳定 ID/名称定位，在副本上执行 `set/add/remove/move/swap` | 新文件、修改回执、校验结果 |
| 一次执行多项修改 | 把 3 项及以上操作组织成原子 `batch` | 成功/失败步骤；失败时不交付半成品 |
| 创建基础 Office 文件 | 创建 DOCX/XLSX/PPTX 结构并逐步添加内容 | 可继续编辑的 Office 文件 |
| 给其他技能提供 Office 底座 | 根据宿主能力和任务类型选择 OfficeCLI、Open Design 或宿主原生工具 | 清晰的执行路线和降级说明 |

### 客户如何使用

1. 提供 `.docx`、`.xlsx` 或 `.pptx` 路径，并说明要检查、创建还是修改。
2. 修改已有文件时同时说明输出路径；默认生成副本，不原地覆盖源文件。
3. Agent 先在临时副本上运行查询，再展示修改目标；删除、覆盖、raw XML、安装、MCP 注册必须单独确认。
4. 三项及以上修改优先使用原子 batch。完成后依次做 schema、issues 和视觉检查。
5. 最终回执说明使用的执行层、修改数量、输出文件、验证证据和剩余限制。

示例：

```text
检查 <report.docx> 的格式和结构问题，先不要修改
把 <deck.pptx> 第 3 页标题改掉，输出为 <deck-fixed.pptx>
审计 <workbook.xlsx>，确认后批量修复公式和格式
用 OfficeCLI 复验刚生成的 PPTX，并给出逐页截图
```

## 安装

本技能随 `soia-dev-design` 领域插件一起安装：

```bash
claude plugin marketplace add soia-team/soia-open-skills && claude plugin install soia-dev-design@soia
```

```bash
codex plugin marketplace add soia-team/soia-open-skills && codex plugin add soia-dev-design@soia
```

WorkBuddy 由技能代劳——对 AI 说「装到 WorkBuddy」即可。

只想要这一个技能：

```bash
npx skills add soia-team/soia-open-dev-design-skills -g -a '*' -s soia-dev-officecli-ops -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
