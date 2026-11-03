"""Default constructions from Lizard_Construction_Set, the meaning of AUTOMATIC, and the solid of an airnode with surfaces on top of it.

Same harness as test_surface_model.py: the real blocks of Lizard_Component.py with stand-ins for Rhino.
"""

import copy
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

from test_surface_model import FakeSurfaceBrep, FakeUserDictionary, M, Vec, airnode, compile_model, errors, library, load_construction, north, south, surface, warnings_of, walls_of


REPO_ROOT = Path(__file__).resolve().parents[1]


def infos(issues):
    return [issue["message"] for issue in issues if issue["level"] == "info"]


def floor(x0=0, x1=5, z=0.0, **options):
    return surface([(x0, 0, z), (x0, 4, z), (x1, 4, z), (x1, 0, z)], **options)


def ceiling(x0=0, x1=5, z=0.0, **options):
    return surface([(x0, 0, z), (x1, 0, z), (x1, 4, z), (x0, 4, z)], **options)


def constructions(**slots):
    return SimpleNamespace(**slots)


class AutomaticTests(unittest.TestCase):
    def test_automatic_is_the_same_as_empty(self):
        for category in ("AUTOMATIC", None):
            a, b = south(0, 5, category=category), north(0, 5, category=category)
            self.assertEqual([], compile_model(airnode("A1", a), airnode("A2", b)))
            self.assertEqual(("ADJACENT", "ADJACENT"), (a.Boundarycond, b.Boundarycond))

    def test_unmatched_automatic_wall_and_roof_are_external(self):
        wall, roof = south(0, 5, category="AUTOMATIC"), ceiling(z=3.0, category="AUTOMATIC")
        self.assertEqual([], errors(compile_model(airnode("A1", wall, roof))))
        self.assertEqual(("EXTERNAL", "EXTERNAL", "ROOF"), (wall.Boundarycond, roof.Boundarycond, roof.Type))

    def test_unmatched_automatic_floor_at_the_ground_is_ground_with_a_warning(self):
        item = floor(category="AUTOMATIC")
        issues = compile_model(airnode("A1", item))
        self.assertEqual([], errors(issues))
        self.assertEqual(("BOUNDARY", "INPUT 1*Tsoil"), (item.Boundarycond, item.Boundarytemp))
        self.assertIn("GROUND is used", warnings_of(issues)[0])

    def test_explicit_external_floor_stays(self):
        item = floor(category="EXTERNAL")
        self.assertEqual([], errors(compile_model(airnode("A1", item))))
        self.assertEqual("EXTERNAL", item.Boundarycond)


class SlotTests(unittest.TestCase):
    def slot(self, item):
        return M["constructionSlot"](item)

    def test_slots(self):
        wall = south(0, 5, category="EXTERNAL")
        self.assertEqual("ExteriorWall", self.slot(wall))
        wall.Boundarycond = "ADJACENT"
        self.assertEqual("InteriorWall", self.slot(wall))
        wall.Boundarycond = "BOUNDARY"
        self.assertEqual("InteriorWall", self.slot(wall))
        self.assertEqual("Roof", self.slot(ceiling(category="EXTERNAL", kind="ROOF")))
        self.assertEqual("InteriorCeiling", self.slot(ceiling(category="ADJACENT", kind="CEILING")))
        self.assertEqual("InteriorFloor", self.slot(floor(category="ADJACENT")))
        self.assertEqual("ExposedFloor", self.slot(floor(category="EXTERNAL")))

    def test_floor_boundary_is_ground_unless_it_mirrors_the_room(self):
        self.assertEqual("GroundFloor", self.slot(floor(category="BOUNDARY", temperature="INPUT 1*TGROUND")))
        self.assertEqual("GroundFloor", self.slot(floor(category="BOUNDARY", temperature="12")))
        self.assertEqual("InteriorFloor", self.slot(floor(category="BOUNDARY", temperature=0)))
        self.assertEqual("InteriorFloor", self.slot(floor(category="BOUNDARY", temperature="INPUT 1*TAIR_@ANAME")))

    def test_hygrothermal_categories_follow_the_side_they_stand_for(self):
        self.assertEqual("ExteriorWall", self.slot(south(0, 5, category="EXTCALEXT")))
        self.assertEqual("InteriorWall", self.slot(south(0, 5, category="EXTCALBND")))
        self.assertEqual("Roof", self.slot(ceiling(category="EXTCALEXT", kind="CEILING")))


