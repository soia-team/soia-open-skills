---
name: soia-meta-sync-skills
description: 将一个共享技能源以软链接同步到用户明确选择的 AI 工具目录；支持预览、单项同步、硬依赖闭包和受限清理。
version: 2.2.0
created_at: 2026-07-07 14:44:10
updated_at: 2026-07-23 10:23:03
created_by: claude opus 4.6
updated_by: gpt-5.6-luna
---

# soia-meta-sync-skills

## 客户可读说明

### 这个技能可以做什么

将一个已安装或本地的共享技能目录同步到用户选择的 AI 工具目录。它只创建或替换同名的软链接；先用 `--dry-run` 展示影响，再在已有明确授权时写入。

### 客户如何使用

提供源目录、目标 id 或路径，以及可选的单项技能名。目标由 `--targets` 显式提供；没有适合的内置 id 时使用绝对路径。

```bash
python3 skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir <shared-skill-dir> \
  --targets codex,claude \
  --dry-run
```

确认计划后移除 `--dry-run`。使用 `--skills <name>` 只同步指定技能，默认会把其 frontmatter 中的 `dependencies.hard` 一并纳入；`--no-deps` 可关闭该行为。使用 `--exclude-skills a,b` 可在本次运行中对每个选中 target 跳过并摘除这些技能的既有软链。

### 依赖与安装

```bash
npx skills add soia-team/soia-open-skills -g -a '*' -s soia-meta-sync-skills -y
```

依赖 Python 3 标准库和一个包含 `SKILL.md` 子目录的源目录。可选配置示例在 `config.example.yml`：它记录用户自己的默认 source/targets 和按 target 隔离的 excludes，命令行参数优先。脚本每次同步（包括默认全量同步）都会读取并遵守持久排除。配置文件放在：

```text
~/.config/soia-skills/soia-meta-sync-skills/config.yml
SOIA_META_SYNC_SKILLS_CONFIG_FILE=<custom-config-path>
```

### 私密信息与中间数据

- 配置只保存客户选择的 source/targets 和 per-target excludes，不保存 API key、cookie、session 或其他凭据。
- 同步计划默认只打印到终端；实际写入的脱敏审计日志按“输出文件”约定轮转，且不记录密钥内容。

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

- 先展示 source、目标、将创建/替换/删除的链接；没有本轮明确写入授权时停在预览。
- 拒绝把 source 自身作为目标；不复制目录。
- 只处理 `soia-*` 管理名和当前点名技能；绝不删除无关第三方技能。
- 默认清理指向不存在目标的一级 `soia-*` 软链接；用 `--no-prune` 保留它们。

## 工作流

1. 确认 `--source-dir`、目标和技能范围；不要猜测个人目录或产品 workspace。
2. 合并配置中的 per-target excludes 与本次 `--exclude-skills`，运行 `--dry-run`，复核每个目标的 create/replace/remove/unlink 计划。
3. 得到授权后执行同一命令（不带 `--dry-run`）。
4. 复核退出码及每个目标的软链接解析结果；仅报告实际执行的验证。

常用命令：

```bash
# 查看内置目标或共享源中的技能
python3 skills/soia-meta-sync-skills/scripts/sync_soia_skills.py --list-targets
python3 skills/soia-meta-sync-skills/scripts/sync_soia_skills.py --source-dir <shared-skill-dir> --list-skills

# 同步一个技能并包含其 hard dependencies
python3 skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir <shared-skill-dir> --targets <target-id-or-path> --skills <skill-name> --dry-run

# 本次排除并摘除既有软链（不持久化）
python3 skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir <shared-skill-dir> --targets codex,claude \
  --exclude-skills <skill-a>,<skill-b> --dry-run

# 确认后持久化到各 target；后续默认全量同步仍会尊重这些排除
python3 skills/soia-meta-sync-skills/scripts/sync_soia_skills.py \
  --source-dir <shared-skill-dir> --targets codex,claude \
  --exclude-skills <skill-a>,<skill-b> --save-excludes
```

私有配置中的持久排除结构：

```yaml
schema_version: 3
excludes:
  codex:
    - "soia-example-skill"
  claude: []
```

排除只会删除同名软链；若 target 中存在同名真实文件或目录，脚本保留并在日志中报告。

## 输出文件

审计日志写到 `${XDG_STATE_HOME:-~/.local/state}/soia-meta-sync-skills/`，最多保留 20 个。它记录参数、链接变更和汇总，不写入密钥内容。

## 参考

- `references/targets-and-confirmation.md`：内置目标和确认规则。
- `references/source-rules.md`：本地、GitHub 与 skillsmp 源的解析规则。
- `references/soia-managed-skills.md`：受限清理的命名边界。

## 验证

```bash
python3 skills/soia-meta-sync-skills/scripts/sync_soia_skills.py --list-targets
python3 -m py_compile skills/soia-meta-sync-skills/scripts/sync_soia_skills.py
```

在临时目录创建一个只含 `SKILL.md` 的测试技能，并对另一个临时目标运行 `--dry-run`；验收输出包含预期的 create/link 计划且目标目录未被写入。再在明确授权的测试目录运行一次非 dry-run，并用 `readlink` 验证链接指向源目录。最后为一个 target 保存 exclude 并执行默认全量同步，验收该 target 的软链保持摘除、其他 target 的同名软链不受影响。
