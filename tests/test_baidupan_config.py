import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_SCRIPT = ROOT / "skills" / "soia-pkm-baidupan" / "scripts" / "baidupan_env.py"


def load_module():
    spec = importlib.util.spec_from_file_location("baidupan_env", ENV_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BaidupanConfigTests(unittest.TestCase):
    def test_private_config_selects_community_provider_without_loading_provider_overrides(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "config.yml"
            config.write_text(
                """schema_version: 1
provider: community
binary: baidupan-cli
env:
  BAIDUPAN_APP_KEY: \"secret-key\"
  BAIDUPAN_APP_SECRET: \"secret-value\"
  BAIDUPAN_APP_NAME: \"soia-pkm-test\"
  BDPAN_CONFIG_PATH: \"/must-not-be-loaded\"
""",
                encoding="utf-8",
            )
            previous = os.environ.get("SOIA_PKM_BAIDUPAN_CONFIG_FILE")
            try:
                os.environ["SOIA_PKM_BAIDUPAN_CONFIG_FILE"] = str(config)
                for key in ("BAIDUPAN_APP_KEY", "BAIDUPAN_APP_SECRET", "BAIDUPAN_APP_NAME"):
                    os.environ.pop(key, None)
                loaded = module.load_private_config(required=True)
                self.assertEqual(module.configured_binary(), "baidupan-cli")
                self.assertNotIn("BDPAN_CONFIG_PATH", loaded["env"])
                module.load_private_env(required=True)
                self.assertEqual(os.environ["BAIDUPAN_APP_NAME"], "soia-pkm-test")
                self.assertNotIn("BDPAN_CONFIG_PATH", os.environ)
            finally:
                if previous is None:
                    os.environ.pop("SOIA_PKM_BAIDUPAN_CONFIG_FILE", None)
                else:
                    os.environ["SOIA_PKM_BAIDUPAN_CONFIG_FILE"] = previous
                for key in ("BAIDUPAN_APP_KEY", "BAIDUPAN_APP_SECRET", "BAIDUPAN_APP_NAME"):
                    os.environ.pop(key, None)


if __name__ == "__main__":
    unittest.main()
