"""tools/build_installer.py puts the current Lizard_Updater.py into the installer template and nothing else."""

import contextlib
import html
import importlib.util
import io
import os
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape


REPO_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_installer", REPO_ROOT / "tools" / "build_installer.py")
TOOL = importlib.util.module_from_spec(spec)
spec.loader.exec_module(TOOL)

OLD_UPDATER = '"""\nUpdate the TRNLizard script components OLD_INSTALLER_MARKER\n"""\ndef runUpdater(a < b & c):\n    pass\n'
TEMPLATE = ('<Archive><chunk name="Object"><items>'
            '<item name="Name" type_name="gh_string" type_code="10">Lizard_Updater</item>'
            '<item name="CodeInput" type_name="gh_string" type_code="10">{0}</item>'
            '</items></chunk><chunk name="Object"><items>'
            '<item name="UserText" type_name="gh_string" type_code="10">log</item>'
            '</items></chunk></Archive>').format(escape(OLD_UPDATER))


class BuildInstallerTests(unittest.TestCase):
    def test_the_updater_code_is_replaced_and_escaped(self):
        code = (REPO_ROOT / "Lizard_Updater.py").read_text(encoding="utf-8-sig")
        result = TOOL.fillTemplate(TEMPLATE, code)
        items = TOOL.updaterItems(result)
        self.assertEqual(1, len(items))
        self.assertEqual(code.replace("\n", "\r\n"), html.unescape(items[0].group(2)))
        self.assertIn('<item name="UserText" type_name="gh_string" type_code="10">log</item>', result)
        self.assertNotIn("OLD_INSTALLER_MARKER", result)

    def test_the_committed_template_is_unchanged_when_its_code_is_current(self):
        import tempfile, os
        template = REPO_ROOT / "installer" / "TRNLizard_Installer.ghx"
        if not template.exists():
            self.skipTest("no installer template")
        out = os.path.join(tempfile.mkdtemp(), "installer.ghx")
        TOOL.main(["--out", out])
        result = open(out, "rb").read()
        self.assertTrue(result.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(result.count(b"\r\n"), result.count(b"\n"))     # CRLF only, as Grasshopper wrote it
        self.assertEqual(1, len(TOOL.updaterItems(result.decode("utf-8-sig"))))

    def test_exactly_one_updater_is_required(self):
        self.assertRaises(ValueError, TOOL.fillTemplate, TEMPLATE.replace("Update the TRNLizard", "Other"), "x")
        twice = TEMPLATE.replace("</Archive>", TEMPLATE[len("<Archive>"):])
        self.assertRaises(ValueError, TOOL.fillTemplate, twice, "x")


SHA = "0123456789abcdef0123456789abcdef01234567"
SOURCE = "https://github.com/o/r/commit/" + SHA


class PinReleaseTests(unittest.TestCase):
    def build(self, *arguments):
        with tempfile.TemporaryDirectory() as folder:
            out = os.path.join(folder, "installer.ghx")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, TOOL.main(["--out", out] + list(arguments)))
            with open(out, "rb") as handle:
                return handle.read()

    def items(self, chunk):
        return dict((item.get("name"), item) for item in chunk.findall("items/item"))

    def setUp(self):
        self.raw = self.build("--source", SOURCE, "--release", "V9.8.7")
        self.xml = self.raw.decode("utf-8-sig")
        self.root = ET.fromstring(self.xml)
        self.definition = self.root.find(".//chunk[@name='DefinitionObjects']")
        self.objects = self.definition.findall("chunks/chunk[@name='Object']")

    def panel(self, nickname):
        for chunk in self.objects:
            container = chunk.find("chunks/chunk[@name='Container']")
            if container is not None and self.items(container).get("NickName") is not None and self.items(container)["NickName"].text == nickname:
                return container
        self.fail("no object named " + nickname)

    def test_the_file_stays_as_grasshopper_writes_it(self):
        self.assertTrue(self.raw.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(self.raw.count(b"\r\n"), self.raw.count(b"\n"))

    def test_every_count_is_right(self):
        for chunk in self.root.iter("chunk"):
            for name, tag in (("items", "item"), ("chunks", "chunk")):
                block = chunk.find(name)
                if block is not None:
                    self.assertEqual(int(block.get("count")), len(block.findall(tag)), chunk.get("name"))
        self.assertEqual(7, int(self.items(self.definition)["ObjectCount"].text))
        self.assertEqual([str(i) for i in range(7)], [chunk.get("index") for chunk in self.objects])

    def test_the_source_panel_is_wired_to_the_updater(self):
        panel = self.panel("source V9.8.7")
        items = self.items(panel)
        self.assertEqual(SOURCE, items["UserText"].text)
        self.assertEqual("0", items["SourceCount"].text)
        self.assertNotIn("Source", items)
        params = [p for p in self.root.iter("chunk") if p.get("name") == "InputParam" and self.items(p)["Name"].text == "source"]
        self.assertEqual(1, len(params))
        param = self.items(params[0])
        self.assertEqual("1", param["SourceCount"].text)
        self.assertEqual(items["InstanceGuid"].text, param["Source"].text)
        guids = [item.text for item in self.root.iter("item") if item.get("name") == "InstanceGuid"]
        self.assertEqual(len(guids), len(set(guids)))

    def test_the_updater_reads_the_commit(self):
        text = (REPO_ROOT / "Lizard_Updater.py").read_text(encoding="utf-8-sig")
        first = text.index("GITHUB_PREFIXES = (")
        scope = {"re": re, "DEFAULT_SOURCE": "x", "DEFAULT_REF": "main", "SCRIPTS_FOLDER": "components"}
        exec(text[first:text.index("def isCommitSha(text):", first)], scope)
        self.assertEqual({"kind": "github", "owner": "o", "repo": "r", "ref": SHA}, scope["parseSource"](SOURCE))

    def test_the_panels_carry_the_release(self):
        items = self.items(self.panel("TRNLizard V9.8.7"))
        self.assertTrue(items["UserText"].text.startswith("TRNLizard installer V9.8.7"))
        self.assertIn("fixes the scripts to this release", items["UserText"].text)
        self.assertNotIn("Optional: connect", items["UserText"].text)

    def test_the_updater_code_is_still_current(self):
        code = (REPO_ROOT / "Lizard_Updater.py").read_text(encoding="utf-8-sig")
        items = TOOL.updaterItems(self.xml)
        self.assertEqual(1, len(items))
        self.assertEqual(code.replace("\n", "\r\n"), html.unescape(items[0].group(2)))

    def test_without_a_release_nothing_is_pinned(self):
        xml = self.build().decode("utf-8-sig")
        self.assertIn('<item name="ObjectCount" type_name="gh_int32" type_code="3">6</item>', xml)
        self.assertNotIn("fixes the scripts", xml)

    def test_source_and_release_belong_together(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            TOOL.main(["--source", SOURCE])

    def test_a_connected_source_is_refused(self):
        with open(TOOL.TEMPLATE, "rb") as handle:
            xml = handle.read().decode("utf-8-sig")
        pinned = TOOL.pinRelease(xml, SOURCE, "V1")
        with self.assertRaisesRegex(ValueError, "already connected"):
            TOOL.wireSource(pinned, "other")


if __name__ == "__main__":
    unittest.main()
