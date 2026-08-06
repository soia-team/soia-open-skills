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

**上架就绪门禁**：外部市场（腾讯 SkillHub 等）会用 AI 评测上架的技能，所以
打包后对暂存产物跑 R1-R5 机器检查（能力边界、触发词、输出样例、测试证据、
境外源提示），有硬缺口直接拒绝打包；`--check-only` 走完全流程后删除暂存
产物、只留报告，与 `--allow-unreleased` 组合即对工作树做咨询检查。
本门禁不预测评测分数，只消除历史评语点名过的缺口类型。

用法：
    python3 stage_for_market.py --repo-dir <域仓> --skill <技能名> --out <暂存目录>
    python3 stage_for_market.py --repo-dir <域仓> --list-eligible
    python3 stage_for_market.py --repo-dir <域仓> --skill <技能名> --out <暂存目录> \
        --allow-unreleased --check-only   # 对工作树做就绪咨询，不留产物
"""

from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import subprocess
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

DISCLAIMER = "本门禁不预测评测分数，只消除历史评语点名过的缺口类型"

URL_RE = re.compile(r"https?://[^\s'\"<>()]+")
# 境内域名启发式清单：host 以 .cn 结尾，或命中这些已知境内镜像/云厂商域名。
DOMESTIC_HOST_MARKERS = (
    "npmmirror.com",
    "tencent.com",
    "aliyun.com",
    "tsinghua.edu.cn",
    "ustc.edu.cn",
    "huaweicloud.com",
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

    gaps = readiness_gaps(target, repo_dir, skill_name)
    if any(level == "硬缺口" for level, _, _ in gaps):
        shutil.rmtree(target, ignore_errors=True)
        blocked = "\n".join(
            f"  {code} {note}" for level, code, note in gaps
            if level == "硬缺口")
        raise ValueError(
            f"{skill_name} 存在上架就绪硬缺口，拒绝打包：\n{blocked}")
    return target


def _url_host(url: str) -> str:
    match = re.match(r"https?://([^/?#\s]+)", url)
    return match.group(1).lower() if match else ""


def _is_domestic_url(url: str) -> bool:
    """按境内域名启发式清单判定 URL 是否境内可达。"""
    host = _url_host(url)
    if not host:
        return False
    if host.endswith(".cn"):
        return True
    return any(host == marker or host.endswith("." + marker)
               for marker in DOMESTIC_HOST_MARKERS)


def _has_real_sample_section(text: str) -> bool:
    """存在标题含「样例/示例」的小节，且小节内有真实表格数据行。

    「真实」指以 `|` 开头的行不含 `<`——占位符模板（`| <path> |`）不算。
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if not heading or not re.search(r"样例|示例", heading.group(2)):
            continue
        level = len(heading.group(1))
        for row in lines[index + 1:]:
            next_heading = re.match(r"^(#{1,6})\s+", row)
            if next_heading and len(next_heading.group(1)) <= level:
                break
            if row.startswith("|") and "<" not in row:
                return True
    return False


def _skill_names(repo_dir: pathlib.Path) -> set[str]:
    """仓内全部技能名：skills/ 下的一级目录名。"""
    skills_dir = repo_dir / "skills"
    if not skills_dir.is_dir():
        return set()
    return {p.name for p in skills_dir.iterdir() if p.is_dir()}


def _r4_test_evidence(target: pathlib.Path, repo_dir: pathlib.Path,
                      skill_name: str) -> tuple[tuple[str, str, str] | None,
                                                str | None]:
    """专属测试的检查与随包证据。返回 (硬缺口, 跨技能跳过提示)。

    匹配策略分三层演进，每层都对应一次真实事故：

    1. **路径字面串**（`skills/<技能名>/`）匹配——漏配：真实测试常把路径分段
       拼接（`ROOT / "skills" / "<技能名>" / "scripts"`），字面串不存在，
       永远匹配不到。
    2. **技能名子串**匹配——过配：域仓里存在跨技能共享测试（一个文件引用许多
       技能的名字，如遍历所有技能的状态表检查），它们也被匹配、拷进包，在包
       布局里必然跑不起来（去找别的技能的文件），把 R4 打成假硬缺口。
    3. **专属判定**（本层）：先取仓内全部技能名，候选里不含任何「其他」技能名
       的才是本技能专属测试；只拷专属测试进包并实跑，跨技能候选不拷（归仓级
       CI 管），只在报告里提示跳过。

    专属测试为空 → 硬缺口；专属测试在包布局跑挂 → 硬缺口（布局耦合），比没有
    更糟。
    """
    tests_dir = repo_dir / "tests"
    candidates: list[pathlib.Path] = []
    if tests_dir.is_dir():
        for path in sorted(tests_dir.rglob("*.py")):
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if skill_name in source:
                candidates.append(path)
    no_exclusive_gap = ("硬缺口", "R4",
                        "无专属自包含测试（只引用本技能与标准库的测试），"
                        "评测将记缺测试保障")
    if not candidates:
        return no_exclusive_gap, None

    others = _skill_names(repo_dir) - {skill_name}
    exclusive: list[pathlib.Path] = []
    cross_skill: list[pathlib.Path] = []
    for path in candidates:
        source = path.read_text(encoding="utf-8", errors="replace")
        if any(name in source for name in others):
            cross_skill.append(path)
        else:
            exclusive.append(path)
    notice = None
    if cross_skill:
        names = ", ".join(str(p.relative_to(tests_dir)) for p in cross_skill)
        notice = f"跳过 {len(cross_skill)} 个跨技能共享测试：{names}"
    if not exclusive:
        return no_exclusive_gap, notice

    staged_tests = target / "tests"
    for src in exclusive:
        rel = src.relative_to(tests_dir)
        dst = staged_tests / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    run = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s",
         str(staged_tests), "-q"],
        capture_output=True, text=True)
    if run.returncode != 0:
        tail = "\n".join((run.stdout + run.stderr).strip().splitlines()[-8:])
        return ("硬缺口", "R4",
                f"测试有仓布局耦合，进包后跑不起来，比没有更糟\n"
                f"    实跑输出（尾部）：{tail}"), notice
    return None, notice


