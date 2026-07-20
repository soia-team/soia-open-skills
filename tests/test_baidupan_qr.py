import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "soia-pkm-baidu-netdisk-ops" / "scripts" / "decode_qr.py"


def load_module():
    spec = importlib.util.spec_from_file_location("decode_qr", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeNumpy:
    uint8 = object()

    @staticmethod
    def frombuffer(data, dtype):
        return data


class FakeDetector:
    def detectAndDecode(self, image):
        return "https://openapi.baidu.com/device?code=example", None, None


class FakeCv2:
    IMREAD_GRAYSCALE = 0
    QRCodeDetector = FakeDetector

    @staticmethod
    def imdecode(data, mode):
        return object()


class BaidupanQrTests(unittest.TestCase):
    def test_decode_image_bytes_returns_qr_payload(self):
        module = load_module()
        with patch.dict("sys.modules", {"cv2": FakeCv2, "numpy": FakeNumpy}):
            self.assertEqual(
                module.decode_image_bytes(b"image"),
                "https://openapi.baidu.com/device?code=example",
            )


if __name__ == "__main__":
    unittest.main()
