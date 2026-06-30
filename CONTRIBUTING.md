# Contributing to soia-open-skills

## 加新 skill 的步骤

1. **Fork** 这个仓库

2. **在 `skills/` 下建一个新目录**，命名用小写连字符（如 `notion-to-obsidian`）：

   ```
   skills/your-skill-name/
   ├── SKILL.md       ← 必须，skill 入口
   └── scripts/       ← 可选，相关脚本
       └── *.py
   ```

3. **写 SKILL.md**，frontmatter 必须有：

   ```yaml
   ---
   name: your-skill-name
   description: 一句话说明 skill 干什么 + 触发词清单（控制在 200 字符内）
   ---
   ```

4. **路径参数化**：
   - 严禁硬编码 `/Users/xxx`、`/home/xxx` 等本地路径
   - 用环境变量（如 `OBSIDIAN_VAULT`）+ 命令行 `--vault` 参数
   - 提供清晰的错误提示（"please set OBSIDIAN_VAULT or use --vault"）

5. **不要 commit 任何 secret**：
   - 不 commit `.env`
   - 不 commit `*.session`
   - 不在代码里写真实 API key / token / 密码
   - 文档里举例用 `<YOUR_KEY>` 占位符

6. **测试**：
   - 至少给出 1 个端到端用例
   - 文档里说明如何手动验证

7. **提 PR**，说明：
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
