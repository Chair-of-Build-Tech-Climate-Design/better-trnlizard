"""inspectModel of Lizard_Component.py and the real Lizard_Model_Inspect.py on stand-ins for Rhino and Grasshopper."""

import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

from test_surface_model import FakeBrep, M, airnode, library, north, south, surface, window_in


REPO_ROOT = Path(__file__).resolve().parents[1]


def floor(z=0.0, **options):
    return surface([(0, 0, z), (0, 4, z), (5, 4, z), (5, 0, z)], **options)


def inspect(*nodes, standalone=False, constructionset=None, autoadjacency=False):
    return M["inspectModel"](list(nodes), library(), autoadjacency, None, standalone, constructionset)


def row_of(report, number):
    return [row for row in report["rows"] if row["surface"] == number][0]


class GroupTests(unittest.TestCase):
    def group(self, item):
        return M["inspectGroup"](item)

    def test_categories(self):
        self.assertEqual("External", self.group(south(0, 5, category="EXTERNAL")))
        self.assertEqual("External", self.group(south(0, 5, category="EXTCALEXT")))
        self.assertEqual("Boundary", self.group(south(0, 5, category="BOUNDARY", temperature="INPUT 1*Tsoil")))
        self.assertEqual("Mirror", self.group(south(0, 5, category="BOUNDARY", temperature="INPUT 1*TAIR_@ANAME")))
        self.assertEqual("Mirror", self.group(south(0, 5, category="EXTCALBND", temperature=0)))
        self.assertEqual("Other", self.group(south(0, 5, category="VIRTUAL")))
        self.assertEqual("Other", self.group(south(0, 5, category="INTERNAL")))
        self.assertEqual("Window", self.group(south(0, 5, category="EXTERNAL", kind="WINDOW")))
        self.assertEqual("Window", self.group(south(0, 5, category="EXTERNAL", kind="ADDWINDOW")))

    def test_what_has_no_answer_is_unresolved(self):
        self.assertEqual("Unresolved", self.group(floor()))
        self.assertEqual("Unresolved", self.group(south(0, 5, category="ADJACENT")))

    def test_adjacent_needs_a_partner(self):
        item = south(0, 5, category="ADJACENT")
        item.Adjsurf = 12
        self.assertEqual("Adjacent", self.group(item))

    def test_every_group_has_a_colour(self):
        self.assertEqual(sorted(M["INSPECT_GROUPS"]), sorted(M["INSPECT_COLOURS"]))


class ReportTests(unittest.TestCase):
    def test_groups_hold_one_branch_per_airnode(self):
        a, b, c = south(0, 6, number=1), north(0, 2, number=2), floor(category="EXTERNAL", number=3)
        report = inspect(airnode("A1", a), airnode("A2", b, c))
        self.assertEqual(["A1", "A2"], report["airnodes"])
        adjacent = report["groups"]["Adjacent"]
        self.assertEqual(2, len(adjacent))
        self.assertEqual([4], [item.Surfnum for item in adjacent[0]])  # the smaller piece of surface 1 got a new number
        self.assertEqual([2], [item.Surfnum for item in adjacent[1]])
        self.assertEqual([[1], [3]], [[item.Surfnum for item in branch] for branch in report["groups"]["External"]])

    def test_pieces_of_a_split_surface_name_their_source(self):
        a, b = south(0, 6, number=10), north(0, 2, number=11)
        report = inspect(airnode("A1", a), airnode("A2", b))
        pieces = [row for row in report["rows"] if row["airnode"] == "A1"]
        self.assertEqual(2, len(pieces))
        self.assertEqual({10}, set(row["source"] for row in pieces))
        self.assertEqual({"External", "Adjacent"}, set(row["group"] for row in pieces))

    def test_row_has_what_a_table_needs(self):
        a, b = south(0, 5, number=20), north(0, 5, number=21)
        report = inspect(airnode("A1", a), airnode("A2", b))
        row = row_of(report, 20)
        self.assertEqual(("A1", "ADJACENT", "WALL", "InteriorWall", "A2:21", "FRONT"), (row["airnode"], row["category"], row["type"], row["slot"], row["partner"], row["frontback"]))
        self.assertAlmostEqual(15.0, row["area"])

    def test_construction_from_a_set_is_marked(self):
        a, b = south(0, 5, number=30, construction=None), south(5, 9, number=31)
        report = inspect(airnode("A1", a, b), constructionset=SimpleNamespace(ExteriorWall="OUT"))
        self.assertEqual((True, "OUT"), (row_of(report, 30)["fromset"], row_of(report, 30)["construction"]))
        self.assertEqual((False, "WALL"), (row_of(report, 31)["fromset"], row_of(report, 31)["construction"]))

    def test_a_model_with_errors_is_still_reported(self):
        item = floor(number=40, category="ADJACENT")
        report = inspect(airnode("A1", item))
        self.assertEqual("Unresolved", row_of(report, 40)["group"])
        self.assertEqual(["error"], [issue["level"] for issue in report["issues"]])

    def test_summary_counts_and_adds_up_areas(self):
        report = inspect(airnode("A1", south(0, 5, category="EXTERNAL"), south(5, 9, category="EXTERNAL")))
        self.assertEqual(["External: 2 surfaces, 27.00 m2"], report["summary"])

    def test_windows_have_their_own_group_and_no_slot(self):
        wall = south(0, 5, category="EXTERNAL", number=50)
        window = window_in(wall, 1, 2)
        report = inspect(airnode("A1", wall, windows=[window]))
        row = row_of(report, window.Surfnum)
        self.assertEqual(("Window", ""), (row["group"], row["slot"]))

    def test_table_has_a_header_and_one_line_per_surface(self):
        report = inspect(airnode("A1", south(0, 5, category="EXTERNAL", number=60)))
        table = M["inspectTable"](report["rows"])
        self.assertEqual(2, len(table))
        self.assertEqual(table[0].count("\t"), table[1].count("\t"))
        self.assertIn("Airnode", table[0])
        self.assertIn("60", table[1])

    def test_standalone_compiles_each_airnode_alone(self):
        a, b = south(0, 5, category="ADJACENT", number=70), north(0, 5, category="ADJACENT", number=71)
        report = inspect(airnode("A1", a), airnode("A2", b), standalone=True)
        self.assertEqual([], [issue for issue in report["issues"] if issue["level"] == "error"])
        self.assertEqual(("Mirror", "Mirror"), (row_of(report, 70)["group"], row_of(report, 71)["group"]))


