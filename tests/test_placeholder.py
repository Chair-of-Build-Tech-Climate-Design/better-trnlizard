"""Lizard_Placeholder against fake Grasshopper objects, and the tables that tools/build_manifest.py writes into it.

The fakes mirror the SDK members the script uses. They show that it drives them as intended; whether real Grasshopper behaves
like the fakes (wires, undo, the window) is the manual test.
"""

import importlib.util
import itertools
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

from test_updater_io_sync import load_updater


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "components" / "Lizard_Placeholder.py"
_ids = itertools.count(1)

spec = importlib.util.spec_from_file_location("build_manifest", REPO_ROOT / "tools" / "build_manifest.py")
TOOL = importlib.util.module_from_spec(spec)
spec.loader.exec_module(TOOL)


class Attributes:
    def __init__(self, owner):
        self.owner = owner
        self.Pivot = (0.0, 0.0)
        self.layouts = 0

    @property
    def GetTopLevel(self):
        return SimpleNamespace(DocObject=self.owner)

    def ExpireLayout(self):
        self.layouts += 1


class Param:
    def __init__(self, name, owner=None):
        self.Name = name
        self.InstanceGuid = "param-%d" % next(_ids)
        self.Sources, self.Recipients = [], []
        self.Attributes = Attributes(owner if owner is not None else self)

    def AddSource(self, source, index=None):
        self.Sources.insert(len(self.Sources) if index is None else index, source)
        source.Recipients.append(self)

    def RemoveSource(self, source):
        self.Sources.remove(source)
        source.Recipients.remove(self)


class Component:
    def __init__(self, name, inputs=(), outputs=(), doc=None):
        self.Name = name
        self.InstanceGuid = "comp-%d" % next(_ids)
        self.Params = SimpleNamespace(Input=[Param(item, self) for item in inputs], Output=[Param(item, self) for item in outputs])
        self.Attributes = Attributes(self)
        self.expired = 0
        self.messages = []
        self.Message = None
        self.cleared = 0
        self.doc = doc

    def param(self, name):
        return next(p for p in self.Params.Input + self.Params.Output if p.Name == name)

    def ExpireSolution(self, recompute):
        self.expired += 1

    def AddRuntimeMessage(self, level, text):
        self.messages.append((level, text))

    def OnPingDocument(self):
        return self.doc

    def CreateAttributes(self):
        self.Attributes = Attributes(self)

    def ClearRuntimeMessages(self):
        self.cleared += 1


class Document:
    def __init__(self):
        self.Objects, self.scheduled, self.undo = [], [], []
        self.aborted = 0
        self.UndoUtil = SimpleNamespace(
            RecordWireEvent=lambda name, param: self.undo.append(("wire", param, list(param.Sources))),
            RecordAddObjectEvent=lambda name, obj: self.undo.append(("add", obj)),
            RecordRemoveObjectEvent=lambda name, obj: self.undo.append(("remove", obj, [p for p in obj.Params.Input + obj.Params.Output if p.Sources or p.Recipients])),
            MergeRecords=lambda count: self.undo.append(("merge", count)),
        )

    def AddObject(self, obj, update):
        self.Objects.append(obj)

    def RemoveObject(self, obj, update):
        self.Objects.remove(obj)

    def ScheduleSolution(self, delay, callback):
        self.scheduled.append(callback)

    def RequestAbortSolution(self):
        self.aborted += 1

    def runScheduled(self):
        scheduled, self.scheduled = self.scheduled, []
        for callback in scheduled:
            callback(self)


class ListItems(list):
    Add = list.append
    Clear = list.clear


class ValueList(Param):
    def __init__(self):
        super().__init__("Value List")
        self.ListItems = ListItems()
        self.expired = 0
        self.ListMode = None
        self.NickName = ""
        self.selected = None

    def CreateAttributes(self):
        self.Attributes = Attributes(self)

    def SelectItem(self, index):
        self.selected = index

    def ExpireSolution(self, recompute):
        self.expired += 1


