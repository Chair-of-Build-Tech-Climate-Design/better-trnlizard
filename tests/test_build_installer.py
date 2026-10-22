"""tools/build_installer.py puts the current Lizard_Updater.py into the installer template and nothing else."""

import html
import importlib.util
import unittest
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


if __name__ == "__main__":
    unittest.main()