class FillTests(unittest.TestCase):
    def compile(self, *nodes, **options):
        return M["compileModel"](list(nodes), library(), constructionset=options.pop("model", None), **options)

    def test_no_set_gives_the_error_with_the_slot(self):
        item = south(0, 5, construction=None)
        issues = self.compile(airnode("A1", item))
        self.assertEqual(1, len(errors(issues)))
        self.assertIn("ExteriorWall", errors(issues)[0])

    def test_final_boundary_condition_chooses_the_slot(self):
        a, b = south(0, 6, construction=None, number=70), north(0, 2, construction=None, number=71)
        na, nb = airnode("A1", a), airnode("A2", b)
        issues = self.compile(na, nb, model=constructions(ExteriorWall="OUT", InteriorWall="WALL"))
        self.assertEqual([], errors(issues))
        pieces = dict((piece.Boundarycond, piece) for piece in walls_of(na))
        self.assertEqual(("OUT", "WALL"), (pieces["EXTERNAL"].Construction, pieces["ADJACENT"].Construction))
        self.assertEqual("WALL", b.Construction)

    def test_explicit_value_wins(self):
        item = south(0, 5, construction="WALL")
        self.compile(airnode("A1", item), model=constructions(ExteriorWall="OUT"))
        self.assertEqual("WALL", item.Construction)

    def test_airnode_set_before_model_set_slot_by_slot(self):
        wall, roof = south(0, 5, construction=None), ceiling(z=3.0, construction=None)
        node = airnode("A1", wall, roof)
        node.Constructionset = constructions(ExteriorWall="WALL")
        issues = self.compile(node, model=constructions(ExteriorWall="OUT", Roof="IFL"))
        self.assertEqual([], errors(issues))
        self.assertEqual(("WALL", "IFL"), (wall.Construction, roof.Construction))

    def test_explicit_side_decides_the_pair_and_is_the_front(self):
        a, b = south(0, 5, construction=None), north(0, 5, construction="OUT")
        issues = self.compile(airnode("A1", a), airnode("A2", b), model=constructions(InteriorWall="WALL"))
        self.assertEqual([], errors(issues))
        self.assertEqual(("OUT", "OUT"), (a.Construction, b.Construction))
        self.assertEqual(("BACK", "FRONT"), (a.Frontback, b.Frontback))

    def test_floor_and_ceiling_take_their_own_slots(self):
        top, bottom = floor(z=3.0, construction=None), ceiling(z=3.0, construction=None)
        issues = self.compile(airnode("A2", top), airnode("A1", bottom), model=constructions(InteriorFloor="IFL", InteriorCeiling="ICL"))
        self.assertEqual([], errors(issues))
        self.assertEqual(("IFL", "FRONT"), (top.Construction, top.Frontback))
        self.assertEqual(("ICL", "BACK"), (bottom.Construction, bottom.Frontback))

    def test_set_with_only_the_floor_is_followed_by_the_ceiling(self):
        top, bottom = floor(z=3.0, construction=None), ceiling(z=3.0, construction=None)
        issues = self.compile(airnode("A2", top), airnode("A1", bottom), model=constructions(InteriorFloor="IFL"))
        self.assertEqual([], errors(issues))
        self.assertEqual(("IFL", "IFL"), (top.Construction, bottom.Construction))

    def test_set_with_only_the_ceiling_cannot_be_used_for_the_front(self):
        top, bottom = floor(z=3.0, construction=None), ceiling(z=3.0, construction=None)
        issues = self.compile(airnode("A2", top), airnode("A1", bottom), model=constructions(InteriorCeiling="ICL"))
        self.assertEqual(1, len(errors(issues)))
        self.assertIn("InteriorFloor", errors(issues)[0])

    def test_rooms_with_different_sets_on_one_wall_are_an_error(self):
        a, b = south(0, 5, construction=None), north(0, 5, construction=None)
        na, nb = airnode("A1", a), airnode("A2", b)
        na.Constructionset, nb.Constructionset = constructions(InteriorWall="WALL"), constructions(InteriorWall="OUT")
        issues = self.compile(na, nb)
        self.assertEqual(1, len(errors(issues)))
        self.assertIn("different constructions", errors(issues)[0])

    def test_non_symmetric_wall_from_a_set_warns_about_the_direction(self):
        a, b = south(0, 5, construction=None), north(0, 5, construction=None)
        issues = self.compile(airnode("A1", a), airnode("A2", b), model=constructions(InteriorWall="OUT"))
        self.assertEqual([], errors(issues))
        self.assertEqual(1, len([message for message in warnings_of(issues) if "non-symmetric" in message]))

    def test_unknown_name_in_a_set_is_an_error(self):
        issues = self.compile(airnode("A1", south(0, 5, construction=None)), model=constructions(ExteriorWall="NOPE"))
        self.assertIn("not in the library", errors(issues)[0])

    def test_what_a_set_filled_is_reported(self):
        a, b = south(0, 5, construction=None, number=80), south(5, 9, construction=None, number=81)
        issues = self.compile(airnode("A1", a, b), model=constructions(ExteriorWall="OUT"))
        self.assertEqual(1, len(infos(issues)))
        self.assertIn("ExteriorWall", infos(issues)[0])
        self.assertIn("OUT", infos(issues)[0])
        self.assertIn("80", infos(issues)[0])

    def test_nothing_is_reported_without_a_set(self):
        self.assertEqual([], infos(self.compile(airnode("A1", south(0, 5, construction="WALL")))))

    def test_windows_and_virtual_surfaces_are_left_alone(self):
        virtual = south(0, 5, category="VIRTUAL", construction=None)
        self.compile(airnode("A1", virtual), model=constructions(ExteriorWall="OUT", InteriorWall="OUT"))
        self.assertIsNone(virtual.Construction)

    def test_converted_surface_without_construction_gets_no_warning(self):
        a, b = south(0, 5, category="EXTERNAL", construction=None), north(0, 5, category="EXTERNAL", construction=None)
        issues = self.compile(airnode("A1", a), airnode("A2", b), autoadjacency=True, model=constructions(InteriorWall="WALL"))
        self.assertEqual([], [message for message in warnings_of(issues) if "keep the construction" in message])
        self.assertEqual(("WALL", "WALL"), (a.Construction, b.Construction))


