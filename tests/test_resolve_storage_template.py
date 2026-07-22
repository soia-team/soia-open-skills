from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "templates"
    / "skill-template"
    / "scripts"
    / "resolve_storage.py"
)
SPEC = importlib.util.spec_from_file_location("template_resolve_storage", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
resolve_storage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resolve_storage)


class ResolveStorageTemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        resolve_storage._WARNED_LEGACY_PATHS.clear()

    def test_v2_config_wins(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            expected = home / ".config/soia-skills/soia-pkm-clip-web/config.yml"
            expected.parent.mkdir(parents=True)
            expected.write_text("enabled: true\n", encoding="utf-8")

            actual = resolve_storage.resolve_config_file(
                "soia-pkm", "soia-pkm-clip-web", "SOIA_PKM_CLIP_WEB_CONFIG_FILE", env={}, home=home
            )

            self.assertEqual(actual, expected)

    def test_v1_fallback_supports_cwork_domain(self) -> None:
        self._assert_v1_fallback("soia-cwork-feishu-cli", "cwork", "soia-open-skills")

    def test_v1_fallback_supports_soia_dev_domain(self) -> None:
        self._assert_v1_fallback("soia-dev-github-ops", "soia-dev", "soia-open-env-skills")

    def _assert_v1_fallback(self, skill_name: str, legacy_domain: str, legacy_repo: str) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            expected = (
                home
                / ".config"
                / "soia-skills"
                / legacy_repo
                / legacy_domain
                / skill_name
                / "config.yml"
            )
            expected.parent.mkdir(parents=True)
            expected.write_text("enabled: true\n", encoding="utf-8")
            stderr = io.StringIO()

            with contextlib.redirect_stderr(stderr):
                actual = resolve_storage.resolve_config_file(
                    legacy_domain, skill_name, "SOIA_TEST_CONFIG_FILE", env={}, home=home
                )
                repeated = resolve_storage.resolve_config_file(
                    legacy_domain, skill_name, "SOIA_TEST_CONFIG_FILE", env={}, home=home
                )

            self.assertEqual(actual, expected)
            self.assertEqual(repeated, expected)
            self.assertEqual(stderr.getvalue().count("mv "), 1)
            self.assertIn(str(expected), stderr.getvalue())

    def test_config_env_override_has_highest_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            override = home / "custom/config.yml"
            v2 = home / ".config/soia-skills/soia-pkm-clip-web/config.yml"
            v2.parent.mkdir(parents=True)
            v2.write_text("enabled: true\n", encoding="utf-8")

            actual = resolve_storage.resolve_config_file(
                "soia-pkm",
                "soia-pkm-clip-web",
                env={"SOIA_PKM_CLIP_WEB_CONFIG_FILE": str(override)},
                home=home,
            )

            self.assertEqual(actual, override)

    def test_write_path_is_always_v2_without_explicit_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            legacy = (
                home
                / ".config/soia-skills/soia-open-env-skills/soia-dev/soia-dev-github-ops/config.yml"
            )
            legacy.parent.mkdir(parents=True)
            legacy.write_text("enabled: true\n", encoding="utf-8")

            actual = resolve_storage.resolve_config_file(
                "soia-dev",
                "soia-dev-github-ops",
                "SOIA_DEV_GITHUB_OPS_CONFIG_FILE",
                for_write=True,
                env={},
                home=home,
            )

            self.assertEqual(
                actual,
                home / ".config/soia-skills/soia-dev-github-ops/config.yml",
            )
            self.assertEqual(
                resolve_storage.resolve_storage_dir(
                    "state",
                    "soia-dev",
                    "soia-dev-github-ops",
                    for_write=True,
                    env={},
                    home=home,
                ),
                home / ".local/state/soia-skills/soia-dev-github-ops",
            )


if __name__ == "__main__":
    unittest.main()
