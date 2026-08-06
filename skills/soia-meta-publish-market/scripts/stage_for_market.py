#!/usr/bin/env python3
"""把仓内技能打包成可上架外部市场的形态。

外部市场（SkillHub、小红书 Red Skill）一次只收一个技能，且拿到的人不会同时
装我们仓里的同伴技能。因此上架要做两件仓内不需要的事：

1. **筛掉有 hard 依赖的技能**——它们在市场上是断链的：用户装了也跑不起来，
   因为强依赖的同伴技能不在那边。optional 依赖只在描述里提一句「装了更好」。
2. **叠加平台 frontmatter**——SkillHub 要求 `slug`/`displayName`/`summary`/
   `license`，我们仓内的 frontmatter 没有这几个字段。

命名策略（2026-08-04 用户裁决）：`slug` 直接用仓内技能名（已带 `soia-` 前缀，
天然全网唯一，且与仓内一一对应便于追溯）；`displayName` 用中文可读名。

用法：
    python3 stage_for_market.py --repo-dir <域仓> --skill <技能名> --out <暂存目录>
    python3 stage_for_market.py --repo-dir <域仓> --list-eligible
"""

from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import sys

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
LICENSE_DEFAULT = "MIT"

# Red Skill 的文件白名单（网页上传提示 + CLI 本地校验实测一致）。
# 实测 2026-08-05：带 agents/openai.yaml 直接被拒
# 「目录中包含不支持上传的文件：agents/openai.yaml，请移除后重试」。
# SkillHub 无此限制（同一份目录 dry-run 通过），所以过滤按渠道区分。
REDSKILL_ALLOWED_SUFFIXES = {
    ".md", ".txt", ".html", ".css", ".js", ".py", ".json", ".xml",
}
CHANNELS = ("skillhub", "redskill")

# Red Skill 的展示名不能落到仓内技能名上。
# 实测 2026-08-06：`name` 取 frontmatter 的 `soia-env-network-diagnose`（25 字符）
# 被平台以 `SUBMIT_REJECTED: 名称长度不符合要求` 拒收；改成「网络诊断助手」后通过。
# 官方 uploader 的取值优先级是 `flags.name || metadata.name || identifier`
# （submit.mjs），所以正确做法是投递时传 `--name`，**不动仓内 frontmatter**——
# 改 frontmatter 会连带影响 identifier 派生和仓内技能身份。
# 平台的具体长度上限未公开，我们只知道 25 被拒、6 通过；因此不猜阈值，
# 改为「redskill 渠道必须显式给出 --display-name」这条确定性约束。
REDSKILL_UPLOADER = (
    'node "$(npm root -g)/@xhs/skillhub-upload/cli/index.mjs" publish'
)


def strip_unsupported(target: pathlib.Path) -> list[str]:
    """删掉目标渠道不接受的文件，返回被删清单。"""
    removed = []
    for path in sorted(target.rglob("*")):
        if path.is_file() and path.suffix.lower() not in REDSKILL_ALLOWED_SUFFIXES:
            removed.append(str(path.relative_to(target)))
            path.unlink()
    for path in sorted(target.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    return removed


def read_frontmatter(skill_md: pathlib.Path) -> tuple[str, str]:
    """返回 (frontmatter 文本, 正文)；缺少 frontmatter 时抛错。"""
    text = skill_md.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"{skill_md} 缺少 frontmatter")
    return match.group(1), text[match.end():]


def field(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"^{key}:\s*(.+?)\s*$", frontmatter, re.M)
    return match.group(1) if match else None


def has_hard_dependency(frontmatter: str) -> bool:
    """技能是否声明了 hard 依赖（上架后会断链）。"""
    match = re.search(r"^\s*hard:\s*\[(.*?)\]", frontmatter, re.M)
    return bool(match and match.group(1).strip())


def export_from_main(repo_dir: pathlib.Path, skill_name: str,
                     dest: pathlib.Path) -> str:
    """把 `origin/main` 上的技能导出到 dest，返回该仓 main 的插件版本号。

    **只从 main 取，不读工作树**（2026-08-05 用户定的硬规矩：只有正式版能上市场）。
    直接导出比「校验工作树是否等于 main」更强：本地检出在哪个分支都不影响结果，
    也就不会因为有人切走分支而误打包未发布内容——多 AI 共用检出时这是常态。
    """
    import subprocess
    import tarfile
    import io
    import json as _json

    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(repo_dir), *args],
                              capture_output=True)

    if git("fetch", "origin", "+refs/heads/main:refs/remotes/origin/main").returncode != 0:
        raise ValueError(f"{repo_dir} 取不到 origin/main，无法确认正式版内容")

    manifest = git("show", "origin/main:.claude-plugin/plugin.json")
    if manifest.returncode != 0:
        raise ValueError(f"{repo_dir} 的 main 上读不到 .claude-plugin/plugin.json")
    version = _json.loads(manifest.stdout.decode("utf-8")).get("version", "")
    if "-SNAPSHOT" in version:
        raise ValueError(
            f"{repo_dir.name} 的 main 版本是 {version}，带 -SNAPSHOT 不是正式版")

    archive = git("archive", "origin/main", f"skills/{skill_name}")
    if archive.returncode != 0:
        raise ValueError(
            f"origin/main 上没有 skills/{skill_name}——该技能尚未发版，不能上架")

    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        for member in tar.getmembers():
            prefix = f"skills/{skill_name}/"
            if not member.name.startswith(prefix):
                continue
            member.name = member.name[len(prefix):]
            if member.name:
                tar.extract(member, dest, filter="data")
    return version


