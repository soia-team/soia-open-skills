# 插件开发与发版

本页说明 SOIA 插件在本地迭代时如何让 Codex 读取新内容，以及领域插件发布后如何刷新生态门户的固定版本。

## 本地插件迭代

适用于已经安装、且 marketplace 条目已指向正在修改的本地插件。完成改动后，不要手改 marketplace 配置；按以下顺序操作：

1. 修改插件内容或 `.codex-plugin/plugin.json`。
2. 用官方 cachebuster 工具替换版本的 build suffix：

   ```bash
   python3 <plugin-creator-root>/scripts/update_plugin_cachebuster.py \
     <plugin-path>
   ```

   工具会保留基础版本并写入 `+codex.local-<UTC 时间戳>`。需要指定 token 时才传 `--cachebuster <token>`。
3. 读取当前 marketplace 名称并重新安装：

   ```bash
   python3 <plugin-creator-root>/scripts/read_marketplace_name.py \
     --marketplace-path <marketplace.json>
   codex plugin add <plugin-name>@<marketplace-name>
   ```

4. 新开一个 Codex 对话，再验证更新后的技能和工具。

默认个人 marketplace 是 `~/.agents/plugins/marketplace.json`；它会被 Codex 自动发现，无需执行 `codex plugin marketplace add`。使用其他本地 marketplace 时，先确认它已配置且条目仍指向当前插件目录。

`<plugin-creator-root>` 是官方 `plugin-creator` skill 的安装目录；在 Codex 默认安装中，它通常位于 `~/.codex/skills/.system/plugin-creator`。公共文档使用占位符，避免绑定某个维护者的机器路径。

## 领域插件发版后刷新元仓

领域插件仓库完成发版后，按此顺序更新生态门户：

1. 在领域仓 bump 版本并更新 `CHANGELOG`，完成该仓的提交、推送和合并。
2. 回到元仓 `soia-open-skills`，运行生成器以获取各领域仓 `main` 的最新固定 SHA：

   ```bash
   python3 scripts/generate_marketplaces.py
   ```

3. 检查生成的 `.agents/plugins/marketplace.json` 与 `.claude-plugin/marketplace.json`，并提交 SHA 刷新结果。

Claude 清单和 Codex 清单均由生成器维护；不要手工修改生成文件。
