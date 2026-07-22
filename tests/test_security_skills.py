import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = (
    ROOT
    / "skills"
    / "soia-safe-track-vulnerability-intel"
    / "scripts"
    / "collect_vulnerabilities.py"
)
INVENTORY = (
    ROOT
    / "skills"
    / "soia-safe-audit-fix-codebase"
    / "scripts"
    / "inventory_codebase.py"
)


class SecuritySkillScriptsTest(unittest.TestCase):
    def run_script(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )

    def test_collector_self_test(self) -> None:
        result = self.run_script(COLLECTOR, "--self-test")
        self.assertEqual(result.stdout.strip(), "self-test: ok")

    def test_inventory_self_test(self) -> None:
        result = self.run_script(INVENTORY, "--self-test")
        self.assertEqual(result.stdout.strip(), "self-test: ok")

    def test_inventory_is_read_only_and_omits_absolute_path_and_secret_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="security-skill-test-") as temp_dir:
            root = Path(temp_dir)
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            (root / ".env").write_text("SECRET_VALUE=do-not-emit\n", encoding="utf-8")
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            result = self.run_script(INVENTORY, str(root))
            payload = json.loads(result.stdout)
            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            self.assertEqual(before, after)
            self.assertEqual(payload["target"]["display_name"], root.name)
            self.assertFalse(payload["target"]["absolute_path_included"])
            self.assertEqual(payload["counts"]["sensitive_name_candidates"], 1)
            self.assertNotIn(temp_dir, result.stdout)
            self.assertNotIn("do-not-emit", result.stdout)


if __name__ == "__main__":
    unittest.main()
