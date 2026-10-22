"""Lizard_Updater: preset UserObjects rebuilt from their templates (trnlizard_presets.json) and shared clusters.

Pure logic (bundle parsing, shared names, rewiring pairs, hashes) is tested directly; the glue runs against the fakes of
test_updater_gh_glue.py / test_updater_userobjects.py plus a fake GH_Cluster with outer params and a document, and
loadClusterXml replaced by template factories (real templates are GH_Archive XML that only Grasshopper can read).
"""

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
import test_updater_userobjects as uo  # noqa: E402
from test_updater_io_sync import load_updater  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
UPDATER_SOURCE = REPO_ROOT / "Lizard_Updater.py"
HYGRO_SOURCE = REPO_ROOT / "Lizard_Hygro.py"
CLUSTER_ID = "f31d8d7a-7536-4ac8-9c96-fde6ecda4d0a"


def bundle(presets=None, shared=None):
    return json.dumps({"format": 1, "presets": presets or {}, "shared": shared or {}})


def entry(name, xml, **extra):
    data = {"name": name, "nickName": name.replace("TRNLizard_", ""), "description": name + " preset",
            "category": "TRNLizard", "subCategory": "0 | Basic", "xml": xml}
    data.update(extra)
    return data


# ---------------------------------------------------------------------------------------------------- fakes

class Document(glue.Document):
    def __init__(self, objects=()):
        super(Document, self).__init__(objects)
        self.removed = []
        self.UndoUtil.RecordRemoveObjectEvent = lambda name, obj: glue.UNDO.append(("remove", obj))

    def RemoveObject(self, obj, update):
        self.Objects.remove(obj)
        self.removed.append(obj)


class Group(glue.GH_Group):
    @property
    def ObjectIDs(self):
        return list(self.members)


class Cluster:
    """GH_Cluster with outer params, an inner document and a Description."""

    def __init__(self, nick="Cluster", objects=(), inputs=(), outputs=()):
        self.Name = self.NickName = nick
        self.Description = ""
        self.inner = Document(objects)
        self.InstanceGuid = glue.Guid()
        self.ComponentGuid = glue.Guid(CLUSTER_ID)
        self.Params = glue.ParamServer()
        for name in inputs:
            self.Params.Input.append(glue.Param(name))
        for name in outputs:
            self.Params.Output.append(glue.Param(name))
        self.Attributes = glue.Attributes()
        self.expired = 0

    def Document(self, password):
        return self.inner

    def CreateAttributes(self):
        self.Attributes = glue.Attributes()

    def NewInstanceGuid(self):
        self.InstanceGuid = glue.Guid()

    def ExpireSolution(self, recompute):
        self.expired += 1


def old_hygro():
    component = glue.LegacyGhPython("Lizard_Hygro", [glue.ScriptVariable(n) for n in glue.HYGRO_INPUTS_BEFORE],
                                    [glue.Param("SurfaceInfo")], code="old hygro code")
    component.CreateAttributes()
    return component


def database_template():
    return Cluster("Lizard_Database", [old_hygro()], outputs=["Data", "Data", "Data", "Data"])


def building_template():
    return Cluster("Lizard_Building_Template", [], outputs=["template"])


def preset_template():
    nested = Cluster("Inner", [old_hygro()])
    database = Cluster("Database", [], outputs=["Data", "Data", "Data", "Data"])   # the old name of Lizard_Database
    readers = [glue.Param("r%d" % i) for i in range(4)]
    for index, reader in enumerate(readers):
        reader.AddSource(database.Params.Output[index])
    group = Group()
    group.AddObject(database.InstanceGuid)
    return Cluster("TRNLizard_Template_Lite", [old_hygro(), nested, database, group] + readers)


TEMPLATES = {"preset-xml": preset_template, "database-xml": database_template, "building-xml": building_template}
SHARED = {"Lizard_Database": entry("Lizard_Database", "database-xml", role="keep", aliases=["Database"]),
          "Lizard_Building_Template": entry("Lizard_Building_Template", "building-xml", role="sync", aliases=[])}


# ---------------------------------------------------------------------------------------------------- pure logic

class PresetLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.updater = load_updater()

    def test_bundle(self):
        parsed = self.updater.parsePresets(bundle({"P": entry("TRNLizard_P", "x")}, SHARED))
        self.assertEqual(["P"], sorted(parsed["presets"]))
        self.assertEqual("TRNLizard_P", parsed["presets"]["P"]["name"])
        self.assertIsNone(parsed["presets"]["P"]["icon"])
        self.assertEqual("keep", parsed["shared"]["Lizard_Database"]["role"])
        self.assertEqual(["Database"], parsed["shared"]["Lizard_Database"]["aliases"])
        for text in ("nope", "[]", bundle({"P": {"name": "P"}}), bundle({"P": entry("P", "  ")}),
                     bundle(shared={"S": entry("S", "x")}), bundle(shared={"S": entry("S", "x", role="other")})):
            with self.subTest(text=text[:40]):
                self.assertRaises(ValueError, self.updater.parsePresets, text)

    def test_shared_names(self):
        shared = self.updater.parsePresets(bundle(shared=SHARED))["shared"]
        self.assertEqual("Lizard_Database", self.updater.sharedNameOf("Database", shared))
        self.assertEqual("Lizard_Database", self.updater.sharedNameOf("Lizard_Database", shared))
        self.assertEqual("Lizard_Building_Template", self.updater.sharedNameOf("Lizard_Building_Template", shared))
        self.assertIsNone(self.updater.sharedNameOf("Inner", shared))
        self.assertIsNone(self.updater.sharedNameOf("Database", None))

    def test_param_pairs(self):
        pairs = self.updater.pairParams
        self.assertEqual([(0, 0), (1, 1), (2, 2)], pairs(["Data", "Data", "Data"], ["Data", "Data", "Data"]))
        self.assertEqual([(1, 0)], pairs(["a", "b"], ["b", "c"]))
        self.assertEqual([], pairs(["Data", "Data"], ["Data"]))

    def test_old_trnlizard_userobjects(self):
        old = self.updater.isOldTRNLizardUserObject
        managed = {"lizard_hygro", "trnlizard_template_lite"}
        self.assertTrue(old("Lizard_Hygro", None, None, managed))
        self.assertTrue(old("Something", "TRNLizard_Template_Lite", "TRNLizard", managed))
        self.assertTrue(old("Lizard_Obsolete", "Lizard_Obsolete", "Lizard", managed))
        self.assertFalse(old("Lizard_Obsolete", "Lizard_Obsolete", "Ladybug", managed))
        self.assertFalse(old("Other", "Other", "Lizard", managed))

    def test_hashes(self):
        parsed = self.updater.parsePresets(bundle({"P": entry("P", "x")}, SHARED))
        preset, shared = parsed["presets"]["P"], parsed["shared"]
        base = self.updater.presetHash(preset, shared, "f1")
        self.assertNotEqual(base, self.updater.presetHash(preset, shared, "f2"))       # a script changed
        self.assertNotEqual(base, self.updater.presetHash(dict(preset, xml="y"), shared, "f1"))
        other = dict(shared, Lizard_Database=dict(shared["Lizard_Database"], xml="new"))
        self.assertNotEqual(base, self.updater.presetHash(preset, other, "f1"))
        self.assertNotEqual(self.updater.scriptsFingerprint({"a": "1"}), self.updater.scriptsFingerprint({"a": "2"}))
        marker = self.updater.sharedMarker(shared["Lizard_Database"])
        self.assertTrue(marker.startswith("[TRNLizard shared ") and marker.endswith("]"))


# ---------------------------------------------------------------------------------------------------- glue