def load_placeholder(component, instances=None):
    """The script as a namespace, run once for a component, with fake Rhino modules."""
    grasshopper = ModuleType("Grasshopper")
    kernel = ModuleType("Grasshopper.Kernel")
    kernel.GH_Document = SimpleNamespace(GH_ScheduleDelegate=lambda function: function)
    kernel.GH_RuntimeMessageLevel = SimpleNamespace(Warning="Warning", Remark="Remark")
    kernel.Special = SimpleNamespace(GH_ValueList=ValueList, GH_ValueListItem=lambda name, expression: (name, expression),
                                     GH_ValueListMode=SimpleNamespace(DropDown="DropDown"))
    grasshopper.Kernel = kernel
    instances = instances or {}

    def find(name, ignoreWhiteSpace, ignoreCapitalisation):
        return SimpleNamespace(CreateInstance=instances[name]) if name in instances else None
    grasshopper.Instances = SimpleNamespace(ComponentServer=SimpleNamespace(FindObjectByName=find), RedrawCanvas=lambda: None)
    scriptcontext = ModuleType("scriptcontext")
    scriptcontext.sticky = {}
    scriptcontext.doc = SimpleNamespace(Path="doc")
    namespace = {"ghenv": SimpleNamespace(Component=component), "__name__": "Lizard_Placeholder"}
    modules = {"Grasshopper": grasshopper, "Grasshopper.Kernel": kernel, "scriptcontext": scriptcontext}
    with mock.patch.dict(sys.modules, modules):
        exec(compile(SCRIPT.read_text(encoding="utf-8"), str(SCRIPT), "exec"), namespace)
    return namespace, scriptcontext


