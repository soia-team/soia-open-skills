# Execution Checklist

## 开工前

- 已锁定 `prototype` / `deck` / `animation` / `style-exploration` / `review` 之一
- 已确认平台、画幅、受众、用途和成功标准
- 已把内容、素材和用户品牌规范标为 `available / missing / placeholder`
- 已通过 `soia-dev-open-design-ops` 的 `check_env.py` 检查 Open Design 环境，`daemon_ctl.py health` 已以 `/api/skills` 数组验证 daemon
- 设计系统已确认正式三件套（`manifest.json`、`DESIGN.md`、`tokens.css`）或明确标为 `DESIGN.md`-only compatibility，并按原子层流程接入
- 已按 A/B/C/D/E 分类选择输出目录，并预览将创建或覆盖的文件

## 生成中

- 先做最小可见版本
- style exploration 至少给 2 个实质不同方向
- prototype 保证关键路径可点击或清楚标注静态范围
- review 给问题分级与可执行修复建议
- 品牌选择有用户输入或可引用的公开来源，placeholder 已标明

## 交付前验证

至少完成与产物相称的一项：

- 浏览器在目标 viewport 打开成功
- Playwright / 上游验证脚本截图成功
- deck / video / GIF / PDF 可打开，页数或时长符合预期
- prototype 关键交互可点击
- review 包含优点、严重度问题和优先修复动作

确认回执同时包含：Open Design 环境/daemon/设计系统检查结果、产物绝对路径、验证命令/结果、缺失素材和 placeholder。

## 最终汇报模板

```markdown
产物：<绝对路径或“纯 stdout”>
类型：prototype / deck / animation / review / style-exploration
输出分类：A / B / C / D / E
验证：<命令、viewport 或打开检查>
待补：<素材/文案/真实数据/导出；没有则写“无”>
```
