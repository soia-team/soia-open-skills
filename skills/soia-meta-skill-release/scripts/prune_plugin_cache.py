#!/usr/bin/env python3
"""清理 Claude Code / Codex 插件缓存里的旧版本目录。

两家客户端在 `plugin update` 后都只新增版本目录，不回收旧的；Claude 的
`.in_use` 标记也不可靠（实测同一插件的新旧两个版本都带这个文件）。因此这里
按语义化版本取最高值作为保留项，其余删除——缓存随时可由 marketplace 重新拉取。

非语义化版本的目录（如官方 chrome 插件的 `latest`）一律保留，避免误判。
"""
import argparse
import pathlib
import re
import shutil

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
ROOTS = [
    pathlib.Path.home() / ".claude/plugins/cache",
    pathlib.Path.home() / ".codex/plugins/cache",
]


def dir_size(path: pathlib.Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="真正删除；缺省只列出计划")
    args = parser.parse_args()

    freed = 0
    planned = []
    for root in ROOTS:
        if not root.is_dir():
            continue
        for plugin_dir in sorted(p for m in root.iterdir() if m.is_dir()
                                 for p in m.iterdir() if p.is_dir()):
            versions = [d for d in plugin_dir.iterdir() if d.is_dir()]
            semver = [d for d in versions if SEMVER.match(d.name)]
            if len(semver) < 2:
                continue  # 只有一个版本，或版本名非语义化（如 latest），不动
            keep = max(semver, key=lambda d: tuple(int(x) for x in SEMVER.match(d.name).groups()))
            for stale in semver:
                if stale == keep:
                    continue
                size = dir_size(stale)
                freed += size
                planned.append((stale, keep.name, size))

    for stale, keep, size in planned:
        rel = str(stale).replace(str(pathlib.Path.home()), "~")
        print(f"  {'删除' if args.apply else '将删'} {rel}  ({size / 1024 / 1024:.1f} MB, 保留 {keep})")
        if args.apply:
            shutil.rmtree(stale)

    print(f"\n  共 {len(planned)} 个旧版本目录，{freed / 1024 / 1024:.1f} MB"
          + ("（已释放）" if args.apply else "（预演，加 --apply 执行）"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
