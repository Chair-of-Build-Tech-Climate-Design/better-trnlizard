"""The hash in the first line of a component script: Lizard_Updater notices scripts changed by hand.

The updater writes every script with the hash of its text in the first line. Before it replaces a script it checks that
line: a script that no longer matches was changed by hand, so it is left alone and reported unless force is True.
"""

import ast
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
from test_updater_io_sync import load_updater  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
UPDATER_SOURCE = REPO_ROOT / "components" / "Lizard_Updater.py"
HYGRO_SOURCE = REPO_ROOT / "components" / "Lizard_Hygro.py"
HYGRO_CODE = HYGRO_SOURCE.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
HYGRO_INPUTS = glue.HYGRO_INPUTS_BEFORE + glue.NEW_HYGRO_INPUTS


class StampTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.updater = load_updater()

    def test_the_hash_is_the_first_line_and_the_script_follows_unchanged(self):
        code = '"""doc"""\nx = 1\n'
        stamped = self.updater.stampCode(code)
        first, rest = stamped.split("\n", 1)
        self.assertTrue(first.startswith("# "))
        self.assertIn(self.updater.getHash(code), first)
        self.assertEqual(code, rest)

    def test_stamping_twice_gives_the_same_text(self):
        stamped = self.updater.stampCode("x = 1\n")
        self.assertEqual(stamped, self.updater.stampCode(stamped))

    def test_the_hash_line_can_be_split_off(self):
        code = "x = 1\n"
        stored, body = self.updater.splitScriptHash(self.updater.stampCode(code))
        self.assertEqual(self.updater.getHash(code), stored)
        self.assertEqual(code, body)
        self.assertEqual((None, code), self.updater.splitScriptHash(code))
        self.assertEqual((None, ""), self.updater.splitScriptHash(None))

    def test_only_the_first_line_counts_as_the_hash_line(self):
        line = self.updater.stampCode("x = 1\n").split("\n", 1)[0]
        code = "y = 2\n" + line + "\nx = 1\n"
        self.assertEqual((None, code), self.updater.splitScriptHash(code))

    def test_a_fresh_script_is_not_changed_by_hand(self):
        self.assertFalse(self.updater.isChangedByHand(self.updater.stampCode("x = 1\n")))

    def test_a_changed_script_is_changed_by_hand(self):
        self.assertTrue(self.updater.isChangedByHand(self.updater.stampCode("x = 1\n").replace("x = 1", "x = 2")))

    def test_a_script_without_the_hash_line_cannot_be_told(self):
        self.assertFalse(self.updater.isChangedByHand("x = 1\n"))
        self.assertFalse(self.updater.isChangedByHand(None))

    def test_what_grasshopper_does_to_a_saved_script_is_no_change(self):
        stamped = self.updater.stampCode("a = 1\nb = 2\n")
        self.assertFalse(self.updater.isChangedByHand(stamped.replace("\n", "\r\n")))
        self.assertFalse(self.updater.isChangedByHand("﻿" + stamped))
        self.assertFalse(self.updater.isChangedByHand(stamped + "\n\n  "))

    def test_the_docstring_and_the_params_of_a_script_stay_as_they_are(self):
        stamped = self.updater.stampCode(HYGRO_CODE)
        self.assertEqual(ast.get_docstring(ast.parse(HYGRO_CODE)), ast.get_docstring(ast.parse(stamped)))
        self.assertEqual(self.updater.parseIONames(HYGRO_CODE), self.updater.parseIONames(stamped))
        self.assertEqual(self.updater.parseDocstringIO(HYGRO_CODE), self.updater.parseDocstringIO(stamped))

    def test_the_updater_is_not_outdated_because_of_its_hash_line(self):
        code = "a = 1\n"
        self.assertIsNone(self.updater.selfCheckMessage(self.updater.stampCode(code), code, "f.py"))


class ForceInputTests(unittest.TestCase):
    def test_force_is_the_last_input_and_says_what_it_overwrites(self):
        code = UPDATER_SOURCE.read_text(encoding="utf-8")
        updater = load_updater()
        inputs, _ = updater.parseDocstringIO(code)
        force = inputs[-1]
        self.assertEqual("force", force["name"])
        self.assertEqual("bool", force["type"])
        self.assertFalse(force["required"])
        for fragment in ("overwrite", "changed by hand", "lost"):
            self.assertIn(fragment, force["description"])