class SubtractTests(unittest.TestCase):
    def test_surface_on_a_face_replaces_that_part(self):
        face = south(0, 6, number=90)
        explicit = south(0, 2, number=91)
        pieces, outside = M["subtractSurfaces"]([face], [explicit])
        self.assertEqual([], outside)
        self.assertEqual([90], list(pieces))
        self.assertEqual(1, len(pieces[90]))
        area = M["polyAreaVector"](pieces[90][0])
        self.assertAlmostEqual(12.0, M["vecDot"](area, area)**0.5)
        self.assertLess(area[1], 0)  # the winding of the face

    def test_surface_over_the_whole_face_leaves_nothing(self):
        pieces, outside = M["subtractSurfaces"]([south(0, 6, number=92)], [south(0, 6, number=93)])
        self.assertEqual(({92: []}, []), (pieces, outside))

    def test_reversed_surface_counts_as_well(self):
        pieces, outside = M["subtractSurfaces"]([south(0, 6, number=94)], [north(0, 6, number=95)])
        self.assertEqual(({94: []}, []), (pieces, outside))

    def test_faces_without_a_surface_on_them_are_not_touched(self):
        pieces, outside = M["subtractSurfaces"]([south(0, 6, number=96), floor(number=97)], [south(0, 2, number=98)])
        self.assertEqual([96], list(pieces))

    def test_surface_outside_the_faces_is_reported(self):
        _, outside = M["subtractSurfaces"]([south(0, 6, number=99)], [north(0, 6, y=2.0, number=100)])
        self.assertEqual([100], [item.Surfnum for item in outside])

    def test_surface_sticking_out_of_a_face_is_reported(self):
        _, outside = M["subtractSurfaces"]([south(0, 6, number=101)], [south(4, 8, number=102)])
        self.assertEqual([102], [item.Surfnum for item in outside])

    def test_surface_in_the_middle_is_cut_out(self):
        pieces, _ = M["subtractSurfaces"]([south(0, 6, number=103)], [surface([(2, 0, 1), (4, 0, 1), (4, 0, 2), (2, 0, 2)], number=104)])
        total = sum(M["vecDot"](M["polyAreaVector"](loop), M["polyAreaVector"](loop))**0.5 for loop in pieces[103])
        self.assertAlmostEqual(16.0, total)