def eligible_skills(repo_dir: pathlib.Path) -> list[tuple[str, bool, str]]:
    """列出 (技能名, 是否可上架, 原因)。"""
    rows = []
    skills_dir = repo_dir / "skills"
    for skill in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        md = skill / "SKILL.md"
        if not md.is_file():
            continue
        try:
            frontmatter, _ = read_frontmatter(md)
        except ValueError as exc:
            rows.append((skill.name, False, str(exc)))
            continue
        if has_hard_dependency(frontmatter):
            hard = re.search(r"^\s*hard:\s*\[(.*?)\]", frontmatter, re.M).group(1)
            rows.append((skill.name, False, f"有 hard 依赖：{hard}"))
        else:
            rows.append((skill.name, True, "可独立运行"))
    return rows


def stage(repo_dir: pathlib.Path, skill_name: str, out_dir: pathlib.Path,
          display_name: str | None = None, summary: str | None = None,
          license_id: str = LICENSE_DEFAULT,
          allow_unreleased: bool = False,
          channel: str = "skillhub") -> pathlib.Path:
    """把一个技能复制到暂存目录并叠加平台 frontmatter。"""
    target = out_dir / skill_name
    if target.exists():
        shutil.rmtree(target)

    if allow_unreleased:
        src = repo_dir / "skills" / skill_name
        if not (src / "SKILL.md").is_file():
            raise ValueError(f"找不到技能：{src}")
        shutil.copytree(src, target)
        released_version = "(未发版，仅本地演练)"
    else:
        released_version = export_from_main(repo_dir, skill_name, target)

    frontmatter, body = read_frontmatter(target / "SKILL.md")
    if has_hard_dependency(frontmatter):
        shutil.rmtree(target, ignore_errors=True)
        raise ValueError(
            f"{skill_name} 声明了 hard 依赖，上架后会断链；"
            f"先去掉依赖或改为 optional 再上架")

    overlay = [
        f"slug: {skill_name}",
        f"displayName: {display_name or field(frontmatter, 'name') or skill_name}",
        f"summary: {summary or field(frontmatter, 'description') or ''}",
        f"license: {license_id}",
    ]
    (target / "SKILL.md").write_text(
        "---\n" + "\n".join(overlay) + "\n" + frontmatter + "\n---\n" + body,
        encoding="utf-8")

    if channel == "redskill":
        removed = strip_unsupported(target)
        if removed:
            print(f"  已剔除 Red Skill 不支持的文件：{', '.join(removed)}")
    return target


def redskill_publish_command(target: pathlib.Path, skill_name: str,
                             display_name: str) -> str:
    """Red Skill 的投递命令；必须带 --name 与 --identifier。

    `--name` 覆盖 frontmatter 里的长技能名（否则被平台拒收）；
    `--identifier` 把平台主键钉死在仓内技能名上——Skill ID 跨版本不可改名，
    不显式钉住的话，将来改了 frontmatter 的 `name` 会在平台上另建一个新技能。
    """
    return (
        f'{REDSKILL_UPLOADER} {target} \\\n'
        f'  --agent --name "{display_name}" --identifier "{skill_name}" \\\n'
        f'  --source <original|repost> --tag "<中文标签，逗号分隔>" \\\n'
        f'  --dry-run --yes'
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-dir", type=pathlib.Path, required=True)
    parser.add_argument("--skill", help="要打包的技能名")
    parser.add_argument("--out", type=pathlib.Path, help="暂存目录")
    parser.add_argument("--display-name", help="对外中文展示名")
    parser.add_argument("--summary", help="对外简介；缺省用 description")
    parser.add_argument("--license", default=LICENSE_DEFAULT)
    parser.add_argument("--channel", choices=CHANNELS, default="skillhub",
                        help="目标渠道；redskill 会剔除其不支持的文件类型")
    parser.add_argument("--allow-unreleased", action="store_true",
                        help="跳过「必须是正式版」校验；仅用于本地演练，不得用于真实上架")
    parser.add_argument("--list-eligible", action="store_true",
                        help="只列出哪些技能可上架，不打包")
    args = parser.parse_args(argv)

    if args.list_eligible:
        for name, ok, reason in eligible_skills(args.repo_dir.resolve()):
            print(f"{'✓' if ok else '✗'} {name}: {reason}")
        return 0

    if not args.skill or not args.out:
        print("error: 打包需要同时给出 --skill 与 --out", file=sys.stderr)
        return 1

    if args.channel == "redskill" and not args.display_name:
        print("error: redskill 渠道必须给 --display-name（中文短名）。"
              "缺省会回落到仓内技能名，实测会被平台以「名称长度不符合要求」拒收，"
              "且长英文名对市场读者也没有意义。", file=sys.stderr)
        return 1

    try:
        target = stage(args.repo_dir.resolve(), args.skill, args.out.resolve(),
                       args.display_name, args.summary, args.license,
                       args.allow_unreleased, args.channel)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"已暂存：{target}")
    print(f"来源：{args.repo_dir.name} main 正式版")
    print("下一步（不会自动执行）：")
    if args.channel == "skillhub":
        print(f"  skillhub publish {target} --dry-run")
    else:
        print(redskill_publish_command(target, args.skill, args.display_name))
        print("  预检通过后去掉 --dry-run 重跑；最后一道确认门读 stdin，"
              "需要客户明确说提交后回答字面量 submit。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
