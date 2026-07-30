"""WorkBuddy 专家安装脚本的守门测试。

WorkBuddy 与 Claude/Codex 的差别不是「命令不一样」而是「没有命令」——它是 Electron
桌面端，没有 CLI，也没有能指向我们仓库的市场通道。安装只能由脚本把域仓副本放进它
硬编码的专家目录。这里锁住三条实测约束，防止以后有人把它改回「更像 Claude」的写法。
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/soia-meta-skill-release/scripts/install_workbuddy_experts.py"

_spec = importlib.util.spec_from_file_location("install_workbuddy_experts", SCRIPT)
iwe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(iwe)


class TargetDirectoryTests(unittest.TestCase):
    def test_targets_the_hardcoded_my_experts_directory(self) -> None:
        """自建专家只认 my-experts，应用内硬编码 38 处；别处放了不显示。"""
        self.assertEqual(iwe.MY_EXPERTS, "plugins/marketplaces/my-experts")

    def test_honours_workbuddy_config_dir(self) -> None:
        """官方规范：专家目录由 WORKBUDDY_CONFIG_DIR 决定，不可写死 ~/.workbuddy。"""
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("WORKBUDDY_CONFIG_DIR", source)


class CopySemanticsTests(unittest.TestCase):
    """必须是实体副本，不能是软链——官方 validate_expert.py 会 resolve() 穿透软链。"""

    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "repo"
        (self.repo / ".codebuddy-plugin").mkdir(parents=True)
        (self.repo / "skills/demo/scripts/__pycache__").mkdir(parents=True)
        (self.repo / ".git").mkdir()
        (self.repo / ".git/HEAD").write_text("ref: refs/heads/main\n")
        (self.repo / "skills/demo/SKILL.md").write_text("---\nname: demo\n---\n")
        (self.repo / "skills/demo/scripts/run.py").write_text("print('ok')\n")
        (self.repo / "skills/demo/scripts/__pycache__/run.pyc").write_bytes(b"\x00" * 16)
        (self.repo / ".codebuddy-plugin/plugin.json").write_text(
            json.dumps({"name": "demo", "skills": ["./skills/demo"]}), encoding="utf-8")
        self.out = iwe.install_one("demo", self.repo, self.tmp / "market")

    def test_produces_a_real_directory_not_a_symlink(self) -> None:
        self.assertTrue(self.out.is_dir())
        self.assertFalse(self.out.is_symlink())

    def test_skill_content_is_present(self) -> None:
        self.assertTrue((self.out / "skills/demo/SKILL.md").exists())
        self.assertTrue((self.out / "skills/demo/scripts/run.py").exists())

    def test_repo_and_build_artifacts_are_excluded(self) -> None:
        for junk in (".git", "skills/demo/scripts/__pycache__"):
            with self.subTest(path=junk):
                self.assertFalse((self.out / junk).exists())

    def test_reinstall_drops_content_no_longer_in_the_repo(self) -> None:
        stale = self.out / "skills/removed"
        stale.mkdir(parents=True)
        rebuilt = iwe.install_one("demo", self.repo, self.tmp / "market")
        self.assertFalse((rebuilt / "skills/removed").exists())


class RosterTests(unittest.TestCase):
    def test_every_plugin_is_mapped(self) -> None:
        expected = {
            # 8 开源
            "soia-dev", "soia-dev-design", "soia-pkm-vault", "soia-media-content",
            "soia-cwork-office", "soia-edu-course", "soia-env", "soia-meta",
            # 4 私有（soia-private-skills 一仓三 plugin root）
            "soia-gov", "soia-workspace", "soia-harness", "soia-corp",
        }
        self.assertEqual(set(iwe.DOMAIN_REPOS), expected)

    def test_multi_root_repos_record_their_subdirectory(self) -> None:
        """soia-private-skills 靠目录分隔出三个插件，root 相对路径不能丢。"""
        self.assertEqual(iwe.DOMAIN_REPOS["soia-gov"], ("soia-private-skills", "."))
        self.assertEqual(iwe.DOMAIN_REPOS["soia-workspace"],
                         ("soia-private-skills", "workspace"))
        self.assertEqual(iwe.DOMAIN_REPOS["soia-harness"],
                         ("soia-private-skills", "harness"))

    def test_registration_goes_through_the_official_script(self) -> None:
        """官方规范铁律 12：禁止绕过 register_expert.py 直接写 marketplace.json。"""
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("register_expert.py", source)
        self.assertNotIn('"marketplace.json"', source)


if __name__ == "__main__":
    unittest.main()