class FakeTree:
    def __init__(self):
        self.branches = {}

    def __class_getitem__(cls, item):
        return cls

    def EnsurePath(self, path):
        self.branches.setdefault(path, [])

    def Add(self, item, path):
        self.branches.setdefault(path, []).append(item)


class FakeInspectBrep(FakeBrep):
    def __init__(self, points):
        super().__init__(points)
        self.moved = None

    def DuplicateBrep(self):
        other = FakeInspectBrep(self.points)
        return other

    def Translate(self, vector):
        self.moved = vector


def run_component(nodes, standalone=None, upstream=(), **multizone):
    source = (REPO_ROOT / "components" / "Lizard_Model_Inspect.py").read_text(encoding="utf-8-sig")
    messages = []
    class Zones:
        def callFromZones(self, breps):
            return list(nodes)
    scriptcontext = ModuleType("scriptcontext")
    scriptcontext.doc = SimpleNamespace(Path="doc")
    scriptcontext.sticky = {"doc": {"ZONECOLL": Zones, "library": library(), "upstreamErrors": lambda component, level: list(upstream), "inspectModel": M["inspectModel"], "inspectTable": M["inspectTable"], "INSPECT_GROUPS": M["INSPECT_GROUPS"], "INSPECT_COLOURS": M["INSPECT_COLOURS"], "date": "today"}}
    grasshopper = ModuleType("Grasshopper")
    grasshopper.DataTree = FakeTree
    kernel = ModuleType("Grasshopper.Kernel")
    kernel.GH_RuntimeMessageLevel = SimpleNamespace(Warning="WARNING", Error="ERROR", Remark="REMARK")
    data = ModuleType("Grasshopper.Kernel.Data")
    data.GH_Path = lambda index: index
    kernel.Data = data
    grasshopper.Kernel = kernel
    system = ModuleType("System")
    drawing = ModuleType("System.Drawing")
    drawing.Color = SimpleNamespace(FromArgb=lambda r, g, b: (r, g, b))
    system.Drawing = drawing
    component = SimpleNamespace(AddRuntimeMessage=lambda level, text: messages.append((level, text)), Name="", NickName="", Message="", Category="", SubCategory="")
    values = {"airnode": ["brep"], "autoadjacency": None, "gaptolerance": None, "constructionset": None}
    values.update(multizone)
    namespace = {"ghenv": SimpleNamespace(Component=component), "Multizone": SimpleNamespace(**values)}
    if standalone is not None:
        namespace["Standalone"] = standalone
    modules = {"scriptcontext": scriptcontext, "Grasshopper": grasshopper, "Grasshopper.Kernel": kernel, "Grasshopper.Kernel.Data": data, "System": system, "System.Drawing": drawing}
    with mock.patch.dict(sys.modules, modules):
        exec(compile(source, "Lizard_Model_Inspect.py", "exec"), namespace)
    return namespace, messages


