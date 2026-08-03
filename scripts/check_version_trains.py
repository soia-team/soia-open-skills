#!/usr/bin/env python3
"""跨仓列车体检：dev 必须带 `-SNAPSHOT`，main 必须不带。

dev 分支制的核心不变量。正式发版的定稿步骤会短暂把 dev 置于正式版本号，
第 5 步重开列车才恢复——中途任何中断都会让 dev 停在违规状态且无人察觉
（2026-08-03 实际发生：pkm 与 media 两个仓静默停在无 SNAPSHOT 状态）。

用法：
    python3 scripts/check_version_trains.py            # 体检全部仓
    python3 scripts/check_version_trains.py --repo <name>
    python3 scripts/check_version_trains.py --json
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys

OWNER = "soia-team"
MANIFEST = ".claude-plugin/plugin.json"
REPOS = [
    "soia-open-skills",
    "soia-open-dev-skills",
    "soia-open-dev-design-skills",
    "soia-open-pkm-vault-skills",
    "soia-open-media-content-skills",
    "soia-open-cwork-office-skills",
    "soia-open-env-skills",
    "soia-open-edu-course-skills",
    "soia-private-skills",
    "soia-private-corp-skills",
]


def fetch_version(repo: str, ref: str) -> str | None:
    """读取指定 ref 上的插件版本；分支或文件不存在时返回 None。"""
    result = subprocess.run(
        ["gh", "api", f"repos/{OWNER}/{repo}/contents/{MANIFEST}?ref={ref}", "--jq", ".content"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        payload = base64.b64decode(result.stdout.strip()).decode("utf-8")
        return json.loads(payload).get("version")
    except (ValueError, UnicodeDecodeError):
        return None


def inspect(repo: str) -> dict:
    main_v = fetch_version(repo, "main")
    dev_v = fetch_version(repo, "dev")
    problems = []
    if main_v is None:
        problems.append("main 读不到 plugin.json")
    elif "-SNAPSHOT" in main_v:
        problems.append(f"main 带 -SNAPSHOT（{main_v}）——开发版本泄漏到发布分支")
    if dev_v is None:
        problems.append("dev 读不到 plugin.json（分支缺失？）")
    elif "-SNAPSHOT" not in dev_v:
        problems.append(f"dev 未开列车（{dev_v}）——发版可能中断在定稿与重开之间")
    return {"repo": repo, "main": main_v, "dev": dev_v, "problems": problems}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", action="append", help="只检查指定仓，可重复")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    targets = args.repo or REPOS
    results = [inspect(r) for r in targets]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            mark = "✗" if r["problems"] else "✓"
            print(f"{mark} {r['repo']}: main={r['main']} dev={r['dev']}")
            for p in r["problems"]:
                print(f"    {p}")

    broken = [r for r in results if r["problems"]]
    if broken:
        print(f"\n{len(broken)} 个仓不满足版本列车不变量", file=sys.stderr)
        return 1
    if not args.json:
        print(f"\n全部 {len(results)} 个仓满足不变量：dev 带 -SNAPSHOT、main 不带")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
