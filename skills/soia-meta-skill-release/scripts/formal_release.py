#!/usr/bin/env python3
"""域仓正式发版编排（dev 分支制）。

七步：版本定稿 PR(→dev) → 发版 PR(dev→main) → tag → GitHub Release →
重开版本列车 PR(→dev)；pin 刷新与客户端更新仍走 skill-release 既有流程。

每份 plugin manifest（claude/codex/codebuddy）独立版本轨道：定稿 = 摘掉各自
的 -SNAPSHOT；重开列车 = 各自 +patch + -SNAPSHOT（下一版若够得上 minor/major，
发版前手工把 dev 版本提上去）。发布版本号取 .claude-plugin/plugin.json 为准。

--dry-run 只打印计划，不执行任何写操作。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

MANIFESTS = [
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    ".codebuddy-plugin/plugin.json",
]


class ReleaseError(RuntimeError):
    pass


def run(cmd: list[str], cwd: pathlib.Path | None = None) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise ReleaseError(
            f"{' '.join(cmd)} failed:\n{(result.stderr or result.stdout).strip()}"
        )
    return result.stdout.strip()


def strip_snapshot(version: str) -> str:
    if not version.endswith("-SNAPSHOT"):
        raise ReleaseError(f"version {version!r} is not a -SNAPSHOT; dev 通道未开列车？")
    return version.removesuffix("-SNAPSHOT")


def next_snapshot(release_version: str) -> str:
    """重开列车默认只 +patch。

    刚发完版时还不知道下一版是修 bug 还是加技能，默认 +minor 等于预判「下一版
    必然有新功能」——实证会虚高：v1.11.0 实际只修了一个显示缺陷，按语义应是
    1.10.1。与 Maven release 插件同惯例：默认递增末位，发版前若内容够得上
    minor/major 再手工把 dev 版本提上去。
    """
    x, y, z = release_version.split(".")
    return f"{x}.{y}.{int(z) + 1}-SNAPSHOT"


CHANGELOG_HEADER = (
    "# Changelog\n\n"
    "本文件由 soia-meta-skill-release 在每次正式发版时自动更新，与 GitHub Release 同源；\n"
    "更早的版本演进见 git 提交历史与 GitHub Releases。\n"
)


def changelog_entry(version: str, notes: str, date: str) -> str:
    """把 notes 草稿（首行为 # vX.Y.Z）转成 CHANGELOG 条目。"""
    body = notes.split("\n", 1)[1] if notes.startswith("#") else notes
    return f"## v{version} — {date}\n\n{body.strip()}\n"


def prepend_changelog(worktree: pathlib.Path, version: str, notes: str,
                      date: str | None = None) -> None:
    """新条目前插到 CHANGELOG.md；保留既有条目，文件不存在则创建。"""
    import datetime

    date = date or datetime.date.today().isoformat()
    path = worktree / "CHANGELOG.md"
    old_entries = ""
    if path.exists():
        text = path.read_text(encoding="utf-8")
        idx = text.find("## ")
        old_entries = text[idx:].rstrip() + "\n" if idx != -1 else ""
    entry = changelog_entry(version, notes, date)
    parts = [CHANGELOG_HEADER, entry]
    if old_entries:
        parts.append(old_entries)
    path.write_text("\n".join(parts), encoding="utf-8")


def read_manifest_versions(repo_dir: pathlib.Path, ref: str) -> dict[str, str]:
    versions: dict[str, str] = {}
    for manifest in MANIFESTS:
        try:
            raw = run(["git", "show", f"{ref}:{manifest}"], cwd=repo_dir)
        except ReleaseError:
            continue  # 仓库可能没有该宿主的 manifest
        versions[manifest] = json.loads(raw)["version"]
    if ".claude-plugin/plugin.json" not in versions:
        raise ReleaseError(f"{ref} 上找不到 .claude-plugin/plugin.json")
    return versions


def rewrite_versions(worktree: pathlib.Path, transform) -> dict[str, str]:
    changed: dict[str, str] = {}
    for manifest in MANIFESTS:
        path = worktree / manifest
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        new_version = transform(data["version"])
        data["version"] = new_version
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        changed[manifest] = new_version
    return changed


def wait_checks(repo: str, pr_number: str, timeout_s: int = 900) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["gh", "pr", "checks", pr_number, "--repo", repo],
            capture_output=True, text=True,
        )
        out = result.stdout + result.stderr
        # PR 刚建时 CI 尚未注册（no checks reported）或网络抖动：都按 pending 重试
        if "no checks reported" in out or (result.returncode != 0 and "fail" not in out):
            time.sleep(15)
            continue
        if "pending" in out:
            time.sleep(20)
            continue
        if "fail" in out:
            raise ReleaseError(f"PR #{pr_number} checks failed:\n{out}")
        return
    raise ReleaseError(f"PR #{pr_number} checks timed out after {timeout_s}s")