class ScriptHashGlueTests(unittest.TestCase):
    def setUp(self):
        glue.SNAPSHOTS.clear()
        del glue.UNDO[:]
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        shutil.copy(HYGRO_SOURCE, self.folder / "Lizard_Hygro.py")
        (self.folder / "Lizard_Rep.py").write_text(glue.REPLACED_SCRIPT, encoding="utf-8")
        shutil.copy(UPDATER_SOURCE, self.folder / "Lizard_Updater.py")
        patcher = mock.patch.dict(sys.modules, glue.fake_modules())
        patcher.start()
        self.addCleanup(patcher.stop)
        import importlib.util
        spec = importlib.util.spec_from_file_location("Lizard_Updater_script_hash", UPDATER_SOURCE)
        self.updater = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.updater)
        self.updater_component = glue.LegacyGhPython(
            "Lizard_Updater", [glue.ScriptVariable("source"), glue.ScriptVariable("runUpdate")], [glue.Param("log")],
            code=UPDATER_SOURCE.read_text(encoding="utf-8"))

    def run_updater(self, doc, force=None):
        self.updater_component.OnPingDocument = lambda: doc
        self.updater.ghenv = SimpleNamespace(Component=self.updater_component)
        return self.updater.runUpdater(str(self.folder), True, False, None, force)

    def hygro(self, code, cls=None):
        component = (cls or glue.LegacyGhPython)("Lizard_Hygro", [glue.ScriptVariable(n) for n in HYGRO_INPUTS],
                                                 [glue.Param("SurfaceInfo")], code=code)
        component.CreateAttributes()
        return component

    def settled(self, component):
        """A component whose inputs already hold their Default and mouse-over text, so that only its code can be out of date."""
        specs = dict((p["name"], p) for p in self.updater.parseDocstringIO(HYGRO_CODE)[0])
        self.updater.applyParamDetails(component, self.updater.KIND_GHPYTHON, specs, [])
        return component

    def changed_by_hand(self, code="old script\n"):
        return self.updater.stampCode(code).replace(code, code + "my change\n")

    def test_a_written_script_gets_the_hash_line(self):
        for cls in (glue.LegacyGhPython, glue.Python3Script):
            sys.modules["scriptcontext"].sticky.clear()   # the report of the run before
            hygro = self.hygro("old script\n", cls)
            doc = glue.Document([hygro])
            self.run_updater(doc)
            doc.scheduled.pop()(doc)
            self.assertEqual(self.updater.stampCode(HYGRO_CODE), hygro.source, cls)

    def test_a_script_with_a_matching_hash_is_updated(self):
        hygro = self.hygro(self.updater.stampCode("old script\n"))
        doc = glue.Document([hygro])
        log, updated, skipped, errors = self.run_updater(doc)
        self.assertEqual(["Lizard_Hygro"], updated)
        self.assertEqual([], errors)
        doc.scheduled.pop()(doc)
        self.assertEqual(self.updater.stampCode(HYGRO_CODE), hygro.Code)

    def test_a_current_script_with_its_hash_is_left_alone(self):
        stamped = self.updater.stampCode(HYGRO_CODE)
        hygro = self.settled(self.hygro(stamped))
        doc = glue.Document([hygro])
        log, updated, skipped, errors = self.run_updater(doc)
        self.assertEqual([], updated)
        self.assertEqual(["Lizard_Hygro"], skipped)
        self.assertEqual([], doc.scheduled)

    def test_a_current_script_saved_by_grasshopper_is_left_alone(self):
        hygro = self.settled(self.hygro(self.updater.stampCode(HYGRO_CODE).replace("\n", "\r\n")))
        doc = glue.Document([hygro])
        log, updated, skipped, errors = self.run_updater(doc)
        self.assertEqual(["Lizard_Hygro"], skipped)
        self.assertEqual([], doc.scheduled)

    def test_a_current_script_without_the_hash_gets_it(self):
        hygro = self.hygro(HYGRO_CODE)
        doc = glue.Document([hygro])
        log, updated, skipped, errors = self.run_updater(doc)
        self.assertEqual(["Lizard_Hygro"], updated)
        doc.scheduled.pop()(doc)
        self.assertEqual(self.updater.stampCode(HYGRO_CODE), hygro.Code)

    def test_an_old_script_without_the_hash_is_updated_with_a_note(self):
        hygro = self.hygro("old script\n")
        doc = glue.Document([hygro])
        log, updated, skipped, errors = self.run_updater(doc)
        self.assertEqual(["Lizard_Hygro"], updated)
        self.assertEqual([], errors)
        self.assertTrue(any("no hash" in line for line in log), log)

    def test_a_script_changed_by_hand_is_left_alone_and_reported(self):
        code = self.changed_by_hand()
        hygro = self.hygro(code)
        doc = glue.Document([hygro])
        log, updated, skipped, errors = self.run_updater(doc)
        self.assertEqual([], updated)
        self.assertEqual([], doc.scheduled)
        self.assertEqual(code, hygro.Code)
        self.assertEqual(1, len(errors))
        for fragment in ("Lizard_Hygro", "changed by hand", "not updated", "force", "lost"):
            self.assertIn(fragment, errors[0])
        self.assertIn(errors[0], log)

    def test_force_overwrites_a_script_changed_by_hand_and_says_so(self):
        hygro = self.hygro(self.changed_by_hand())
        doc = glue.Document([hygro])
        log, updated, skipped, errors = self.run_updater(doc, force=True)
        self.assertEqual(["Lizard_Hygro"], updated)
        self.assertEqual([], errors)
        self.assertTrue(any(line.startswith("WARNING") and "Lizard_Hygro" in line and "overwritten" in line for line in log), log)
        doc.scheduled.pop()(doc)
        self.assertEqual(self.updater.stampCode(HYGRO_CODE), hygro.Code)

    def test_only_force_true_overwrites(self):
        for value in (None, False):
            hygro = self.hygro(self.changed_by_hand())
            log, updated, skipped, errors = self.run_updater(glue.Document([hygro]), force=value)
            self.assertEqual([], updated, value)
            self.assertEqual(1, len(errors), value)

    def test_a_script_changed_by_hand_to_the_new_script_only_gets_its_hash_again(self):
        stale = self.updater.stampCode("old script\n").replace("old script\n", HYGRO_CODE)
        hygro = self.hygro(stale)
        doc = glue.Document([hygro])
        log, updated, skipped, errors = self.run_updater(doc)
        self.assertEqual([], errors)
        self.assertEqual(["Lizard_Hygro"], updated)
        doc.scheduled.pop()(doc)
        self.assertEqual(self.updater.stampCode(HYGRO_CODE), hygro.Code)

    def test_a_component_that_would_be_replaced_is_kept_too(self):
        component = glue.LegacyGhPython("Lizard_Rep", [glue.ScriptVariable("a"), glue.ScriptVariable("b")],
                                        [glue.Param("r"), glue.Param("gone")], code=self.changed_by_hand())
        component.CreateAttributes()
        doc = glue.Document([component])
        log, updated, skipped, errors = self.run_updater(doc)
        self.assertEqual([], updated)
        self.assertEqual([], doc.scheduled)
        self.assertEqual(1, len(errors))
        self.assertFalse(component.Locked)
        log, updated, skipped, errors = self.run_updater(doc, force=True)
        self.assertEqual(["Lizard_Rep"], updated)
        doc.scheduled.pop()(doc)
        self.assertTrue(component.Locked)   # the usual replacement: the old copy keeps the changes for reference

    def test_a_template_of_a_preset_always_gets_the_script_of_the_source(self):
        hygro = self.hygro(self.changed_by_hand())
        doc = glue.Document([hygro])
        counts = {"scripts": 0, "shared": 0, "errors": []}
        scripts = {"Lizard_Hygro": str(self.folder / "Lizard_Hygro.py")}
        self.updater.updateTemplateDocument(doc, scripts, {}, counts)
        self.assertEqual([], counts["errors"])
        self.assertEqual(1, counts["scripts"])
        self.assertEqual(self.updater.stampCode(HYGRO_CODE), hygro.Code)


if __name__ == "__main__":
    unittest.main()