def _r5_foreign_sources(target: pathlib.Path) -> tuple[str, str, str] | None:
    """包内所有 .md 里的 http(s) URL 若全境外，记警告（不阻断）。"""
    urls: list[str] = []
    for path in sorted(target.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        urls.extend(URL_RE.findall(text))
    if not urls:
        return None
    if any(_is_domestic_url(url) for url in urls):
        return None
    return ("警告", "R5",
            "探测/依赖源疑似全境外，国内环境可用性会被评测扣分")


def readiness_gaps(target: pathlib.Path, repo_dir: pathlib.Path,
                   skill_name: str) -> list[tuple[str, str, str]]:
    """对暂存目录里的最终产物做上架就绪门禁，返回 (等级, 编号, 说明)。

    等级取「硬缺口」或「警告」。检查对象是暂存目录里叠加了 frontmatter、做完
    渠道过滤之后的产物，不是仓库。逐项结果打印到 stdout。
    """
    skill_md = target / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    gaps: list[tuple[str, str, str]] = []

    # R1 边界表达：市场用户拿到的是孤立技能，必须自述能力边界。
    if not any(re.match(r"^#{1,6}\s+.*(不负责|能力边界)", line)
               for line in text.splitlines()):
        gaps.append(("硬缺口", "R1",
                     "SKILL.md 没有含「不负责/能力边界」的标题节；"
                     "市场用户拿到的是孤立技能，必须自述能力边界"))

    # R2 触发词：评测按触发词判断技能何时该被调起。
    frontmatter, _ = read_frontmatter(skill_md)
    description = field(frontmatter, "description") or ""
    if not re.search(r"触发|Triggers", description):
        gaps.append(("硬缺口", "R2",
                     "frontmatter 的 description 没有触发词"
                     "（「触发」或「Triggers」）；评测靠触发词判断何时调起技能"))

    # R3 输出样例：评测点名过缺真实输出样例，占位符模板不算。
    if not _has_real_sample_section(text):
        gaps.append(("硬缺口", "R3",
                     "没有含真实数据的「样例/示例」小节；"
                     "评测点名过缺真实输出样例，占位符模板不算"))

    # R4 测试证据。
    r4_gap, r4_notice = _r4_test_evidence(target, repo_dir, skill_name)
    if r4_gap is not None:
        gaps.append(r4_gap)

    # R5 境外源提示。
    r5 = _r5_foreign_sources(target)
    if r5 is not None:
        gaps.append(r5)

    print(f"[就绪门禁] {skill_name} 逐项结果：")
    notice_printed = False
    for level, code, note in gaps:
        print(f"  {code} [{level}] {note}")
        if code == "R4" and r4_notice is not None:
            print(f"  R4 提示：{r4_notice}")
            notice_printed = True
    if r4_notice is not None and not notice_printed:
        print(f"  R4 提示：{r4_notice}")
    if not gaps:
        print("  R1-R5 全部通过")
    print(f"  {DISCLAIMER}")
    return gaps


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
    parser.add_argument("--check-only", action="store_true",
                        help="走完打包+就绪门禁后删除暂存产物，只留报告；"
                             "与 --allow-unreleased 组合即对工作树做咨询检查")
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
    if args.check_only:
        shutil.rmtree(target, ignore_errors=True)
        print(f"{args.skill}：打包与就绪门禁完成（--check-only，暂存产物已删除）")
        return 0
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
