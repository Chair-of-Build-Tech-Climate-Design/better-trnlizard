"""Lizard_Updater upgrades itself from a GitHub source when the manifest names a higher UPDATER_VERSION.

The new script must match the manifest hash, say the announced version and compile in the Python that runs the component;
anything else is refused with a pointer to the installer. Whether real Grasshopper recompiles a component that changes
its own code from a ScheduleSolution callback is the manual test in Rhino 7 and 8; here the fakes of
test_updater_gh_glue.py show that the updater drives the same members as for any other component.
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import test_updater_gh_glue as glue  # noqa: E402
import test_updater_github as github_tests  # noqa: E402
from test_updater_github import FakeGitHub, load_tool, manifest_text  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
UPDATER_SOURCE = REPO_ROOT / "components" / "Lizard_Updater.py"
HYGRO_SOURCE = REPO_ROOT / "components" / "Lizard_Hygro.py"
SHA = github_tests.SHA
UPDATER_PATH = "components/Lizard_Updater.py"
UPDATER = github_tests.UPDATER
INSTALLER_ADVICE = "TRNLizard_Installer.ghx of the latest release"


def manifest_with_updater(scripts, version, code=None, sha=None, fmt=2):
    files = {name: {"sha256": UPDATER.getHash(text), "size": len(text)} for name, text in scripts.items()}
    code = code if code is not None else scripts[UPDATER_PATH]
    return json.dumps({"format": fmt, "generated": "2026-11-04T10:00:00Z",
                       "updater": {"path": UPDATER_PATH, "version": version, "sha256": sha or UPDATER.getHash(code)},
                       "files": files})


class VersionTests(unittest.TestCase):
    def test_the_version_of_a_script(self):
        self.assertEqual(7, UPDATER.parseUpdaterVersion("a = 1\nUPDATER_VERSION = 7   # note\nb = 2\n"))
        self.assertEqual(7, UPDATER.parseUpdaterVersion("UPDATER_VERSION=7\r\n"))

    def test_a_script_from_before_the_version_has_none(self):
        self.assertIsNone(UPDATER.parseUpdaterVersion("a = 1\n"))
        self.assertIsNone(UPDATER.parseUpdaterVersion(None))
        self.assertIsNone(UPDATER.parseUpdaterVersion("    UPDATER_VERSION = 7\n"))   # not at the top level
        self.assertIsNone(UPDATER.parseUpdaterVersion("x = 'UPDATER_VERSION = 7'\n"))

    def test_this_updater_says_its_version(self):
        code = UPDATER_SOURCE.read_text(encoding="utf-8-sig")
        self.assertEqual(UPDATER.UPDATER_VERSION, UPDATER.parseUpdaterVersion(code))
        self.assertGreaterEqual(UPDATER.UPDATER_VERSION, 1)

    def test_a_newer_updater_is_not_called_outdated_by_an_older_source(self):
        self.assertIsNone(UPDATER.selfCheckMessage("UPDATER_VERSION = 2\na = 1\n", "UPDATER_VERSION = 1\na = 2\n", "f.py"))
        self.assertIsNone(UPDATER.selfCheckMessage("UPDATER_VERSION = 2\na = 1\n", "a = 2\n", "f.py"))

    def test_an_updater_of_the_same_or_a_lower_version_is_outdated(self):
        for own in ("UPDATER_VERSION = 2\na = 1\n", "UPDATER_VERSION = 1\na = 1\n", "a = 1\n"):
            self.assertIn("outdated", UPDATER.selfCheckMessage(own, "UPDATER_VERSION = 2\na = 2\n", "f.py"), own)

    def test_the_message_no_longer_says_the_updater_never_updates_itself(self):
        self.assertNotIn("never", UPDATER.selfCheckMessage("a = 1\n", "a = 2\n", "f.py"))


class SyntaxCheckTests(unittest.TestCase):
    def test_a_good_script_passes(self):
        self.assertIsNone(UPDATER.checkCodeSyntax('"""doc"""\r\nx = 1\r\n'))
        self.assertIsNone(UPDATER.checkCodeSyntax(UPDATER_SOURCE.read_text(encoding="utf-8-sig")))

    def test_a_broken_script_gives_the_error(self):
        problem = UPDATER.checkCodeSyntax("def broken(:\n    pass\n")
        self.assertIsInstance(problem, str)
        self.assertTrue(problem)

    def test_a_bad_indent_is_found(self):
        self.assertTrue(UPDATER.checkCodeSyntax("if True:\nx = 1\n"))

    def test_nothing_of_the_script_is_run(self):
        self.assertIsNone(UPDATER.checkCodeSyntax("raise RuntimeError('must not run')\n"))


class UpdaterEntryTests(unittest.TestCase):
    GOOD = {"path": UPDATER_PATH, "version": 3, "sha256": "a" * 64}

    def parse(self, entry, **extra):
        return UPDATER.parseUpdaterEntry(json.dumps(dict({"format": 2, "files": {}, "updater": entry}, **extra)))

    def test_a_valid_entry(self):
        self.assertEqual(self.GOOD, self.parse(self.GOOD))

    def test_it_is_read_whatever_the_format(self):
        self.assertEqual(self.GOOD, self.parse(self.GOOD, format=99))

    def test_no_entry(self):
        self.assertIsNone(UPDATER.parseUpdaterEntry(json.dumps({"format": 1, "files": {}})))

    def test_invalid_text(self):
        for text in ("{not json", "[]", "1"):
            self.assertIsNone(UPDATER.parseUpdaterEntry(text), text)

    def test_invalid_entries(self):
        changes = ({"path": "../x.py"}, {"path": "sub/x.py"}, {"path": "C:x.py"}, {"path": "x.txt"}, {"path": 1},
                   {"version": 0}, {"version": -1}, {"version": True}, {"version": "3"}, {"version": 1.5},
                   {"sha256": "abc"}, {"sha256": "g" * 64}, {"sha256": None})
        for change in changes:
            self.assertIsNone(self.parse(dict(self.GOOD, **change)), change)
        self.assertIsNone(self.parse("x"))
        self.assertIsNone(self.parse({"path": UPDATER_PATH}))


class ManifestToolTests(unittest.TestCase):
    def setUp(self):
        self.tool = load_tool()
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        (self.root / "components").mkdir()
        self.script = self.root / "components" / "Lizard_Updater.py"
        self.script.write_text("UPDATER_VERSION = 3\nx = 1\n", encoding="utf-8")
        self.path = self.root / "trnlizard_manifest.json"
        self.out = mock.patch("sys.stdout", new=__import__("io").StringIO())

    def run_tool(self, *args):
        with self.out as stream:
            code = self.tool.main(list(args) + ["--root", str(self.root)])
            return code, stream.getvalue()

    def manifest(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def test_the_manifest_names_the_updater(self):
        self.assertEqual(0, self.run_tool()[0])
        self.assertEqual({"path": UPDATER_PATH, "version": 3, "sha256": UPDATER.getHash("UPDATER_VERSION = 3\nx = 1\n")},
                         self.manifest()["updater"])
        self.assertEqual(0, self.run_tool("--check")[0])

    def test_a_repository_without_the_updater_has_no_entry(self):
        self.script.unlink()
        (self.root / "components" / "Lizard_A.py").write_text("a = 1\n", encoding="utf-8")
        self.assertEqual(0, self.run_tool()[0])
        self.assertNotIn("updater", self.manifest())

    def test_a_changed_updater_with_the_same_version_is_refused(self):
        self.assertEqual(0, self.run_tool()[0])
        before = self.path.read_text(encoding="utf-8")
        self.script.write_text("UPDATER_VERSION = 3\nx = 2\n", encoding="utf-8")
        code, output = self.run_tool()
        self.assertEqual(1, code)
        self.assertIn("UPDATER_VERSION", output)
        self.assertEqual(before, self.path.read_text(encoding="utf-8"))

    def test_a_changed_updater_with_a_lower_version_is_refused(self):
        self.assertEqual(0, self.run_tool()[0])
        self.script.write_text("UPDATER_VERSION = 2\nx = 2\n", encoding="utf-8")
        self.assertEqual(1, self.run_tool()[0])

    def test_a_changed_updater_with_a_higher_version_is_written(self):
        self.assertEqual(0, self.run_tool()[0])
        self.script.write_text("UPDATER_VERSION = 4\nx = 2\n", encoding="utf-8")
        self.assertEqual(0, self.run_tool()[0])
        self.assertEqual(4, self.manifest()["updater"]["version"])

    def test_an_updater_without_a_version_is_refused(self):
        self.script.write_text("x = 1\n", encoding="utf-8")
        code, output = self.run_tool()
        self.assertEqual(1, code)
        self.assertIn("UPDATER_VERSION", output)

    def test_an_outdated_entry_makes_the_manifest_stale(self):
        self.assertEqual(0, self.run_tool()[0])
        data = self.manifest()
        data["updater"]["version"] = 1
        self.path.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(1, self.run_tool("--check")[0])

    def test_the_committed_manifest_names_the_current_updater(self):
        manifest = json.loads((REPO_ROOT / "trnlizard_manifest.json").read_text(encoding="utf-8"))
        code = UPDATER_SOURCE.read_text(encoding="utf-8-sig")
        self.assertEqual({"path": UPDATER_PATH, "version": UPDATER.UPDATER_VERSION, "sha256": UPDATER.getHash(code)},
                         manifest["updater"])


class SyncTests(unittest.TestCase):
    NEW = "UPDATER_VERSION = 7\nx = 1\n"

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.scripts = {UPDATER_PATH: self.NEW, "components/Lizard_A.py": "a = 1\n"}
        self.github = FakeGitHub(self.scripts)
        self.github.manifest_override = manifest_with_updater(self.scripts, 7)
        patcher = mock.patch.object(UPDATER, "UPDATER_VERSION", 5)
        patcher.start()
        self.addCleanup(patcher.stop)
        sleeper = mock.patch("time.sleep")
        sleeper.start()
        self.addCleanup(sleeper.stop)
        self.cache = os.path.join(self.root, "o_r_main")

    def sync(self, upgrade=None):
        log, errors = [], []
        info = {"kind": "github", "owner": "o", "repo": "r", "ref": "main"}
        upgrade = {} if upgrade is None else upgrade
        return UPDATER.syncGitHubSource(info, log, errors, fetch=self.github, root=self.root, upgrade=upgrade), upgrade, log, errors

    def test_a_higher_version_is_handed_over_and_nothing_else_is_done(self):
        folder, upgrade, log, errors = self.sync()
        self.assertIsNone(folder)
        self.assertEqual([], errors)
        self.assertEqual(self.NEW, upgrade["code"])
        self.assertEqual(7, upgrade["version"])
        self.assertEqual(["Lizard_Updater.py"], self.github.downloads())
        self.assertFalse(os.path.exists(self.cache))

    def test_the_script_comes_from_the_commit_of_the_manifest(self):
        self.sync()
        urls = [url for url, _ in self.github.calls]
        self.assertIn("https://raw.githubusercontent.com/o/r/{0}/{1}".format(SHA, UPDATER_PATH), urls)

    def test_the_same_or_a_lower_version_is_a_normal_update(self):
        for version in (5, 4):
            shutil.rmtree(self.cache, ignore_errors=True)
            self.github.manifest_override = manifest_with_updater(self.scripts, version)
            folder, upgrade, log, errors = self.sync()
            self.assertEqual(self.cache, folder)
            self.assertEqual([], errors)
            self.assertNotIn("code", upgrade)

    def test_a_manifest_without_the_entry_is_a_normal_update(self):
        self.github.manifest_override = manifest_text(self.scripts, fmt=2)
        folder, upgrade, log, errors = self.sync()
        self.assertEqual(self.cache, folder)
        self.assertNotIn("code", upgrade)

    def assert_refused(self, fragment):
        folder, upgrade, log, errors = self.sync()
        self.assertNotIn("code", upgrade)
        self.assertEqual(self.cache, folder)   # this updater carries on with the update
        self.assertEqual(1, len(errors), errors)
        for text in ("not upgraded to version 7", fragment, "https://github.com/o/r", INSTALLER_ADVICE):
            self.assertIn(text, errors[0])
        self.assertIn("Error: " + errors[0], log)
        return errors[0]

    def test_a_syntax_error_is_refused_with_the_installer_as_the_way(self):
        broken = "UPDATER_VERSION = 7\ndef broken(:\n"
        self.scripts[UPDATER_PATH] = broken
        self.github = FakeGitHub(self.scripts)
        self.github.manifest_override = manifest_with_updater(self.scripts, 7)
        self.assert_refused("syntax check")

    def test_a_download_that_does_not_match_the_manifest_is_refused(self):
        self.github.manifest_override = manifest_with_updater(self.scripts, 7, sha="b" * 64)
        self.github.served["components/Lizard_Updater.py"] = self.NEW
        folder, upgrade, log, errors = self.sync()
        self.assertNotIn("code", upgrade)
        self.assertTrue(any("not upgraded to version 7" in e and INSTALLER_ADVICE in e for e in errors), errors)

    def test_a_script_that_says_another_version_is_refused(self):
        self.scripts[UPDATER_PATH] = "UPDATER_VERSION = 6\nx = 1\n"
        self.github = FakeGitHub(self.scripts)
        self.github.manifest_override = manifest_with_updater(self.scripts, 7)
        self.assert_refused("version 6")

    def test_a_failed_download_is_refused(self):
        self.github.fail(UPDATER_PATH, 404)
        folder, upgrade, log, errors = self.sync()
        self.assertNotIn("code", upgrade)
        self.assertTrue(any("not upgraded to version 7" in e and INSTALLER_ADVICE in e for e in errors), errors)

    def test_an_upgrade_that_did_not_take_effect_is_not_tried_again(self):
        sha = UPDATER.getHash(self.NEW)
        folder, upgrade, log, errors = self.sync({"attempted": sha})
        self.assertNotIn("code", upgrade)
        self.assertEqual(self.cache, folder)
        self.assertIn("did not take effect", errors[0])
        self.assertIn(INSTALLER_ADVICE, errors[0])

    def test_another_version_is_tried_after_a_failed_one(self):
        folder, upgrade, log, errors = self.sync({"attempted": "c" * 64})
        self.assertEqual(self.NEW, upgrade["code"])

    def test_without_the_upgrade_argument_nothing_is_upgraded(self):
        log, errors = [], []
        info = {"kind": "github", "owner": "o", "repo": "r", "ref": "main"}
        self.assertEqual(self.cache, UPDATER.syncGitHubSource(info, log, errors, fetch=self.github, root=self.root))
        self.assertEqual([], errors)

    def test_a_format_too_new_with_a_higher_updater_is_an_upgrade_and_no_error(self):
        self.github.manifest_override = manifest_with_updater(self.scripts, 7, fmt=UPDATER.MANIFEST_FORMAT + 1)
        folder, upgrade, log, errors = self.sync()
        self.assertEqual([], errors)
        self.assertEqual(self.NEW, upgrade["code"])

    def test_a_format_too_new_with_a_refused_upgrade_says_both(self):
        self.scripts[UPDATER_PATH] = "UPDATER_VERSION = 7\ndef broken(:\n"
        self.github = FakeGitHub(self.scripts)
        self.github.manifest_override = manifest_with_updater(self.scripts, 7, fmt=UPDATER.MANIFEST_FORMAT + 1)
        folder, upgrade, log, errors = self.sync()
        self.assertIsNone(folder)
        self.assertEqual(2, len(errors), errors)
        self.assertIn("syntax check", errors[0])
        self.assertIn("too old", errors[1])


class GlueTests(unittest.TestCase):
    def setUp(self):
        glue.SNAPSHOTS.clear()
        del glue.UNDO[:]
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        patcher = mock.patch.dict(sys.modules, glue.fake_modules())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.current = UPDATER_SOURCE.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
        self.version = int(UPDATER.UPDATER_VERSION)
        self.hygro_code = HYGRO_SOURCE.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
        self.updater = self.load(self.current)
        self.component = glue.LegacyGhPython(
            "Lizard_Updater", [glue.ScriptVariable(n) for n in ("source", "runUpdate", "makeUserObjects", "cleanOldUserObjects")],
            [glue.Param("log")], code=self.current)
        self.component.CreateAttributes()
        self.hygro = glue.LegacyGhPython("Lizard_Hygro", [glue.ScriptVariable(n) for n in glue.HYGRO_INPUTS_BEFORE],
                                         [glue.Param("SurfaceInfo")], code="old hygro code")
        self.hygro.CreateAttributes()
        self.doc = glue.Document([self.hygro, self.component])
        self.publish(self.newer())

    def load(self, code):
        path = self.root / "loaded_{0}.py".format(len(list(self.root.glob("loaded_*"))))
        path.write_text(code, encoding="utf-8")
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def newer(self, text=""):
        marker = "UPDATER_VERSION = {0}".format(self.version)
        self.assertIn(marker, self.current)
        return self.current.replace(marker, "UPDATER_VERSION = {0}".format(self.version + 1)) + text

    def publish(self, code, version=None, entry=True):
        self.files = {UPDATER_PATH: code, "components/Lizard_Hygro.py": self.hygro_code}
        data = {"format": 2, "generated": "2026-11-04T10:00:00Z",
                "files": {n: {"sha256": UPDATER.getHash(t), "size": len(t)} for n, t in self.files.items()}}
        if entry:
            data["updater"] = {"path": UPDATER_PATH, "version": version or self.version + 1, "sha256": UPDATER.getHash(code)}
        self.files["trnlizard_manifest.json"] = json.dumps(data)

    def fetch(self, updater):
        def get(url, accept=None):
            if "api.github.com" in url:
                return SHA
            for name, text in self.files.items():
                if url.endswith("/" + name):
                    return text
            raise updater.SourceError(updater.describeHttpFailure(url, 404, "Not Found"), 404)
        return get

    def run_updater(self, updater=None, force=None, source="https://github.com/o/r"):
        updater = updater or self.updater
        self.component.OnPingDocument = lambda: self.doc
        updater.ghenv = SimpleNamespace(Component=self.component)
        updater.httpGetText = self.fetch(updater)
        updater.sourceCacheRoot = lambda: str(self.root / "cache")
        return updater.runUpdater(source, True, False, None, force)

    def apply_scheduled(self):
        self.assertEqual(1, len(self.doc.scheduled))
        self.doc.scheduled.pop()(self.doc)

    def test_the_new_script_replaces_this_component_after_the_solution(self):
        log, updated, skipped, errors = self.run_updater()
        self.assertEqual([], errors)
        self.assertEqual(self.current, self.component.Code)   # nothing changed during the solution
        self.assertTrue(any("upgrade" in line and str(self.version + 1) in line for line in log), log)
        self.apply_scheduled()
        self.assertEqual(self.updater.stampCode(self.newer()), self.component.Code)
        self.assertGreater(self.component.expired, 0)

    def test_nothing_else_is_updated_by_the_old_code(self):
        log, updated, skipped, errors = self.run_updater()
        self.assertEqual([], updated)
        self.apply_scheduled()
        self.assertEqual("old hygro code", self.hygro.Code)
        self.assertFalse((self.root / "cache").exists() and list((self.root / "cache").rglob("*.py")))

    def test_a_new_input_of_the_updater_is_added_in_place(self):
        self.run_updater()
        self.apply_scheduled()
        self.assertEqual(["source", "runUpdate", "makeUserObjects", "cleanOldUserObjects", "force"],
                         [p.Name for p in self.component.Params.Input])
        self.assertFalse(self.component.Locked)

    def test_the_new_code_carries_on_with_the_update_and_reports_the_upgrade(self):
        self.run_updater()
        self.apply_scheduled()
        new = self.load(self.newer())
        log, updated, skipped, errors = self.run_updater(new)
        self.assertEqual([], errors)
        self.assertEqual(["Lizard_Hygro"], updated)
        self.assertTrue(any("upgraded" in line and str(self.version + 1) in line for line in log), log)
        self.apply_scheduled()
        self.assertEqual(new.stampCode(self.hygro_code), self.hygro.Code)
        self.assertEqual(new.stampCode(self.newer()), self.component.Code)

    def test_the_rhino_8_python_3_component_is_upgraded_through_its_source(self):
        self.component = glue.Python3Script(
            "Lizard_Updater", [glue.RhinoCodeParam(n) for n in ("source", "runUpdate", "makeUserObjects", "cleanOldUserObjects")],
            [glue.Param("log")], code=self.current)
        self.component.CreateAttributes()
        self.doc = glue.Document([self.hygro, self.component])
        log, updated, skipped, errors = self.run_updater()
        self.assertEqual([], errors)
        self.apply_scheduled()
        self.assertEqual(self.updater.stampCode(self.newer()), self.component.source)

    def test_an_upgrade_that_did_not_take_effect_does_not_loop(self):
        self.run_updater()
        self.apply_scheduled()
        # the component still runs the old code, as if Grasshopper had not recompiled it
        log, updated, skipped, errors = self.run_updater()
        self.assertEqual(["Lizard_Hygro"], updated)
        self.assertTrue(any("did not take effect" in e and INSTALLER_ADVICE in e for e in errors), errors)
        code = self.component.Code
        self.apply_scheduled()
        self.assertEqual(code, self.component.Code)

    def test_a_script_with_a_syntax_error_is_refused_and_the_update_goes_on(self):
        self.publish(self.newer("\ndef broken(:\n"))
        log, updated, skipped, errors = self.run_updater()
        self.assertEqual(self.current, self.component.Code)
        self.assertEqual(["Lizard_Hygro"], updated)
        refusal = [e for e in errors if "not upgraded" in e]
        self.assertEqual(1, len(refusal), errors)
        for fragment in ("syntax check", "https://github.com/o/r", INSTALLER_ADVICE):
            self.assertIn(fragment, refusal[0])
        self.apply_scheduled()
        self.assertEqual(self.current, self.component.Code)
        self.assertEqual(self.updater.stampCode(self.hygro_code), self.hygro.Code)

    def test_an_updater_changed_by_hand_is_kept_until_force(self):
        changed = self.updater.stampCode(self.current) + "\n# my change\n"
        self.component.Code = changed
        log, updated, skipped, errors = self.run_updater()
        self.assertEqual(changed, self.component.Code)
        self.assertTrue(any("changed by hand" in e and "force" in e for e in errors), errors)
        self.assertFalse(any(".." in e for e in errors), errors)
        self.assertEqual(["Lizard_Hygro"], updated)
        self.apply_scheduled()
        self.assertEqual(changed, self.component.Code)

        sys.modules["scriptcontext"].sticky.clear()
        log, updated, skipped, errors = self.run_updater(force=True)
        self.assertEqual([], [e for e in errors if "changed by hand" in e])
        self.apply_scheduled()
        self.assertEqual(self.updater.stampCode(self.newer()), self.component.Code)

    def test_an_updater_that_would_lose_an_input_is_refused(self):
        self.publish(self.newer().replace("    cleanOldUserObjects (bool):", "    renamed (bool):", 1))
        log, updated, skipped, errors = self.run_updater()
        self.assertEqual(self.current, self.component.Code)
        self.assertEqual(["Lizard_Hygro"], updated)
        self.assertFalse(self.component.Locked)
        self.assertTrue(any("not upgraded" in e and INSTALLER_ADVICE in e for e in errors), errors)

    def test_a_local_folder_never_upgrades_the_updater(self):
        folder = self.root / "clone"
        (folder / "components").mkdir(parents=True)
        (folder / "components" / "Lizard_Updater.py").write_text(self.newer(), encoding="utf-8")
        (folder / "components" / "Lizard_Hygro.py").write_text(self.hygro_code, encoding="utf-8")
        (folder / "trnlizard_manifest.json").write_text(self.files["trnlizard_manifest.json"], encoding="utf-8")
        log, updated, skipped, errors = self.run_updater(source=str(folder))
        self.assertEqual(["Lizard_Hygro"], updated)
        self.apply_scheduled()
        self.assertEqual(self.current, self.component.Code)
        self.assertTrue(any("outdated" in e and "by hand" in e for e in errors), errors)

    def test_a_current_updater_with_its_hash_does_nothing_special(self):
        self.publish(self.current, version=self.version)
        self.component.Code = self.updater.stampCode(self.current)
        log, updated, skipped, errors = self.run_updater()
        self.assertEqual([], errors)
        self.assertEqual(["Lizard_Hygro"], updated)
        self.assertFalse(any("upgrade" in line for line in log), log)


if __name__ == "__main__":
    unittest.main()
