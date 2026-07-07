# maintain · AI 会话日志接入（Claude Code / Codex）

把 vault 里未提交的改动，在每次 AI 会话/回合结束时自动追加一条摘要到
`30_日志与思考/20_Agent工作日志/<年>/<agent>/<日期>.md`。底层脚本是
`scripts/session_end_log.sh`（两平台共用），Codex 侧多一层
`scripts/codex_notify_wrapper.sh`。

> ⚠️ **显著提醒**：不管是 Claude Code 的 `.claude/settings.json` 还是 Codex 的
> `config.toml`，都是用户全局/项目级的运行配置。**写入或修改这些文件前，必须先向
> 用户说明要改什么、为什么改，并获得明确同意，绝不能静默改配置**。这条不因为
> "只是加一个 hook"而放宽。

## 两平台机制差异

| | Claude Code | Codex |
|---|---|---|
| 触发点 | `SessionEnd` hook，**会话结束**时触发一次 | `notify` 机制，**每个回合(turn)结束**都触发 |
| 配置文件 | `.claude/settings.json`（项目级）或 `~/.claude/settings.json`（全局） | `~/.codex/config.toml`（或项目级 `.codex/config.toml`） |
| 能挂几条命令 | `hooks.SessionEnd` 是数组，可以并存多条 | `notify` 只能配置**一条**命令 |
| 去重需求 | 天然一次会话一条快照，不需要额外节流 | 一次会话可能触发几十次，必须靠脚本节流合并，否则日志刷屏 |

`session_end_log.sh` 已经内置节流（按 `git status --porcelain` 内容算 md5，
和 `<vault>/.git/soia-session-log-<agent>.state` 里的上次值一致就直接退出），
两个平台共用同一个脚本，只是 `--agent` 传值不同。

## Claude Code 接入

**步骤**：

1. 先确认用户的 vault 绝对路径、想挂项目级还是全局级 `settings.json`。
2. 读现有 `settings.json`：
   - 没有 `hooks.SessionEnd` → 直接加这个键。
   - 已有 `hooks.SessionEnd` → **在现有数组里追加一个 entry，不要整体覆盖文件**
     （其他 hook 可能是别的 skill 或用户手动配的，覆盖会把它们删掉）。
3. 写入前把改动内容（diff 或最终 JSON）给用户看一遍，确认后再落盘。

**hook 片段示例**：

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"~/.claude/skills/soia-pkm-maintain/scripts/session_end_log.sh\" --agent Claude-Code --vault \"<vault绝对路径>\"",
            "async": true,
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

- `command` 里的 skill 路径按实际同步到的目录改（`~/.claude/skills/...`
  或项目内 `.claude/skills/...`），`--vault` 换成用户 vault 的绝对路径。
- `async: true` + `timeout: 30`：不阻塞会话结束流程，30 秒内跑不完就放弃。
- 如果同一个 `settings.json` 已经有别的 `SessionEnd` entry，新增一个数组元素即可，
  不要合并进已有 entry 的 `hooks` 数组里（保持每个 entry 职责独立，方便单独增删）。

**回滚**：把这个 entry 从 `hooks.SessionEnd` 数组里删掉即可，不影响其他 hook。

## Codex 接入

Codex 的 `notify` 字段在 `config.toml` 里长这样（真实取值可能不同）：

```toml
notify = ["/path/to/some-notify-program", "turn-ended"]
```

Codex 在**每个回合结束**时调用这条命令，并把描述事件的 JSON 作为额外参数追加在
后面。因为只能配置一条命令，如果用户已经有 notify 用途（比如接了某个
computer-use 客户端做提醒），不能直接覆盖，要用 `scripts/codex_notify_wrapper.sh`
做一层包装：先原样调用用户原来的命令，再触发日志脚本。

**步骤**：

1. 读用户现有 `config.toml` 里的 `notify = [...]`，记下原命令（程序路径 + 固定参数）。
   如果用户原本没有配置 `notify`，`ORIGINAL_NOTIFY_CMD` 留空数组即可。
2. 不要修改 `codex_notify_wrapper.sh` 写死个人路径；vault 通过 `--vault` 或私有 env 文件里的 `OBSIDIAN_VAULT` 传入。
3. 把 `config.toml` 的 `notify` 改成只指向 wrapper：
   ```toml
   notify = ["/绝对路径/soia-pkm-maintain/scripts/codex_notify_wrapper.sh", "--vault", "<vault绝对路径>"]
   ```
   如果原来已有 notify 且必须保留，用 `--original-count N --` 把原命令固定参数放在后面，例如：
   ```toml
   notify = ["/绝对路径/codex_notify_wrapper.sh", "--vault", "<vault绝对路径>", "--original-count", "2", "--", "/old/program", "turn-ended"]
   ```
   `N` 是原 notify 固定参数数量；Codex 追加的事件 JSON 会被 wrapper 转发给原命令。
4. 改动前，把"要动哪个文件、改成什么样、原 notify 会不会丢功能"讲清楚，
   等用户确认再落盘。

**因为是回合级触发**：`session_end_log.sh` 的节流会保证同一份未提交改动只落一条
快照，不会因为 Codex 一次会话触发几十次而刷屏。

**回滚**：把 `config.toml` 的 `notify` 改回原值即可；`codex_notify_wrapper.sh`
本身不用删，留着但不被 `config.toml` 引用就不会生效。

## 卸载

- Claude Code：删除 `hooks.SessionEnd` 数组里对应的 entry。
- Codex：把 `notify` 改回原命令（或删除该字段）。
- 两者都可选删掉节流状态文件 `<vault>/.git/soia-session-log-<agent>.state`
  （不删也无害，下次没有这个文件会重新生成）。
