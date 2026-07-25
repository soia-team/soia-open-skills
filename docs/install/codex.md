# Codex 安装指南

Codex 原生读取 `$HOME/.agents/skills`。`~/.codex/skills` 中的软链接对 Codex 的读取没有额外作用。

## 路线 A：npx

```bash
npx skills add soia-team/<仓库名> -g \
  -a codex -s <技能名> -y
```

技能本体进入 `~/.agents/skills`，Codex 随后直接读取该全局目录。`-a codex` 不会把技能隔离到 Codex，也不会阻止其他原生读取全局目录的宿主看到它。

`--copy` 不改变 Codex 的读取路径；即使目标目录生成副本，Codex 仍读取 `~/.agents/skills`。

验证、更新和卸载：

```bash
test -f ~/.agents/skills/<技能名>/SKILL.md
npx skills ls -g -a codex
npx skills update -g
npx skills remove -g -a '*' -s <技能名> -y
```

## 路线 B：Codex 插件

```bash
codex plugin marketplace add soia-team/soia-open-skills
codex plugin add <域插件名>@soia
```

市场定义来自仓库根目录 `.agents/plugins/marketplace.json`。插件安装到 `~/.codex/plugins/cache/soia/<域插件名>/`；市场和插件记录写入 `~/.codex/config.toml` 的 `[marketplaces.*]` 与 `[plugins."<插件名>@<市场>"]`。

### 插件是叠加，不是替代

Codex 会同时读取：

1. 全局 `~/.agents/skills`；
2. 已安装的 Codex 插件。

因此，安装 Codex 插件不会减少全局索引，移除插件也不会隐藏 `~/.agents/skills` 中的同名技能。若目标是减少 Codex 读取的全局技能，必须调整全局安装集合；不能靠插件安装或插件移除实现。

验证、更新和卸载插件：

```bash
codex plugin list
codex plugin marketplace upgrade soia
codex plugin remove <域插件名>@soia
```

[← 返回安装指南](README.md)
