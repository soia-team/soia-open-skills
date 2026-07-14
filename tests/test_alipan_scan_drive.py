import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "soia-pkm-alipan" / "scripts" / "scan_drive.py"


def load_module():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("scan_drive", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScanDriveTests(unittest.TestCase):
    def test_parse_ll_output_preserves_repeated_spaces_and_sha1(self):
        module = load_module()
        output = """
当前目录: /资料
----
  1  62773faf37b033a372074651b7ceec718f4a4733  -  -  -  2022-05-08 11:57:35  2022-05-08 11:57:35  31.  课程资料/
  2  6abc  1.00KB  0123456789ABCDEF0123456789ABCDEF01234567  1024  2022-05-08 11:57:36  2022-05-08 11:57:36  讲义  最终版.pdf
                                               总: 1.00KB  文件总数: 1, 目录总数: 1
----
"""

        rows = module.parse_ll_output(output)

        self.assertEqual(
            rows,
            [
                {
                    "id": "62773faf37b033a372074651b7ceec718f4a4733",
                    "name": "31.  课程资料",
                    "dir": True,
                    "size": None,
                    "sha1": None,
                },
                {
                    "id": "6abc",
                    "name": "讲义  最终版.pdf",
                    "dir": False,
                    "size": 1024,
                    "sha1": "0123456789ABCDEF0123456789ABCDEF01234567",
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()
