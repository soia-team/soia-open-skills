# 市场 pin 刷新

域仓改动合并到 main 后，插件用户不会立即拿到——市场清单里的 sha pin 仍指向旧提交。发布授权覆盖 pin 刷新时按下列步骤完成；元仓 main 受分支保护（PR + `audit` 必过 + `enforce_admins`），只能以 PR 提交，不能直推。

## 1. 确认域仓改动已合并

```bash
gh api repos/soia-team/<域仓>/commits/main --jq '.sha'
```

## 2. 在元仓重新生成市场清单

在元仓 checkout 中：

```bash
git checkout main && git pull && git checkout -b chore/refresh-marketplace
```

```bash
python3 scripts/generate_marketplaces.py
python3 scripts/generate_router_index.py
python3 scripts/generate_skill_pages.py
```

生成器重新拉取各域仓 main 的最新 sha，改写 `.claude-plugin/marketplace.json`、`.agents/plugins/marketplace.json` 与路由索引。只纳入授权 pin 与对应派生物，检查是否带入范围外变化。`git status` 无变化说明清单已是最新，跳到客户端更新。

## 3. 提交 PR 并合并

```bash
git commit --only <本次逐个批准路径> -m "chore(marketplace): refresh sha pins"
git push -u origin <本次分支>
```

```bash
gh pr create --base <元仓规则指定目标分支> --title "chore(marketplace): refresh sha pins" --body "刷新 sha pin 至各域仓最新提交。" --repo soia-team/soia-open-skills
```

等 `audit` 通过后合并：

```bash
gh pr checks <PR号> --repo soia-team/soia-open-skills
```

```bash
gh pr merge <PR号> --merge --repo soia-team/soia-open-skills
```

合并方式须保留正式发布所需的 main→dev 祖先关系；合并不自动删除分支。`audit` 的 marketplace freshness 检查会独立重算清单，两边不一致即失败，保证发布出去的 pin 指向域仓当前 main。

## 4. 核对 sha pin 已更新

```bash
gh api repos/soia-team/soia-open-skills/contents/.claude-plugin/marketplace.json --jq '.content' | base64 -d | python3 -c "import json,sys;print({p['name']:str(p.get('source',{}).get('sha',''))[:12] for p in json.load(sys.stdin)['plugins']})"
```

与第 1 步的域仓 sha 一致即清单已是最新。
