"""发布技能里的缓存清理命令必须按插件粒度，不能按市场粒度。

回归 2026-07-27：技能第 5 步原本写 `rm -rf ~/.codex/plugins/cache/soia`。
`soia` 是**市场名**——该目录下是同市场全部 8 个插件，这条命令会把它们一起删掉；
之后只 `plugin add` 目标插件，其余 7 个就此消失。并行 AI 实际踩到并需人工恢复。
"""
from __future__ import annotations

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/soia-meta-skill-release/SKILL.md"

# 市场级缓存路径：末尾就是市场名，没有再跟插件名
MARKET_WIDE_DELETE = re.compile(r"rm\s+-rf[^\n`]*~/\.codex/plugins/cache/[\w-]+(?![\w/-])")


class ReleaseCacheCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = SKILL.read_text(encoding="utf-8")
        # 说明性文字里会引用这条危险命令作为反例，只检查代码块
        self.code = "\n".join(
            block for block in re.findall(r"```bash\n(.*?)```", self.text, re.S)
        )

    def test_no_market_wide_plugin_cache_delete_in_commands(self) -> None:
        hits = MARKET_WIDE_DELETE.findall(self.code)
        self.assertEqual(
            hits, [],
            f"插件缓存清理必须精确到插件目录（cache/<市场>/<插件>），命中市场级删除：{hits}",
        )

    def test_plugin_scoped_delete_is_present(self) -> None:
        self.assertIn("~/.codex/plugins/cache/soia/<域插件名>", self.code)

    def test_install_list_is_recorded_and_diffed(self) -> None:
        """删缓存前后要能对账，否则连带损失无人察觉。"""
        self.assertIn("soia-installed-before.txt", self.code)
        self.assertIn("diff", self.code)


if __name__ == "__main__":
    unittest.main()
