# Contributing to soia-open-skills

## 加新 skill 的步骤

1. **Fork** 这个仓库

2. **先读技能规范**：[SKILL_SPEC.md](./SKILL_SPEC.md)。所有 public skill 必须遵守其中的路径、配置、secret、个人信息和验证口径约束。

3. **从模板复制一个新目录**，命名用小写连字符（如 `notion-to-obsidian`）：

   ```bash
   cp -R templates/skill-template skills/your-skill-name
   mv skills/your-skill-name/SKILL.md.template skills/your-skill-name/SKILL.md
   ```

4. **写 SKILL.md**，frontmatter 必须有：

   ```yaml
   ---
   name: your-skill-name
   description: 一句话说明 skill 干什么 + 触发词清单（控制在 200 字符内）
   ---
   ```

   frontmatter 只放 `name` 和 `description`，不要新增 `version` 等字段。
   不要新增 `metadata.json`；公开仓使用 `SKILL.md` + 可选 `agents/openai.yaml`。

5. **路径参数化**：
   - 严禁硬编码 `/Users/xxx`、`/home/xxx` 等本地路径
   - 严禁把维护者自己的 vault 子目录当作公共默认值（如某个中文 PARA 目录）
   - 用环境变量（如 `OBSIDIAN_VAULT`）+ 命令行 `--vault` 参数
   - 提供清晰的错误提示（"please set OBSIDIAN_VAULT or use --vault"）

6. **不要 commit 任何 secret**：
   - 不 commit `.env`
   - 不 commit `*.session`
   - 不在代码里写真实 API key / token / 密码
   - 文档里举例用 `<YOUR_KEY>` 占位符

7. **同步公共说明**：
   - 新增 skill 或新增 domain 时，更新根目录 `README.md` 和 `README.en.md` 的简介、目录、安装/配置入口和触发示例。
   - `skills/README.md` 是生成文件，不要手工编辑；运行 `python3 scripts/generate_skill_catalog.py` 更新它。
   - 如果 skill 有机器可读配置和人类说明，保持 YAML/JSON 事实源与 Markdown 说明的链接一致，避免维护两份权限或字段清单。

8. **测试**：
   - 至少给出 1 个端到端用例
   - 文档里说明如何手动验证
   - 区分「静态检查通过」「已安装」「端到端测试通过」「已提交」，不要混用
   - 提交前运行：

     ```bash
     python3 scripts/audit_skills.py
     git diff --check
     ```

9. **提 PR**，说明：
   - 这个 skill 解决什么问题
   - 触发词是什么
   - 与其他 skill 的关系

## 改 bug / 改进体验

直接提 PR，关联 issue 编号。无需事先沟通。

## 行为准则

- 中文 / 英文都欢迎
- 不接受打广告、写垃圾内容
- 尊重原作者（如果借鉴了别人的 skill，明确标注）

## 联系

提 issue 或直接邮件 soia-team@xxx