def with_breps(item):
    item.Surface = item.Faces = FakeInspectBrep(M["surfacePoints"](item))
    return item


class ComponentTests(unittest.TestCase):
    def test_name_and_outputs(self):
        text = (REPO_ROOT / "components" / "Lizard_Model_Inspect.py").read_text(encoding="utf-8-sig")
        self.assertIn('ghenv.Component.Name = "Lizard_Model_Inspect"', text)
        for group in M["INSPECT_GROUPS"]:
            self.assertIn("    {0} (object):".format(group), text)

    def test_shared_functions_are_registered(self):
        text = (REPO_ROOT / "components" / "Lizard_Component.py").read_text(encoding="utf-8-sig")
        for name in ("inspectModel", "inspectTable", "INSPECT_GROUPS", "INSPECT_COLOURS"):
            self.assertIn('sc.sticky[sc.doc.Path]["%s"]' % name, text)

    def test_outputs_are_trees_by_airnode_and_sorted_by_name(self):
        a, b = with_breps(south(0, 5, number=1)), with_breps(north(0, 5, number=2))
        result, _ = run_component([airnode("B", a), airnode("A", b)])
        self.assertEqual(["A", "B"], result["Airnodes"])
        self.assertEqual({0: [b.Faces], 1: [a.Faces]}, result["Adjacent"].branches)
        self.assertEqual({0: [], 1: []}, result["External"].branches)

    def test_preview_has_a_colour_per_brep(self):
        wall = with_breps(south(0, 5, category="EXTERNAL", number=3))
        result, _ = run_component([airnode("A", wall)])
        self.assertEqual(1, len(result["Preview"]))
        self.assertEqual([M["INSPECT_COLOURS"]["External"]], result["Colours"])

    def test_windows_are_lifted_off_their_wall_in_the_preview_only(self):
        wall = with_breps(south(0, 5, category="EXTERNAL", number=4))
        window = with_breps(window_in(wall, 1, 2))
        result, _ = run_component([airnode("A", wall, windows=[window])])
        self.assertEqual(M["INSPECT_COLOURS"]["Window"], result["Colours"][-1])
        self.assertIsNotNone(result["Preview"][-1].moved)
        self.assertIsNone(window.Faces.moved)

    def test_errors_reach_the_component(self):
        item = with_breps(floor(number=5, category="ADJACENT"))
        result, messages = run_component([airnode("A", item)])
        self.assertEqual("ERROR", messages[0][0])
        self.assertTrue(result["Problems"][0].startswith("ERROR: "))
        self.assertEqual([item.Faces], result["ProblemSurfaces"])
        self.assertIn("1 error", result["ghenv"].Component.Message)

    def test_info_is_listed_but_is_no_problem_surface(self):
        wall = with_breps(south(0, 5, number=6, construction=None))
        result, messages = run_component([airnode("A", wall)], constructionset=SimpleNamespace(ExteriorWall="OUT"))
        self.assertEqual([], messages)
        self.assertTrue(result["Problems"][0].startswith("INFO: "))
        self.assertEqual([], result["ProblemSurfaces"])

    def test_standalone_input_reaches_the_model(self):
        a = with_breps(south(0, 5, category="ADJACENT", number=7))
        _, messages = run_component([airnode("A", a)], standalone=True)
        self.assertEqual([], [message for message in messages if message[0] == "ERROR"])

    def test_upstream_errors_are_listed_and_counted(self):
        wall = with_breps(south(0, 5, category="EXTERNAL", number=8))
        result, messages = run_component([airnode("A", wall)], upstream=["Surface: Construction name not found in the library!"])
        self.assertEqual("ERROR", messages[0][0])
        self.assertIn("Upstream error, Surface", result["Problems"][0])
        self.assertIn("1 error", result["ghenv"].Component.Message)

    def test_a_failed_set_is_an_error_here_too(self):
        wall = with_breps(south(0, 5, number=9, construction=None))
        failure = M["ComponentFailure"]("Lizard_Construction_Set", "ExteriorWall: construction NOPE not found")
        result, messages = run_component([airnode("A", wall)], constructionset=failure)
        self.assertEqual(["ERROR"], [message[0] for message in messages])
        self.assertIn("NOPE", result["Problems"][0])

    def test_nothing_connected_does_nothing(self):
        source = (REPO_ROOT / "components" / "Lizard_Model_Inspect.py").read_text(encoding="utf-8-sig")
        self.assertIn("if Multizone:", source)


if __name__ == "__main__":
    unittest.main()
