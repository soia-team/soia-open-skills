# THIRD_PARTY_NOTICES

> Last updated: 2026-07-22
> 本文件只登记生态门户与留存 `soia-meta-*` 技能直接使用或明确引用的第三方项目。
> 已迁移技能的第三方声明由对应目标仓维护；迁移 PR 需在目标仓审核合并后生效。

## 运行时工具

| 上游 | 协议快照 | 用于 | 关系 |
|---|---|---|---|
| [`vercel-labs/skills`](https://github.com/vercel-labs/skills) | 无 SPDX 识别（NOASSERTION） | `soia-meta-sync-skills`、`soia-meta-skill-release` | 两个 meta 技能调用用户已安装的 `npx skills` CLI 完成安装、更新与 lock 管理；本仓不复制或修改上游代码 |

## 维护规则

1. 新增或修改留存技能时，凡出现新的上游链接、安装指令或外部服务，必须同步登记。
2. 协议列是快照，不代表实时值；复用或分发前重新核对上游许可证。
3. 无明确协议的上游仅作为外部工具调用或只读参考，不得复制代码。