class PlaceholderTests(unittest.TestCase):
    def setUp(self):
        self.doc = Document()
        self.placeholder = Component("Lizard_Placeholder", ["Input"], ["Output"], self.doc)
        self.placeholder.Attributes.Pivot = (7.0, 9.0)
        self.doc.Objects.append(self.placeholder)
        self.instances = {"Lizard_Regime": lambda: Component("Lizard_Regime", ["Day"], ["Regime"]),
                          "Lizard_Lite": lambda: Component("Lizard_Lite", [], ["Regime"]),
                          "Lizard_Airnode": lambda: Component("Lizard_Airnode", ["Regime", "Mode"], ["Airnode"]),
                          "Lizard_Other": lambda: Component("Lizard_Other", ["In"], [])}
        self.script, self.scriptcontext = load_placeholder(self.placeholder, self.instances)
        self.script["OPTIONS"].clear()
        self.script["SOURCES"].clear()
        self.script["OPTIONS"]["Lizard_Airnode.Mode"] = {"type": "object", "options": ["STANDARD", "Fine=DETAILED", "Three=3"], "default": "DETAILED"}
        self.script["SOURCES"]["Lizard_Airnode.Regime"] = ["Lizard_Regime.Regime", "Lizard_Lite.Regime"]
        self.script["SOURCES"]["Lizard_Other.In"] = ["Lizard_Lite.Regime"]
        self.airnode = Component("Lizard_Airnode", ["Regime", "Mode"], ["Airnode"], self.doc)
        self.doc.Objects.append(self.airnode)
        self.output = self.placeholder.param("Output")
        self.input = self.placeholder.param("Input")
        self.chosen = []

    def choose(self, answer):
        def choose(port, found):
            self.chosen.append((port, [item["label"] for item in found]))
            return next((item for item in found if item["label"] == answer), None)
        self.script["choose"] = choose

    def state(self):
        return self.scriptcontext.sticky["Lizard_Placeholder"]

    def solve(self):
        """One solution of the Placeholder; the sticky stays."""
        self.placeholder.messages = []
        self.script["run"](self.placeholder)

    def connect_to(self, param):
        """The wire to an input of a component, as the script of that component then sees it."""
        param.AddSource(self.output)
        with self.assertRaises(SystemExit):
            self.script["checkPlaceholder"](param.Attributes.GetTopLevel.DocObject)

    def test_without_wires_it_is_ready_and_its_check_is_registered(self):
        self.assertIn(str(self.placeholder.InstanceGuid), self.state()["placeholders"])
        self.assertIs(self.script["checkPlaceholder"], self.scriptcontext.sticky["checkPlaceholder"])

    def test_the_line_of_a_script_calls_the_check(self):
        line = load_updater().requiredLine('"""\nArgs:\n    a (float): first\n        Access: item\n"""\n')
        self.airnode.param("Regime").AddSource(self.output)
        with mock.patch.dict(sys.modules, {"scriptcontext": self.scriptcontext}):
            with self.assertRaises(SystemExit):
                exec(line, {"ghenv": SimpleNamespace(Component=self.airnode)})
        self.assertEqual(1, len(self.doc.scheduled))

    def test_the_line_does_nothing_for_an_ordinary_wire(self):
        self.airnode.param("Regime").AddSource(Component("Lizard_Regime", [], ["Regime"], self.doc).param("Regime"))
        self.script["checkPlaceholder"](self.airnode)
        self.assertEqual([], self.doc.scheduled)

    def test_the_document_changes_only_after_the_solution(self):
        self.connect_to(self.airnode.param("Mode"))
        self.assertIn(self.placeholder, self.doc.Objects)
        self.assertNotIn(str(self.placeholder.InstanceGuid), self.state()["placeholders"])

    def test_the_solution_stops_after_the_component_of_the_wire(self):
        self.connect_to(self.airnode.param("Mode"))
        self.assertEqual(1, self.doc.aborted)

    def test_the_error_of_the_stop_is_cleared_before_the_window(self):
        def choose(port, found):
            self.assertEqual(1, self.airnode.cleared)
        self.script["choose"] = choose
        self.connect_to(self.airnode.param("Regime"))
        self.doc.runScheduled()
        self.assertEqual(1, self.airnode.cleared)

    def test_its_own_input_does_not_stop_the_solution(self):
        self.input.AddSource(Component("Lizard_Lite", [], ["Regime"], self.doc).param("Regime"))
        self.solve()
        self.assertEqual(0, self.doc.aborted)

    def test_a_second_run_of_the_script_does_not_schedule_again(self):
        self.connect_to(self.airnode.param("Mode"))
        self.script["checkPlaceholder"](self.airnode)
        self.assertEqual(1, len(self.doc.scheduled))

    def test_options_alone_become_a_value_list_in_its_place(self):
        del self.script["SOURCES"]["Lizard_Airnode.Regime"]
        mode = self.airnode.param("Mode")
        self.connect_to(mode)
        self.doc.runScheduled()
        self.assertNotIn(self.placeholder, self.doc.Objects)
        new = self.doc.Objects[-1]
        self.assertIsInstance(new, ValueList)
        self.assertEqual([("STANDARD", '"STANDARD"'), ("Fine", '"DETAILED"'), ("Three", "3")], new.ListItems)
        self.assertEqual((1, "DropDown", "Mode"), (new.selected, new.ListMode, new.NickName))
        self.assertEqual((7.0, 9.0), new.Attributes.Pivot)
        self.assertEqual([new], mode.Sources)
        self.assertEqual([], self.chosen)

    def test_a_text_input_gets_a_number_as_text(self):
        self.assertEqual('"0"', self.script["listExpression"]("str", "0"))
        self.assertEqual("0", self.script["listExpression"]("int", "0"))
        self.assertEqual('"AIR"', self.script["listExpression"]("object", "AIR"))

    def test_several_candidates_ask_and_the_choice_replaces_it(self):
        self.choose("Lizard_Lite.Regime")
        regime = self.airnode.param("Regime")
        self.connect_to(regime)
        self.doc.runScheduled()
        self.assertEqual([("Lizard_Airnode.Regime", ["Lizard_Regime.Regime", "Lizard_Lite.Regime"])], self.chosen)
        new = self.doc.Objects[-1]
        self.assertEqual("Lizard_Lite", new.Name)
        self.assertEqual([new.param("Regime")], regime.Sources)
        self.assertEqual([], self.output.Recipients)
        self.assertEqual(1, new.expired)

    def test_options_and_a_source_are_both_offered(self):
        self.script["SOURCES"]["Lizard_Airnode.Mode"] = ["Lizard_Lite.Regime"]
        self.choose("Lizard_Lite.Regime")
        self.connect_to(self.airnode.param("Mode"))
        self.doc.runScheduled()
        self.assertEqual(["Value List: STANDARD, Fine, Three", "Lizard_Lite.Regime"], self.chosen[0][1])

    def test_the_place_in_a_list_of_sources_stays(self):
        self.script["SOURCES"]["Lizard_Airnode.Regime"] = ["Lizard_Regime.Regime"]
        regime = self.airnode.param("Regime")
        first, last = Param("first"), Param("last")
        regime.AddSource(first)
        regime.AddSource(self.output)
        regime.AddSource(last)
        with self.assertRaises(SystemExit):
            self.script["checkPlaceholder"](self.airnode)
        self.doc.runScheduled()
        self.assertEqual(["first", "Regime", "last"], [source.Name for source in regime.Sources])

    def test_cancel_removes_the_wire_and_leaves_it_ready(self):
        self.choose(None)
        regime = self.airnode.param("Regime")
        self.connect_to(regime)
        self.doc.runScheduled()
        self.assertEqual([], regime.Sources)
        self.assertIn(self.placeholder, self.doc.Objects)
        self.assertEqual(1, self.placeholder.expired)
        self.solve()
        self.assertEqual([], self.placeholder.messages)
        self.assertIn(str(self.placeholder.InstanceGuid), self.state()["placeholders"])
        self.connect_to(regime)
        self.assertEqual(1, len(self.doc.scheduled))

    def test_no_annotation_removes_the_wire_with_a_warning_once(self):
        other = Component("Lizard_Other", ["Unknown"], [], self.doc)
        self.connect_to(other.param("Unknown"))
        self.doc.runScheduled()
        self.assertEqual([], other.param("Unknown").Sources)
        self.solve()
        self.assertEqual("Warning", self.placeholder.messages[0][0])
        self.assertIn("Unknown", self.placeholder.messages[0][1])
        self.assertEqual("Unknown: Unknown", self.placeholder.Message)
        self.solve()
        self.assertEqual([], self.placeholder.messages)
        self.assertEqual("", self.placeholder.Message)

    def test_a_missing_component_removes_the_wire_with_a_warning(self):
        self.script["SOURCES"]["Lizard_Airnode.Regime"] = ["Lizard_Gone.Regime"]
        regime = self.airnode.param("Regime")
        self.connect_to(regime)
        self.doc.runScheduled()
        self.assertEqual([], regime.Sources)
        self.solve()
        self.assertIn("Lizard_Gone", self.placeholder.messages[0][1])

    def test_a_missing_port_removes_the_wire_with_a_warning(self):
        self.script["SOURCES"]["Lizard_Airnode.Regime"] = ["Lizard_Lite.Gone"]
        regime = self.airnode.param("Regime")
        self.connect_to(regime)
        self.doc.runScheduled()
        self.assertEqual([], regime.Sources)
        self.assertEqual(1, len([obj for obj in self.doc.Objects if obj is self.placeholder]))
        self.solve()
        self.assertIn("Gone", self.placeholder.messages[0][1])

    def test_a_wire_removed_before_the_change_is_left_alone(self):
        mode = self.airnode.param("Mode")
        self.connect_to(mode)
        mode.RemoveSource(self.output)
        self.doc.runScheduled()
        self.assertIn(self.placeholder, self.doc.Objects)
        self.solve()
        self.assertIn(str(self.placeholder.InstanceGuid), self.state()["placeholders"])

    def test_undo_brings_it_back_without_the_wire(self):
        self.script["SOURCES"]["Lizard_Airnode.Regime"] = ["Lizard_Regime.Regime"]
        regime = self.airnode.param("Regime")
        self.connect_to(regime)
        self.doc.runScheduled()
        self.assertEqual([("wire", regime, []), ("add", self.doc.Objects[-1]), ("remove", self.placeholder, []), ("merge", 3)], self.doc.undo)

    def test_an_input_on_its_own_input_is_noticed_by_itself(self):
        lite = Component("Lizard_Lite", [], ["Regime"], self.doc)
        self.choose("Lizard_Other.In")
        self.input.AddSource(lite.param("Regime"))
        self.solve()
        self.assertEqual(1, len(self.doc.scheduled))
        self.doc.runScheduled()
        self.assertEqual(["Lizard_Airnode.Regime", "Lizard_Other.In"], self.chosen[0][1])
        new = self.doc.Objects[-1]
        self.assertEqual("Lizard_Other", new.Name)
        self.assertEqual([lite.param("Regime")], new.param("In").Sources)
        self.assertEqual([new.param("In")], lite.param("Regime").Recipients)
        self.assertEqual(("merge", 2), self.doc.undo[-1])

    def test_one_consumer_replaces_it_without_asking(self):
        del self.script["SOURCES"]["Lizard_Airnode.Regime"]
        lite = Component("Lizard_Lite", [], ["Regime"], self.doc)
        self.input.AddSource(lite.param("Regime"))
        self.solve()
        self.doc.runScheduled()
        self.assertEqual("Lizard_Other", self.doc.Objects[-1].Name)
        self.assertEqual([], self.chosen)

    def test_an_output_nothing_takes_removes_the_wire_with_a_warning(self):
        source = Component("Lizard_Regime", ["Day"], ["Unknown"], self.doc)
        self.input.AddSource(source.param("Unknown"))
        self.solve()
        self.doc.runScheduled()
        self.assertEqual([], self.input.Sources)
        self.solve()
        self.assertIn("output Unknown of Lizard_Regime", self.placeholder.messages[0][1])
        self.assertEqual("Unknown: Unknown", self.placeholder.Message)

    def came_with(self, *params):
        """A Placeholder whose first solution finds wires to these inputs."""
        placeholder = Component("Lizard_Placeholder", ["Input"], ["Output"], self.doc)
        self.doc.Objects.append(placeholder)
        for param in params:
            param.AddSource(placeholder.param("Output"))
        self.script["run"](placeholder)
        return placeholder

    def test_a_wire_it_came_with_does_nothing(self):
        placeholder = self.came_with(self.airnode.param("Mode"))
        self.assertEqual(("Remark", "Waiting for a wire"), (placeholder.messages[0][0], placeholder.Message))
        self.script["checkPlaceholder"](self.airnode)
        self.assertEqual([], self.doc.scheduled)
        placeholder = Component("Lizard_Placeholder", ["Input"], ["Output"], self.doc)
        placeholder.param("Input").AddSource(Param("somewhere"))
        self.script["run"](placeholder)
        self.assertEqual([], self.doc.scheduled)

    def test_a_new_wire_takes_over_from_those_it_came_with(self):
        mode = self.airnode.param("Mode")
        other = Component("Lizard_Other", ["In"], [], self.doc)
        placeholder = Component("Lizard_Placeholder", ["Input"], ["Output"], self.doc)
        self.doc.Objects.append(placeholder)
        other.param("In").AddSource(placeholder.param("Output"))
        placeholder.param("Input").AddSource(Param("somewhere"))
        self.script["run"](placeholder)
        self.assertEqual([], self.doc.scheduled)
        mode.AddSource(placeholder.param("Output"))
        with self.assertRaises(SystemExit):
            self.script["checkPlaceholder"](self.airnode)
        self.doc.runScheduled()
        self.assertNotIn(placeholder, self.doc.Objects)
        self.assertEqual(([], []), (other.param("In").Sources, placeholder.param("Input").Sources))
        self.assertIsInstance(mode.Sources[0], ValueList)

    def test_a_new_wire_takes_over_from_a_wire_to_another_kind_of_component(self):
        panel = Param("Panel")
        panel.AddSource(self.output)
        self.script["checkPlaceholder"](Component("Lizard_Other", ["In"], [], self.doc))
        self.assertEqual([], self.doc.scheduled)
        self.connect_to(self.airnode.param("Mode"))
        self.doc.runScheduled()
        self.assertEqual([], panel.Sources)

    def test_cancel_keeps_the_wires_it_had(self):
        self.choose(None)
        other = Component("Lizard_Other", ["In"], [], self.doc)
        placeholder = self.came_with(other.param("In"))
        regime = self.airnode.param("Regime")
        regime.AddSource(placeholder.param("Output"))
        with self.assertRaises(SystemExit):
            self.script["checkPlaceholder"](self.airnode)
        self.doc.runScheduled()
        self.assertEqual(([placeholder.param("Output")], []), (other.param("In").Sources, regime.Sources))

    def test_a_known_wire_connected_again_counts(self):
        mode = self.airnode.param("Mode")
        placeholder = self.came_with(mode)
        mode.RemoveSource(placeholder.param("Output"))
        self.script["checkPlaceholder"](self.airnode)
        self.assertEqual([], self.doc.scheduled)
        mode.AddSource(placeholder.param("Output"))
        with self.assertRaises(SystemExit):
            self.script["checkPlaceholder"](self.airnode)
        self.assertEqual(1, len(self.doc.scheduled))

    def test_new_wires_on_both_sides_only_warn(self):
        self.airnode.param("Mode").AddSource(self.output)
        self.input.AddSource(Param("somewhere"))
        self.solve()
        self.assertEqual("Warning", self.placeholder.messages[0][0])
        self.assertEqual("Several new wires", self.placeholder.Message)
        self.script["checkPlaceholder"](self.airnode)
        self.assertEqual([], self.doc.scheduled)
        self.assertEqual(0, self.doc.aborted)

    def test_two_new_inputs_warn_through_a_solution_of_the_placeholder(self):
        other = Component("Lizard_Other", ["In"], [], self.doc)
        self.airnode.param("Mode").AddSource(self.output)
        other.param("In").AddSource(self.output)
        self.script["checkPlaceholder"](self.airnode)
        self.script["checkPlaceholder"](other)
        self.assertEqual(1, len(self.doc.scheduled))
        self.doc.runScheduled()
        self.assertEqual(1, self.placeholder.expired)
        self.solve()
        self.assertIn("2 new wires", self.placeholder.messages[0][1])
        self.assertEqual([], self.doc.scheduled)
        self.assertIn(self.placeholder, self.doc.Objects)

    def test_removing_all_but_one_new_wire_brings_it_in(self):
        other = Component("Lizard_Other", ["In"], [], self.doc)
        mode = self.airnode.param("Mode")
        mode.AddSource(self.output)
        other.param("In").AddSource(self.output)
        self.solve()
        other.param("In").RemoveSource(self.output)
        self.script["checkPlaceholder"](other)  # not the component of the wire that is left: this script goes on
        self.assertEqual(0, self.doc.aborted)
        self.doc.runScheduled()
        self.assertIsInstance(mode.Sources[0], ValueList)

    def test_removing_a_wire_on_its_input_brings_in_the_other_side(self):
        mode = self.airnode.param("Mode")
        mode.AddSource(self.output)
        source = Param("somewhere")
        self.input.AddSource(source)
        self.solve()
        self.input.RemoveSource(source)
        self.solve()
        self.doc.runScheduled()
        self.assertIsInstance(mode.Sources[0], ValueList)

    def test_a_failure_in_the_callback_removes_the_wire_and_warns(self):
        def broken(doc, placeholder, source, recipient):
            raise RuntimeError("broken")
        self.script["resolve"] = broken
        mode = self.airnode.param("Mode")
        self.connect_to(mode)
        self.doc.runScheduled()
        self.assertEqual([], mode.Sources)
        self.solve()
        self.assertEqual("broken", self.placeholder.messages[0][1])
        self.assertEqual("Failed", self.placeholder.Message)

    def test_the_search_needs_all_words_in_any_case(self):
        found = [{"label": "Lizard_Zone_Regime.Regime"}, {"label": "Lizard_Lite_Zone_Regime.Regime"}, {"label": "Value List: A, B"}]
        search = self.script["filterCandidates"]
        self.assertEqual(found, search(found, "  "))
        self.assertEqual(found[:2], search(found, "REGIME"))
        self.assertEqual(found[1:2], search(found, "regime lite"))
        self.assertEqual([], search(found, "nothing"))


