"""Lizard_Updater: a Grasshopper UserObject (.ghuser) per TRNLizard script in <UserObjects folder>/TRNLizard.

The pure logic (component identity from the script, eligibility, file names, the state planning) is tested directly;
the Grasshopper glue runs against the fakes of test_updater_gh_glue.py, extended here by GH_UserObject (records its
Description, SetDataFromObject and SaveToFile, which writes a dummy file), Grasshopper.Folders.DefaultUserObjectFolder
(a temp folder), ComponentServer.EmitObject creating script components with their default params (x, y / out, a) and the
ribbon refresh members.  Whether real Grasshopper behaves like the fakes is the manual test.
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
from test_updater_io_sync import load_updater  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
UPDATER_SOURCE = REPO_ROOT / "Lizard_Updater.py"
HYGRO_SOURCE = REPO_ROOT / "Lizard_Hygro.py"
IRONPYTHON2_ID = "97aa26ef-88ae-4ba6-98a6-ed6ddeca11d1"   # Rhino 8 Python 2 Script (any id of the fakes)
ICON = object()

SIMPLE_SCRIPT = '''"""
A simple component.
Second line of the description.
-
TRNLizard

Args:
    a (float): first
        Access: list
        Required: True
    -------- section
    b (str): second
        Access: tree
        Required: False

Returns:
    out (object): log
        Access: item
    r (object): result
        Access: item
"""
ghenv.Component.Name = "Lizard_Simple"
ghenv.Component.Category = "TRNLizard"
'''

AMBIGUOUS_SCRIPT = '''"""
Twice the same input.

Args:
    a (float): first
    a (float): again
