# Codex 安装指南

Codex 直接读取共享真源 `~/.agents/skills`，npx 安装后立即可用；同时支持插件市场。

## 路线 A：npx 安装技能

```bash
npx skills add soia-team/soia-open-dev-skills -g -a codex -s soia-dev-coding-protocol -y
```

技能本体写入 `~/.agents/skills`，Codex 从该目录直接读取，无需额外同步步骤。

`~/.codex/skills` 目录中指向共享真源的软链接对 Codex 而言是冗余的——它已经在发现链中包含 `$HOME/.agents/skills`。

## 路线 B：插件市场

### 注册市场

```bash
codex plugin marketplace add soia-team/soia-open-skills
```

Codex 读取仓库根的 `.agents/plugins/marketplace.json`（其原生清单格式）。

### 安装领域插件

```bash
codex plugin add soia-dev@soia
```

可用插件：`soia-dev`、`soia-dev-design`、`soia-pkm-vault`、`soia-media-content`、`soia-cwork-office`、`soia-edu-course`、`soia-env`、`soia-meta`。

### 插件是叠加而非替代（重要）

Codex 的插件技能**叠加**在共享真源之上：

```
Codex 实际加载的技能
  = ~/.agents/skills 全部技能（共享真源，无法通过插件关闭）
  + 已安装插件的技能
  + Codex 内置技能（~/.codex/skills/.system）
```

因此**安装插件不会减少 Codex 的常驻索引**。若目标是降低 Codex 的上下文占用，只能缩减 `~/.agents/skills` 本身的技能数量——例如只在共享真源保留高频技能，长尾技能通过 `soia-meta-find-skill` 按需检索安装。

## 验证

```bash
codex plugin list
```

查看 Codex 实际加载了哪些技能及其来源路径：

```bash
codex debug prompt-input
```

## 更新

```bash
codex plugin marketplace add soia-team/soia-open-skills
```

重新执行 `marketplace add` 会刷新市场清单。npx 路线用 `npx skills update`。

## 卸载

```bash
codex plugin remove soia-dev@soia
```

## 特有说明

- 技能列表占用上下文预算约 2%，技能过多时每条描述会被自动压缩。
- 插件配置记录在 `~/.codex/config.toml` 的 `[marketplaces.*]` 与 `[plugins."名@市场"]` 段。
- Codex 的技能发现链依次为：当前目录 `.agents/skills` → 上级目录 → 仓库根 → `$HOME/.agents/skills` → `/etc/codex/skills` → 内置。

[← 返回安装指南](README.md)