class PresetGlueTests(unittest.TestCase):
    def setUp(self):
        glue.SNAPSHOTS.clear()
        del glue.UNDO[:]
        del uo.GH_UserObject.SAVED[:]
        self.folder = Path(tempfile.mkdtemp())
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copy(HYGRO_SOURCE, self.folder / "Lizard_Hygro.py")
        shutil.copy(UPDATER_SOURCE, self.folder / "Lizard_Updater.py")
        self.modules, self.ribbon = uo.userobject_modules(self.root, self.emit)
        self.modules["Grasshopper.Kernel"].Special = SimpleNamespace(GH_Cluster=Cluster, GH_Group=Group)
        patcher = mock.patch.dict(sys.modules, self.modules)
        patcher.start()
        self.addCleanup(patcher.stop)
        import importlib.util
        spec = importlib.util.spec_from_file_location("Lizard_Updater_presets", UPDATER_SOURCE)
        self.updater = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.updater)
        self.built = []

        def load(xml):
            cluster = TEMPLATES[xml]()
            self.built.append(cluster)
            return cluster
        self.updater.loadClusterXml = load
        self.updater_component = uo.EmittedLegacy(
            "Lizard_Updater", [glue.ScriptVariable("source"), glue.ScriptVariable("runUpdate")],
            [glue.Param("log")], code=UPDATER_SOURCE.read_text(encoding="utf-8"))
        self.scripts = {"Lizard_Hygro": str(self.folder / "Lizard_Hygro.py")}
        self.shared = self.updater.parsePresets(bundle(shared=SHARED))["shared"]

    def emit(self, guid):
        cls = {glue.LEGACY_ID: uo.EmittedLegacy, glue.PYTHON3_ID: uo.EmittedPython3}.get(str(guid))
        return cls() if cls else None

    def write_bundle(self, presets=None):
        presets = presets if presets is not None else {"TRNLizard_Template_Lite": entry("TRNLizard_Template_Lite", "preset-xml")}
        (self.folder / "trnlizard_presets.json").write_text(bundle(presets, SHARED), encoding="utf-8")

    def run_updater(self, doc=None, make=None):
        doc = doc if doc is not None else Document([])
        self.updater_component.OnPingDocument = lambda: doc
        self.updater.ghenv = SimpleNamespace(Component=self.updater_component)
        return self.updater.runUpdater(str(self.folder), True, make)

    # ------------------------------------------------------------------ templates

    def test_a_template_gets_the_latest_scripts_and_the_shared_clusters(self):
        preset = preset_template()
        top_hygro, nested, database, group = preset.inner.Objects[:4]
        readers = preset.inner.Objects[4:]
        counts = {"scripts": 0, "shared": 0, "errors": []}
        self.updater.updateTemplateDocument(preset.inner, self.scripts, self.shared, counts)

        self.assertEqual({"scripts": 3, "shared": 1, "errors": []}, counts)   # 2 in the preset, 1 in the new database
        hygro_code = HYGRO_SOURCE.read_text(encoding="utf-8-sig")
        expected_inputs = glue.HYGRO_INPUTS_BEFORE + glue.NEW_HYGRO_INPUTS
        for component in (top_hygro, nested.inner.Objects[0]):
            self.assertEqual(hygro_code, component.Code)
            self.assertEqual(expected_inputs, [p.Name for p in component.Params.Input])
        self.assertNotIn(database, preset.inner.Objects)
        new = [o for o in preset.inner.Objects if isinstance(o, Cluster) and o.NickName == "Lizard_Database"]
        self.assertEqual(1, len(new))
        new = new[0]
        self.assertEqual(hygro_code, new.inner.Objects[0].Code)                  # its scripts are updated too
        self.assertIn(self.updater.sharedMarker(self.shared["Lizard_Database"]), new.Description)
        for index, reader in enumerate(readers):                                 # Data x4 rewired by position
            self.assertEqual([new.Params.Output[index]], reader.Sources)
        self.assertIn(str(new.InstanceGuid), group.members)

    def test_a_template_component_that_lost_params_is_swapped_without_keeping_the_old_one(self):
        old = glue.LegacyGhPython("Lizard_Rep", [glue.ScriptVariable("a"), glue.ScriptVariable("b"),
                                                 glue.ScriptVariable("c")],
                                  [glue.Param("out", glue.PARAM_STRING_ID), glue.Param("r"), glue.Param("gone")],
                                  code="old code")
        old.CreateAttributes()
        source, reader = glue.Param("src"), glue.Param("reader")
        old.Params.Input[0].AddSource(source)
        reader.AddSource(old.Params.Output[1])
        (self.folder / "Lizard_Rep.py").write_text(glue.REPLACED_SCRIPT, encoding="utf-8")
        doc = Document([old, source, reader])
        self.modules["Grasshopper"].Instances.ComponentServer.EmitObject = (
            lambda guid: glue.COMPONENT_TYPES[str(guid)]())   # a copy starts without params, as in the glue tests
        counts = {"scripts": 0, "shared": 0, "errors": []}
        self.updater.updateTemplateDocument(doc, {"Lizard_Rep": str(self.folder / "Lizard_Rep.py")}, None, counts)
        self.assertEqual([], counts["errors"])
        self.assertEqual([old], doc.removed)
        new = [o for o in doc.Objects if getattr(o, "Name", None) == "Lizard_Rep"][0]
        self.assertFalse(new.Locked)
        self.assertEqual(["a", "c", "d"], [p.Name for p in new.Params.Input])
        self.assertEqual([source], new.Params.Input[0].Sources)
        self.assertEqual([new.Params.Output[1]], reader.Sources)
        self.assertFalse(any(isinstance(o, glue.GH_Group) for o in doc.Objects))   # no red group in a template

    # ------------------------------------------------------------------ canvas

    def test_an_outdated_building_template_on_the_canvas_is_replaced_and_rewired(self):
        canvas_copy = building_template()
        reader = glue.Param("reader")
        reader.AddSource(canvas_copy.Params.Output[0])
        doc = Document([canvas_copy, reader])
        self.write_bundle({})
        log, updated, skipped, errors = self.run_updater(doc, make=False)
        self.assertEqual(["Lizard_Building_Template"], updated)
        self.assertEqual(1, len(doc.scheduled))
        doc.scheduled[0](doc)
        self.assertEqual([canvas_copy], doc.removed)
        new = [o for o in doc.Objects if isinstance(o, Cluster)][0]
        self.assertEqual([new.Params.Output[0]], reader.Sources)
        self.assertIn(self.updater.sharedMarker(self.shared["Lizard_Building_Template"]), new.Description)
        self.assertIn(("remove", canvas_copy), glue.UNDO)

        log, updated, skipped, errors = self.run_updater(doc, make=False)   # report run
        log, updated, skipped, errors = self.run_updater(doc, make=False)
        self.assertEqual([], updated)
        self.assertIn("Lizard_Building_Template", skipped)

    def test_a_database_on_the_canvas_is_never_replaced(self):
        canvas_copy = Cluster("Lizard_Database", [], outputs=["Data", "Data", "Data", "Data"])
        doc = Document([canvas_copy])
        self.write_bundle({})
        log, updated, skipped, errors = self.run_updater(doc, make=False)
        self.assertEqual([], updated)
        self.assertEqual([], doc.scheduled)
        self.assertIn(canvas_copy, doc.Objects)
        self.assertTrue(any("kept as it is" in line for line in log))

    # ------------------------------------------------------------------ UserObjects

    def test_presets_and_shared_clusters_become_userobjects_rebuilt_when_a_script_changes(self):
        self.write_bundle()
        log, updated, skipped, errors = self.run_updater()
        self.assertEqual([], errors)
        saved = dict((u.Description.Name, u) for u in uo.GH_UserObject.SAVED)
        for name in ("TRNLizard_Template_Lite", "Lizard_Database", "Lizard_Building_Template", "Lizard_Hygro"):
            self.assertIn(name, saved)
        preset = saved["TRNLizard_Template_Lite"]
        self.assertEqual(("TRNLizard", "0 | Basic", "Template_Lite"), (
            preset.Description.Category, preset.Description.SubCategory, preset.Description.NickName))
        cluster = preset.data
        self.assertEqual(HYGRO_SOURCE.read_text(encoding="utf-8-sig"), cluster.inner.Objects[0].Code)
        self.assertTrue(any(line.startswith("UserObject written: TRNLizard_Template_Lite") and
                            "3 script components updated, 1 shared clusters put in" in line for line in log))

        del uo.GH_UserObject.SAVED[:]
        log, updated, skipped, errors = self.run_updater()
        self.assertEqual([], uo.GH_UserObject.SAVED)

        (self.folder / "Lizard_Hygro.py").write_text(HYGRO_SOURCE.read_text(encoding="utf-8-sig") + "\n# changed\n",
                                                    encoding="utf-8")
        log, updated, skipped, errors = self.run_updater()
        names = sorted(u.Description.Name for u in uo.GH_UserObject.SAVED)
        self.assertEqual(["Lizard_Building_Template", "Lizard_Database", "Lizard_Hygro", "TRNLizard_Template_Lite"], names)

    def test_a_broken_template_is_an_error_and_the_rest_is_written(self):
        self.write_bundle({"TRNLizard_Broken": entry("TRNLizard_Broken", "missing-xml")})
        log, updated, skipped, errors = self.run_updater()
        self.assertEqual(1, len(errors))
        self.assertIn("UserObject TRNLizard_Broken not written", errors[0])
        self.assertIn("Lizard_Hygro", [u.Description.Name for u in uo.GH_UserObject.SAVED])


if __name__ == "__main__":
    unittest.main()
