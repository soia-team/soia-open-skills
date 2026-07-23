# SOIA Open Skills Catalog

> Generated from `skills/*/SKILL.md` and optional `agents/openai.yaml`.
> Do not edit by hand. Run `python3 scripts/generate_skill_catalog.py`.
> Discoverable by `npx skills add soia-team/soia-open-skills -l`: 4 skills.

## Source Fields

- `SKILL.md` is the canonical cross-agent instruction file. Capabilities, dependencies, setup, workflow steps, logs, and completion summaries must live there.
- `agents/openai.yaml` is optional UI/catalog metadata for OpenAI/Codex-style surfaces and SOIA registry display: `display_name`, `short_description`, and `default_prompt`.
- Claude Code and generic skills.sh-compatible agents must be assumed to consume `SKILL.md`; do not put required workflow steps only in `agents/openai.yaml`.
- Legacy `metadata.json` files are not used to generate this catalog.

## Meta

| Skill | Description | Default Prompt |
|---|---|---|
| [`soia-meta-find-skill`](./soia-meta-find-skill/) | 按自然语言需求检索、定位并加载 SOIA 全生态技能。 | Use $soia-meta-find-skill to find and load the best SOIA skill for my request. |
| [`soia-meta-prompt-clarity`](./soia-meta-prompt-clarity/) | 中英文提示词编写、诊断、防误伤改写与可验证规格化 | Use $soia-meta-prompt-clarity to turn my request into a clear, directly usable prompt; preserve my chosen prompt and explanation languages, and use a named framework only when it materially improves the result. |
| [`soia-meta-skill-release`](./soia-meta-skill-release/) | 完成 merge 后技能的本机安装、软链、lock 与版本发布收尾。 | Use $soia-meta-skill-release to finish local release cleanup for merged skill names from an owner/name repository. |
| [`soia-meta-sync-skills`](./soia-meta-sync-skills/) | 将共享技能目录以软链接同步到用户选择的 AI 工具目录。 | Use $soia-meta-sync-skills to preview and sync a shared skill source to explicitly selected AI tool directories. |

## Registry Export

Generate v7 SOIA registry manifests from the same sources when needed:

```bash
python3 scripts/generate_skill_catalog.py --registry-out <soia-repo>/runtime/registry/skills
```
