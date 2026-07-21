from __future__ import annotations

import base64
import importlib.util
import json
import sys
import tempfile
import unittest
import urllib.parse
import zipfile
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "soia-dev-drawio-visio-diagrams" / "scripts"


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_vsdx(path: Path, unsafe: bool = False) -> None:
    pages = """<?xml version="1.0"?>
<Pages xmlns="http://schemas.microsoft.com/office/visio/2012/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
 <Page ID="1" Name="Architecture"><Rel r:id="rId1"/></Page>
</Pages>"""
    rels = """<?xml version="1.0"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Target="page1.xml" Type="page"/>
</Relationships>"""
    page = """<?xml version="1.0"?>
<PageContents xmlns="http://schemas.microsoft.com/office/visio/2012/main">
 <Shapes>
  <Shape ID="1" Name="Service"><Text>Policy Service</Text></Shape>
  <Shape ID="2" Name="Dynamic connector"><Text>calls</Text></Shape>
 </Shapes>
 <Connects><Connect FromSheet="2" ToSheet="1"/></Connects>
</PageContents>"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("visio/document.xml", "<VisioDocument/>")
        archive.writestr("visio/pages/pages.xml", pages)
        archive.writestr("visio/pages/_rels/pages.xml.rels", rels)
        archive.writestr("visio/pages/page1.xml", page)
        if unsafe:
            archive.writestr("../escape.xml", "<x/>")


def write_drawio(path: Path, compressed: bool = False) -> None:
    graph = """<mxGraphModel><root>
<mxCell id="0"/><mxCell id="1" parent="0"/>
<mxCell id="node-1" value="Legacy Gateway" style="fillColor=#ffffff;" vertex="1" parent="1"><mxGeometry x="10" y="20" width="120" height="40" as="geometry"/></mxCell>
<mxCell id="edge-1" value="routes" edge="1" source="node-1" target="node-1" parent="1"><mxGeometry relative="1" as="geometry"/></mxCell>
</root></mxGraphModel>"""
    if compressed:
        encoded = urllib.parse.quote(graph, safe="~()*!.'-_")
        compressor = zlib.compressobj(wbits=-15)
        payload = base64.b64encode(compressor.compress(encoded.encode()) + compressor.flush()).decode()
        body = payload
    else:
        body = graph
    path.write_text(f'<mxfile><diagram id="p1" name="Page-1">{body}</diagram></mxfile>', encoding="utf-8")


class DrawioVisioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vsdx = load_module("inspect_vsdx")
        cls.drawio = load_module("inspect_drawio")
        cls.editor = load_module("edit_drawio")
        cls.cli = load_module("drawio_cli")

    def test_inspect_vsdx_extracts_pages_shapes_text_and_connections(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "fixture.vsdx"
            write_vsdx(source)
            result = self.vsdx.inspect_vsdx(source)
            self.assertEqual(result["page_count"], 1)
            self.assertEqual(result["shape_count"], 2)
            self.assertEqual(result["connect_record_count"], 1)
            self.assertEqual(result["pages"][0]["name"], "Architecture")
            self.assertIn("Policy Service", result["texts"])

    def test_inspect_vsdx_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "unsafe.vsdx"
            write_vsdx(source, unsafe=True)
            with self.assertRaises(self.vsdx.InspectionError):
                self.vsdx.inspect_vsdx(source)

    def test_inspect_drawio_supports_uncompressed_and_compressed_pages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for compressed in (False, True):
                source = root / f"fixture-{compressed}.drawio"
                write_drawio(source, compressed=compressed)
                result = self.drawio.inspect_drawio(source)
                self.assertEqual(result["page_count"], 1)
                self.assertEqual(result["vertex_count"], 1)
                self.assertEqual(result["edge_count"], 1)
                self.assertIn("Legacy Gateway", result["texts"])

    def test_edit_plan_changes_copy_and_preserves_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.drawio"
            output = root / "upgraded.drawio"
            plan = root / "plan.json"
            write_drawio(source)
            before = source.read_bytes()
            plan.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "rename_pages": [{"from": "Page-1", "to": "Production"}],
                        "replace_text": [{"from": "Legacy Gateway", "to": "API Gateway", "match": "exact"}],
                        "set_style": [{"cell_id": "node-1", "properties": {"fillColor": "#dae8fc"}}],
                        "set_geometry": [{"cell_id": "node-1", "x": 30, "width": 160}],
                    }
                ),
                encoding="utf-8",
            )
            receipt = self.editor.apply_plan(source, plan, output)
            self.assertEqual(source.read_bytes(), before)
            self.assertTrue(output.exists())
            self.assertEqual(receipt["changes"], {"rename_pages": 1, "replace_text": 1, "set_style": 1, "set_geometry": 1})
            inspected = self.drawio.inspect_drawio(output)
            self.assertEqual(inspected["pages"][0]["name"], "Production")
            self.assertIn("API Gateway", inspected["texts"])

    def test_edit_plan_fails_on_unmatched_text_and_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.drawio"
            output = root / "output.drawio"
            plan = root / "plan.json"
            write_drawio(source)
            plan.write_text(json.dumps({"schema_version": 1, "replace_text": [{"from": "missing", "to": "x"}]}), encoding="utf-8")
            with self.assertRaises(self.editor.EditError):
                self.editor.apply_plan(source, plan, output)
            output.write_text("keep", encoding="utf-8")
            with self.assertRaises(self.editor.EditError):
                self.editor.apply_plan(source, plan, output)

    def test_validate_output_checks_drawio_root_and_png_signature(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            drawio = root / "diagram.drawio"
            png = root / "diagram.png"
            write_drawio(drawio)
            png.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
            self.assertEqual(self.cli.validate_output(drawio, "drawio")["size"], drawio.stat().st_size)
            self.assertEqual(self.cli.validate_output(png, "png")["size"], png.stat().st_size)


if __name__ == "__main__":
    unittest.main()
