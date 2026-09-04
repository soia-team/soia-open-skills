#!/usr/bin/env python3
"""从各域仓的 SKILL.md 派生面向人的技能页 docs/skills/<名>.md。

**为什么在门户仓而不是技能目录里**：`SKILL_SPEC.md` 明文禁止 per-skill README
（"No documentation clutter … do not add per-skill README"），理由是避免同一份
清单散进多个文件。这条规则本身是对的——所以技能页放在门户仓的 docs/ 下，
技能目录一个字都不动。

**为什么派生而不是另写**：每个 SKILL.md 已经有「客户可读说明」一节，那本来就是
写给人看的。另写 74 份等于制造第二份真源，改技能时必然漂移。这里只搬运不创作，
`--check` 进 CI，SKILL.md 改了而页没重生成就变红。

数据来源与 generate_router_index.py 一致：默认从 GitHub main 抓取，
`--repos-root` 可指向本地各域仓工作副本，便于合并前预览。

    python3 scripts/generate_skill_pages.py                    # 从 GitHub 生成
    python3 scripts/generate_skill_pages.py --repos-root ..     # 从本地工作副本生成
    python3 scripts/generate_skill_pages.py --check             # CI 校验
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

OWNER = "soia-team"

# 元仓自己的技能读本地工作树，不走 GitHub main。
#
# 原因：新增元仓技能时 routing 已登记、但 main 上还没有（要等下次发版才上去），
# 从 main 抓必然 404，形成自举死锁。同仓的 catalog / expert manifest / README
# 覆盖检查本来就读本地——统一到同一个源才自洽。域仓仍读 main：它们的内容由
# 各自发版决定，本地检出可能停在 dev。
PORTAL_REPOSITORY = "soia-open-skills"
PORTAL_ROOT = pathlib.Path(__file__).resolve().parents[1]


def portal_skill_md(skill_path: str) -> str:
    path = PORTAL_ROOT / skill_path / "SKILL.md"
    if not path.is_file():
        raise RuntimeError(f"portal skill not found: {path}")
    return path.read_text(encoding="utf-8")


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "routing/routing-manifest.json"
OUTPUT_DIR = REPO_ROOT / "docs/skills"

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)
TRIGGER_SPLIT = re.compile(r"触发[词]?[：:]|Triggers?[：:]")

# 域仓 → 插件名。README 的安装命令要用插件名，不是仓名。
REPO_TO_PLUGIN = {
    "soia-open-dev-skills": "soia-dev",
    "soia-open-dev-design-skills": "soia-dev-design",
    "soia-open-pkm-vault-skills": "soia-pkm-vault",
    "soia-open-media-content-skills": "soia-media-content",
    "soia-open-cwork-office-skills": "soia-cwork-office",
    "soia-open-edu-course-skills": "soia-edu-course",
    "soia-open-env-skills": "soia-env",
    "soia-open-skills": "soia-meta",
}

# 「客户可读说明」里这几节是给 Agent 或维护者的执行约定，不该进面向读者的页面；
# 「依赖与安装」与本页自带的安装节重复。
#
# 用前缀匹配而非精确匹配：实际标题有变体，例如
# 「私密信息与中间数据：文件放在哪里」「私有配置加载与命令入口」。
# 精确匹配会漏掉它们——测试就是这么抓到的。
INTERNAL_PREFIXES = ("依赖与安装", "日志与完成回执", "私密信息与中间数据",
                     "客户可见日志与总结", "私有配置")
INTERNAL_SUBSECTIONS = re.compile(
    r"^### (?:" + "|".join(re.escape(p) for p in INTERNAL_PREFIXES) + r")[^\n]*\n.*?(?=^### |\Z)",
    re.S | re.M,
)


def fetch_skill_md(repo: str, skill_path: str) -> str:
    if repo == PORTAL_REPOSITORY:
        return portal_skill_md(skill_path)
    command = [
        "gh", "api", "-H", "Accept: application/vnd.github.raw+json",
        f"repos/{OWNER}/{repo}/contents/{skill_path}/SKILL.md?ref=main",
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown gh error"
        raise RuntimeError(f"failed to fetch {repo}/{skill_path}/SKILL.md: {detail}")
    return result.stdout


def local_skill_md(root: pathlib.Path, repo: str, skill_path: str) -> str:
    path = root / repo / skill_path / "SKILL.md"
    if not path.exists():
        raise RuntimeError(f"not found: {path}")
    return path.read_text(encoding="utf-8")


def parse(text: str) -> dict[str, str]:
    fm = FRONTMATTER.match(text)
    block = fm.group(1) if fm else ""
    desc = re.search(r"^description:\s*(.+?)(?=\n[a-z_]+:|\Z)", block, re.M | re.S)
    raw = " ".join((desc.group(1) if desc else "").split())
    parts = TRIGGER_SPLIT.split(raw, maxsplit=1)
    body = text[fm.end():] if fm else text
    section = re.search(r"^## 客户可读说明\n(.*?)(?=^## (?!客户可读说明))", body, re.S | re.M)
    customer = INTERNAL_SUBSECTIONS.sub("", section.group(1).strip()).strip() if section else ""
    return {
        "duty": parts[0].strip().rstrip("；;，,。"),
        "triggers": parts[1].strip() if len(parts) > 1 else "",
        "customer": customer,
    }


def render(name: str, repo: str, skill: dict[str, str]) -> str:
    plugin = REPO_TO_PLUGIN[repo]
    install_guidance = [
        "安装前先确认项目/全局、目标 Agent 与单技能/整域/全量；范围不清先询问。"
        "默认是当前项目、明确 Agent、单个技能：\n",
        "```bash\n"
        f"npx skills add {OWNER}/{repo} -a <agent> -s {name} -y\n"
        "```\n",
        "客户明确选择全局时再加 `-g`；明确选择全部 Agent 时才把 `<agent>` 换成 `'*'`。\n",
    ]
    out = [
        f"# {name}\n",
        f"> {skill['duty']}\n",
        f"所属：[`{plugin}`](https://github.com/{OWNER}/{repo}) · "
        f"[技能源码](https://github.com/{OWNER}/{repo}/tree/main/skills/{name}) · "
        f"[← 全部技能](README.md)\n",
    ]
    if skill["triggers"]:
        out += ["## 怎么触发\n",
                "装好后用自然语言说话即可，Agent 按下列意图命中本技能：\n",
                f"{skill['triggers']}\n"]
    if skill["customer"]:
        # 派生内容以 ### 开头，必须有 h2 承接，否则 h1 → h3 目录层级断裂。
        # 缺触发词的技能没有前置 h2，这个承接就是唯一的那一个。
        out.append("## 能力与用法\n")
        out.append(skill["customer"] + "\n")
    out += [
        "## 安装\n",
        f"客户明确选择安装整个 `{plugin}` 领域插件时：\n",
        "```bash\n"
        f"claude plugin marketplace add {OWNER}/soia-open-skills && claude plugin install {plugin}@soia\n"
        "```\n",
        "```bash\n"
        f"codex plugin marketplace add {OWNER}/soia-open-skills && codex plugin add {plugin}@soia\n"
        "```\n",
        "客户选择 WorkBuddy 时由技能代劳——对 AI 说「装到 WorkBuddy」即可。\n",
        *install_guidance,
        "---\n",
        "本页由 `scripts/generate_skill_pages.py` 从该技能的 `SKILL.md` 派生，"
        "请勿手改——改 `SKILL.md` 后重跑生成器。\n",
    ]
    return "\n".join(out)


def render_index(pages: list[tuple[str, str, str]]) -> str:
    """pages: (name, repo, duty)，按仓分组。"""
    out = [
        "# 技能详情页\n",
        f"全生态 {len(pages)} 个公开技能，每个一页：触发词、产物、用法示例与安装命令。\n",
        "内容从各技能的 `SKILL.md` 派生，改技能后由 CI 校验是否同步。\n",
        "[← 返回门户](../../README.md)\n",
    ]
    by_repo: dict[str, list[tuple[str, str]]] = {}
    for name, repo, duty in pages:
        by_repo.setdefault(repo, []).append((name, duty))
    for repo in sorted(by_repo, key=lambda r: -len(by_repo[r])):
        plugin = REPO_TO_PLUGIN[repo]
        items = sorted(by_repo[repo])
        out.append(f"## `{plugin}`　{len(items)} 个技能\n")
        out.append("| 技能 | 一句话职责 |\n|---|---|")
        out += [f"| [`{n}`]({n}.md) | {d} |" for n, d in items]
        out.append("")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="只比对不写，CI 用")
    parser.add_argument("--repos-root", type=pathlib.Path,
                        help="从本地各域仓工作副本读取，缺省从 GitHub main 抓")
    parser.add_argument("--jobs", type=int, default=12)
    args = parser.parse_args(argv)

    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    # routing-manifest 刻意排除 soia-meta-find-skill——路由器不是自己的路由目标。
    # 但它是一个公开技能，详情页该有，这里补回来。
    if not any(e["skill_name"] == "soia-meta-find-skill" for e in entries):
        entries.append({"skill_name": "soia-meta-find-skill",
                        "repo": "soia-open-skills",
                        "skillPath": "skills/soia-meta-find-skill"})
    fetch = ((lambda r, p: local_skill_md(args.repos_root.resolve(), r, p))
             if args.repos_root else fetch_skill_md)

    results: dict[str, tuple[str, dict[str, str]]] = {}
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(fetch, e["repo"], e["skillPath"]): e for e in entries}
        for fut in as_completed(futures):
            e = futures[fut]
            results[e["skill_name"]] = (e["repo"], parse(fut.result()))

    pages = {f"{n}.md": render(n, repo, s) for n, (repo, s) in results.items()}
    index = [(n, repo, s["duty"]) for n, (repo, s) in results.items()]
    pages["README.md"] = render_index(index)

    if args.check:
        drift = [n for n, c in sorted(pages.items())
                 if not (OUTPUT_DIR / n).exists()
                 or (OUTPUT_DIR / n).read_text(encoding="utf-8") != c]
        stale = ([p.name for p in OUTPUT_DIR.iterdir() if p.name not in pages]
                 if OUTPUT_DIR.exists() else [])
        if drift or stale:
            print("❌ 技能详情页与 SKILL.md 不一致，请重跑 generate_skill_pages.py：")
            for n in drift:
                print(f"   过期或缺失: {n}")
            for n in stale:
                print(f"   多余（技能已删？）: {n}")
            return 1
        print(f"skill pages are current ({len(results)} skills)")
        return 0

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)
    for n, c in pages.items():
        (OUTPUT_DIR / n).write_text(c, encoding="utf-8")
    print(f"  ✓ docs/skills/：{len(results)} 个技能页 + 索引")
    return 0


if __name__ == "__main__":
    sys.exit(main())