class ExpandTests(unittest.TestCase):
    """CONSTRUCTION.expandSolids, with solidFaces, makeSurfaceBrep and the record geometry replaced."""

    def setUp(self):
        self.construction, self.sticky = load_construction()

    def brep(self, faces=1, lid=None, name="a"):
        brep = FakeSurfaceBrep(name)
        brep.Faces = SimpleNamespace(Count=faces)
        if lid:
            brep.UserDictionary.Set("LID", lid)
        return brep

    def test_two_solids_are_a_problem(self):
        _, problem = self.construction.expandSolids([self.brep(6), self.brep(6, name="b")], "c1")
        self.assertIn("one solid", problem)

    def test_bare_single_faces_are_registered(self):
        breps, problem = self.construction.expandSolids([self.brep(1)], "c1")
        self.assertIsNone(problem)
        self.assertEqual(1, len(self.sticky["Const_coll"]))
        self.assertTrue(breps[0].UserDictionary.ContainsKey("LID"))

    def test_surfaces_with_settings_pass_unchanged(self):
        known = self.construction.addToConstruction([self.brep(1)], "c0")[0]
        breps, problem = self.construction.expandSolids([known], "c1")
        self.assertIsNone(problem)
        self.assertIs(known, breps[0])
        self.assertEqual(1, len(self.sticky["Const_coll"]))


class SolidBrep(FakeSurfaceBrep):
    """A single face with real points."""

    def __init__(self, name, points):
        super().__init__(name)
        self.points = points

    def DuplicateBrep(self):
        other = SolidBrep(self.name, self.points)
        other.UserDictionary = FakeUserDictionary(self.UserDictionary)
        return other


def south_face(name, x0, x1):
    return SolidBrep(name, [(x0, 0, 0), (x1, 0, 0), (x1, 0, 3), (x0, 0, 3)])


class ExpandSolidTests(unittest.TestCase):
    """The way of a solid through expandSolids, with the Rhino calls replaced."""

    def setUp(self):
        self.construction, self.sticky = load_construction()
        scope = type(self.construction).expandSolids.__globals__
        scope["surfaceNormal"] = lambda brep: Vec(*M["vecUnit"](M["polyAreaVector"](brep.points)))
        scope["getSurfaceVertices"] = lambda normal, brep: [Vec(*point) for point in brep.points]
        scope["makeSurfaceBrep"] = lambda points, normal: SolidBrep("piece%d" % len(self.sticky["Const_coll"]), points)
        scope["solidFaces"] = lambda solid: (self.faces, None)
        self.faces = [south_face("wall", 0, 6), SolidBrep("floor", [(0, 0, 0), (0, 4, 0), (6, 4, 0), (6, 0, 0)])]
        self.solid = SimpleNamespace(UserDictionary=FakeUserDictionary(), Faces=SimpleNamespace(Count=6))

    def records(self, breps):
        return self.construction.callFromConstruction(breps)

    def test_faces_have_no_settings(self):
        breps, problem = self.construction.expandSolids([self.solid], "c1")
        self.assertIsNone(problem)
        self.assertEqual([(None, None)]*2, [(item.Boundarycond, item.Construction) for item in self.records(breps)])

    def test_solution_after_solution_keeps_the_numbers(self):
        first = [item.Surfnum for item in self.records(self.construction.expandSolids([self.solid], "c1")[0])]
        second = [item.Surfnum for item in self.records(self.construction.expandSolids([self.solid], "c1")[0])]
        self.assertEqual(first, second)

    def test_surface_with_settings_replaces_the_part_it_covers(self):
        known = self.construction.addToConstruction([south_face("part", 0, 2)], "c0")[0]
        self.sticky["Const_coll"][known.UserDictionary["LID"]].Construction = "OUT"
        breps, problem = self.construction.expandSolids([known, self.solid], "c1")
        self.assertIsNone(problem)
        records = self.records(breps)
        self.assertEqual(3, len(records))
        constructions_of = sorted(str(item.Construction) for item in records)
        self.assertEqual(["None", "None", "OUT"], constructions_of)
        spans = sorted(sorted(set(point.X for point in item.Vertices)) for item in records if all(point.Y == 0 for point in item.Vertices))
        self.assertEqual([[0.0, 2.0], [2.0, 6.0]], spans)

    def test_surface_beside_the_solid_is_a_problem(self):
        known = self.construction.addToConstruction([south_face("part", 4, 8)], "c0")[0]
        _, problem = self.construction.expandSolids([known, self.solid], "c1")
        self.assertIn("do not lie on a face", problem)

    def test_window_does_not_cut_a_face(self):
        window = self.construction.addToConstruction([south_face("window", 1, 2)], "c0")[0]
        self.sticky["Const_coll"][window.UserDictionary["LID"]].Type = "WINDOW"
        breps, problem = self.construction.expandSolids([window, self.solid], "c1")
        self.assertIsNone(problem)
        self.assertEqual(3, len(breps))


