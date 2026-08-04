# Changelog

本文件由 soia-meta-skill-release 在每次正式发版时自动更新，与 GitHub Release 同源；
更早的版本演进见 git 提交历史与 GitHub Releases。

## v1.11.2 — 2026-08-04

发版模型改为 dev 快进覆盖 main：main 与 dev 指向同一提交，分叉在结构上不可能发生；分支一律从 main 开、PR 进 dev。

## 新增
- feat(release)!: fast-forward dev onto main instead of merging (#238)
- feat(audit): enforce metadata authenticity in SKILL.md frontmatter (#231)
- feat(release): guard the dev version-train invariant (#225)

## 修复
- fix(release): verify merge-commit capability before releasing (#230)
- fix(release): patch-level trains, bump skill version, guard both (#227)
- fix(release): merge-commit release PRs and detect divergence properly (#226)
- fix(codex): declare interface.websiteURL so the plugin page shows the site (#221)

## 维护
- docs(workflow): branch off main, merge into dev (#239)
- chore(sync): merge main into dev and correct train to patch level
- chore(release): open next train after v1.11.1 (#236)
- release: finalize v1.11.1 (drop -SNAPSHOT) (#234)
- docs(governance): require explicit per-release authorization (#233)
- chore(release): switch dev train to patch level
- chore(release): open next train after v1.11.0 (#224)
- release: finalize v1.11.0 (drop -SNAPSHOT) (#222)
- chore(release): open version train 1.11.0-SNAPSHOT on dev (#220)

## v1.11.1 — 2026-08-04

发布纪律工具化：发版改用 merge commit 消除历史分叉，新增版本列车与技能版本两个守卫，列车改 patch 级，正式发版需逐次授权。

## 新增
- feat(audit): enforce metadata authenticity in SKILL.md frontmatter (#231)
- feat(release): guard the dev version-train invariant (#225)

## 修复
- fix(release): verify merge-commit capability before releasing (#230)
- fix(release): patch-level trains, bump skill version, guard both (#227)
- fix(release): merge-commit release PRs and detect divergence properly (#226)
- fix(codex): declare interface.websiteURL so the plugin page shows the site (#221)

## 维护
- docs(governance): require explicit per-release authorization (#233)
- chore(release): switch dev train to patch level
- chore(release): open next train after v1.11.0 (#224)
- release: finalize v1.11.0 (drop -SNAPSHOT) (#222)
- chore(release): open version train 1.11.0-SNAPSHOT on dev (#220)

## v1.11.0 — 2026-08-03

修复 Codex 插件详情页「网站」显示不可用；发布流水线补 CHANGELOG 自动生成与 dev 快照试装。

## 修复
- fix(codex): declare interface.websiteURL so the plugin page shows the site (#221)

## 维护
- chore(release): open version train 1.11.0-SNAPSHOT on dev (#220)

## v1.9.0 — 2026-08-02

技能检索路由、提示词规格化与生态同步、发布工具。支持 Claude Code · Codex · WorkBuddy 三个宿主。
