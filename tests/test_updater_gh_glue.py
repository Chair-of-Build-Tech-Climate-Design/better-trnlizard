"""Lizard_Updater Grasshopper glue against fake Grasshopper objects.

The fakes mirror the SDK members the updater uses (GH_ComponentParamServer.RegisterInputParam/UnregisterInputParameter,
IGH_VariableParameterComponent.CreateParameter/CanInsertParameter/VariableParameterMaintenance, IGH_Param.AddSource/
ReplaceSource, GH_Archive.AppendObject/Serialize_Xml/Deserialize_Xml/ExtractObject, ComponentServer.EmitObject, GH_Group,
GH_Document.AddObject/ScheduleSolution, legacy GhPython Code/Hints/TypeHint, Rhino 8 TryGetSource/SetSource/TypeHints)
and the behaviour of GhPython's parameter maintenance (Name = NickName, inputs optional, default type hint).  They show
that the updater drives these members as intended; whether real Grasshopper behaves like the fakes is the manual test.
"""

import itertools
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
UPDATER_SOURCE = REPO_ROOT / "Lizard_Updater.py"
HYGRO_SOURCE = REPO_ROOT / "Lizard_Hygro.py"

LEGACY_ID = "410755b1-224a-4c1e-a407-bf32fb45ea7e"   # GhPython Script (ZuiPythonComponent)
PYTHON3_ID = "719467e6-7cf5-4848-99b0-c5dd57e5442c"  # Rhino 8 Python 3 Script
PARAM_STRING_ID = "3ede854e-c753-40eb-84cb-b48008f14fd4"
GENERIC_ID = "8ec86459-bf01-4409-baee-174d0d2b13d0"
SCRIPT_VARIABLE_ID = "84fa917c-1ed8-4db3-8be1-7bdc4a6495a2"
GHDOC_HINT = "87f87f55-5b71-41f4-8aea-21d494016f81"
LEGACY_HINTS = [
    ("35915213-5534-4277-81b8-1bdc9e7383d2", "No Type Hint"),
    (GHDOC_HINT, "ghdoc Object when geometry"),
    ("d60527f5-b5af-4ef6-8970-5f96fe412559", "bool"),
    ("48d01794-d3d8-4aef-990e-127168822244", "int"),
    ("39fbc626-7a01-46ab-a18e-ec1c0c41685b", "float"),
    ("37261734-eec7-4f50-b6a8-b8d1f3c4396b", "str"),
    ("2ceb0405-fdfe-403d-a4d6-8786da45fb9d", "Brep"),
]

_ids = itertools.count(1)


class Guid:
    def __init__(self, value=None):
        self.value = value or "00000000-0000-0000-0000-%012d" % next(_ids)

    def __str__(self):
        return self.value

    def ToString(self):
        return self.value


class NetList(list):
    @property
    def Count(self):
        return len(self)


class Point:
    def __init__(self, x, y):
        self.X, self.Y = x, y


class Attributes:
    def __init__(self):
        self.Pivot = Point(0.0, 0.0)
        self.layouts = 0

    def ExpireLayout(self):
        self.layouts += 1


class Hint:
    def __init__(self, hint_id, type_name):
        self.HintID = Guid(hint_id)
        self.TypeName = type_name


class Param:
    """IGH_Param with wires (Sources of an input, Recipients of an output)."""

    def __init__(self, name, type_id=GENERIC_ID, access="item"):
        self.Name = self.NickName = name
        self.Description = ""
        self.Access = access
        self.Optional = True
        self.Sources, self.Recipients = [], []
        self.InstanceGuid = Guid()
        self.ComponentGuid = Guid(type_id)
        self.Attributes = None

    def CreateAttributes(self):
        self.Attributes = Attributes()

    def AddSource(self, source):
        self.Sources.append(source)
        source.Recipients.append(self)

    def RemoveSource(self, source):
        self.Sources.remove(source)
        source.Recipients.remove(self)

    def ReplaceSource(self, old, new):
        self.Sources[self.Sources.index(old)] = new
        old.Recipients.remove(self)
        new.Recipients.append(self)

    def RemoveAllSources(self):
        for source in list(self.Sources):
            self.RemoveSource(source)

    def NewInstanceGuid(self):
        self.InstanceGuid = Guid()

    def RecordUndoEvent(self, name):
        UNDO.append(("change", self))

    def __repr__(self):
        return "<Param %s>" % self.Name