class FakeRhinoFace:
    def __init__(self, name, planar=True, loops=1):
        self.name, self.planar = name, planar
        self.Loops = SimpleNamespace(Count=loops)

    def IsPlanar(self, tolerance):
        return self.planar

    def DuplicateFace(self, shrink):
        return self.name


class FakeSolid:
    def __init__(self, faces, solid=True, orientation="Outward"):
        self.Faces = faces
        self.IsSolid = solid
        self.SolidOrientation = orientation
        self.flips = 0
        self.merged = False

    def DuplicateBrep(self):
        return self

    def MergeCoplanarFaces(self, tolerance):
        self.merged = True
        return True

    def Flip(self):
        self.flips += 1


class FakeFaceList(list):
    @property
    def Count(self):
        return len(self)


class SolidFacesTests(unittest.TestCase):
    def setUp(self):
        text = (REPO_ROOT / "Lizard_Component.py").read_text(encoding="utf-8-sig")
        first = text.index("def solidFaces(solid):")
        self.scope = {"abs_tolerance": 0.001, "rc": SimpleNamespace(Geometry=SimpleNamespace(BrepSolidOrientation=SimpleNamespace(Inward="Inward")))}
        exec(text[first:text.index("def flipSurfaceBreps(item):", first)], self.scope)

    def run_on(self, *faces, **options):
        self.solid = FakeSolid(FakeFaceList(faces), **options)
        return self.scope["solidFaces"](self.solid)

    def test_planar_faces(self):
        self.assertEqual((["a", "b"], None), self.run_on(FakeRhinoFace("a"), FakeRhinoFace("b")))
        self.assertTrue(self.solid.merged)
        self.assertEqual(0, self.solid.flips)

    def test_inward_solid_is_flipped(self):
        self.run_on(FakeRhinoFace("a"), orientation="Inward")
        self.assertEqual(1, self.solid.flips)

    def test_open_brep_curved_face_and_hole_are_problems(self):
        self.assertIn("not a closed solid", self.run_on(FakeRhinoFace("a"), solid=False)[1])
        self.assertIn("curved", self.run_on(FakeRhinoFace("a", planar=False))[1])
        self.assertIn("hole", self.run_on(FakeRhinoFace("a", loops=2))[1])


