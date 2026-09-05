"""Install coverage remains fail-closed while supporting progressive disclosure."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    "check_install_sections", Path(__file__).parents[1] / "scripts/check_install_sections.py"
)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
COVERAGE = "claude plugin install <domain>\nnpx skills add <repo>\nWorkBuddy"


class InstallSectionsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.skill = self.repo / "skills" / "example"
        (self.skill / "references").mkdir(parents=True)
        self.doc = self.skill / "SKILL.md"

    def audit(self, text):
        self.doc.write_text(text, encoding="utf-8")
        return checker.audit_skill(self.doc, self.repo)["missing"]

    def test_inline_coverage(self):
        self.assertEqual(self.audit("### 依赖与安装\n" + COVERAGE), [])

    def test_explicit_local_install_reference(self):
        (self.skill / "references/install.md").write_text(COVERAGE, encoding="utf-8")
        self.assertEqual(self.audit(
            "### 依赖与安装\n[安装说明](references/install.md)\n## 工作流\n其他内容"
        ), [])

    def test_other_sections_and_unlabelled_links_do_not_supply_coverage(self):
        (self.skill / "references/install.md").write_text(COVERAGE, encoding="utf-8")
        self.assertTrue(self.audit(
            "### 依赖与安装\n[其他资料](references/install.md)\n### 工作流\n" + COVERAGE
        ))

    def test_missing_reference_fails_even_with_inline_coverage(self):
        missing = self.audit("### 安装\n" + COVERAGE + "\n[安装说明](references/missing.md)")
        self.assertTrue(any("无法读取" in item for item in missing))

    def test_path_escape_and_symlink_are_rejected(self):
        outside = self.repo / "outside.md"
        outside.write_text(COVERAGE, encoding="utf-8")
        (self.skill / "references/link.md").symlink_to(outside)
        for target in ("../../outside.md", "references/link.md", str(outside)):
            with self.subTest(target=target):
                missing = self.audit(f"### 安装\n[安装说明]({target})")
                self.assertTrue(any("无效安装引用" in item for item in missing))

    def test_remote_or_fragment_link_is_not_coverage(self):
        (self.skill / "references/install.md").write_text(COVERAGE, encoding="utf-8")
        for target in ("https://example.com/install.md", "references/install.md#absent"):
            with self.subTest(target=target):
                self.assertTrue(self.audit(f"### 安装\n[安装说明]({target})"))

    def test_no_recursive_reference_discovery(self):
        (self.skill / "references/a.md").write_text("[安装说明](b.md)", encoding="utf-8")
        (self.skill / "references/b.md").write_text(COVERAGE, encoding="utf-8")
        self.assertTrue(self.audit("### 安装\n[安装说明](references/a.md)"))


if __name__ == "__main__":
    unittest.main()