class ScriptVariable(Param):
    """Grasshopper Param_ScriptVariable of legacy GhPython: type hints from Hints (set by the parameter maintenance)."""

    def __init__(self, name, access="item"):
        super().__init__(name, SCRIPT_VARIABLE_ID, access)
        self.Hints = None
        self.TypeHint = None


class RhinoCodeParam(Param):
    """RhinoCodePluginGH ScriptVariableParam: variable name, pretty name, tooltip and TypeHints.Select."""

    def __init__(self, name):
        super().__init__(name, "08908df5-fa14-4982-9ab2-1aa0927566aa")
        self.VariableName = name
        self.PrettyName = name
        self.ToolTip = ""
        self.TypeHints = SimpleNamespace(selected=[], Select=lambda value: self.TypeHints.selected.append(value))


class ParamServer:
    def __init__(self):
        self.Input, self.Output = NetList(), NetList()
        self.changed = 0

    def RegisterInputParam(self, param, index):
        self.Input.insert(index, param)

    def RegisterOutputParam(self, param, index):
        self.Output.insert(index, param)

    def UnregisterInputParameter(self, param, isolate):
        if isolate:
            param.RemoveAllSources()
        self.Input.remove(param)

    def UnregisterOutputParameter(self, param, isolate):
        if isolate:
            for recipient in list(param.Recipients):
                recipient.RemoveSource(param)
        self.Output.remove(param)

    def OnParametersChanged(self):
        self.changed += 1


class GH_Component:
    pass


class ScriptComponent(GH_Component):
    TYPE_NAME = "?"
    COMPONENT_ID = "?"

    def __init__(self, name="", inputs=(), outputs=(), code=""):
        self.Name = name
        self.NickName = name
        self.InstanceGuid = Guid()
        self.ComponentGuid = Guid(self.COMPONENT_ID)
        self.Params = ParamServer()
        self.Locked = False
        self.Attributes = None
        self.expired = 0
        self.maintenance = 0
        self.source = code
        for param in inputs:
            self.Params.Input.append(param)
        for param in outputs:
            self.Params.Output.append(param)

    def GetType(self):
        return SimpleNamespace(Name=self.TYPE_NAME)

    def CreateAttributes(self):
        self.Attributes = Attributes()

    def ExpireSolution(self, recompute):
        self.expired += 1

    def NewInstanceGuid(self):
        self.InstanceGuid = Guid()

    def RecordUndoEvent(self, name):
        UNDO.append(("change", self))

    def CanInsertParameter(self, side, index):
        if side == "Output" and self.Params.Output and self.Params.Output[0].Name == "out":
            return index > 0
        return True

    def VariableParameterMaintenance(self):
        self.maintenance += 1


class LegacyGhPython(ScriptComponent):
    TYPE_NAME = "ZuiPythonComponent"
    COMPONENT_ID = LEGACY_ID

    @property
    def Code(self):
        return self.source

    @Code.setter
    def Code(self, value):
        self.source = value

    def CreateParameter(self, side, index):
        if side == "Input":
            param = ScriptVariable("x")
            param.Description = "Script variable x"
            return param
        return Param("a")

    def VariableParameterMaintenance(self):
        # GhPython FixGhInput: Name = NickName, every input optional, hints offered, default hint ghdoc Object
        super().VariableParameterMaintenance()
        for param in self.Params.Input:
            if isinstance(param, ScriptVariable):
                param.Name = param.NickName
                param.Optional = True
                param.Hints = [Hint(hint_id, name) for hint_id, name in LEGACY_HINTS]
                if param.TypeHint is None:
                    param.TypeHint = param.Hints[1]


class Python3Script(ScriptComponent):
    TYPE_NAME = "Python3Component"
    COMPONENT_ID = PYTHON3_ID

    def TryGetSource(self):
        return True, self.source

    def SetSource(self, text):
        self.source = text

    def CreateParameter(self, side, index):
        return RhinoCodeParam("x")


COMPONENT_TYPES = {LEGACY_ID: LegacyGhPython, PYTHON3_ID: Python3Script}
SNAPSHOTS = {}
UNDO = []


