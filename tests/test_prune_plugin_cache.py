"""插件缓存回收脚本的行为约束。

回归 2026-07-27：Claude / Codex 在 plugin update 后只新增版本目录不回收旧的，
本机堆到 12 个陈旧目录 13 MB；且 Claude 的 .in_use 标记不可靠（同一插件新旧
两个版本都带），所以回收只能按语义化版本判断。
"""
from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/soia-meta-skill-release/scripts/prune_plugin_cache.py"


def load_module():
    spec = importlib.util.spec_from_file_location("prune_plugin_cache", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PrunePluginCacheTests(unittest.TestCase):
    def build(self, base: pathlib.Path, layout: dict[str, list[str]]) -> None:
        for plugin, versions in layout.items():
            for version in versions:
                directory = base / plugin / version
                directory.mkdir(parents=True)
                (directory / "SKILL.md").write_text("fixture", encoding="utf-8")

    def run_prune(self, base: pathlib.Path, apply: bool):
        module = load_module()
        with mock.patch.object(module, "ROOTS", [base]), \
                mock.patch("sys.argv", ["prune", *(["--apply"] if apply else [])]):
            module.main()

    def test_keeps_only_the_highest_semver_and_never_touches_other_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = pathlib.Path(temporary)
            self.build(base, {
                "market/plugin-a": ["1.1.0", "1.3.0", "1.2.0"],
                # 官方插件用得到的非语义化目录，必须原样保留
                "market/plugin-b": ["26.721.41059", "latest"],
                "market/plugin-c": ["2.0.0"],
            })
            self.run_prune(base, apply=True)

            self.assertEqual(
                sorted(p.name for p in (base / "market/plugin-a").iterdir()), ["1.3.0"]
            )
            self.assertEqual(
                sorted(p.name for p in (base / "market/plugin-b").iterdir()),
                ["26.721.41059", "latest"],
            )
            self.assertEqual(
                sorted(p.name for p in (base / "market/plugin-c").iterdir()), ["2.0.0"]
            )

    def test_dry_run_deletes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = pathlib.Path(temporary)
            self.build(base, {"market/plugin-a": ["1.0.0", "1.1.0"]})
            self.run_prune(base, apply=False)
            self.assertEqual(
                sorted(p.name for p in (base / "market/plugin-a").iterdir()),
                ["1.0.0", "1.1.0"],
            )

    def test_ten_dot_zero_beats_nine_dot_nine(self) -> None:
        """版本比较必须按数值而非字符串——字符串比较会把 9.9.0 判成最高。"""
        with tempfile.TemporaryDirectory() as temporary:
            base = pathlib.Path(temporary)
            self.build(base, {"market/plugin-a": ["9.9.0", "10.0.0"]})
            self.run_prune(base, apply=True)
            self.assertEqual(
                sorted(p.name for p in (base / "market/plugin-a").iterdir()), ["10.0.0"]
            )


if __name__ == "__main__":
    unittest.main()
