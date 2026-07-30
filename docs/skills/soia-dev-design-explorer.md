# soia-dev-design-explorer

> 基于 Open Design（经 soia-dev-open-design-ops）做高保真 HTML 原型、设计变体、幻灯片、动画探索与设计评审；要求用户品牌输入、五分类输出落点与可复现验证

所属：[`soia-dev-design`](https://github.com/soia-team/soia-open-dev-design-skills) · [技能源码](https://github.com/soia-team/soia-open-dev-design-skills/tree/main/skills/soia-dev-design-explorer) · [← 全部技能](README.md)

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 高保真 prototype / deck / animation | 收集目标、画幅、内容和资产，借助 Open Design 逐步生成 | 产物路径、预览、缺口与验证证据 |
| style exploration | 生成 2–4 个可比较方向，不让用户只凭文字盲选 | 方向差异、真实视觉和推荐理由 |
| design review | 对已有页面或截图分级评审 | 结论、严重度、优先修复动作 |

不用于常规前端实现、CSS bug 修复、低保真线框或 PRD 编写。

### 客户如何使用

提供：

1. 交付类型：`prototype` / `deck` / `animation` / `style-exploration` / `review`；
2. 平台与画幅；
3. 受众、用途和成功标准；
4. 真实内容与资产；
5. 用户自带的品牌规范（文件、URL 或明确说明“无”）；
6. 输出类别与路径；
7. Open Design checkout 路径；设计系统接入时再提供项目路径或 `DESIGN.md`。

需求模糊时先给 2–3 个互斥形态选项。品牌信息不足时使用中性探索方向并标注 placeholder，不从记忆猜品牌色。

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
npx skills add soia-team/soia-open-dev-design-skills -g -a '*' -s soia-dev-design-explorer -y
```

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
