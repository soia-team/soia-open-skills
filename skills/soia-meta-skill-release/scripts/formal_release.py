#!/usr/bin/env python3
"""域仓正式发版编排（dev 分支制）。

七步：版本定稿 PR(→dev) → 发版 PR(dev→main) → tag → GitHub Release →
重开版本列车 PR(→dev)；pin 刷新与客户端更新仍走 skill-release 既有流程。

每份 plugin manifest（claude/codex/codebuddy）独立版本轨道：定稿 = 摘掉各自
的 -SNAPSHOT；重开列车 = 各自 next-minor + -SNAPSHOT。发布版本号取
.claude-plugin/plugin.json 为准。

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
    x, y, _z = release_version.split(".")
    return f"{x}.{int(y) + 1}.0-SNAPSHOT"


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
        out = run(["gh", "pr", "checks", pr_number, "--repo", repo]) if True else ""
        if "pending" not in out:
            if "fail" in out:
                raise ReleaseError(f"PR #{pr_number} checks failed:\n{out}")
            return
        time.sleep(20)
    raise ReleaseError(f"PR #{pr_number} checks timed out after {timeout_s}s")


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
        run(["git", "fetch", "origin", "dev", "main"], cwd=repo_dir)
        dev_versions = read_manifest_versions(repo_dir, "origin/dev")
        release_version = strip_snapshot(dev_versions[".claude-plugin/plugin.json"])

        plan = [
            f"1. 定稿 PR → dev：各 manifest 摘掉 -SNAPSHOT（发布版 {release_version}）",
            "2. 发版 PR：dev → main（正文 = Release Notes 草稿）",
            f"3. tag v{release_version} 于 main HEAD 并推送",
            f"4. gh release create v{release_version}",
            "5. 重开列车 PR → dev：各 manifest 进入 next-minor -SNAPSHOT",
            "6. 提醒：元仓刷 pin（发布门禁会验证 main 无 -SNAPSHOT）",
        ]
        print(f"== {args.repo} 正式发版 v{release_version} ==")
        print("\n".join(plan))
        if args.dry_run:
            print("\n（--dry-run，未执行）")
            return 0

        # 1. 定稿 PR → dev
        pr_flow(
            args.repo, repo_dir, base="dev",
            branch=f"release/v{release_version}-finalize",
            title=f"release: finalize v{release_version} (drop -SNAPSHOT)",
            body="发版定稿：各 manifest 摘掉 -SNAPSHOT。",
            edit=lambda wt: rewrite_versions(wt, strip_snapshot),
        )

        # 2. 发版 PR dev → main
        notes_script = pathlib.Path(__file__).parent / "generate_release_notes.py"
        run(["git", "fetch", "origin", "dev"], cwd=repo_dir)
        notes = run(
            [sys.executable, str(notes_script), "--repo-dir", str(repo_dir),
             "--ref", "origin/dev", "--release-version", release_version,
             "--summary", args.summary]
        )
        pr_url = run(
            ["gh", "pr", "create", "--repo", args.repo, "--base", "main",
             "--head", "dev", "--title", f"release: {plugin_name} v{release_version}",
             "--body", notes]
        )
        pr_number = pr_url.rstrip("/").rsplit("/", 1)[-1]
        wait_checks(args.repo, pr_number)
        run(["gh", "pr", "merge", pr_number, "--repo", args.repo, "--squash"])

        # 3+4. tag + Release
        run(["git", "fetch", "origin", "main"], cwd=repo_dir)
        main_sha = run(["git", "rev-parse", "origin/main"], cwd=repo_dir)
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

        print(f"\n✅ {plugin_name} v{release_version} 已发布（tag + Release + 列车重开）")
        print("下一步：元仓刷 pin → 客户端更新 → 真机验收（skill-release 既有流程）")
        return 0
    except ReleaseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
