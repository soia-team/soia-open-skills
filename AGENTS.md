# soia-open-skills

公开技能仓：soia-meta-* 生态技能、共享规范与市场门户。客户不共享维护者的机器、账号和私有工作区；仓名不触发 SOIA 产品 proposal/board 流程。

## 边界

- 不提交秘密、账号标识、私有 config/.env、机器绝对路径或家庭/健康/财务等上下文；示例用占位符。凭据留在官方登录态/密钥存储，不复制到普通日志。
- 新配置写 `~/.config/soia-skills/<skill-name>/config.yml`（v2），客户差异经参数、环境变量或非秘密配置传入；v1 只读迁移输入，不自动搬移/删除用户配置。
- 已授权局部修改与相关验证连续完成，保留他人改动；派发、提交/合并、发布、安装、权限与重要删除各守本次授权，不从完成自检推导后续授权。

## 按需入口

- 修改技能时读目标完整 `SKILL.md`；创建/改名/拆分/实质重构才读 [技能规范](SKILL_SPEC.md) 和模板。
- 改 config/state/cache/temp/凭据/落盘回执时读 [数据规范](DATA_STORAGE_SPEC.md)；普通文案不加载它。
- 贡献或生命周期操作查 [CONTRIBUTING.md](CONTRIBUTING.md)对应章节；不批量读所有参考。
- `skills/README.md` 是生成物；事实列表保持单一机器真源。技能正文承载跨宿主核心流程，供应商细节按需放 references。
- 安装须明确 scope、宿主及技能/整域/全量；正式验收使用已发布远端，不将未发布 checkout 当正式安装。普通维护不安装。

## 验证

纯指令/文案检查差异、链接与条款一致性；行为变化运行受影响测试。技能行为、脚本、依赖或公共工具提交前执行下列门禁；正式集成/发布的 CI 必选项仍全部保留：

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/generate_skill_catalog.py --check
python3 scripts/audit_skills.py
git diff --check
```

缺依赖且环境安装已获准时才安装 requirements-dev；辅助 quick validator 不支持本仓扩展 frontmatter 时记录限制，不删除必需版本/作者/时间字段迁就它。

## Git 与发布

- 新分支默认从正式 `main` 开，PR 显式指向 `dev`；确实依赖未发布内容才从 dev 开并说明。合并需 audit 通过与本次许可。
- 普通开发不直接 push main/dev，feature PR 不改插件列车版本。dev 带 `-SNAPSHOT`；main 保持正式版。
- 正式发布须当次明确授权：定稿 PR → dev/CI，核对 main 是 dev 祖先及实际合并冲突，再仅快进 main、tag/Release、重开 SNAPSHOT、完成 pin。一个已批准计划内不逐命令重问；夹带未批准内容时暂停。
- 本仓默认分支必须 main：市场中的 soia-meta 使用 `source: ./`、无 pin，默认 dev 会直达 SNAPSHOT。
- 特例仅限已批准正式 pin 与对应生成说明页：可 PR → main，经 audit 与许可合并；不得夹带技能实现或 SNAPSHOT。其余 PR → dev。
- 未批准无人值守市场刷新，不新增 PAT 或削弱分支保护来自动刷新；市场排期/P3/P4/D5-D8 按 Owner 当前计划核实，不在入口复制旧状态。
