# 项目安全报告契约

## 报告头

```yaml
report_id: CODE-AUDIT-<timestamp-or-repo-id>
checked_at: <RFC3339-with-timezone>
target:
  root: <redacted-or-customer-selected-path>
  branch: <branch-or-none>
  commit: <sha-or-none>
  dirty: <true-or-false>
scope:
  included: []
  excluded: []
tools_run: []
tools_missing: []
code_changed_during_audit: false
```

## 正文结构

```markdown
# 项目代码安全报告：<项目>

## 一句话结论
<总体风险、最关键问题、是否可以进入修复确认>

## 管理摘要
- Critical / High / Medium / Low / Info 数量
- 最高风险数据流
- 已确认、推断、待确认数量
- 立即行动和建议修复批次

## 范围与覆盖
| 领域 | 已检查 | 方法 | 未覆盖/原因 |

## 架构与攻击面
- 外部入口与信任边界
- 身份、权限和租户边界
- 数据存储和敏感数据
- 外部网络、文件、命令和反序列化
- CI/CD、容器、IaC 和运行环境

## Findings
### F-001 · <严重度> · <标题>
- 状态：confirmed / inferred / needs-evidence
- 置信度：high / medium / low
- 位置：`path:line`
- 证据：最小必要代码/配置、调用链或依赖位置
- 前提：攻击者需要控制什么、路径是否可达
- 影响：机密性、完整性、可用性和资产范围
- 反证检查：尝试推翻时检查了什么
- 修复方向：不在审计阶段直接改
- 验证建议：直接测试、正常路径和回归
- 映射：CWE/CVE/厂商公告（适用时）

## 依赖与供应链
| 包/制品 | 版本 | 来源 | 漏洞 | 可达性 | 结论 |

## 被驳回或降级的候选
| 候选 | 扫描器/来源 | 反证 | 结论 |

## 修复批次预览
### B1 · <目标>
- Findings：F-001、F-003
- 拟修改文件：明确列表
- 行为变化：安全边界如何改变
- 测试：直接、正常、回归、重扫、独立复核
- 回滚：恢复方法
- 范围扩大条件：何时需要重新确认

## 确认请求
<要求客户确认具体批次/Finding；说明当前尚未修改代码>

## 覆盖缺口与残余风险
- 未安装工具、无法构建模块、缺部署信息或秘密配置
- 仅静态可见、未运行时验证的结论
```

## Finding 严重度

| 等级 | 标准 |
|---|---|
| Critical | 可现实地导致未认证 RCE、跨租户控制、关键秘密/大规模数据泄露或供应链接管 |
| High | 重大权限绕过、敏感数据访问、可利用注入或高影响依赖漏洞 |
| Medium | 需要较强前提、影响受限或存在有效缓解的安全缺陷 |
| Low | 防御纵深、有限信息泄露或低影响错误配置 |
| Info | 已核对的观察、加固建议或不构成漏洞的事实 |

严重度必须同时写利用前提和资产影响。扫描器标签可以作为候选，不可直接复制成最终严重度。

## 修复回执

```markdown
修复结论：approved / partial / changes-requested / blocked

| Finding | 决策 | 文件 | 直接测试 | 回归 | 重扫 | 独立复核 |

未处理项：<reject/defer/blocked 的证据和承接路径>
工作树：<仅包含已授权改动，或列出保留的客户原有改动>
残余风险：<未覆盖场景或“无”>
远端动作：<未执行，除非另有明确授权>
```
