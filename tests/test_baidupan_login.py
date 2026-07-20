import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "soia-pkm-baidu-netdisk-ops"


def load_module(name: str, path: Path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BaidupanLoginTests(unittest.TestCase):
    def test_device_login_uses_fixed_official_command(self):
        module = load_module("device_login", SKILL_DIR / "scripts" / "device_login.py")
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "config.yml"
            config.write_text("schema_version: 1\nprovider: official\nbinary: bdpan\n", encoding="utf-8")
            previous = os.environ.get("SOIA_PKM_BAIDU_NETDISK_OPS_CONFIG_FILE")
            try:
                os.environ["SOIA_PKM_BAIDU_NETDISK_OPS_CONFIG_FILE"] = str(config)
                completed = subprocess.CompletedProcess(["bdpan"], 0)
                with patch.object(module.shutil, "which", return_value="/bin/bdpan"), patch.object(
                    module.subprocess, "run", return_value=completed
                ) as run:
                    self.assertEqual(module.main([]), 0)
                run.assert_called_once_with(
                    ["bdpan", "login", "--device-code", "--accept-disclaimer"],
                    check=False,
                )
            finally:
                if previous is None:
                    os.environ.pop("SOIA_PKM_BAIDU_NETDISK_OPS_CONFIG_FILE", None)
                else:
                    os.environ["SOIA_PKM_BAIDU_NETDISK_OPS_CONFIG_FILE"] = previous


if __name__ == "__main__":
    unittest.main()
