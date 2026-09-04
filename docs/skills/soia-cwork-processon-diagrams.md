# soia-cwork-processon-diagrams

> 安全盘点并按授权导出、校验和归档 ProcessOn 图表

所属：[`soia-cwork-office`](https://github.com/soia-team/soia-open-cwork-office-skills) · [技能源码](https://github.com/soia-team/soia-open-cwork-office-skills/tree/main/skills/soia-cwork-processon-diagrams) · [← 全部技能](README.md)

## 怎么触发

装好后用自然语言说话即可，Agent 按下列意图命中本技能：

ProcessOn 盘点、导出架构图、批量下载图表

## 能力与用法

### 这个技能可以做什么

| 客户想要 | 技能会做 | 客户能看到 |
|---|---|---|
| 盘点团队空间 | 从指定节点递归到每个子目录和叶子文件，按小批次保存并审计恢复状态 | Markdown/JSON 树、进度快照、遗漏差集、权限缺口与完成回执 |
| 看图里有什么 | 进入“浏览”视图读取可访问文字，并用截图核对视觉布局 | 内容摘要、关键文字与截图 |
| 导出图表 | 按客户授权选择 VSDX、POS、PNG、SVG、PDF、XMind 或 Office 格式 | 下载文件、格式/大小/SHA-256 验收 |
| 归档浏览器下载 | 解析 CLI、环境变量和私有 YAML 中的路径，让 Playwright 按 run/artifact 直写受管 staging；校验后在同一文件系统无复制归档 | staging/最终路径、transfer mode、SHA-256 和审计 manifest |
| 批量续跑归档 | 从归档计划初始化下载队列，逐项领取、记录成功/失败/阻断并重放审计 | `download-progress.json`、下一批列表和机械验收结果 |
| 收口异常尾单 | 对已失败/阻断项使用精确 artifact 白名单重试；对计划内同名项生成与计划 SHA 绑定的顺序确认；对未知类型只观察固定 provider 图标 | 定向批次回执、碰撞确认文件、未知类型观察清单；歧义和安全项不会被硬算成功 |
| 受控并发归档 | 在一个技能专用 context 内固定复用 1–2 个 headless worker 页；下载可并发，归档和进度仍单写入 | 并发 proof、逐批 receipt、弹页/worker 关闭对账和进度镜像 |
| 长任务续跑监督 | 顺序运行已证明的小批次；每批审计后才继续，宿主中断可从私有监督状态恢复 | `archive-supervisor-state.json`、逐批状态和停止原因 |
| 不干扰地控制浏览器 | 从任意 AI/终端调用本地 Playwright runner，在技能专用 profile 中 headless 执行 | 独立登录态、页面关闭计数、下载回执；客户主 Chrome 不被接管 |
| 解析已有导出 | 读取本地 POS/XMind/SVG/图片；VSDX 可交给可选 draw.io/Visio 技能 | 标题、图表类型、节点文字、尺寸与校验值 |

### 客户如何使用

客户提供以下信息中的最少必要部分：

1. ProcessOn 团队、文件夹或图表 URL；也可以给出空间名和文件名。
2. 目标动作：初始化盘点、增量盘点、下载归档，或解析/转换已有导出文件。
3. 导出时指定文件范围、格式和交付目录；未指定格式时，流程图默认选择当前菜单可用的 Visio `.vsdx`，思维导图默认选择 `.xmind`。两类都建议同时保留 POS 作为 ProcessOn 原生结构备份。无法从图标、浏览视图或菜单确认类型时，只写入“待人工确认”清单，不猜测格式、不自动下载。视觉复用优先 SVG/高清 PNG，审阅交付优先 PDF。
4. 第一次使用时，客户只在 runner 弹出的**独立 ProcessOn 窗口**手动输入用户名、密码、短信码或验证码；成功后窗口自动关闭，后续批量默认 headless。技能不读取、记录或输出 Cookie、Local Storage、密码文件或凭据。
5. 可选复制 [路径配置模板](assets/config.example.yml) 到私有配置目录，固定临时下载、最终交付、审计清单和保留天数。

示例：

```text
初始化盘点这个 ProcessOn 团队空间，只读，不下载：<team-url>
对上次盘点和今天重新审计后的快照做增量盘点，不猜测删除项
按已审计计划下载已确认流程图为 VSDX、思维导图为 XMind，归档到 <output-dir>
解析 <export-dir> 里的 POS，或把 VSDX 转成 draw.io 真源后升级
```

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
npx skills add soia-team/soia-open-cwork-office-skills -a <agent> -s soia-cwork-processon-diagrams -y
```

客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。

---

本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，请勿手改——改 `SKILL.md` 后重跑生成器。
