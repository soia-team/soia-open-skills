# Providers

按需读取本文件。它只做 provider 路由；详细规则分散到单独 reference，避免一个大文件把所有场景塞进上下文。

## 选择顺序

1. 用户本轮明确指定的 provider。
2. 配置文件 `outputs.<type>.provider`。
3. 目标产物默认 provider。
4. 当前 agent 实际可用工具。

无法确认 provider 是否可用时，先做只读检查，不要直接承诺产物。provider 缺失时按对应 bootstrap 推进；需要用户认证或改配置时停在人工闸门。

## 读取索引

| Provider / 场景 | 读取 |
|-----------------|------|
| Obsidian / local visual / Codex imagegen / publish | [provider-soia-local.md](provider-soia-local.md) |
| NotebookLM / `teng-lin/notebooklm-py` | [provider-notebooklm.md](provider-notebooklm.md) |
| NotebookLM 全 artifact 测试 | [notebooklm-test-matrix.md](notebooklm-test-matrix.md) |
| Open Design / html-ppt / MCP 接入 | [provider-open-design.md](provider-open-design.md) |
| Open Design 视觉提示词 | [prompt-open-design.md](prompt-open-design.md) |

## 公共边界

- 不写死个人路径、账号、token、cookie、家庭信息或 vault 私有路径。
- 秘钥和登录态只放 provider 自己的私有认证位置，例如 `NOTEBOOKLM_HOME` 或 provider 官方配置目录。
- 任何自动安装都必须来自用户明确要求、配置策略或目标 provider 的 bootstrap；不要为普通本地转换强行安装增强 provider。
- NotebookLM 和 Open Design 都是外部 provider：未通过健康检查时，回执要写真实降级，不得声称已调用。