class FailureTests(unittest.TestCase):
    def failure(self):
        return M["ComponentFailure"]("Lizard_Construction_Set", "ExteriorWall: construction NOPE not found")

    def test_the_value_is_asked_and_not_its_class(self):
        self.assertTrue(M["isFailure"](self.failure()))
        self.assertTrue(M["isFailure"](SimpleNamespace(Failed=True)))
        for value in (None, "", "NOPE", 0, constructions(ExteriorWall="OUT"), [self.failure()]):
            self.assertFalse(M["isFailure"](value))

    def test_failed_set_of_the_model_stops_the_model_with_one_error(self):
        item = south(0, 5, construction=None)
        issues = M["compileModel"]([airnode("A1", item)], library(), constructionset=self.failure())
        self.assertEqual(1, len(errors(issues)))
        self.assertIn("Multizone", errors(issues)[0])
        self.assertIn("NOPE", errors(issues)[0])
        self.assertIsNone(item.Construction)

    def test_failed_set_of_an_airnode_does_not_fall_back_to_the_model(self):
        item = south(0, 5, construction=None)
        node = airnode("A1", item)
        node.Constructionset = self.failure()
        issues = M["compileModel"]([node], library(), constructionset=constructions(ExteriorWall="OUT"))
        self.assertEqual(1, len(errors(issues)))
        self.assertIn("Airnode A1", errors(issues)[0])

    def test_failure_also_stops_a_model_that_does_not_need_the_set(self):
        issues = M["compileModel"]([airnode("A1", south(0, 5))], library(), constructionset=self.failure())
        self.assertEqual(1, len(errors(issues)))

    def test_failure_survives_a_deep_copy(self):
        self.assertTrue(M["isFailure"](copy.deepcopy(self.failure())))


class FakeDocObject:
    """A component (with inputs) or a floating parameter (with sources)."""

    def __init__(self, name, messages=(), inputs=None, sources=None):
        self.NickName, self.InstanceGuid = name, name
        self.messages = list(messages)
        self.Attributes = SimpleNamespace(GetTopLevel=SimpleNamespace(DocObject=self))
        if inputs is not None:
            self.Params = SimpleNamespace(Input=[SimpleNamespace(Sources=list(group)) for group in inputs])
        else:
            self.Sources = list(sources or [])

    def RuntimeMessages(self, level):
        return self.messages if level == "ERROR" else []


class UpstreamTests(unittest.TestCase):
    def setUp(self):
        text = (REPO_ROOT / "Lizard_Component.py").read_text(encoding="utf-8-sig")
        first = text.index("def upstreamErrors(component, level):")
        scope = {}
        exec(text[first:text.index("def solidFaces(solid):", first)], scope)
        self.upstream = scope["upstreamErrors"]

    def test_nothing_red(self):
        source = FakeDocObject("Surface", inputs=[[]])
        self.assertEqual([], self.upstream(FakeDocObject("Airnode", inputs=[[source]]), "ERROR"))

    def test_error_of_the_direct_source(self):
        source = FakeDocObject("Surface", ["no such construction"], inputs=[[]])
        self.assertEqual(["Surface: no such construction"], self.upstream(FakeDocObject("Airnode", inputs=[[source]]), "ERROR"))

    def test_error_behind_a_merge_and_a_floating_parameter(self):
        red = FakeDocObject("Surface", ["bad"], inputs=[[]])
        merge = FakeDocObject("Merge", inputs=[[red], [FakeDocObject("Other", inputs=[[]])]])
        floating = FakeDocObject("Brep", sources=[merge])
        self.assertEqual(["Surface: bad"], self.upstream(FakeDocObject("Airnode", inputs=[[floating]]), "ERROR"))

    def test_own_errors_do_not_count(self):
        self.assertEqual([], self.upstream(FakeDocObject("Airnode", ["own"], inputs=[[]]), "ERROR"))

    def test_shared_source_is_reported_once(self):
        red = FakeDocObject("Schedule", ["bad"], inputs=[[]])
        a, b = FakeDocObject("A", inputs=[[red]]), FakeDocObject("B", inputs=[[red]])
        self.assertEqual(1, len(self.upstream(FakeDocObject("Airnode", inputs=[[a, b]]), "ERROR")))

    def test_a_loop_of_references_ends(self):
        a = FakeDocObject("A", inputs=[[]])
        b = FakeDocObject("B", inputs=[[a]])
        a.Params.Input[0].Sources.append(b)
        self.assertEqual([], self.upstream(FakeDocObject("Airnode", inputs=[[a]]), "ERROR"))


