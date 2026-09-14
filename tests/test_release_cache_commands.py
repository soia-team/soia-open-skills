"""发布技能里的缓存清理命令必须按插件粒度，不能按市场粒度。

回归 2026-07-27：技能第 5 步原本写 `rm -rf ~/.codex/plugins/cache/soia`。
`soia` 是**市场名**——该目录下是同市场全部 8 个插件，这条命令会把它们一起删掉；
之后只 `plugin add` 目标插件，其余 7 个就此消失。并行 AI 实际踩到并需人工恢复。
"""
from __future__ import annotations

import pathlib
import re
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/soia-meta-skill-release/SKILL.md"

# 市场级缓存路径：末尾就是市场名，没有再跟插件名
MARKET_WIDE_DELETE = re.compile(r"rm\s+-rf[^\n`]*~/\.codex/plugins/cache/[\w-]+(?![\w/-])")


def read_instruction_text(skill: pathlib.Path = SKILL) -> str:
    """检查入口及入口真实链接的参考，不假设安装命令必须留在入口。"""
    text = skill.read_text(encoding="utf-8")
    links = dict.fromkeys(re.findall(r"\]\((references/[^)#]+\.md)\)", text))
    documents = [text]
    for link in links:
        reference = (skill.parent / link).resolve()
        if not reference.is_relative_to(skill.parent.resolve()):
            raise ValueError(f"reference escapes skill: {link}")
        documents.append(reference.read_text(encoding="utf-8"))
    return "\n".join(documents)


def bash_commands(text: str) -> str:
    return "\n".join(re.findall(r"```bash\n(.*?)```", text, re.S))


class ReleaseCacheCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = read_instruction_text()
        # 说明性文字里会引用这条危险命令作为反例，只检查代码块
        self.code = bash_commands(self.text)

    def test_no_market_wide_plugin_cache_delete_in_commands(self) -> None:
        hits = MARKET_WIDE_DELETE.findall(self.code)
        self.assertEqual(
            hits, [],
            f"插件缓存清理必须精确到插件目录（cache/<市场>/<插件>），命中市场级删除：{hits}",
        )

    def test_optional_cleanup_requires_authorized_plugin_scope(self) -> None:
        self.assertIn("先列目标并获授权", self.text)
        self.assertIn("只处理已选择插件", self.text)
        self.assertIn("不能删整个市场下的其它插件", self.text)

    def test_market_wide_delete_in_linked_reference_is_detected(self) -> None:
        """负控：危险命令迁到已链接 reference 后仍然必须被抓住。"""
        root_text = "[安装](references/selected-install.md)\n"
        dangerous = "rm -rf ~/.codex/plugins/cache/soia"
        reference_text = f"```bash\n{dangerous}\n```\n"
        with mock.patch.object(pathlib.Path, "read_text", side_effect=[root_text, reference_text]):
            code = bash_commands(read_instruction_text())
        self.assertEqual(MARKET_WIDE_DELETE.findall(code), [dangerous])

    def test_install_list_is_recorded_and_diffed(self) -> None:
        """删缓存前后要能对账，否则连带损失无人察觉。"""
        self.assertIn("soia-installed-before.txt", self.code)
        self.assertIn("diff", self.code)

    def test_claude_side_also_reconciles(self) -> None:
        """Claude 侧同样需要对账。

        回归 2026-07-27：一轮全量卸载重装后漏装 5 个插件（2 个开源 + 3 个私有），
        直到手动核对才发现。`plugin update` 对未安装的插件只报 not installed，
        不会自动补装。
        """
        self.assertIn("claude-soia-before.txt", self.code)


if __name__ == "__main__":
    unittest.main()