def snapshot(component):
    def params(side):
        return [dict(cls=type(p), name=p.Name, nick=p.NickName, description=p.Description, access=p.Access,
                     type_id=str(p.ComponentGuid), guid=p.InstanceGuid, sources=list(p.Sources),
                     hint=getattr(p, "TypeHint", None), hints=getattr(p, "Hints", None)) for p in side]
    return dict(name=component.Name, nick=component.NickName, source=component.source, guid=component.InstanceGuid,
                pivot=(component.Attributes.Pivot.X, component.Attributes.Pivot.Y) if component.Attributes else (0.0, 0.0),
                inputs=params(component.Params.Input), outputs=params(component.Params.Output))


def restore(target, state, keep_sources):
    target.Name, target.NickName, target.source, target.InstanceGuid = state["name"], state["nick"], state["source"], state["guid"]
    target.Attributes.Pivot = Point(*state["pivot"])
    for side_name in ("inputs", "outputs"):
        side = target.Params.Input if side_name == "inputs" else target.Params.Output
        for item in state[side_name]:
            cls = item["cls"]
            param = cls(item["name"]) if cls in (ScriptVariable, RhinoCodeParam) else cls(item["name"], item["type_id"])
            param.NickName, param.Description, param.Access, param.InstanceGuid = item["nick"], item["description"], item["access"], item["guid"]
            if hasattr(param, "TypeHint"):
                param.TypeHint, param.Hints = item["hint"], item["hints"]
            if keep_sources:  # unresolved wires of a raw copy
                param.Sources = list(item["sources"])
            side.append(param)


class GH_Archive:
    def __init__(self):
        self.xml = None

    def AppendObject(self, component, name):
        key = len(SNAPSHOTS)
        SNAPSHOTS[key] = snapshot(component)
        chunks = []
        for kind, side in (("InputParam", component.Params.Input), ("OutputParam", component.Params.Output)):
            for p in side:
                items = ['<item name="Source" index="%d" type_name="gh_guid" type_code="9">%s</item>' % (i, s.InstanceGuid)
                         for i, s in enumerate(p.Sources)]
                items.append('<item name="SourceCount" type_name="gh_int32" type_code="3">%d</item>' % len(p.Sources))
                chunks.append('<chunk name="%s"><items count="%d">%s</items></chunk>' % (kind, len(items), "".join(items)))
        self.xml = '<Archive name="Root"><chunk name="%s" snapshot="%d">%s</chunk></Archive>' % (name, key, "".join(chunks))
        return True

    def Serialize_Xml(self):
        return self.xml

    def Deserialize_Xml(self, xml):
        self.xml = xml
        return True

    def ExtractObject(self, target, name):
        key = int(re.search(r'name="%s" snapshot="(\d+)"' % name, self.xml).group(1))
        restore(target, SNAPSHOTS[key], keep_sources='<item name="Source" ' in self.xml)
        return True


class GH_Group:
    def __init__(self):
        self.members, self.NickName, self.Colour, self.Attributes = [], "", None, None
        self.InstanceGuid = Guid()

    def CreateAttributes(self):
        self.Attributes = Attributes()

    def AddObject(self, guid):
        self.members.append(str(guid))


class Document:
    def __init__(self, objects=()):
        self.Objects = list(objects)
        self.scheduled = []
        self.UndoUtil = SimpleNamespace(
            RecordAddObjectEvent=lambda name, obj: UNDO.append(("add", obj)),
            RecordWireEvent=lambda name, param: UNDO.append(("wire", param)),
        )

    def AddObject(self, obj, update):
        self.Objects.append(obj)

    def ScheduleSolution(self, delay, callback):
        self.scheduled.append(callback)


class GH_Cluster:
    def __init__(self, nick, objects):
        self.NickName = nick
        self.inner = Document(objects)
        self.InstanceGuid = Guid()
        self.expired = 0

    def Document(self, password):
        return self.inner

    def ExpireSolution(self, recompute):
        self.expired += 1