def run_set_component(known=("OUT",), **slots):
    source = (REPO_ROOT / "Lizard_Construction_Set.py").read_text(encoding="utf-8-sig")
    messages = []
    scriptcontext = ModuleType("scriptcontext")
    scriptcontext.doc = SimpleNamespace(Path="doc")
    scriptcontext.sticky = {"doc": {"library": SimpleNamespace(Walls=[SimpleNamespace(Name=name) for name in known]), "ComponentFailure": M["ComponentFailure"]}}
    grasshopper = ModuleType("Grasshopper")
    kernel = ModuleType("Grasshopper.Kernel")
    kernel.GH_RuntimeMessageLevel = SimpleNamespace(Error="ERROR")
    grasshopper.Kernel = kernel
    component = SimpleNamespace(AddRuntimeMessage=lambda level, text: messages.append(text), Name="", NickName="", Message="", Category="", SubCategory="")
    namespace = {"ghenv": SimpleNamespace(Component=component)}
    namespace.update(dict((slot, slots.get(slot)) for slot in M["CONSTRUCTION_SLOTS"]))
    with mock.patch.dict(sys.modules, {"scriptcontext": scriptcontext, "Grasshopper": grasshopper, "Grasshopper.Kernel": kernel}):
        exec(compile(source, "Lizard_Construction_Set.py", "exec"), namespace)
    return namespace["Set"], messages


class SetComponentTests(unittest.TestCase):
    def test_valid_names_give_a_set(self):
        result, messages = run_set_component(ExteriorWall="OUT")
        self.assertEqual([], messages)
        self.assertFalse(M["isFailure"](result))
        self.assertEqual("OUT", result.ExteriorWall)

    def test_unknown_name_gives_a_failure_and_no_set_at_all(self):
        result, messages = run_set_component(ExteriorWall="OUT", Roof="NOPE")
        self.assertEqual(1, len(messages))
        self.assertTrue(M["isFailure"](result))
        self.assertIn("NOPE", result.Message)
        self.assertIsNone(getattr(result, "ExteriorWall", None))


class ComponentTests(unittest.TestCase):
    def test_the_next_components_react_to_errors(self):
        for name in ("Lizard_Thermal_Airnode.py", "Lizard_Multizone.py"):
            text = (REPO_ROOT / name).read_text(encoding="utf-8-sig")
            self.assertIn('["upstreamErrors"](ghenv.Component, err)', text)
            self.assertIn('["isFailure"](ConstructionSet)', text)

    def test_system_stops_on_upstream_errors_before_it_writes(self):
        text = (REPO_ROOT / "Lizard_System.py").read_text(encoding="utf-8-sig")
        self.assertRegex(text, r"if WriteSimulationFiles:\s+upstreamerrors = [^\n]*upstreamErrors[\s\S]{0,300}sys\.exit\(\)\s+for rui,runitem")

    def test_component_has_all_the_slots_and_their_docs(self):
        text = (REPO_ROOT / "Lizard_Construction_Set.py").read_text(encoding="utf-8-sig")
        self.assertIn('ghenv.Component.Name = "Lizard_Construction_Set"', text)
        for slot in M["CONSTRUCTION_SLOTS"]:
            self.assertIn("    {0} (str):".format(slot), text)
            self.assertIn("self.{0} = {0}".format(slot), text)

    def test_genmatrices_survives_an_empty_construction(self):
        text = (REPO_ROOT / "Lizard_GenMatrices.py").read_text(encoding="utf-8-sig")
        self.assertIn('"Virtual" in (item.Construction or \'\')', text)

    def test_inputs_are_registered(self):
        airnode_text = (REPO_ROOT / "Lizard_Thermal_Airnode.py").read_text(encoding="utf-8-sig")
        multizone_text = (REPO_ROOT / "Lizard_Multizone.py").read_text(encoding="utf-8-sig")
        self.assertIn('"ConstructionSet",', airnode_text)
        self.assertIn("ConstructionSet (object):", airnode_text)
        self.assertIn("ConstructionSet (object):", multizone_text)
        self.assertIn("self.constructionset = ConstructionSet", multizone_text)


if __name__ == "__main__":
    unittest.main()
