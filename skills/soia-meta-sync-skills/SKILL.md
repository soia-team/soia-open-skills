---
name: soia-meta-sync-skills
description: 按明确范围把共享技能目录软链到项目或宿主，写入前先 dry-run。触发：技能同步、同步预览、把技能链到项目
version: 2.4.2
created_at: 2026-07-07 14:44:10
updated_at: 2026-09-30 13:14:57
created_by: claude opus 4.6
updated_by: claude opus 5.5
---

# soia-meta-sync-skills

范围先行：默认不选全局、全宿主或全量。项目模式只写 `<project>/.agents/skills`；全局宿主目录只在客户显式给出 `--scope global` 与 `--targets` 后处理。

## 客户可读说明

### 这个技能可以做什么

把一个已安装或本地的共享技能目录同步到客户选择的 AI 工具目录：只创建或替换同名软链接，清理已退役名称，并默认清理悬空的 `soia-*` 软链。先用 `--dry-run` 展示影响，有明确授权再写入。

### 客户如何使用

提供源目录、`--scope`、目标粒度和技能范围；缺 `--scope`、`--target-kind` 或项目 Agent 选择时脚本只返回 `selection_required`，不写入。

```bash
python3 skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir <shared-skill-dir> \
  --scope project --project-dir <project> --agents codex \
  --target-kind skill --skills <skill-name> \
  --dry-run
```

`skill`、`domain`、`all` 都支持，默认不全量。`--skills '*'` / `--targets '*'` 须显式选 `all` 并先 dry-run，全宿主写入还需 `--confirm-all-targets`。`--skills` 单技能同步会带上其 hard dependencies（`--no-deps` 关闭）。`--exclude-skills a,b` 在本次对每个选中 target 跳过并摘除这些技能的既有软链，加 `--save-excludes` 才持久化到私有配置；target 中同名的真实文件或目录保留并在日志报告。`--list-targets` / `--list-skills` 查看内置目标与源中技能。

### 依赖与安装

依赖 Python 3 标准库和一个含 `SKILL.md` 子目录的源目录。

整域：`claude plugin marketplace add soia-team/soia-open-skills` 后 `claude plugin install soia-meta@soia`。只要这一个技能时用 `npx skills add soia-team/soia-open-skills -a <explicit-agent> -s soia-meta-sync-skills -y`；它落进共享真源 `~/.agents/skills`，与插件同装会出现两份各自漂移的索引，二选一。WorkBuddy 以角色化专家装载，全宿主选择也不覆盖它，见 [docs/install/workbuddy.md](https://github.com/soia-team/soia-open-skills/blob/main/docs/install/workbuddy.md)。

可选私有配置 `~/.config/soia-skills/soia-meta-sync-skills/config.yml`（或 `SOIA_META_SYNC_SKILLS_CONFIG_FILE`，模板 `assets/config.example.yml`）记录 source/targets 与按 target 隔离的 excludes，命令行参数优先，不替代本轮范围选择：

```yaml
schema_version: 3
excludes:
  codex:
    - "soia-example-skill"
  claude: []
```

### 私密信息与中间数据

- 配置只存 source/targets 与 per-target excludes，不存 API key、cookie、session 或其他凭据。
- 计划默认只打印到终端；实际写入的脱敏审计日志在 `${XDG_STATE_HOME:-~/.local/state}/soia-meta-sync-skills/`，最多保留 20 个，记录参数、链接变更与汇总，不含密钥。

### 日志与完成回执

```markdown
完成：<dry-run 或实际同步结果>。

日志摘要：
- source: <共享技能源>
- targets: <目标目录>
- linked/removed: <数量与名称>
- skipped/failed: <原因或无>

验证：<命令退出码、软链接解析或 dry-run>
问题与下一步：<确认、缺依赖或无>
```

## 安全边界

- 先 dry-run 展示 source、目标与将创建/替换/删除的链接；没有本轮明确写入授权就停在预览。选择字段齐全不构成写入批准：已展示影响并获明确批准、且含 source、具体 target、action 与删除/替换影响的完整计划，才可写入或由 find-skill、installer、release 传来直接执行；扩大目标、宿主、粒度、source 或删除/替换范围时重新确认。
- 拒绝把 source 自身作为目标；只建软链，不复制目录。
- 只处理 `soia-*` 管理名与当前点名的技能，不删无关第三方技能；悬空 `soia-*` 软链默认清理，`--no-prune` 保留。
- 源目录、目标与技能范围不猜个人目录或产品 workspace。授权后执行与 dry-run 相同的命令（去掉 `--dry-run`），再核对退出码与每个目标的软链解析结果，只报实际执行的验证。

## 参考

- `references/targets-and-confirmation.md`：内置目标与确认规则。
- `references/source-rules.md`：本地、GitHub 与 skillsmp 源的解析规则。
- `references/soia-managed-skills.md`：受限清理的命名边界。

## 维护本技能时的验证

```bash
python3 skills/soia-meta-sync-skills/scripts/sync_soia_skills.py --list-targets
python3 -m py_compile skills/soia-meta-sync-skills/scripts/sync_soia_skills.py
```

在临时目录建一个只含 `SKILL.md` 的测试技能，对另一个临时项目跑 `--scope project --target-kind skill --dry-run`，验收输出含预期 create/link 计划且目标未被写入；在明确授权的测试目录跑一次非 dry-run，用 `readlink` 验证链接指向源；再以 `global + all` 做 dry-run，确认没有 `--confirm-all-targets` 时实际写入被拒绝。