def fake_modules():
    system = ModuleType("System")
    drawing = ModuleType("System.Drawing")
    drawing.PointF = Point
    drawing.Color = SimpleNamespace(FromArgb=lambda a, r, g, b: ("ARGB", a, r, g, b))
    system.Drawing = drawing
    system.Type = SimpleNamespace(GetType=lambda name: ("Type", name) if name.startswith("System.") else None)
    grasshopper = ModuleType("Grasshopper")
    kernel = ModuleType("Grasshopper.Kernel")
    kernel.GH_Component = GH_Component
    kernel.GH_ParameterSide = SimpleNamespace(Input="Input", Output="Output")
    kernel.GH_ParamAccess = SimpleNamespace(item="item", list="list", tree="tree")
    kernel.GH_RuntimeMessageLevel = SimpleNamespace(Warning="Warning", Error="Error", Remark="Remark")
    kernel.GH_Document = SimpleNamespace(GH_ScheduleDelegate=lambda function: function)
    kernel.IGH_VariableParameterComponent = object
    kernel.Special = SimpleNamespace(GH_Cluster=GH_Cluster, GH_Group=GH_Group)
    grasshopper.Kernel = kernel
    grasshopper.Instances = SimpleNamespace(
        ComponentServer=SimpleNamespace(EmitObject=lambda guid: COMPONENT_TYPES[str(guid)]()))
    gh_io = ModuleType("GH_IO")
    serialization = ModuleType("GH_IO.Serialization")
    serialization.GH_Archive = GH_Archive
    gh_io.Serialization = serialization
    clr = ModuleType("clr")
    clr.AddReference = lambda name: None
    clr.GetClrType = lambda t: ("Type", t)
    scriptcontext = ModuleType("scriptcontext")
    scriptcontext.sticky = {}
    rhino = ModuleType("Rhino")
    rhino.Geometry = SimpleNamespace(Brep="Brep")
    return {"System": system, "System.Drawing": drawing, "Grasshopper": grasshopper, "Grasshopper.Kernel": kernel,
            "GH_IO": gh_io, "GH_IO.Serialization": serialization, "clr": clr, "scriptcontext": scriptcontext, "Rhino": rhino}


HYGRO_INPUTS_BEFORE = ["BRep", "Settings", "------------------ hygrothermal", "datafile_assembly"]
NEW_HYGRO_INPUTS = ["write_report", "report_interval", "add_heat_depth", "add_heat", "layer_min_div"]

REPLACED_SCRIPT = '''"""
Test component whose IO lost params.

Args:
    a (float): first
        Access: item
        Required: True
    c (str): third
        Access: list
        Required: False
    d (int): new input
        Access: item
        Required: False

Returns:
    r (object): kept output
        Access: item
    extra (object): new output
        Access: item
"""
ghenv.Component.Name = "Lizard_Rep"
'''