class TableTests(unittest.TestCase):
    updater = load_updater()

    def script(self):
        return load_placeholder(Component("Lizard_Placeholder", ["Input"], ["Output"], Document()))[0]

    def test_the_written_tables_are_up_to_date(self):
        path, text, updated = TOOL.updatedPlaceholder(str(REPO_ROOT))
        self.assertEqual(updated, text)

    def test_the_parser_of_the_tool_agrees_with_the_updater(self):
        for path in sorted((REPO_ROOT / "components").glob("Lizard_*.py")):
            code = path.read_text(encoding="utf-8")
            for ours, theirs in zip(TOOL.parseParams(code), self.updater.parseDocstringIO(code)):
                theirs = [p for p in theirs or [] if not p["separator"]]
                self.assertEqual([(p["name"], p["type"], p["options"], p["default"]) for p in theirs],
                                 [(p["name"], p["type"], p["options"], p["default"]) for p in ours], path.name)

    def test_a_source_nothing_gives_stops_the_tool(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder)
        (folder / "components").mkdir()
        doc = '"""\nArgs:\n    a (object): a\n        Access: item\n        Source: Lizard_B.gone\n\nReturns:\n    r (object): r\n        Access: item\n"""\n'
        (folder / "components" / "Lizard_A.py").write_text(doc, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Lizard_A.a.*Lizard_B.gone"):
            TOOL.placeholderTables(str(folder))

    def test_a_source_points_at_an_output_and_its_input_exists(self):
        script = self.script()
        scripts = dict((path.stem, TOOL.parseParams(path.read_text(encoding="utf-8"))) for path in (REPO_ROOT / "components").glob("Lizard_*.py"))
        for target, sources in script["SOURCES"].items():
            component, _, port = target.partition(".")
            self.assertIn(port, [p["name"] for p in scripts[component][0]], target)
            self.assertEqual(len(sources), len(set(sources)), target)

    def test_a_regime_has_all_its_makers_and_an_output_finds_its_inputs(self):
        script = self.script()
        self.assertEqual(["Lizard_Zone_Regime.Regime", "Lizard_Lite_Zone_Regime.Regime", "Lizard_Zone_Reg4108.Regime"],
                         [item["label"] for item in script["candidatesForInput"]("Lizard_Thermal_Airnode", "Regime")])
        self.assertEqual(["Lizard_Thermal_Airnode.Regime"], [item["label"] for item in script["candidatesForOutput"]("Lizard_Zone_Regime", "Regime")])

    def test_an_option_with_a_label_has_both_parts(self):
        script = self.script()
        for key, entry in script["OPTIONS"].items():
            for text in entry["options"]:
                label, value = script["optionItem"](text)
                self.assertTrue(label and value, (key, text))

    def test_the_new_options_are_values_the_scripts_use(self):
        code = "".join(path.read_text(encoding="utf-8").split('"""', 2)[2] for path in (REPO_ROOT / "components").glob("Lizard_*.py"))
        script = self.script()
        checked = 0
        for key in ("Lizard_Coupling.Type", "Lizard_Mechanical_Ventilation.Mode", "Lizard_Thermal_Airnode.BeamMode",
                    "Lizard_System.StartMonth", "Lizard_BSDF_Settings.ShdControl", "Lizard_Cooling.ControlledTemperature"):
            for text in script["OPTIONS"][key]["options"]:
                self.assertIn(script["optionItem"](text)[1], code, key)
                checked += 1
        self.assertGreater(checked, 0)


if __name__ == "__main__":
    unittest.main()