"""
ghenv.Component.Name = "Lizard_Ambiguous"
'''


# ---------------------------------------------------------------------------------------------------- fakes

class UserObjectFields:
    """Members of the fake script components that the UserObject builder sets (GH_Component has them all)."""

    def _fields(self):
        self.Description = ""
        self.Category = ""
        self.SubCategory = ""
        self.Message = ""
        self.Icon_24x24 = ICON


class EmittedLegacy(glue.LegacyGhPython, UserObjectFields):
    """A new legacy GhPython Script as ComponentServer.EmitObject creates it: inputs x, y; outputs out, a."""

    def __init__(self, *args, **kwargs):
        if args or kwargs:
            super(EmittedLegacy, self).__init__(*args, **kwargs)
        else:
            super(EmittedLegacy, self).__init__(
                "Python Script", [glue.ScriptVariable("x"), glue.ScriptVariable("y")],
                [glue.Param("out", glue.PARAM_STRING_ID), glue.Param("a")])
        self._fields()


class EmittedPython3(glue.Python3Script, UserObjectFields):
    def __init__(self, *args, **kwargs):
        super(EmittedPython3, self).__init__(*args, **kwargs)
        self._fields()


class IronPython2Script(glue.Python3Script, UserObjectFields):
    TYPE_NAME = "IronPython2Component"
    COMPONENT_ID = IRONPYTHON2_ID

    def __init__(self, *args, **kwargs):
        if args or kwargs:
            super(IronPython2Script, self).__init__(*args, **kwargs)
        else:
            super(IronPython2Script, self).__init__(
                "Python 2 Script", [glue.RhinoCodeParam("x"), glue.RhinoCodeParam("y")],
                [glue.Param("out", glue.PARAM_STRING_ID), glue.Param("a")])
        self._fields()


class GH_UserObject:
    SAVED = []

    def __init__(self):
        self.Description = SimpleNamespace(Name="", NickName="", Description="", Category="", SubCategory="")
        self.Exposure = None
        self.Icon = None
        self.BaseGuid = None
        self.Path = None
        self.data = None

    def SetDataFromObject(self, obj):
        self.data = obj
        self.inputs = [p.Name for p in obj.Params.Input]
        self.outputs = [p.Name for p in obj.Params.Output]
        return True

    def SaveToFile(self):
        Path(self.Path).write_text("ghuser of " + self.Description.Name, encoding="utf-8")
        GH_UserObject.SAVED.append(self)
        return True


def userobject_modules(user_object_root, emit):
    modules = glue.fake_modules()
    modules["System"].Guid = lambda text: glue.Guid(text)
    grasshopper, kernel = modules["Grasshopper"], modules["Grasshopper.Kernel"]
    kernel.GH_UserObject = GH_UserObject
    kernel.GH_Exposure = SimpleNamespace(primary="primary", secondary="secondary")
    ribbon = []
    kernel.GH_ComponentServer = SimpleNamespace(UpdateRibbonUI=lambda: ribbon.append("UpdateRibbonUI"))
    grasshopper.Folders = SimpleNamespace(DefaultUserObjectFolder=str(user_object_root))
    grasshopper.Instances = SimpleNamespace(ComponentServer=SimpleNamespace(
        EmitObject=emit, AddUserObject=lambda uo: ribbon.append(("AddUserObject", uo.Description.Name))))
    return modules, ribbon


# ---------------------------------------------------------------------------------------------------- pure logic

class UserObjectLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.updater = load_updater()

    def test_identity_comes_from_the_declared_string_literals(self):
        info = self.updater.parseComponentInfo(HYGRO_SOURCE.read_text(encoding="utf-8-sig"), "Lizard_Hygro")
        self.assertEqual({"name": "Lizard_Hygro", "nickName": "Hygrothermal", "category": "Lizard",
                          "subCategory": "1 | Construction", "message": "VER 2.1.2\n2020"},
                         dict((k, info[k]) for k in ("name", "nickName", "category", "subCategory", "message")))
        self.assertEqual("Predefine active layer parameters for multiple active layer wall types considering "
                         "Crank-Nicholson calculation.", info["description"])

    def test_commented_indented_and_expression_values_are_ignored_and_defaults_used(self):
        code = ('"""\nFirst line.\nSecond line.\n\nOther paragraph.\n-\nTRNLizard\n"""\n'
                'version = "1"\n'
                'ghenv.Component.Name   =   "Lizard_Thing"  # the name\n'
                '#ghenv.Component.Category = "Lizard"\n'
                '# ghenv.Component.SubCategory = "0 | Project"\n'
                "ghenv.Component.Message = 'VER %s\\n%s'%(version,date)\n"
                'if True:\n    ghenv.Component.NickName = "Indented"\n'
                "ghenv.Component.Message = 'later literal'\n")
        info = self.updater.parseComponentInfo(code, "Lizard_File")
        self.assertEqual("Lizard_Thing", info["name"])
        self.assertEqual("Thing", info["nickName"])
        self.assertEqual("Lizard", info["category"])
        self.assertEqual("9 | Other", info["subCategory"])
        self.assertEqual("later literal", info["message"])
        self.assertEqual("First line.\nSecond line.", info["description"])

    def test_a_script_without_identity_gets_the_file_name(self):
        info = self.updater.parseComponentInfo('x = 1\n', "Lizard_Window_Settings")
        self.assertEqual(("Lizard_Window_Settings", "Window_Settings", "Lizard", "9 | Other", ""),
                         (info["name"], info["nickName"], info["category"], info["subCategory"], info["message"]))
        self.assertEqual("TRNLizard component Lizard_Window_Settings", info["description"])

    def test_identity_of_the_repo_scripts(self):
        expected = {
            "Lizard_Comfort": ("Lizard_Comfort", "Comfort", "Lizard", "5 | Tools"),
            "Lizard_Daily_Schedule": ("Lizard_Daily_Schedule", "Daily Schedule", "TRNLizard", "2 | Extras"),
            "Lizard_Surface": ("Lizard_Surface", "Surface", "Lizard", "9 | Other"),
            "Lizard_Surface_Settings": ("Lizard_Surface_Settings", "Surface Settings", "Lizard", "9 | Other"),
            "Lizard_Weekly_Schedule": ("Lizard_Weekly_Schedule", "Weekly Schedule", "Lizard", "5 | Tools"),
            "Lizard_DCK_Template": ("Lizard_DCK_Template", "DCK_Template", "Lizard", "9 | Other"),
            "Lizard_b18_to_Rhino": ("Lizard_b18_to_Rhino", "b18_to_Rhino", "Lizard", "9 | Other"),
        }
        for base, values in expected.items():
            with self.subTest(script=base):
                info = self.updater.parseComponentInfo((REPO_ROOT / (base + ".py")).read_text(encoding="utf-8-sig"), base)
                self.assertEqual(values, (info["name"], info["nickName"], info["category"], info["subCategory"]))
        message = self.updater.parseComponentInfo((REPO_ROOT / "Lizard_Component.py").read_text(encoding="utf-8-sig"),
                                                  "Lizard_Component")["message"]
        self.assertEqual("", message)   # 'VER %s\n%s'%(version,date): set by the script when it runs

    def test_eligibility(self):
        self.assertTrue(self.updater.isComponentScript(SIMPLE_SCRIPT))
        self.assertTrue(self.updater.isComponentScript('"""\nReturns:\n    r (object): x\n"""\n'))
        self.assertTrue(self.updater.isComponentScript('ghenv.Component.Name = "Lizard_X"\n'))
        self.assertFalse(self.updater.isComponentScript('"""A helper module."""\nx = 1\n'))
        self.assertFalse(self.updater.isComponentScript('#ghenv.Component.Name = "Lizard_X"\nx = 1\n'))
        for path in sorted(REPO_ROOT.glob("Lizard_*.py")):
            with self.subTest(script=path.name):
                self.assertTrue(self.updater.isComponentScript(path.read_text(encoding="utf-8-sig")))

    def test_file_names_are_safe(self):
        self.assertEqual("Lizard_Hygro.ghuser", self.updater.userObjectFileName("Lizard_Hygro"))
        self.assertEqual("a_b_c_d.ghuser", self.updater.userObjectFileName("a/b\\c:d"))
        self.assertEqual("x_.ghuser", self.updater.userObjectFileName("x?. "))
        self.assertEqual("Lizard_UserObject.ghuser", self.updater.userObjectFileName(".."))
        self.assertTrue(self.updater.isOwnUserObjectFile("Lizard_Hygro.ghuser"))
        for name in ("../x.ghuser", "C:x.ghuser", "a\\b.ghuser", "x.gh", "", None, 3):
            self.assertFalse(self.updater.isOwnUserObjectFile(name), name)

    def entry(self, script, sha="h1", name=None):
        name = name or script
        return {"script": script, "name": name, "file": name + ".ghuser", "sha256": sha}

    def test_state_planning(self):
        state = {"format": self.updater.USEROBJECT_FORMAT, "userObjects": {
            "A": {"sha256": "h1", "file": "A.ghuser"},
            "B": {"sha256": "old", "file": "B.ghuser"},
            "C": {"sha256": "h1", "file": "C.ghuser"},
            "D": {"sha256": "h1", "file": "D.ghuser"},
            "Gone": {"sha256": "h1", "file": "Gone.ghuser"},
            "Evil": {"sha256": "h1", "file": "../Evil.ghuser"},
            "R": {"sha256": "h1", "file": "R_old.ghuser"},
        }}
        entries = [self.entry("A"), self.entry("B"), self.entry("C"), self.entry("D"), self.entry("New"),
                   self.entry("R", name="R_new")]
        existing = ["a.GHUSER", "B.ghuser", "D.ghuser", "Gone.ghuser", "foreign.ghuser", "R_old.ghuser", "R_new.ghuser"]
        plan = self.updater.planUserObjects(entries, state, existing)
        reasons = dict((entry["script"], reason) for entry, reason in plan["write"])
        self.assertEqual({"B": "script changed", "C": "file missing", "New": "new", "R": "component name changed"}, reasons)
        self.assertEqual(["A", "D"], [entry["script"] for entry in plan["unchanged"]])
        self.assertEqual([("Gone", "Gone.ghuser"), ("R", "R_old.ghuser")], plan["stale"])   # never foreign or ../
        self.assertEqual([], plan["conflicts"])

    def test_another_format_or_no_state_rewrites_everything(self):
        state = {"format": self.updater.USEROBJECT_FORMAT - 1, "userObjects": {"A": {"sha256": "h1", "file": "A.ghuser"}}}
        plan = self.updater.planUserObjects([self.entry("A"), self.entry("B")], state, ["A.ghuser", "B.ghuser"])
        self.assertEqual([("A", "UserObject format changed"), ("B", "not in the state file")],
                         [(entry["script"], reason) for entry, reason in plan["write"]])
        for state in (None, [], {"format": 1, "userObjects": []}):
            plan = self.updater.planUserObjects([self.entry("A")], state, [])
            self.assertEqual([("A", "new")], [(entry["script"], reason) for entry, reason in plan["write"]])
            self.assertEqual([], plan["stale"])

    def test_two_scripts_writing_the_same_file_conflict(self):
        plan = self.updater.planUserObjects([self.entry("X", name="Same"), self.entry("Y", name="same")], None, [])
        self.assertEqual(["X"], [entry["script"] for entry, reason in plan["write"]])
        self.assertEqual([("Y", "X")], [(entry["script"], other) for entry, other in plan["conflicts"]])


# ---------------------------------------------------------------------------------------------------- glue

class UserObjectGlueTests(unittest.TestCase):
    def setUp(self):
        glue.SNAPSHOTS.clear()
        del glue.UNDO[:]
        del GH_UserObject.SAVED[:]
        self.folder = Path(tempfile.mkdtemp())
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copy(HYGRO_SOURCE, self.folder / "Lizard_Hygro.py")
        shutil.copy(UPDATER_SOURCE, self.folder / "Lizard_Updater.py")
        (self.folder / "Lizard_Simple.py").write_text(SIMPLE_SCRIPT, encoding="utf-8")
        (self.folder / "Lizard_Helper.py").write_text('"""Helper functions."""\nx = 1\n', encoding="utf-8")
        self.types = {glue.LEGACY_ID: EmittedLegacy, glue.PYTHON3_ID: EmittedPython3, IRONPYTHON2_ID: IronPython2Script}
        self.emitted = []
        self.modules, self.ribbon = userobject_modules(self.root, self.emit)
        patcher = mock.patch.dict(sys.modules, self.modules)
        patcher.start()
        self.addCleanup(patcher.stop)
        import importlib.util
        spec = importlib.util.spec_from_file_location("Lizard_Updater_userobjects", UPDATER_SOURCE)
        self.updater = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.updater)
        self.updater_component = EmittedLegacy(
            "Lizard_Updater", [glue.ScriptVariable("sourceFolder"), glue.ScriptVariable("runUpdate")],
            [glue.Param("log")], code=UPDATER_SOURCE.read_text(encoding="utf-8"))
        self.uo_folder = self.root / "TRNLizard"

    def emit(self, guid):
        cls = self.types.get(str(guid))
        if cls is None:
            return None
        component = cls()
        self.emitted.append(component)
        return component

    def run_updater(self, doc=None, make=None, updater=None):
        doc = doc if doc is not None else glue.Document([])
        updater = updater or self.updater_component
        updater.OnPingDocument = lambda: doc
        self.updater.ghenv = SimpleNamespace(Component=updater)
        return self.updater.runUpdater(str(self.folder), True, make)

    def saved(self):
        return dict((uo.Description.Name, uo) for uo in GH_UserObject.SAVED)

    def state(self):
        return json.loads((self.uo_folder / "lizard_userobjects.json").read_text(encoding="utf-8"))

    # ------------------------------------------------------------------ building

    def test_a_userobject_per_component_script_with_the_docstring_params_and_the_script_identity(self):
        log, updated, skipped, errors = self.run_updater()

        self.assertEqual([], errors)
        saved = self.saved()
        self.assertEqual(["Lizard_Hygro", "Lizard_Simple", "Lizard_Updater"], sorted(saved))
        self.assertTrue(any("No UserObject for Lizard_Helper.py" in line for line in log))
        self.assertIn("UserObjects: 3 written, 0 unchanged", log)
        self.assertTrue(log.index("UserObjects: 3 written, 0 unchanged") > log.index("=== Update Summary ==="))

        hygro_uo = saved["Lizard_Hygro"]
        comp = hygro_uo.data
        self.assertIsInstance(comp, EmittedLegacy)
        hygro_code = HYGRO_SOURCE.read_text(encoding="utf-8-sig")
        self.assertEqual(hygro_code, comp.Code)
        inputs, outputs = self.updater.parseIONames(hygro_code)
        self.assertEqual(inputs, [p.Name for p in comp.Params.Input])           # separators included, x/y gone
        self.assertIn("------------------ hygrothermal", inputs)
        self.assertEqual(["out"] + outputs, [p.Name for p in comp.Params.Output])   # code output kept, a gone
        self.assertEqual([p.Name for p in comp.Params.Input], hygro_uo.inputs)
        params = dict((p.Name, p) for p in comp.Params.Input)
        self.assertEqual("list", params["BRep"].Access)
        self.assertEqual("Brep", params["BRep"].TypeHint.TypeName)
        self.assertEqual("bool", params["write_report"].TypeHint.TypeName)
        self.assertEqual("int", params["layer_min_div"].TypeHint.TypeName)
        self.assertTrue(params["write_report"].Description.startswith("True or not connected"))
        self.assertEqual(("Lizard_Hygro", "Hygrothermal", "Lizard", "1 | Construction", "VER 2.1.2\n2020"),
                         (comp.Name, comp.NickName, comp.Category, comp.SubCategory, comp.Message))
        self.assertTrue(comp.Description.startswith("Predefine active layer"))
        d = hygro_uo.Description
        self.assertEqual(("Lizard_Hygro", "Hygrothermal", "Lizard", "1 | Construction", comp.Description),
                         (d.Name, d.NickName, d.Category, d.SubCategory, d.Description))
        self.assertEqual("primary", hygro_uo.Exposure)
        self.assertIs(ICON, hygro_uo.Icon)
        self.assertEqual(str(self.uo_folder / "Lizard_Hygro.ghuser"), hygro_uo.Path)
        self.assertTrue((self.uo_folder / "Lizard_Hygro.ghuser").is_file())

        simple = saved["Lizard_Simple"].data
        self.assertEqual(["a", "-------- section", "b"], [p.Name for p in simple.Params.Input])
        self.assertEqual(["out", "r"], [p.Name for p in simple.Params.Output])
        self.assertEqual(["list", "item", "tree"], [p.Access for p in simple.Params.Input])
        self.assertEqual(("Simple", "TRNLizard", "9 | Other", ""), (simple.NickName, simple.Category, simple.SubCategory, simple.Message))
        self.assertEqual("A simple component.\nSecond line of the description.", simple.Description)

        updater_uo = saved["Lizard_Updater"].data
        self.assertEqual(["source", "runUpdate", "makeUserObjects"], [p.Name for p in updater_uo.Params.Input])
        self.assertEqual(["out", "log", "updated", "skipped", "errors"], [p.Name for p in updater_uo.Params.Output])

        state = self.state()
        self.assertEqual(self.updater.USEROBJECT_FORMAT, state["format"])
        self.assertEqual({"sha256": self.updater.getHash(hygro_code), "file": "Lizard_Hygro.ghuser", "name": "Lizard_Hygro"},
                         state["userObjects"]["Lizard_Hygro"])
        self.assertEqual(["Lizard_Hygro", "Lizard_Simple", "Lizard_Updater"], sorted(state["userObjects"]))
        self.assertIn("UpdateRibbonUI", self.ribbon)
        self.assertEqual(3, len([item for item in self.ribbon if item[0] == "AddUserObject"]))

    def test_unchanged_scripts_are_not_written_again_and_changes_or_missing_files_are(self):
        self.run_updater()
        del GH_UserObject.SAVED[:]
        del self.ribbon[:]

        log, updated, skipped, errors = self.run_updater()
        self.assertEqual([], GH_UserObject.SAVED)
        self.assertIn("UserObjects: 0 written, 3 unchanged", log)
        self.assertEqual([], self.ribbon)

        (self.folder / "Lizard_Simple.py").write_text(SIMPLE_SCRIPT + "x = 2\n", encoding="utf-8")
        (self.uo_folder / "Lizard_Hygro.ghuser").unlink()
        log, updated, skipped, errors = self.run_updater()
        self.assertEqual(["Lizard_Hygro", "Lizard_Simple"], sorted(self.saved()))
        self.assertIn("UserObjects: 2 written, 1 unchanged", log)
        self.assertTrue(any("Lizard_Simple -> Lizard_Simple.ghuser (script changed" in line for line in log))
        self.assertTrue(any("Lizard_Hygro -> Lizard_Hygro.ghuser (file missing" in line for line in log))
        self.assertEqual([], [item for item in self.ribbon if item[0] == "AddUserObject" and item[1] == "Lizard_Simple"])

        del GH_UserObject.SAVED[:]
        self.updater.USEROBJECT_FORMAT += 1   # a new builder rewrites them all
        log, updated, skipped, errors = self.run_updater()
        self.assertEqual(3, len(GH_UserObject.SAVED))
        self.assertEqual(self.updater.USEROBJECT_FORMAT, self.state()["format"])

    def test_stale_userobjects_are_removed_but_never_other_files(self):
        self.run_updater()
        foreign = self.uo_folder / "Someone_Else.ghuser"
        foreign.write_text("not ours", encoding="utf-8")
        (self.folder / "Lizard_Simple.py").unlink()

        log, updated, skipped, errors = self.run_updater()
        self.assertEqual([], errors)
        self.assertFalse((self.uo_folder / "Lizard_Simple.ghuser").exists())
        self.assertTrue(foreign.exists())
        self.assertTrue((self.uo_folder / "Lizard_Hygro.ghuser").exists())
        self.assertTrue(any(line.startswith("UserObject removed: Lizard_Simple.ghuser") for line in log))
        self.assertIn("UserObjects: 0 written, 2 unchanged, 1 removed", log)
        self.assertEqual(["Lizard_Hygro", "Lizard_Updater"], sorted(self.state()["userObjects"]))

    def test_a_renamed_component_replaces_its_old_file(self):
        self.run_updater()
        (self.folder / "Lizard_Simple.py").write_text(SIMPLE_SCRIPT.replace('"Lizard_Simple"', '"Lizard_Simpler"'),
                                                      encoding="utf-8")
        log, updated, skipped, errors = self.run_updater()
        self.assertEqual([], errors)
        self.assertFalse((self.uo_folder / "Lizard_Simple.ghuser").exists())
        self.assertTrue((self.uo_folder / "Lizard_Simpler.ghuser").exists())
        self.assertEqual("Lizard_Simpler.ghuser", self.state()["userObjects"]["Lizard_Simple"]["file"])

    # ------------------------------------------------------------------ component kind

    def test_a_python3_updater_writes_legacy_ghpython_userobjects(self):
        updater = EmittedPython3("Lizard_Updater", [], [glue.Param("log")], code=UPDATER_SOURCE.read_text(encoding="utf-8"))
        log, updated, skipped, errors = self.run_updater(updater=updater)
        self.assertEqual([], errors)
        self.assertTrue(all(isinstance(uo.data, EmittedLegacy) for uo in GH_UserObject.SAVED))
        self.assertTrue(any("Rhino 8 Python 3 Script" in line and "legacy GhPython" in line for line in log))

    def test_an_ironpython2_updater_writes_userobjects_of_its_own_kind(self):
        updater = IronPython2Script("Lizard_Updater", [], [glue.Param("log")], code=UPDATER_SOURCE.read_text(encoding="utf-8"))
        log, updated, skipped, errors = self.run_updater(updater=updater)
        self.assertEqual([], errors)
        comps = [uo.data for uo in GH_UserObject.SAVED]
        self.assertEqual(3, len(comps))
        self.assertTrue(all(isinstance(comp, IronPython2Script) for comp in comps))
        simple = self.saved()["Lizard_Simple"].data
        self.assertEqual(SIMPLE_SCRIPT, simple.source)
        self.assertEqual(["a", "-------- section", "b"], [p.VariableName for p in simple.Params.Input])
        self.assertEqual([("Type", "System.Double")], simple.Params.Input[0].TypeHints.selected)
        self.assertEqual([("Type", "System.String")], simple.Params.Input[2].TypeHints.selected)
        self.assertFalse(simple.Params.Input[0].Optional)
        self.assertTrue(simple.Params.Input[2].Optional)

    def test_without_legacy_ghpython_a_python3_updater_reports_an_error_and_still_updates_the_canvas(self):
        del self.types[glue.LEGACY_ID]
        hygro = glue.LegacyGhPython("Lizard_Hygro", [glue.ScriptVariable(n) for n in glue.HYGRO_INPUTS_BEFORE],
                                    [glue.Param("SurfaceInfo")], code="old")
        hygro.CreateAttributes()
        doc = glue.Document([hygro])
        updater = EmittedPython3("Lizard_Updater", [], [glue.Param("log")], code=UPDATER_SOURCE.read_text(encoding="utf-8"))

        log, updated, skipped, errors = self.run_updater(doc, updater=updater)
        self.assertEqual(["Lizard_Hygro"], updated)
        self.assertEqual(1, len(errors))
        self.assertIn("legacy GhPython Script component", errors[0])
        self.assertEqual([], GH_UserObject.SAVED)
        self.assertEqual({}, self.state()["userObjects"])

        doc.scheduled.pop()(doc)   # the canvas update goes on and reports the UserObjects in its summary
        self.assertEqual(glue.HYGRO_INPUTS_BEFORE + glue.NEW_HYGRO_INPUTS, [p.Name for p in hygro.Params.Input])
        self.assertIn("UserObjects: 0 written, 0 unchanged", log)

    # ------------------------------------------------------------------ switches and failures

    def test_make_userobjects_false_is_a_canvas_update_only(self):
        log, updated, skipped, errors = self.run_updater(make=False)
        self.assertEqual([], GH_UserObject.SAVED)
        self.assertFalse(self.uo_folder.exists())
        self.assertFalse(any(line.startswith("UserObjects") for line in log))

    def test_a_failing_script_is_reported_and_the_others_are_written(self):
        (self.folder / "Lizard_Ambiguous.py").write_text(AMBIGUOUS_SCRIPT, encoding="utf-8")
        log, updated, skipped, errors = self.run_updater()
        self.assertEqual(1, len(errors))
        self.assertIn("UserObject Lizard_Ambiguous not written", errors[0])
        self.assertEqual(["Lizard_Hygro", "Lizard_Simple", "Lizard_Updater"], sorted(self.saved()))
        self.assertNotIn("Lizard_Ambiguous", self.state()["userObjects"])
        self.assertIn("UserObjects: 3 written, 0 unchanged", log)

    def test_a_failing_save_keeps_the_old_file_tracked_and_is_retried(self):
        self.run_updater()
        (self.folder / "Lizard_Simple.py").write_text(SIMPLE_SCRIPT + "x = 2\n", encoding="utf-8")
        with mock.patch.object(GH_UserObject, "SaveToFile", lambda uo: False):
            log, updated, skipped, errors = self.run_updater()
        self.assertEqual(1, len(errors))
        self.assertIn("SaveToFile failed", errors[0])
        self.assertEqual({"sha256": "", "file": "Lizard_Simple.ghuser", "name": "Lizard_Simple"},
                         self.state()["userObjects"]["Lizard_Simple"])
        del GH_UserObject.SAVED[:]
        log, updated, skipped, errors = self.run_updater()
        self.assertEqual([], errors)
        self.assertEqual(["Lizard_Simple"], sorted(self.saved()))

    def test_the_canvas_update_runs_with_the_userobjects_in_one_run(self):
        hygro = glue.LegacyGhPython("Lizard_Hygro", [glue.ScriptVariable(n) for n in glue.HYGRO_INPUTS_BEFORE],
                                    [glue.Param("SurfaceInfo")], code="old")
        hygro.CreateAttributes()
        doc = glue.Document([hygro])
        log, updated, skipped, errors = self.run_updater(doc)
        self.assertEqual(["Lizard_Hygro"], updated)
        self.assertEqual([], errors)
        self.assertEqual(3, len(GH_UserObject.SAVED))
        self.assertEqual([hygro], doc.Objects)   # the UserObject components never go onto the canvas
        doc.scheduled.pop()(doc)
        self.assertIn("UserObjects: 3 written, 0 unchanged", log)
        self.assertTrue(log.index("UserObjects: 3 written, 0 unchanged") > log.index("=== Update Summary ==="))


if __name__ == "__main__":
    unittest.main()
