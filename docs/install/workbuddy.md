# WorkBuddy 安装指南

WorkBuddy 是桌面客户端，接 SOIA 技能有两条路线。

| | 专家路线（推荐） | 软链路线 |
|---|---|---|
| 装什么 | 一个角色化专家，自带该域全部技能 | 单个技能软链到 `~/.workbuddy/skills` |
| 按需能力 | 有——不召唤就不在场 | 无，装了就常驻索引 |
| 附带 | 人设、推荐提示词、头像 | 只有技能本身 |
| 适合 | 日常使用 | 只想要某一个技能 |

## 路线 A：安装 SOIA 专家（推荐）

一个域仓就是一个专家——仓根同时是 Claude 插件、Codex 插件和 WorkBuddy 专家包，
技能不复制，`avatar` 直接用该仓的 `assets/icon.png`（与 Codex 的 logo 是同一个文件）。

| 专家 | 花名 | 携带技能 |
|---|---|---|
| 知识库管家 | Soia Vault | 知识库全域 26 个：网页/公众号/X/小红书/云盘归档、整理、解读、转 PPT 与长图 |

其余域仓的专家清单陆续补齐。

### 装载机制（重要，决定了怎么装）

WorkBuddy 的自建专家**只认一个目录**：

```text
~/.workbuddy/plugins/marketplaces/my-experts/plugins/<专家名>/
```

`my-experts` 在客户端里是硬编码的，另建市场（哪怕登记进 `known_marketplaces.json`）
也不会显示专家。官方 `expert-manager` 技能里那句「专家必须生成到专家目录才能被检测到，
其他目录生成后将无法使用」是字面事实。

与 Claude/Codex 的两点不同：

- **没有按 sha pin 拉远端仓这一层**。WorkBuddy 市场条目的 `source` 只能是路径字符串，
  不支持 `{"source":"github","repo":…,"sha":…}` 这种对象。
- **软链不行**。官方校验器对路径做 `resolve()`，会穿透到真实路径后判定「不在专家目录下」。

所以装载方式是**在该目录下放一份该域仓的 checkout**——和 Claude 在
`~/.claude/plugins/cache/…` 有一份克隆、Codex 在 `~/.codex/plugins/cache/…` 有一份，
是完全对等的做法。git 仓库里不存副本，磁盘上每个宿主各有自己的 checkout。

### 安装

```bash
git clone --depth 1 https://github.com/soia-team/soia-open-pkm-vault-skills.git ~/.workbuddy/plugins/marketplaces/my-experts/plugins/soia-pkm-vault
```

再把它登记进 `my-experts` 的市场清单
（`~/.workbuddy/plugins/marketplaces/my-experts/.codebuddy-plugin/marketplace.json`）：

```json
{
  "name": "my-experts",
  "description": "my-experts marketplace (auto-generated)",
  "plugins": [
    {
      "name": "soia-pkm-vault",
      "source": "./plugins/soia-pkm-vault",
      "description": "知识库技能：初始化、整理、提炼、翻译、转换与书库"
    }
  ]
}
```

已有其他专家时**追加条目**，不要覆盖整个文件。改完重启 WorkBuddy。

### 验证

```bash
ls ~/.workbuddy/plugins/marketplaces/my-experts/plugins
```

界面上到【专家·技能·连接器 → 我的专家】应能看到该专家。召唤后可用
「你有多少个可用技能」自查——该域技能应全部在场，未召唤时不在场。

### 更新

重新 clone 或在该目录 `git pull`。专家清单里的 `skills` 数组由域仓自己的
`scripts/generate_expert_manifest.py` 维护，`--check` 已进各仓 CI，不会与 `skills/` 失配。

### 卸载

删掉该目录，并从 `marketplace.json` 的 `plugins` 数组移除对应条目。

## 路线 B：软链单个技能

只想要某一个技能时用同步工具。先装 `soia-meta` 插件拿到同步脚本：

```bash
claude plugin marketplace add soia-team/soia-open-skills
```

```bash
claude plugin install soia-meta@soia
```

预览要同步什么（`<版本>` 取 `ls ~/.claude/plugins/cache/soia/soia-meta` 里最新的一个）：

```bash
python3 ~/.claude/plugins/cache/soia/soia-meta/<版本>/skills/soia-meta-sync-skills/scripts/sync_soia_skills.py --targets workbuddy --skills <技能名> --dry-run
```

确认预览后移除 `--dry-run` 执行。

### 验证

```bash
readlink ~/.workbuddy/skills/<技能名>
```

### 卸载

用同步工具的 `--exclude-skills` 排除该技能后重跑，或直接删掉软链。

## 特有说明

- WorkBuddy 也支持 zip 导入**单个技能**（【添加技能 → 上传技能】，包根需含 `SKILL.md`），
  但那个入口不接受专家包，也不接受市场 URL。
- 专家携带的技能与 `~/.workbuddy/skills` 里的软链互不影响。两条路线装了同一个技能时，
  索引里会出现两份且各自漂移——和插件与 npx 并存是同一类问题，建议二选一。

[← 返回安装指南](README.md)