def wait_commit_audit(repo: str, sha: str, timeout_s: int = 900) -> None:
    """等某个提交上的 audit 出结论；未注册（none）按进行中处理，继续等。"""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        conclusion = subprocess.run(
            ["gh", "api", f"repos/{repo}/commits/{sha}/check-runs",
             "--jq", '[.check_runs[] | select(.name=="audit") | .conclusion] | first // "none"'],
            capture_output=True, text=True).stdout.strip().strip('"')
        if conclusion == "success":
            return
        if conclusion not in ("none", "", "null"):
            raise ReleaseError(
                f"提交 {sha[:7]} 的 audit 结论是 {conclusion}，不是 success；"
                f"快进发布要求该提交本身已通过检查。")
        time.sleep(15)
    raise ReleaseError(f"等待提交 {sha[:7]} 的 audit 超时（{timeout_s}s）")


def pr_flow(
    repo: str,
    repo_dir: pathlib.Path,
    base: str,
    branch: str,
    title: str,
    body: str,
    edit,
) -> None:
    """建分支 → 应用 edit(worktree) → 提交 → PR → 等 audit → squash 合并。"""
    scratch = repo_dir / ".git" / "formal-release-worktree"
    run(["git", "fetch", "origin", base], cwd=repo_dir)
    if scratch.exists():
        run(["git", "worktree", "remove", "--force", str(scratch)], cwd=repo_dir)
    run(["git", "worktree", "add", "-b", branch, str(scratch), f"origin/{base}"], cwd=repo_dir)
    try:
        edit(scratch)
        run(["git", "add", "-A"], cwd=scratch)
        run(["git", "commit", "-m", title], cwd=scratch)
        run(["git", "push", "-u", "origin", branch], cwd=scratch)
        pr_url = run(
            ["gh", "pr", "create", "--repo", repo, "--base", base,
             "--head", branch, "--title", title, "--body", body],
            cwd=scratch,
        )
        pr_number = pr_url.rstrip("/").rsplit("/", 1)[-1]
        wait_checks(repo, pr_number)
        run(["gh", "pr", "merge", pr_number, "--repo", repo, "--squash", "--delete-branch"])
    finally:
        run(["git", "worktree", "remove", "--force", str(scratch)], cwd=repo_dir)
        subprocess.run(["git", "-C", str(repo_dir), "branch", "-D", branch],
                       capture_output=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--repo-dir", type=pathlib.Path, required=True)
    parser.add_argument("--summary", default="", help="Release Notes 一句话摘要")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    repo_dir = args.repo_dir.resolve()
    plugin_name = args.repo.rsplit("/", 1)[-1]

    try:
        # 显式 refspec：single-branch 克隆下裸 fetch 不会创建 origin/dev 引用
        run(["git", "fetch", "origin",
             "+refs/heads/dev:refs/remotes/origin/dev",
             "+refs/heads/main:refs/remotes/origin/main", "--tags"], cwd=repo_dir)
        dev_versions = read_manifest_versions(repo_dir, "origin/dev")
        release_version = strip_snapshot(dev_versions[".claude-plugin/plugin.json"])

        # 前置校验：main 必须是 dev 的祖先，否则快进推送不成立。
        # main 若有 dev 缺的提交，说明有人绕过流程直接改了 main，或上次发版走了
        # merge/squash——先 sync main→dev 恢复不变量再发。
        ff_ok = subprocess.run(
            ["git", "-C", str(repo_dir), "merge-base", "--is-ancestor",
             "origin/main", "origin/dev"], capture_output=True)
        if ff_ok.returncode != 0:
            behind = run(["git", "rev-list", "--count", "origin/dev..origin/main"],
                         cwd=repo_dir)
            raise ReleaseError(
                f"main 有 {behind} 个 dev 缺的提交，无法快进发布。"
                f"先提 sync PR 把 main 合回 dev，再重新发版。"
            )

        plan = [
            f"1. 定稿 PR → dev：各 manifest 摘掉 -SNAPSHOT（发布版 {release_version}）",
            "2. 快进推送 dev → main（main 与 dev 同一提交，结构上不可能分叉）",
            f"3. tag v{release_version} 于该提交并推送",
            f"4. gh release create v{release_version}",
            "5. 重开列车 PR → dev：各 manifest +patch 进入 -SNAPSHOT",
            "6. 提醒：元仓刷 pin（发布门禁会验证 main 无 -SNAPSHOT）",
        ]
        print(f"== {args.repo} 正式发版 v{release_version} ==")
        print("\n".join(plan))
        if args.dry_run:
            print("\n（--dry-run，未执行）")
            return 0

        # notes 先于定稿生成（span=上个 tag..origin/dev），供 CHANGELOG 与发版 PR 共用
        notes_script = pathlib.Path(__file__).parent / "generate_release_notes.py"
        notes = run(
            [sys.executable, str(notes_script), "--repo-dir", str(repo_dir),
             "--ref", "origin/dev", "--release-version", release_version,
             "--summary", args.summary]
        )

        # 1. 定稿 PR → dev：摘 SNAPSHOT + CHANGELOG 前插（发版即更新，与 Release 同源）
        def finalize_edit(wt: pathlib.Path) -> None:
            rewrite_versions(wt, strip_snapshot)
            prepend_changelog(wt, release_version, notes)

        pr_flow(
            args.repo, repo_dir, base="dev",
            branch=f"release/v{release_version}-finalize",
            title=f"release: finalize v{release_version} (drop -SNAPSHOT)",
            body="发版定稿：各 manifest 摘掉 -SNAPSHOT，Release Notes 前插 CHANGELOG.md。",
            edit=finalize_edit,
        )

        # 2. 快进推送 dev → main。
        #
        # 不走 PR 合并：PR 的三种合并方式都会在 main 上造出 dev 没有的提交——
        # squash 连祖先关系都断（下次发版必冲突）、merge 留个 merge 提交、rebase
        # 重写 SHA。只有快进能让 main 与 dev 指向同一提交，分叉在结构上不可能发生。
        #
        # 这不是跳过检查：推上去的就是 dev 的 HEAD，audit 已在该提交上跑过（dev
        # 同样要求 audit 必过）。下面显式确认这一点后再推。
        run(["git", "fetch", "origin",
             "+refs/heads/dev:refs/remotes/origin/dev"], cwd=repo_dir)
        dev_sha = run(["git", "rev-parse", "origin/dev"], cwd=repo_dir)
        # 定稿 PR 刚合并时，dev HEAD 的 audit 往往尚未注册（conclusion=none）——
        # 必须轮询等待，只查一次会把「还没开始」误判成「没通过」。2026-08-04 实测踩到。
        wait_commit_audit(args.repo, dev_sha)
        run(["git", "push", "origin", f"{dev_sha}:refs/heads/main"], cwd=repo_dir)

        # 3+4. tag + Release（打在同一提交上）
        run(["git", "fetch", "origin", "main"], cwd=repo_dir)
        main_sha = run(["git", "rev-parse", "origin/main"], cwd=repo_dir)
        if main_sha != dev_sha:
            raise ReleaseError(
                f"快进后 main({main_sha[:7]}) 与 dev({dev_sha[:7]}) 不一致，中止")
        run(["git", "tag", f"v{release_version}", main_sha], cwd=repo_dir)
        run(["git", "push", "origin", f"v{release_version}"], cwd=repo_dir)
        notes_file = repo_dir / ".git" / f"release-notes-v{release_version}.md"
        notes_file.write_text(notes, encoding="utf-8")
        run(
            ["gh", "release", "create", f"v{release_version}", "--repo", args.repo,
             "--title", f"{plugin_name} v{release_version}",
             "--notes-file", str(notes_file)]
        )

        # 5. 重开版本列车
        pr_flow(
            args.repo, repo_dir, base="dev",
            branch=f"release/v{release_version}-reopen",
            title=f"chore(release): open next train after v{release_version}",
            body="发版后重开版本列车：各 manifest 进入 next-minor -SNAPSHOT。",
            edit=lambda wt: rewrite_versions(
                wt, lambda v: next_snapshot(v if "-SNAPSHOT" not in v else strip_snapshot(v))
            ),
        )

        # 6. 收尾断言：dev 必须已重开列车。发版中断在定稿与重开之间会让 dev
        #    停在正式版本号且无人察觉（2026-08-03 实际发生两次），这里显式兜底。
        run(["git", "fetch", "origin",
             "+refs/heads/dev:refs/remotes/origin/dev"], cwd=repo_dir)
        dev_version = read_manifest_versions(
            repo_dir, "origin/dev")[".claude-plugin/plugin.json"]
        if "-SNAPSHOT" not in dev_version:
            raise ReleaseError(
                f"发版已完成但 dev 未重开列车（当前 {dev_version}）——"
                f"请提 PR 把各 manifest 置为 {next_snapshot(release_version)}；"
                f"用 scripts/check_version_trains.py 复检全生态"
            )

        print(f"\n✅ {plugin_name} v{release_version} 已发布"
              f"（tag + Release + 列车重开 → {dev_version}）")
        print("下一步：元仓刷 pin → 客户端更新 → 真机验收（skill-release 既有流程）")
        return 0
    except ReleaseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