class UpdaterGlueTests(unittest.TestCase):
    def setUp(self):
        SNAPSHOTS.clear()
        del UNDO[:]
        self.folder = Path(tempfile.mkdtemp())
        shutil.copy(HYGRO_SOURCE, self.folder / "Lizard_Hygro.py")
        (self.folder / "Lizard_Rep.py").write_text(REPLACED_SCRIPT, encoding="utf-8")
        (self.folder / "_ignored.py").write_text("x = 1\n", encoding="utf-8")
        self.modules = fake_modules()
        patcher = mock.patch.dict(sys.modules, self.modules)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(shutil.rmtree, self.folder)
        import importlib.util
        spec = importlib.util.spec_from_file_location("Lizard_Updater_glue", UPDATER_SOURCE)
        self.updater = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.updater)
        # the updater itself: a script component whose script is in the folder too, it must never update itself
        shutil.copy(UPDATER_SOURCE, self.folder / "Lizard_Updater.py")
        self.updater_component = LegacyGhPython("Lizard_Updater", [ScriptVariable("source"), ScriptVariable("runUpdate")],
                                                [Param("log")], code=UPDATER_SOURCE.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------ helpers

    def run_updater(self, doc, run=True):
        self.updater_component.OnPingDocument = lambda: doc
        self.updater.ghenv = SimpleNamespace(Component=self.updater_component)
        return self.updater.runUpdater(str(self.folder), run)

    def apply_scheduled(self, doc):
        self.assertEqual(1, len(doc.scheduled))
        doc.scheduled.pop()(doc)

    def legacy_hygro(self):
        inputs = [ScriptVariable(name) for name in HYGRO_INPUTS_BEFORE]
        component = LegacyGhPython("Lizard_Hygro", inputs, [Param("SurfaceInfo")], code="old hygro code")
        component.CreateAttributes()
        return component

    def replaced_component(self, locked=False):
        component = LegacyGhPython(
            "Lizard_Rep",
            [ScriptVariable("a"), ScriptVariable("b"), ScriptVariable("c")],
            [Param("out", PARAM_STRING_ID), Param("r"), Param("gone")],
            code="old code",
        )
        component.CreateAttributes()
        component.Attributes.Pivot = Point(100.0, 200.0)
        component.Locked = locked
        self.sources = {name: Param("src_" + name) for name in ("S1", "S2", "S3", "S4")}
        component.Params.Input[0].AddSource(self.sources["S1"])
        component.Params.Input[1].AddSource(self.sources["S2"])
        component.Params.Input[2].AddSource(self.sources["S3"])
        component.Params.Input[2].AddSource(self.sources["S4"])
        self.recipients = {name: Param("rcp_" + name) for name in ("R1", "R2", "R3")}
        self.recipients["R1"].AddSource(component.Params.Output[1])
        self.recipients["R2"].AddSource(component.Params.Output[1])   # first of two sources of R2: its place must be kept
        self.recipients["R2"].AddSource(self.sources["S1"])
        self.recipients["R3"].AddSource(component.Params.Output[2])
        return component

    # ------------------------------------------------------------------ additions in place

    def test_additions_are_made_in_place_after_the_solution_and_reported_on_the_next_run(self):
        hygro = self.legacy_hygro()
        doc = Document([hygro])

        log, updated, skipped, errors = self.run_updater(doc)
        # nothing changed during the solution
        self.assertEqual(HYGRO_INPUTS_BEFORE, [p.Name for p in hygro.Params.Input])
        self.assertEqual("old hygro code", hygro.Code)
        self.assertEqual(["Lizard_Hygro"], updated)
        self.assertEqual([], errors)
        self.assertTrue(any("params added in place" in line for line in log))
        self.assertTrue(any("GhPython (legacy, IronPython 2.7)" in line for line in log))

        self.apply_scheduled(doc)
        self.assertEqual(HYGRO_INPUTS_BEFORE + NEW_HYGRO_INPUTS, [p.Name for p in hygro.Params.Input])
        self.assertEqual(["SurfaceInfo"], [p.Name for p in hygro.Params.Output])
        self.assertEqual(HYGRO_SOURCE.read_text(encoding="utf-8-sig").replace("\r\n", "\n"), hygro.Code)
        new = {p.Name: p for p in hygro.Params.Input[4:]}
        for name in NEW_HYGRO_INPUTS:
            self.assertEqual(name, new[name].NickName)
            self.assertEqual("item", new[name].Access)
            self.assertTrue(new[name].Optional)
            self.assertTrue(new[name].Description and not new[name].Description.startswith("Script variable"))
        hints = {name: new[name].TypeHint.TypeName for name in NEW_HYGRO_INPUTS}
        self.assertEqual({"write_report": "bool", "report_interval": "float", "add_heat_depth": "float",
                          "add_heat": "ghdoc Object when geometry", "layer_min_div": "int"}, hints)
        self.assertEqual(1, hygro.Params.changed)
        self.assertEqual(1, hygro.maintenance)
        self.assertGreaterEqual(hygro.expired, 1)
        self.assertIn(("change", hygro), UNDO)
        self.assertEqual(1, len(doc.Objects))   # no new objects
        self.assertEqual(1, self.updater_component.expired)

        log, updated, skipped, errors = self.run_updater(doc, run=False)   # the run triggered by the callback
        self.assertEqual(["Lizard_Hygro"], updated)
        self.assertEqual([], errors)
        self.assertIn("=== Update Summary ===", log)
        self.assertTrue(any(line.startswith("Done: Lizard_Hygro (add)") for line in log))

        log, updated, skipped, errors = self.run_updater(doc)   # next update run: nothing to do
        self.assertEqual(["Lizard_Hygro"], skipped)
        self.assertEqual([], doc.scheduled)

    # ------------------------------------------------------------------ replacement

    def test_removal_creates_a_wired_copy_in_a_red_group_and_locks_the_old_component(self):
        old = self.replaced_component()
        doc = Document([old])

        log, updated, skipped, errors = self.run_updater(doc)
        self.assertEqual(["Lizard_Rep"], updated)
        self.apply_scheduled(doc)

        new = [o for o in doc.Objects if isinstance(o, LegacyGhPython) and o is not old]
        self.assertEqual(1, len(new))
        new = new[0]
        group = [o for o in doc.Objects if isinstance(o, GH_Group)][0]
        # the old component: locked, params and wires of the removed params untouched
        self.assertTrue(old.Locked)
        self.assertEqual(["a", "b", "c"], [p.Name for p in old.Params.Input])
        self.assertEqual("old code", old.Code)
        self.assertEqual([self.sources["S2"]], old.Params.Input[1].Sources)
        self.assertEqual([self.recipients["R3"]], old.Params.Output[2].Recipients)
        # the new component: new code, new IO, new ids, placed right and down
        self.assertEqual(REPLACED_SCRIPT, new.Code)
        self.assertEqual(["a", "c", "d"], [p.Name for p in new.Params.Input])
        self.assertEqual(["out", "r", "extra"], [p.Name for p in new.Params.Output])
        self.assertNotEqual(str(old.InstanceGuid), str(new.InstanceGuid))
        old_ids = {str(p.InstanceGuid) for p in list(old.Params.Input) + list(old.Params.Output)}
        self.assertFalse(old_ids & {str(p.InstanceGuid) for p in list(new.Params.Input) + list(new.Params.Output)})
        self.assertEqual((140.0, 240.0), (new.Attributes.Pivot.X, new.Attributes.Pivot.Y))
        self.assertEqual("int", new.Params.Input[2].TypeHint.TypeName)   # the new input d
        self.assertEqual("item", new.Params.Input[2].Access)
        self.assertEqual("new output", new.Params.Output[2].Description)
        # inputs: same sources by name, in the same order; the new input has none
        self.assertEqual([self.sources["S1"]], new.Params.Input[0].Sources)
        self.assertEqual([self.sources["S3"], self.sources["S4"]], new.Params.Input[1].Sources)
        self.assertEqual([], new.Params.Input[2].Sources)
        # outputs: recipients moved (not copied), keeping their place in the source list
        self.assertEqual([], old.Params.Output[1].Recipients)
        self.assertEqual([new.Params.Output[1]], self.recipients["R1"].Sources)
        self.assertEqual([new.Params.Output[1], self.sources["S1"]], self.recipients["R2"].Sources)
        self.assertEqual([old.Params.Output[2]], self.recipients["R3"].Sources)
        # the group
        self.assertEqual([str(new.InstanceGuid)], group.members)
        self.assertEqual(("ARGB", 150, 255, 0, 0), group.Colour)
        for fragment in ("inputs removed: b", "outputs removed: gone", "locked", "delete"):
            self.assertIn(fragment, group.NickName)
        self.assertIn(("add", new), UNDO)
        self.assertIn(("change", old), UNDO)

        log, updated, skipped, errors = self.run_updater(doc, run=False)
        self.assertEqual(["Lizard_Rep"], updated)
        self.assertEqual([], errors)

        # a later update run leaves the locked old copy alone and finds the new component up to date
        log, updated, skipped, errors = self.run_updater(doc)
        self.assertEqual(sorted(["Lizard_Rep", "Lizard_Rep"]), sorted(skipped))
        self.assertEqual([], doc.scheduled)

    def test_locked_component_with_removed_params_is_not_replaced(self):
        old = self.replaced_component(locked=True)
        doc = Document([old])

        log, updated, skipped, errors = self.run_updater(doc)

        self.assertEqual(["Lizard_Rep"], skipped)
        self.assertEqual([], doc.scheduled)
        self.assertTrue(any("locked" in line for line in log))

    # ------------------------------------------------------------------ clusters

    def test_inside_a_cluster_additions_are_made_and_removals_are_left_to_the_user(self):
        hygro = self.legacy_hygro()
        rep = self.replaced_component()
        cluster = GH_Cluster("Lizard_Building_Template", [hygro, rep])
        doc = Document([cluster])

        log, updated, skipped, errors = self.run_updater(doc)
        self.assertEqual(["Lizard_Hygro"], updated)
        self.assertEqual(1, len(errors))
        self.assertIn("Manual update needed for Lizard_Rep inside cluster Lizard_Building_Template", errors[0])

        self.apply_scheduled(doc)
        self.assertEqual(HYGRO_INPUTS_BEFORE + NEW_HYGRO_INPUTS, [p.Name for p in hygro.Params.Input])
        self.assertGreaterEqual(cluster.expired, 1)
        self.assertEqual(["a", "b", "c"], [p.Name for p in rep.Params.Input])
        self.assertEqual("old code", rep.Code)
        self.assertFalse(rep.Locked)
        self.assertEqual([cluster], doc.Objects)

    # ------------------------------------------------------------------ Rhino 8 script components

    def test_rhino8_python3_component_uses_its_own_source_and_param_api(self):
        inputs = [Param(name, "08908df5-fa14-4982-9ab2-1aa0927566aa") for name in HYGRO_INPUTS_BEFORE]
        component = Python3Script("Lizard_Hygro", inputs, [Param("SurfaceInfo")], code="old")
        component.CreateAttributes()
        doc = Document([component])

        log, updated, skipped, errors = self.run_updater(doc)
        self.assertTrue(any("Rhino 8 Python 3 Script (CPython 3)" in line for line in log))
        self.apply_scheduled(doc)

        self.assertEqual(HYGRO_SOURCE.read_text(encoding="utf-8-sig").replace("\r\n", "\n"), component.source)
        new = component.Params.Input[4:]
        self.assertEqual(NEW_HYGRO_INPUTS, [p.VariableName for p in new])
        self.assertEqual(NEW_HYGRO_INPUTS, [p.NickName for p in new])
        self.assertTrue(all(p.ToolTip for p in new))
        self.assertTrue(all(p.Optional for p in new))
        self.assertEqual([("Type", "System.Boolean")], new[0].TypeHints.selected)
        self.assertEqual([("Type", "System.Double")], new[1].TypeHints.selected)
        self.assertEqual([], new[3].TypeHints.selected)   # object: default hint kept
        self.assertEqual([("Type", "System.Int32")], new[4].TypeHints.selected)

    def test_the_updater_never_updates_itself_and_ignores_scripts_without_a_component(self):
        hygro = self.legacy_hygro()
        doc = Document([hygro, self.updater_component])
        log, updated, skipped, errors = self.run_updater(doc)
        self.assertEqual(["Lizard_Hygro"], updated)
        self.assertEqual([], skipped + errors)
        self.assertFalse(any("_ignored" in line or "Processing: Lizard_Updater" in line for line in log))
        self.assertFalse(any(line.startswith("WARNING") for line in log))
        self.apply_scheduled(doc)
        self.assertEqual(UPDATER_SOURCE.read_text(encoding="utf-8"), self.updater_component.Code)

    def test_an_outdated_updater_says_so_and_still_updates_the_other_components(self):
        self.updater_component.Code = "an older updater"
        hygro = self.legacy_hygro()
        doc = Document([hygro, self.updater_component])

        log, updated, skipped, errors = self.run_updater(doc)
        self.assertEqual(["Lizard_Hygro"], updated)
        self.assertEqual(1, len(errors))
        for fragment in ("Lizard_Updater.py", "never updates itself", "by hand", "line 1"):
            self.assertIn(fragment, errors[0])
        self.assertIn("WARNING: " + errors[0], log)

        self.apply_scheduled(doc)
        self.assertEqual("an older updater", self.updater_component.Code)
        log, updated, skipped, errors = self.run_updater(doc, run=False)   # the final report keeps the warning
        self.assertEqual(1, len(errors))
        self.assertEqual(HYGRO_INPUTS_BEFORE + NEW_HYGRO_INPUTS, [p.Name for p in hygro.Params.Input])

    def test_an_outdated_updater_shows_a_warning_balloon_and_outdated_until_it_is_current(self):
        messages = []
        self.updater_component.AddRuntimeMessage = lambda level, text: messages.append((level, text))
        self.updater_component.Message = ""
        self.updater_component.Code = "an older updater"
        doc = Document([self.legacy_hygro(), self.updater_component])

        log, updated, skipped, errors = self.run_updater(doc)
        self.assertEqual("OUTDATED", self.updater_component.Message)
        self.assertEqual([("Warning", errors[0])], messages)
        self.assertIn("new Lizard_Updater from the TRNLizard tab", errors[0])
        del messages[:]
        self.apply_scheduled(doc)
        self.run_updater(doc, run=False)   # the report run and every later run keep showing it
        self.run_updater(doc, run=False)
        self.assertEqual(2, len(messages))
        self.assertEqual("OUTDATED", self.updater_component.Message)

        self.updater_component.Code = UPDATER_SOURCE.read_text(encoding="utf-8")   # replaced by the new one
        del messages[:]
        self.run_updater(doc)
        self.assertEqual([], messages)
        self.assertEqual("", self.updater_component.Message)


if __name__ == "__main__":
    unittest.main()
