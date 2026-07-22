from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "skills"
    / "soia-cwork-processon-diagrams"
    / "scripts"
    / "processon_browser_runner.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("processon_browser_runner", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakePage:
    def __init__(self, context=None, url="https://www.processon.com/") -> None:
        self.context = context
        self.url = url
        self.closed = False
        self.keyboard = self

    def is_closed(self):
        return self.closed

    def close(self, run_before_unload=False):
        self.closed = True
        if self.context and self in self.context.pages:
            self.context.pages.remove(self)

    def go_back(self, **_kwargs):
        return None

    def press(self, _key):
        return None

    def wait_for_load_state(self, *_args, **_kwargs):
        return None


class FakeContext:
    def __init__(self, count=1) -> None:
        self.pages = []
        self.closed = False
        for _ in range(count):
            self.pages.append(FakePage(self))

    def new_page(self):
        page = FakePage(self)
        self.pages.append(page)
        return page

    def close(self):
        self.closed = True
        for page in list(self.pages):
            page.close()


class FakeLocator:
    def filter(self, **_kwargs):
        return self

    def nth(self, _index):
        return self


class LocatorPage:
    def get_by_role(self, *_args, **_kwargs):
        return FakeLocator()

    def get_by_text(self, *_args, **_kwargs):
        return FakeLocator()

    def get_by_label(self, *_args, **_kwargs):
        return FakeLocator()


class ProcessOnBrowserRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_default_profile_is_skill_owned_not_normal_chrome(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            profile = self.module.default_profile_dir(home=home, environ={})
            self.assertIn(self.module.SKILL_NAME, str(profile))
            self.assertTrue(str(profile).endswith("browser-profile"))

    def test_normal_chrome_profile_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            normal = home / "Library" / "Application Support" / "Google" / "Chrome" / "Default"
            with self.assertRaisesRegex(self.module.BrowserRunnerError, "normal Chrome"):
                self.module.validate_profile_dir(normal, home=home, environ={})

    def test_nonempty_unmarked_profile_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary) / "profile"
            profile.mkdir()
            (profile / "foreign-file").write_text("not ours", encoding="utf-8")
            with self.assertRaisesRegex(self.module.BrowserRunnerError, "non-empty unmarked"):
                self.module.ensure_dedicated_profile(profile)

    def test_context_closes_stale_and_active_pages_on_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeContext(count=3)

            def launcher(_profile, _headless):
                return context

            with self.module.managed_context(
                Path(temporary) / "profile", headless=True, launcher=launcher
            ) as (_context, page, receipt):
                self.assertFalse(page.closed)
                self.assertEqual(receipt.stale_pages_closed, 2)

            self.assertTrue(context.closed)
            self.assertTrue(page.closed)
            self.assertEqual(receipt.pages_closed_at_exit, 1)

    def test_context_closes_pages_when_worker_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = FakeContext(count=1)

            def launcher(_profile, _headless):
                return context

            with self.assertRaisesRegex(self.module.ManagedBrowserFailure, "boom") as raised:
                with self.module.managed_context(
                    Path(temporary) / "profile", headless=True, launcher=launcher
                ) as (_context, page, _receipt):
                    raise RuntimeError("boom")

            self.assertTrue(context.closed)
            self.assertTrue(page.closed)
            self.assertEqual(raised.exception.receipt["pages_closed_at_exit"], 1)
            self.assertEqual(raised.exception.original_type, "RuntimeError")

    def test_action_contract_forbids_credentials_and_form_fill(self) -> None:
        with self.assertRaisesRegex(self.module.BrowserRunnerError, "unsupported action"):
            self.module.validate_steps([{"action": "fill", "label": "账号", "value": "x"}])
        with self.assertRaisesRegex(self.module.BrowserRunnerError, "sensitive field"):
            self.module.validate_steps([{"action": "snapshot", "cookie": "x"}])

    def test_semantic_locators_reject_remote_mutations_and_unnamed_controls(self) -> None:
        page = LocatorPage()
        with self.assertRaisesRegex(self.module.BrowserRunnerError, "remote mutation"):
            self.module.step_locator(page, {"text": "删除"})
        with self.assertRaisesRegex(self.module.BrowserRunnerError, "visible name"):
            self.module.step_locator(page, {"role": "button"})
        with self.assertRaisesRegex(self.module.BrowserRunnerError, "semantic locator"):
            self.module.step_locator(page, {"css": ".dangerous"})
        self.assertIsInstance(
            self.module.step_locator(page, {"role": "menuitem", "name": "VISIO文件"}),
            FakeLocator,
        )

    def test_popup_action_requires_nested_steps_and_processon_urls_only(self) -> None:
        with self.assertRaisesRegex(self.module.BrowserRunnerError, "non-empty list"):
            self.module.validate_steps([{"action": "popup", "text": "打开"}])
        with self.assertRaisesRegex(self.module.BrowserRunnerError, "only HTTPS ProcessOn"):
            self.module.validate_processon_url("https://example.com/")
        self.assertEqual(
            self.module.validate_processon_url("https://www.processon.com/org/teams/example"),
            "https://www.processon.com/org/teams/example",
        )

    def test_target_reached_rejects_login_redirect(self) -> None:
        target = "https://www.processon.com/org/teams/example"
        self.assertTrue(self.module.target_reached(target, target))
        self.assertFalse(
            self.module.target_reached("https://www.processon.com/login", target)
        )

    def test_wait_text_uses_nth_to_tolerate_duplicate_processon_nodes(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('elif action == "wait_text":', script)
        self.assertIn('int(step.get("nth", 0))', script)

    def test_snapshot_includes_semantically_labeled_non_button_icons(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        for marker in ["[data-title]", "[data-tooltip]", 'get_attribute("data-tooltip")']:
            with self.subTest(marker=marker):
                self.assertIn(marker, script)

    def test_inspect_text_is_fixed_and_does_not_accept_caller_javascript(self) -> None:
        self.assertIn("inspect_text", self.module.ALLOWED_ACTIONS)
        self.module.validate_steps(
            [{"action": "inspect_text", "text": "<diagram-title>", "nth": 0}]
        )
        with self.assertRaisesRegex(self.module.BrowserRunnerError, "sensitive field"):
            self.module.validate_steps(
                [{"action": "inspect_text", "text": "x", "session_storage": "x"}]
            )

    def test_row_menu_is_provider_scoped_and_text_locators_prefer_visible_nodes(self) -> None:
        self.assertIn("row_menu", self.module.ALLOWED_ACTIONS)
        script = SCRIPT.read_text(encoding="utf-8")
        for marker in [
            "def open_processon_row_menu",
            "file_list_item",
            "span.more.icons.icon-gengduo",
            "filter(visible=True)",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, script)

    def test_cli_has_bounded_spa_settle_delay(self) -> None:
        parser = self.module.build_parser()
        args = parser.parse_args(
            ["snapshot", "--url", "https://www.processon.com/org/teams/example"]
        )
        self.assertEqual(args.settle_ms, 2_000)
        overridden = parser.parse_args(
            [
                "--settle-ms",
                "3500",
                "snapshot",
                "--url",
                "https://www.processon.com/org/teams/example",
            ]
        )
        self.assertEqual(overridden.settle_ms, 3_500)

    def test_skill_contract_makes_portable_runner_the_batch_default(self) -> None:
        skill_root = SCRIPT.parents[1]
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        workflow = (skill_root / "references" / "download-workflow.md").read_text(
            encoding="utf-8"
        )
        failures = (skill_root / "references" / "known-failure-modes.md").read_text(
            encoding="utf-8"
        )
        for marker in [
            "processon_browser_runner.py",
            "正式批量只能使用技能专用 profile",
            "禁止附着客户默认 Chrome profile",
            "pages_closed_at_exit",
            "settle",
            "正常完成与异常退出都必须返回关闭回执",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, skill)
        self.assertIn("不得在客户正在使用的 Chrome", workflow)
        self.assertIn("宿主浏览器工具会干扰客户并制造孤儿标签", failures)
        self.assertLess(len(skill.splitlines()), 500)


if __name__ == "__main__":
    unittest.main()
