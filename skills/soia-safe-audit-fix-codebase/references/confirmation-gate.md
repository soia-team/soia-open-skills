# 确认门契约

## 核心状态机

```text
requested
  -> audit_read_only
  -> report_ready
  -> awaiting_confirmation
  -> confirmed
  -> fixing
  -> validating
  -> completed | partial | blocked
```

`awaiting_confirmation` 之前不得产生目标代码 diff。初始请求中的“并修复”“顺便改掉”“自动处理”不替代报告后的确认。

## 修复批次必须包含

```yaml
batch_id: B1
audit_baseline:
  commit: <sha-or-none>
  worktree_fingerprint: <status-summary>
findings: [F-001, F-003]
files_planned: []
behavior_change: ""
tests_planned: []
rollback: ""
scope_expansion_triggers: []
residual_risk: ""
```

没有 `file:line`、依赖/制品位置或可复核证据的候选项不能进入自动修复批次。

## 有效确认

确认必须能唯一映射到当前报告和批次：

```text
确认 B1，修复 F-001、F-003；允许修改预览中的文件并运行列出的测试。
```

以下表达无效或需要追问：

- “都改了吧”，但报告有多个高风险批次；
- “继续”，但报告后代码或分支已经变化；
- 只确认漏洞名称，没有确认文件/测试范围；
- 要求顺便提交、push 或部署，但没有单独授权这些远端动作。

只有一个批次且紧接着预览回复“确认/继续”时，可以把它解释为该批次确认；回执中仍要复述实际授权范围。

## 确认失效条件

- 分支或 commit 改变；
- 目标文件发生无法归因于本技能的修改；
- 新发现要求修改批次外文件、公开 API、数据库、权限模型或部署架构；
- 原测试计划无法运行，需要采用更高风险验证；
- 客户暂停、缩小或撤回授权。

失效后保留已完成的只读证据，刷新受影响 Finding 和批次，再次请求确认。不要把旧确认扩展到新范围。

## 授权不包含

默认修复确认仅包含本地代码/配置修改和批次列出的测试，不包含：

- commit、push、PR、合并、发布或部署；
- 生产数据迁移、重启或流量切换；
- 生产 PoC、端口扫描、爆破、外传测试或破坏性验证；
- 安装系统级软件、修改全局安全策略或发送外部报告。

这些动作逐类单独取得授权。
