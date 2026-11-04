"""compileModel of Lizard_Component.py: adjacency with splitting, boundary conditions, the final check, and the settings of
a surface that are written in several steps.

The real blocks run with fake Rhino objects: only makeSurfaceVertices, makeSurfaceBrep, flipSurfaceBreps and the Brep class are stand-ins.
"""

import copy
import math
import re
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "components" / "Lizard_Component.py"


class Vec:
    def __init__(self, x, y, z):
        self.X, self.Y, self.Z = float(x), float(y), float(z)

    def __mul__(self, factor):
        return Vec(self.X*factor, self.Y*factor, self.Z*factor)

    def __getitem__(self, index):
        return (self.X, self.Y, self.Z)[index]

    def __eq__(self, other):
        return (self.X, self.Y, self.Z) == (other.X, other.Y, other.Z)

    def __hash__(self):
        return hash((self.X, self.Y, self.Z))

    def __repr__(self):
        return "Vec(%g, %g, %g)" % (self.X, self.Y, self.Z)


class FakeBrep:
    def __init__(self, points):
        self.points = points
        self.flips = 0

    def Flip(self):
        self.flips += 1


def between(text, start, end):
    first = text.index(start)
    return text[first:text.index(end, first)]


def load():
    text = SOURCE.read_text(encoding="utf-8-sig")
    namespace = {"math": math, "copy": copy, "re": re}
    blocks = [
        between(text, "# ---- Surface kernel (begin)", "# ---- Surface kernel (end)"),
        between(text, "# ---- Surface model (begin)", "# ---- Surface model (end)"),
        between(text, "class AIRNODE:", "class POLLUTANTS:"),
        between(text, "class GEOMETRY:", "class AIRNODE:"),
        between(text, "def getSurfaceType(breps):", "@timing\ndef getWinOrientation"),
        between(text, "def defineGeosurf(floorgeo,surfacecoll):", "#this function runs through").split("@timing")[0],
    ]
    # IronPython 2 print statements of defineGeosurf
    blocks = [re.sub(r"^(\s*)print (.*)$", r"\1print(\2)", block, flags=re.M) for block in blocks]
    exec(compile("\n".join(blocks), str(SOURCE), "exec"), namespace)
    namespace["makeSurfaceVertices"] = lambda points: [Vec(*point) for point in points]
    namespace["makeSurfaceBrep"] = lambda points, normal: FakeBrep(points)

    def flip_breps(item):
        item.Faces.Flip()
        if item.Surface is not item.Faces:
            item.Surface.Flip()
    namespace["flipSurfaceBreps"] = flip_breps
    return namespace


M = load()
ORIENTATIONS = {(0, 0, 1): "H_0_0", (0, 0, -1): "H_0_180", (0, -1, 0): "S_0_90", (0, 1, 0): "N_180_90", (1, 0, 0): "E_270_90", (-1, 0, 0): "W_90_90"}


class Counter:
    number = 0


def surface(points, category=None, construction="WALL", frontback=None, number=None, kind=None, temperature=0):
    """A GEOMETRY as Lizard_Thermal_Airnode leaves it; the points are counter-clockwise seen from outside."""
    Counter.number += 1
    item = M["GEOMETRY"]()
    item.Surfnum = number if number is not None else Counter.number
    item.Vertices = [Vec(*point) for point in points]
    area = M["polyAreaVector"]([tuple(map(float, point)) for point in points])
    length = M["vecDot"](area, area)**0.5
    normal = M["vecUnit"](area)
    item.Normalvector = Vec(*normal)
    item.Area = length
    item.Boundarycond = category
    item.Construction = construction
    item.Frontback = frontback
    item.Boundarytemp = temperature
    item.Orientation = ORIENTATIONS.get(tuple(int(round(c)) for c in normal), "S_0_90")
    item.Surface = item.Faces = FakeBrep(points)
    item.Type = kind or {"H_0_0": "ROOF" if category == "EXTERNAL" else "CEILING", "H_0_180": "FLOOR"}.get(item.Orientation, "WALL")
    return item


def south(x0, x1, y=0.0, **options):
    """Wall with its normal towards -y."""
    return surface([(x0, y, 0), (x1, y, 0), (x1, y, 3), (x0, y, 3)], **options)


def north(x0, x1, y=0.0, **options):
    """Wall with its normal towards +y."""
    return surface([(x1, y, 0), (x0, y, 0), (x0, y, 3), (x1, y, 3)], **options)


def window_in(host, x0, x1, z0=1.0, z1=2.0):
    y = host.Vertices[0].Y
    points = [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
    if host.Normalvector.Y > 0:
        points.reverse()
    window = surface(points, kind="WINDOW", construction="WIN")
    host.Subsurface.append(window.Surface)
    host.Subsurfacedef.append(window)
    host.Area = host.Area-window.Area
    return window


def airnode(name, *surfaces, windows=()):
    node = M["AIRNODE"](name)
    node.Surfaces = list(windows)+list(surfaces)
    return node


def library(**extra):
    walls = {"WALL": ("A B A", "0.1 0.2 0.1"), "OUT": ("P Q R", "0.1 0.2 0.3"), "IFL": ("WOOD CONC GYP", "0.01 0.2 0.01"), "ICL": ("GYP CONC WOOD", "0.01 0.2 0.01")}
    walls.update({"TABS": ("A AL A", "0.1 0.2 0.1"), "TABSFL": ("WOOD CC GYP", "0.01 0.2 0.01"), "TABSCL": ("GYP CC WOOD", "0.01 0.2 0.01")})
    walls.update(extra)
    return SimpleNamespace(Walls=[SimpleNamespace(Name=name, Layers=layers, Thickness=thickness, Uvalue=1.5, Abs_front=0.6, Abs_back=0.5) for name, (layers, thickness) in walls.items()], Layers=[SimpleNamespace(Name="AL", Pdiameter="0.02"), SimpleNamespace(Name="CC", Pdiameter="", Cc_pidiameter="0.003"), SimpleNamespace(Name="A", Pdiameter="")])


def active(item, circuit=1):
    """What Lizard_Active_Layer_Surface leaves on the first surface of a circuit."""
    item.Activelayer, item.Intemp = circuit, "INPUT 1*TSUP_AL{0}".format(circuit)
    return item


def compile_model(*airnodes, **options):
    return M["compileModel"](list(airnodes), library(), **options)


def errors(issues):
    return [issue["message"] for issue in issues if issue["level"] == "error"]


def warnings_of(issues):
    return [issue["message"] for issue in issues if issue["level"] == "warning"]


def walls_of(node):
    return [item for item in node.Surfaces if not M["isWindowSurface"](item)]


class AdjacencyTests(unittest.TestCase):
    def test_matching_walls_stay_as_they_are(self):
        a = south(0, 5, category="ADJACENT", frontback="FRONT")
        b = north(0, 5, category="ADJACENT", frontback="BACK")
        vertices = list(a.Vertices)
        issues = compile_model(airnode("A1", a), airnode("A2", b))
        self.assertEqual([], issues)
        self.assertEqual(vertices, a.Vertices)
        self.assertIsNone(a.Sourcesurf)
        self.assertEqual((b.Surfnum, "A2", "ADJACENT", "FRONT"), (a.Adjsurf, a.Adjairnode, a.Boundarycond, a.Frontback))
        self.assertEqual((a.Surfnum, "A1", "ADJACENT", "BACK"), (b.Adjsurf, b.Adjairnode, b.Boundarycond, b.Frontback))
        self.assertEqual(a.Orientation, b.Orientation)

    def test_one_wall_against_two_is_split(self):
        a = south(0, 6, category="ADJACENT", number=10)
        b, c = north(0, 2, category="ADJACENT", number=11), north(2, 6, category="ADJACENT", number=12)
        na, nb = airnode("A1", a), airnode("A2", b, c)
        issues = compile_model(na, nb)
        self.assertEqual([], issues)
        pieces = walls_of(na)
        self.assertEqual([12.0, 6.0], [round(piece.Area, 6) for piece in pieces])
        self.assertEqual(10, pieces[0].Surfnum)  # the biggest piece keeps the number
        self.assertEqual(13, pieces[1].Surfnum)
        self.assertEqual([10, 10], [piece.Sourcesurf for piece in pieces])
        self.assertEqual((12, 11), (pieces[0].Adjsurf, pieces[1].Adjsurf))
        self.assertEqual((10, 13), (c.Adjsurf, b.Adjsurf))
        self.assertEqual(["A2", "A2"], [piece.Adjairnode for piece in pieces])
        self.assertEqual(sorted(("BACK", "FRONT")), sorted((pieces[0].Frontback, c.Frontback)))
        for piece in pieces:
            self.assertEqual(-1.0, piece.Normalvector.Y)
            area = M["polyAreaVector"](M["surfacePoints"](piece))
            self.assertLess(area[1], 0)  # same winding as the wall it came from
            self.assertIsInstance(piece.Faces, FakeBrep)

    def test_many_to_many(self):
        a, b = south(0, 3, category="AUTOMATIC"), south(3, 6, category="AUTOMATIC")
        c, d = north(0, 4, category="AUTOMATIC"), north(4, 6, category="AUTOMATIC")
        n1, n2 = airnode("A1", a, b), airnode("A2", c, d)
        self.assertEqual([], compile_model(n1, n2))
        for node in (n1, n2):
            self.assertEqual(18.0, round(sum(item.Area for item in walls_of(node)), 6))
            self.assertEqual(3, len(walls_of(node)))
        by_number = {item.Surfnum: item for node in (n1, n2) for item in walls_of(node)}
        for item in by_number.values():
            self.assertEqual("ADJACENT", item.Boundarycond)
            self.assertEqual(item.Surfnum, by_number[item.Adjsurf].Adjsurf)
            self.assertAlmostEqual(item.Area, by_number[item.Adjsurf].Area)

    def test_the_part_nobody_faces_gets_its_own_condition(self):
        a = south(0, 6, category="AUTOMATIC", number=20)
        b = north(1, 3, category="AUTOMATIC", number=21)
        n1, n2 = airnode("A1", a), airnode("A2", b)
        self.assertEqual([], compile_model(n1, n2))
        categories = sorted((item.Boundarycond, round(item.Area, 6)) for item in walls_of(n1))
        self.assertEqual("ADJACENT", b.Boundarycond)
        self.assertEqual(6.0, round(sum(area for category, area in categories if category == "ADJACENT"), 6))
        self.assertEqual(12.0, round(sum(area for category, area in categories if category == "EXTERNAL"), 6))
        self.assertEqual(2, len([category for category, area in categories if category == "EXTERNAL"]))

    def test_small_wall_inside_a_big_one_makes_simple_surfaces(self):
        a = south(0, 10, category="AUTOMATIC")
        a.Vertices = [Vec(0, 0, 0), Vec(10, 0, 0), Vec(10, 0, 4), Vec(0, 0, 4)]
        a.Area = 40.0
        b = surface([(6, 0, 1), (4, 0, 1), (4, 0, 3), (6, 0, 3)], category="AUTOMATIC")
        n1, n2 = airnode("A1", a), airnode("A2", b)
        self.assertEqual([], compile_model(n1, n2))
        self.assertEqual(3, len(walls_of(n1)))
        self.assertEqual(40.0, round(sum(item.Area for item in walls_of(n1)), 6))
        for item in walls_of(n1):
            points = M["surfacePoints"](item)
            self.assertEqual(len(points), len(set(points)))

    def test_surfaces_of_one_room_are_not_coupled(self):
        a, b = south(0, 5, category="AUTOMATIC"), north(0, 5, category="AUTOMATIC")
        issues = compile_model(airnode("A1", a, b))
        self.assertEqual("EXTERNAL", a.Boundarycond)
        self.assertEqual("EXTERNAL", b.Boundarycond)
        self.assertIn("are not coupled", warnings_of(issues)[0])

    def test_overlap_on_one_side_is_an_error(self):
        a, b = south(0, 5, category="AUTOMATIC"), south(0, 5, category="AUTOMATIC")
        self.assertIn("overlap", errors(compile_model(airnode("A1", a), airnode("A2", b)))[0])

    def test_numbers_do_not_depend_on_the_order_of_the_airnodes(self):
        def build():
            return airnode("A1", south(0, 6, category="ADJACENT", number=10)), airnode("A2", north(0, 2, category="ADJACENT", number=11), north(2, 6, category="ADJACENT", number=12))
        n1, n2 = build()
        compile_model(n1, n2)
        n3, n4 = build()
        compile_model(n4, n3)
        self.assertEqual([item.Surfnum for item in walls_of(n1)], [item.Surfnum for item in walls_of(n3)])


class GapToleranceTests(unittest.TestCase):
    def test_near_miss_is_reported(self):
        a, b = south(0, 5, category="AUTOMATIC"), north(0, 5, y=-0.2, category="AUTOMATIC")
        issues = compile_model(airnode("A1", a), airnode("A2", b))
        self.assertEqual("EXTERNAL", a.Boundarycond)
        self.assertIn("raise GapTolerance", " ".join(warnings_of(issues)))

    def test_raising_the_tolerance_pairs_them(self):
        a, b = south(0, 5, category="AUTOMATIC"), north(0, 5, y=-0.2, category="AUTOMATIC")
        self.assertEqual([], compile_model(airnode("A1", a), airnode("A2", b), gaptolerance=0.3))
        self.assertEqual(("ADJACENT", b.Surfnum), (a.Boundarycond, a.Adjsurf))
        self.assertEqual(-0.2, b.Vertices[0].Y)  # each side stays in its own plane

    def test_a_shift_narrower_than_the_gap_does_not_split(self):
        a, b = south(0, 5, category="AUTOMATIC"), north(0.1, 5.1, y=-0.2, category="AUTOMATIC")
        n1, n2 = airnode("A1", a), airnode("A2", b)
        self.assertEqual([], compile_model(n1, n2, gaptolerance=0.3))
        self.assertEqual(([a], [b]), (walls_of(n1), walls_of(n2)))
        self.assertEqual("ADJACENT", a.Boundarycond)


class BoundaryConditionTests(unittest.TestCase):
    def test_automatic_roof_is_a_roof(self):
        roof = surface([(0, 0, 3), (5, 0, 3), (5, 4, 3), (0, 4, 3)], category="AUTOMATIC")
        self.assertEqual([], compile_model(airnode("A1", roof)))
        self.assertEqual(("EXTERNAL", "ROOF"), (roof.Boundarycond, roof.Type))

    def test_unset_wall_is_external(self):
        wall = south(0, 5)
        self.assertEqual([], compile_model(airnode("A1", wall)))
        self.assertEqual("EXTERNAL", wall.Boundarycond)

    def test_unset_floor_without_a_room_below_gets_the_fallback(self):
        floor = surface([(0, 0, 0), (0, 4, 0), (5, 4, 0), (5, 0, 0)])
        self.assertIn("no boundary condition", warnings_of(compile_model(airnode("A1", floor)))[0])
        self.assertEqual("INPUT 1*Tsoil", floor.Boundarytemp)

    def test_unset_floor_above_a_room_is_adjacent(self):
        floor = surface([(0, 0, 3), (0, 4, 3), (5, 4, 3), (5, 0, 3)], construction="IFL")
        ceiling = surface([(0, 0, 3), (5, 0, 3), (5, 4, 3), (0, 4, 3)], construction="ICL")
        self.assertEqual([], compile_model(airnode("A1", floor), airnode("A2", ceiling)))
        self.assertEqual(("ADJACENT", "FRONT", "IFL"), (floor.Boundarycond, floor.Frontback, floor.Construction))
        self.assertEqual(("ADJACENT", "BACK", "ICL"), (ceiling.Boundarycond, ceiling.Frontback, ceiling.Construction))

    def test_adjacent_without_a_partner_is_an_error(self):
        wall = south(0, 5, category="ADJACENT")
        self.assertIn("No adjacent surface", errors(compile_model(airnode("A1", wall)))[0])

    def test_adjacent_of_an_airnode_run_alone_mirrors_the_room(self):
        wall = south(0, 5, category="ADJACENT")
        self.assertEqual([], compile_model(airnode("A1", wall), standalone=True))
        self.assertEqual(("BOUNDARY", "INPUT 1*TAIR_A1"), (wall.Boundarycond, wall.Boundarytemp))

    def test_autobound_pairs_mirror_the_neighbour(self):
        a, b = south(0, 6, category="AUTOBOUND", number=30), north(0, 2, category="AUTOBOUND", number=31)
        n1 = airnode("A1", a)
        compile_model(n1, airnode("A2", b))
        self.assertEqual(("BOUNDARY", "INPUT 1*TAIR_A1", "A1"), (b.Boundarycond, b.Boundarytemp, b.Bndairnode))
        temperatures = sorted(item.Boundarytemp for item in walls_of(n1))
        self.assertEqual(["INPUT 1*TAIR_A1", "INPUT 1*TAIR_A2"], temperatures)


class AutoAdjacencyTests(unittest.TestCase):
    def test_plain_categories_stay_without_the_switch(self):
        a, b = south(0, 5, category="EXTERNAL"), north(0, 5, category="EXTERNAL")
        self.assertEqual([], compile_model(airnode("A1", a), airnode("A2", b)))
        self.assertEqual(("EXTERNAL", "EXTERNAL"), (a.Boundarycond, b.Boundarycond))

    def test_the_switch_makes_them_adjacent_and_keeps_the_rest(self):
        a = south(0, 6, category="EXTERNAL", number=40)
        b = north(0, 2, category="BOUNDARY", number=41, temperature="INPUT 1*TAIR_@ANAME")
        n1 = airnode("A1", a)
        issues = compile_model(n1, airnode("A2", b), autoadjacency=True)
        self.assertEqual([], errors(issues))
        self.assertEqual(1, len(warnings_of(issues)))  # one for all surfaces of a construction
        self.assertIn("check that it suits an inner wall", warnings_of(issues)[0])
        self.assertEqual([41, 42], sorted(item.Surfnum for item in issues[0]["surfaces"]))  # 42 = the part of surface 40 that faces 41
        self.assertEqual("ADJACENT", b.Boundarycond)
        self.assertEqual({"ADJACENT": 6.0, "EXTERNAL": 12.0}, {item.Boundarycond: round(item.Area, 6) for item in walls_of(n1)})

    def test_external_ceiling_that_faces_a_room_is_a_ceiling(self):
        roof = surface([(0, 0, 3), (5, 0, 3), (5, 4, 3), (0, 4, 3)], category="EXTERNAL", construction="ICL")
        floor = surface([(0, 0, 3), (0, 4, 3), (5, 4, 3), (5, 0, 3)], category="BOUNDARY", construction="IFL")
        self.assertEqual("ROOF", roof.Type)
        self.assertEqual([], errors(compile_model(airnode("A1", roof), airnode("A2", floor), autoadjacency=True)))
        self.assertEqual(("ADJACENT", "CEILING"), (roof.Boundarycond, roof.Type))

    def test_explicit_boundaries_are_kept(self):
        a = south(0, 5, category="AUTOMATIC")
        locked = [north(0, 5, category="BOUNDARY", temperature="INPUT 1*T_NEIGHBOUR"), north(0, 5, category="EXTCALEXT"), north(0, 5, category="EXTFICALC")]
        for other in locked:
            with self.subTest(other.Boundarycond):
                wall = south(0, 5, category="AUTOMATIC")
                issues = compile_model(airnode("A1", wall), airnode("A2", other), autoadjacency=True)
                self.assertEqual(("EXTERNAL", 0), (wall.Boundarycond, other.Adjsurf))
                self.assertIn("keeps its own", " ".join(warnings_of(issues)))

    def test_virtual_surfaces_are_left_alone(self):
        a = south(0, 5, category="VIRTUAL", construction="Virtual")
        b = north(0, 5, category="VIRTUAL", construction="Virtual")
        self.assertEqual([], compile_model(airnode("A1", a), airnode("A2", b), autoadjacency=True))
        self.assertEqual(("VIRTUAL", 0), (a.Boundarycond, a.Adjsurf))


class ConstructionTests(unittest.TestCase):
    def test_an_empty_side_follows_the_other(self):
        a, b = south(0, 5, category="AUTOMATIC", construction=None), north(0, 5, category="AUTOMATIC", construction="OUT")
        self.assertEqual([], compile_model(airnode("A1", a), airnode("A2", b)))
        self.assertEqual("OUT", a.Construction)

    def test_different_constructions_are_an_error(self):
        a, b = south(0, 5, category="AUTOMATIC"), north(0, 5, category="AUTOMATIC", construction="OUT")
        self.assertIn("different constructions", errors(compile_model(airnode("A1", a), airnode("A2", b)))[0])

    def test_no_construction_is_an_error(self):
        wall = south(0, 5, construction=None)
        self.assertIn("has no construction", errors(compile_model(airnode("A1", wall)))[0])

    def test_unknown_construction_is_an_error(self):
        wall = south(0, 5, construction="NOPE")
        self.assertIn("not in the library", errors(compile_model(airnode("A1", wall)))[0])

    def test_all_errors_are_listed_together(self):
        issues = compile_model(airnode("A1", south(0, 5, construction=None), north(0, 5, y=9, construction="NOPE"), south(0, 5, y=-9, category="ADJACENT")))
        self.assertEqual(3, len(errors(issues)))

    def test_library_values_come_from_the_final_construction(self):
        wall = south(0, 5, construction="OUT")
        compile_model(airnode("A1", wall))
        self.assertEqual((1.5, 0.6, 0.5), (wall.Uvalue, wall.Abs_front, wall.Abs_back))
        self.assertAlmostEqual(0.6, wall.Wallthickness)


class FrontBackTests(unittest.TestCase):
    def test_same_side_on_symmetric_walls_is_silent(self):
        a, b = south(0, 5, category="ADJACENT", frontback="FRONT"), north(0, 5, category="ADJACENT", frontback="FRONT")
        self.assertEqual([], compile_model(airnode("A2", a), airnode("A1", b)))
        self.assertEqual(("BACK", "FRONT"), (a.Frontback, b.Frontback))

    def test_same_side_on_non_symmetric_walls_is_a_warning(self):
        a, b = south(0, 5, category="ADJACENT", frontback="FRONT", construction="OUT"), north(0, 5, category="ADJACENT", frontback="FRONT", construction="OUT")
        issues = compile_model(airnode("A1", a), airnode("A2", b))
        self.assertEqual([], errors(issues))
        self.assertIn("non-symmetric", warnings_of(issues)[0])

    def test_one_given_side_decides(self):
        a, b = south(0, 5, category="ADJACENT", frontback="BACK"), north(0, 5, category="ADJACENT")
        compile_model(airnode("A1", a), airnode("A2", b))
        self.assertEqual(("BACK", "FRONT"), (a.Frontback, b.Frontback))

    def test_surfaces_without_a_pair_become_front(self):
        wall = south(0, 5)
        compile_model(airnode("A1", wall))
        self.assertEqual("FRONT", wall.Frontback)

    def test_active_layer_goes_from_front_to_back(self):
        a, b = active(south(0, 5, category="ADJACENT", frontback="FRONT", construction="TABS")), north(0, 5, category="ADJACENT", frontback="BACK", construction=None)
        self.assertEqual([], errors(compile_model(airnode("A1", a), airnode("A2", b))))
        self.assertEqual((1, "INPUT 1*TSUP_AL1"), (b.Activelayer, b.Intemp))

    def test_second_circuit_goes_from_front_to_back(self):
        a, b = active(south(0, 5, category="ADJACENT", frontback="FRONT", construction="TABS"), 2), north(0, 5, category="ADJACENT", frontback="BACK", construction=None)
        self.assertEqual([], errors(compile_model(airnode("A1", a), airnode("A2", b))))
        self.assertEqual((2, "INPUT 1*TSUP_AL2"), (b.Activelayer, b.Intemp))

    def test_active_side_is_front_when_the_airnode_sorts_last(self):
        a, b = active(south(0, 5, category="ADJACENT", construction="TABS")), north(0, 5, category="ADJACENT", construction="TABS")
        self.assertEqual([], compile_model(airnode("A2", a), airnode("A1", b)))
        self.assertEqual(("FRONT", "BACK"), (a.Frontback, b.Frontback))
        self.assertEqual((1, 1), (a.Activelayer, b.Activelayer))

    def test_active_ceiling_is_front_of_a_floor_with_a_construction(self):
        ceiling = active(surface([(0, 0, 3), (6, 0, 3), (6, 4, 3), (0, 4, 3)], construction="TABSCL"))
        floor = surface([(0, 0, 3), (0, 4, 3), (6, 4, 3), (6, 0, 3)], construction="TABSFL")
        self.assertEqual([], compile_model(airnode("A1", floor), airnode("A2", ceiling)))
        self.assertEqual(("FRONT", "BACK"), (ceiling.Frontback, floor.Frontback))
        self.assertEqual(1, floor.Activelayer)

    def test_explicit_back_on_the_active_side_is_an_error(self):
        a, b = active(south(0, 5, category="ADJACENT", frontback="BACK", construction="TABS")), north(0, 5, category="ADJACENT", construction=None)
        self.assertIn("is the BACK of the pair", errors(compile_model(airnode("A1", a), airnode("A2", b)))[0])

    def test_both_sides_active_keep_working(self):
        a, b = active(south(0, 5, category="ADJACENT", frontback="FRONT", construction="TABS")), active(north(0, 5, category="ADJACENT", frontback="BACK", construction="TABS"))
        self.assertEqual([], errors(compile_model(airnode("A1", a), airnode("A2", b))))

    def test_split_active_surface_becomes_a_serial_circuit(self):
        a = active(south(0, 6, category="ADJACENT", number=80, construction="TABS"))
        b, c = north(0, 2, category="ADJACENT", number=81, construction=None), north(2, 6, category="ADJACENT", number=82, construction=None)
        n1, n2 = airnode("A1", a), airnode("A2", b, c)
        issues = compile_model(n1, n2)
        self.assertEqual([], errors(issues))
        self.assertIn("serial circuit", warnings_of(issues)[0])
        self.assertEqual([(80, "INPUT 1*TSUP_AL1"), (83, "INPUT 1*TOFL_S80")], [(item.Surfnum, item.Intemp) for item in n1.Surfaces])
        self.assertEqual({82: "INPUT 1*TSUP_AL1", 81: "INPUT 1*TOFL_S80"}, dict([(item.Surfnum, item.Intemp) for item in n2.Surfaces]))

    def test_split_without_an_active_layer_keeps_its_intemp(self):
        a = south(0, 6, category="ADJACENT", number=84)
        b, c = north(0, 2, category="ADJACENT", number=85), north(2, 6, category="ADJACENT", number=86)
        n1 = airnode("A1", a)
        self.assertEqual([], errors(compile_model(n1, airnode("A2", b, c))))
        self.assertEqual(["INPUT 1*Tinal1"]*2, [item.Intemp for item in n1.Surfaces])


class WindowTests(unittest.TestCase):
    def test_window_moves_to_the_piece_that_holds_it(self):
        a = south(0, 6, category="AUTOMATIC", number=50)
        window = window_in(a, 0.5, 1.5)
        b, c = north(0, 2, category="AUTOMATIC", number=51), north(2, 6, category="EXTERNAL", number=52)
        n1 = airnode("A1", a, windows=[window])
        issues = compile_model(n1, airnode("A2", b, c), autoadjacency=True)
        self.assertIn("has no window at the same place", " ".join(errors(issues)))
        hosts = [item for item in walls_of(n1) if item.Subsurfacedef]
        self.assertEqual(1, len(hosts))
        self.assertEqual([window.Surface], hosts[0].Subsurface)
        self.assertEqual(5.0, round(hosts[0].Area, 6))  # 2 x 3 m without the window of 1 m2

    def test_window_on_the_cut_is_an_error(self):
        a = south(0, 6, category="AUTOMATIC")
        window = window_in(a, 1.5, 2.5)
        b, c = north(0, 2, category="AUTOMATIC"), north(2, 6, category="AUTOMATIC")
        issues = compile_model(airnode("A1", a, windows=[window]), airnode("A2", b, c))
        self.assertIn("crosses the line", errors(issues)[0])

    def test_window_of_a_part_with_nobody_behind_stays_external(self):
        a = south(0, 6, category="AUTOMATIC", number=60)
        window = window_in(a, 3.0, 4.0)
        b = north(0, 2, category="AUTOMATIC", number=61)
        n1 = airnode("A1", a, windows=[window])
        self.assertEqual([], compile_model(n1, airnode("A2", b)))
        self.assertEqual("EXTERNAL", window.Boundarycond)

    def test_interior_windows_are_paired(self):
        a, b = south(0, 5, category="ADJACENT"), north(0, 5, category="ADJACENT", frontback="BACK")
        w1, w2 = window_in(a, 1, 2), window_in(b, 1, 2)
        w1.Orientation = "S_0_90"
        issues = compile_model(airnode("A1", a, windows=[w1]), airnode("A2", b, windows=[w2]))
        self.assertEqual([], issues)
        self.assertEqual((w2.Surfnum, "A2", "ADJACENT"), (w1.Adjsurf, w1.Adjairnode, w1.Boundarycond))
        self.assertEqual((w1.Surfnum, "A1", "BACK"), (w2.Adjsurf, w2.Adjairnode, w2.Frontback))
        self.assertEqual("S_0_90", w2.Orientation)

    def test_interior_window_without_a_partner_is_an_error(self):
        a, b = south(0, 5, category="ADJACENT"), north(0, 5, category="ADJACENT")
        w1 = window_in(a, 1, 2)
        self.assertIn("has no window", errors(compile_model(airnode("A1", a, windows=[w1]), airnode("A2", b)))[0])


class FollowersOfASplitTests(unittest.TestCase):
    def test_surface_output_covers_the_pieces(self):
        a = south(0, 6, category="ADJACENT", number=70)
        b, c = north(0, 2, category="ADJACENT", number=71), north(2, 6, category="ADJACENT", number=72)
        output = SimpleNamespace(Type="SURFACE", SurfaceID=[70], Ntype=["TSI"], NtypesShort=["TSI_S70"], NtypesNo=[1])
        n1 = airnode("A1", a)
        n1.Output = [output]
        compile_model(n1, airnode("A2", b, c))
        self.assertEqual([70, 73], output.SurfaceID)
        self.assertEqual(["TSI_S70", "TSI_S73"], output.NtypesShort)

    def test_serial_active_layer_is_not_split(self):
        a = south(0, 6, category="ADJACENT", number=80)
        b, c = north(0, 2, category="ADJACENT", number=81), north(2, 6, category="ADJACENT", number=82)
        c.Intemp = "INPUT 1*TOFL_S80"
        self.assertIn("serial active layer", errors(compile_model(airnode("A1", a), airnode("A2", b, c)))[0])

    def test_geosurf_is_computed_per_piece_and_before_the_orientation_is_shared(self):
        floor = surface([(0, 0, 3), (0, 4, 3), (6, 4, 3), (6, 0, 3)], number=90, construction="IFL")
        wall = south(0, 6, y=0.0, number=91, category="EXTERNAL")
        first, second = surface([(0, 0, 3), (2, 0, 3), (2, 4, 3), (0, 4, 3)], number=92, construction="ICL"), surface([(2, 0, 3), (6, 0, 3), (6, 4, 3), (2, 4, 3)], number=93, construction="ICL")
        upper, lower = airnode("A1", floor, wall), airnode("A2", first, second)
        upper.Geosurffloor = lower.Geosurffloor = 0.6
        lowerfloor = surface([(0, 0, 0), (0, 4, 0), (6, 4, 0), (6, 0, 0)], number=94, category="BOUNDARY", construction="WALL")
        lower.Surfaces.append(lowerfloor)
        self.assertEqual([], compile_model(upper, lower))
        pieces = [item for item in upper.Surfaces if item.Sourcesurf == 90]
        self.assertEqual(2, len(pieces))
        self.assertEqual(0.6, round(sum(piece.Geosurf for piece in pieces), 3))
        self.assertEqual("H_0_180", first.Orientation)  # the ceiling takes the orientation of its front side

    def test_a_back_floor_counts_as_a_floor_for_geosurf(self):
        floor = surface([(0, 0, 3), (0, 4, 3), (6, 4, 3), (6, 0, 3)], number=95, construction="IFL", frontback="BACK")
        wall = south(0, 6, y=0.0, number=96, category="EXTERNAL")
        ceiling = surface([(0, 0, 3), (6, 0, 3), (6, 4, 3), (0, 4, 3)], number=97, construction="ICL")
        upper = airnode("A1", floor, wall)
        upper.Geosurffloor = 0.6
        self.assertEqual([], compile_model(upper, airnode("A2", ceiling)))
        self.assertEqual(0.6, floor.Geosurf)
        self.assertEqual("H_0_0", floor.Orientation)


class HygrothermalTests(unittest.TestCase):
    def test_final_condition_chooses_the_model(self):
        a, b = south(0, 5, category="EXTERNAL"), south(0, 5, y=9, category="BOUNDARY", temperature="INPUT 1*TX")
        c = south(0, 5, y=18)
        a.Hygrothermal = b.Hygrothermal = c.Hygrothermal = True
        self.assertEqual([], compile_model(airnode("A1", a, b, c)))
        self.assertEqual(("EXTCALEXT", "EXTCALBND", "EXTCALEXT"), (a.Boundarycond, b.Boundarycond, c.Boundarycond))

    def test_adjacent_hamt_surface_is_an_error(self):
        a, b = south(0, 5), north(0, 5)
        a.Hygrothermal = True
        self.assertIn("HAMT", errors(compile_model(airnode("A1", a), airnode("A2", b)))[0])

    def test_explicit_hamt_surface_does_not_take_part(self):
        a, b = south(0, 5, category="EXTERNAL"), north(0, 5, category="EXTERNAL")
        a.Hygrothermal = True
        issues = compile_model(airnode("A1", a), airnode("A2", b), autoadjacency=True)
        self.assertEqual([], errors(issues))
        self.assertIn("keeps its own", warnings_of(issues)[0])
        self.assertEqual(("EXTCALEXT", "EXTERNAL"), (a.Boundarycond, b.Boundarycond))


class OrientSurfacesTests(unittest.TestCase):
    def room(self):
        floor = surface([(0, 0, 0), (0, 4, 0), (5, 4, 0), (5, 0, 0)])
        ceiling = surface([(0, 0, 3), (5, 0, 3), (5, 4, 3), (0, 4, 3)])
        walls = [surface([(0, 0, 0), (5, 0, 0), (5, 0, 3), (0, 0, 3)]), surface([(5, 0, 0), (5, 4, 0), (5, 4, 3), (5, 0, 3)]),
                 surface([(5, 4, 0), (0, 4, 0), (0, 4, 3), (5, 4, 3)]), surface([(0, 4, 0), (0, 0, 0), (0, 0, 3), (0, 4, 3)])]
        return [floor, ceiling]+walls

    def test_correct_room(self):
        self.assertEqual(([], True), M["orientSurfaces"](self.room()))

    def test_wrong_surface_is_flipped_with_all_it_carries(self):
        room = self.room()
        wrong = room[1]
        M["flipSurface"](wrong)
        self.assertEqual(1, wrong.Faces.flips)
        flipped, closed = M["orientSurfaces"](room)
        self.assertEqual(([wrong], True), (flipped, closed))
        self.assertEqual(2, wrong.Faces.flips)
        self.assertEqual(1.0, wrong.Normalvector.Z)
        self.assertGreater(M["polyAreaVector"](M["surfacePoints"](wrong))[2], 0)

    def test_window_follows_its_wall(self):
        room = self.room()
        wall = room[2]
        window = surface([(3, 0, 1), (1, 0, 1), (1, 0, 2), (3, 0, 2)], kind="WINDOW")  # normal into the room
        M["flipSurface"](wall)
        flipped, closed = M["orientSurfaces"](room+[window])
        self.assertTrue(closed)
        self.assertIn(window, flipped)
        self.assertEqual(-1.0, window.Normalvector.Y)

    def test_open_room_is_left_alone(self):
        room = self.room()[:-1]
        M["flipSurface"](room[0])
        vertices = list(room[0].Vertices)
        self.assertEqual(([], False), M["orientSurfaces"](room))
        self.assertEqual(vertices, room[0].Vertices)


class FakeUserDictionary(dict):
    def ContainsKey(self, key):
        return key in self

    def Set(self, key, value):
        self[key] = value


class FakeSurfaceBrep:
    def __init__(self, name):
        self.name = name
        self.UserDictionary = FakeUserDictionary()

    def DuplicateBrep(self):
        other = FakeSurfaceBrep(self.name)
        other.UserDictionary = FakeUserDictionary(self.UserDictionary)
        return other

    def GetArea(self):
        return 1.0

    def GetBoundingBox(self, accurate):
        return SimpleNamespace(Min=self.name, Max=self.name)


def load_construction():
    text = SOURCE.read_text(encoding="utf-8-sig")
    block = between(text, "class CONSTRUCTION:", "class ZONECOLL():")
    block = re.sub(r"^(\s*)print (.*)$", r"\1print(\2)", block, flags=re.M).replace(".has_key(key)", ".__contains__(key)").replace(".has_key('Const_coll')", ".__contains__('Const_coll')").replace(".has_key('Surface_Counter')", ".__contains__('Surface_Counter')")
    sticky = {"doc": {"GEOMETRY": lambda brep: _geometry(brep), "library": None}}
    namespace = dict(M)
    namespace.update({
        "copy": copy, "re": re, "sc": SimpleNamespace(sticky=sticky, doc=SimpleNamespace(Path="doc")),
        "surfaceNormal": lambda brep: Vec(0, 0, 1),
        "getSurfaceVertices": lambda normal, brep: [Vec(0, 0, 0), Vec(1, 0, 0), Vec(0, 1, 0)],
        "cleanVertices": lambda points: points,
        "checkVerticesOrder": lambda points, normal: points,
        "getWinOrientation": lambda brep: "S_0_90",
        "library": SimpleNamespace(Walls=[]),
    })
    exec(compile(block, str(SOURCE), "exec"), namespace)
    return namespace["CONSTRUCTION"](), sticky["doc"]


def _geometry(brep):
    record = M["GEOMETRY"](brep)
    return record


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.construction, self.sticky = load_construction()

    def settings(self, **values):
        fields = {"Boundarycond": None, "Construction": None, "Boundarytemp": None, "Frontback": None}
        fields.update(values)
        return SimpleNamespace(**fields)

    def add(self, brep, guid, settings=None):
        breps = self.construction.addToConstruction([brep], guid)
        self.construction.updateConstructionNew(breps, settings)
        return breps[0]

    def record(self, brep):
        return self.sticky["Const_coll"][brep.UserDictionary["LID"]]

    def test_empty_settings_stay_unset(self):
        brep = self.add(FakeSurfaceBrep("a"), "c1", self.settings(Construction="WALL"))
        record = self.record(brep)
        self.assertEqual(("WALL", None, None), (record.Construction, record.Boundarycond, record.Frontback))

    def test_no_settings_at_all_leave_everything_open(self):
        record = self.record(self.add(FakeSurfaceBrep("a"), "c1"))
        self.assertEqual((None, None), (record.Construction, record.Boundarycond))

    def test_later_component_only_changes_what_it_sets(self):
        first = self.add(FakeSurfaceBrep("a"), "c1", self.settings(Construction="WALL", Boundarycond="EXTERNAL"))
        second = self.add(first, "c2", self.settings(Boundarycond="BOUNDARY", Boundarytemp="TAIR_A2"))
        record = self.record(second)
        self.assertEqual(("WALL", "BOUNDARY", "INPUT 1*TAIR_A2"), (record.Construction, record.Boundarycond, record.Boundarytemp))
        self.assertEqual(self.record(first).Surfnum, record.Surfnum)

    def test_branches_do_not_touch_each_other(self):
        first = self.add(FakeSurfaceBrep("a"), "c1", self.settings(Construction="WALL"))
        left = self.add(first, "c2", self.settings(Construction="LEFT"))
        right = self.add(first, "c3", self.settings(Construction="RIGHT"))
        self.assertEqual(("WALL", "LEFT", "RIGHT"), (self.record(first).Construction, self.record(left).Construction, self.record(right).Construction))

    def test_the_input_brep_keeps_its_id(self):
        first = self.add(FakeSurfaceBrep("a"), "c1", self.settings(Construction="WALL"))
        lid = first.UserDictionary["LID"]
        second = self.add(first, "c2", self.settings(Boundarycond="EXTERNAL"))
        self.assertEqual(lid, first.UserDictionary["LID"])
        self.assertNotEqual(lid, second.UserDictionary["LID"])

    def test_a_new_solution_keeps_the_number_and_forgets_removed_settings(self):
        first = self.add(FakeSurfaceBrep("a"), "c1", self.settings(Construction="WALL", Boundarycond="EXTERNAL"))
        again = self.add(FakeSurfaceBrep("a"), "c1", self.settings(Construction="WALL"))
        self.assertEqual(self.record(first).Surfnum, self.record(again).Surfnum)
        self.assertIsNone(self.record(again).Boundarycond)

    def test_new_surfaces_get_new_numbers(self):
        self.assertNotEqual(self.record(self.add(FakeSurfaceBrep("a"), "c1")).Surfnum, self.record(self.add(FakeSurfaceBrep("b"), "c1")).Surfnum)

    def test_numeric_temperature_stays_a_number_and_efical_gets_the_surface_number(self):
        record = self.record(self.add(FakeSurfaceBrep("a"), "c1", self.settings(Boundarytemp="20")))
        self.assertEqual("20", record.Boundarytemp)
        record = self.record(self.add(FakeSurfaceBrep("b"), "c1", self.settings(Boundarycond="EXTFICALC", Boundarytemp="TF_S")))
        self.assertEqual("INPUT 1*TF_S%s" % record.Surfnum, record.Boundarytemp)

    def test_window_settings_add_attributes_the_surface_does_not_have(self):
        settings = SimpleNamespace(Type="WINDOW", Construction="WIN_A_1", Trnflow=None, Shdinput=None, Fixshade=0)
        record = self.record(self.add(FakeSurfaceBrep("a"), "c1", settings))
        self.assertEqual(("WINDOW", "WIN_A_1_S_0_90", None, None, 0), (record.Type, record.Construction, record.Trnflow, record.Shdinput, record.Fixshade))


def run_surface_component(settings, walls=("WALL",)):
    """The real Lizard_Surface.py on a fake CONSTRUCTION; returns (written settings, runtime messages, SurfaceInfo)."""
    source = (REPO_ROOT / "components" / "Lizard_Surface.py").read_text(encoding="utf-8-sig")
    written = []
    messages = []

    class Construction:
        def addToConstruction(self, breps, guid):
            return breps

        def updateConstructionNew(self, breps, surface):
            written.append(surface)

        def getWallThickness(self, breps):
            pass

        def callFromConstruction(self, breps):
            return []

    scriptcontext = ModuleType("scriptcontext")
    scriptcontext.doc = SimpleNamespace(Path="doc")
    scriptcontext.sticky = {"doc": {"CONSTRUCTION": Construction, "library": SimpleNamespace(Walls=[SimpleNamespace(Name=name) for name in walls])}}
    grasshopper = ModuleType("Grasshopper")
    kernel = ModuleType("Grasshopper.Kernel")
    kernel.GH_RuntimeMessageLevel = SimpleNamespace(Warning="WARNING", Error="ERROR")
    grasshopper.Kernel = kernel
    component = SimpleNamespace(InstanceGuid=SimpleNamespace(ToString=lambda: "guid"), AddRuntimeMessage=lambda level, text: messages.append(text))
    class BRep(str):
        Faces = SimpleNamespace(Count=1)

    namespace = {"ghenv": SimpleNamespace(Component=component), "BRep": [BRep("brep")], "Settings": settings}
    with mock.patch.dict(sys.modules, {"scriptcontext": scriptcontext, "Grasshopper": grasshopper, "Grasshopper.Kernel": kernel}):
        exec(compile(source, "Lizard_Surface.py", "exec"), namespace)
    return written, messages, namespace["SurfaceInfo"]


class SurfaceComponentTests(unittest.TestCase):
    def test_no_settings_at_all(self):
        written, messages, info = run_surface_component(None)
        self.assertEqual(([None], [], ["brep"]), (written, messages, info))

    def test_empty_construction_is_fine_here(self):
        settings = SimpleNamespace(Construction=None, Boundarycond="EXTERNAL")
        self.assertEqual(["brep"], run_surface_component(settings)[2])

    def test_unknown_construction_is_still_reported_at_once(self):
        written, messages, info = run_surface_component(SimpleNamespace(Construction="NOPE", Boundarycond=None))
        self.assertIsNone(info)
        self.assertEqual(["Construction name not found in the library!"], messages)


def box_room(name, x0, x1, y0, y1, z0, z1, ground=False):
    """A closed room whose surfaces leave everything to compileModel; a floor with ground=True gets the category BOUNDARY."""
    floor = surface([(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)], category="BOUNDARY" if ground else None, construction="IFL" if not ground else "WALL")
    ceiling = surface([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], construction="ICL")
    walls = [surface([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]), surface([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)]),
             surface([(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)]), surface([(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)])]
    return airnode(name, floor, ceiling, *walls)


class BuildingTests(unittest.TestCase):
    def test_two_storeys_with_different_room_layouts(self):
        rooms = [box_room("G%d" % i, i*4.0, (i+1)*4.0, 0.0, 6.0, 0.0, 3.0, ground=True) for i in range(3)]
        rooms += [box_room("U%d" % i, 0.0, 12.0, i*3.0, (i+1)*3.0, 3.0, 6.0) for i in range(2)]
        for room in rooms:
            self.assertEqual(([], True), M["orientSurfaces"](room.Surfaces))
        issues = compile_model(*rooms)
        self.assertEqual([], issues)
        surfaces = {item.Surfnum: item for room in rooms for item in room.Surfaces}
        self.assertEqual(len(surfaces), sum(len(room.Surfaces) for room in rooms))
        interior = 0.0
        for item in surfaces.values():
            if item.Boundarycond == "ADJACENT":
                partner = surfaces[item.Adjsurf]
                self.assertEqual(item.Surfnum, partner.Adjsurf)
                self.assertEqual(item.Airnode, partner.Adjairnode)
                self.assertAlmostEqual(item.Area, partner.Area)
                self.assertNotEqual(item.Frontback, partner.Frontback)
                self.assertLess(M["vecDot"](M["polyAreaVector"](M["surfacePoints"](item)), M["polyAreaVector"](M["surfacePoints"](partner))), 0)
                interior += item.Area
        slab = 12.0*6.0
        partitions_ground = 2*6.0*3.0
        partitions_upper = 12.0*3.0
        self.assertAlmostEqual(2*(slab+partitions_ground+partitions_upper), interior)
        for room in rooms:
            floor_area = sum(item.Area for item in room.Surfaces if item.Type == "FLOOR")
            expected = 24.0 if room.Name.startswith("G") else 36.0
            self.assertAlmostEqual(expected, floor_area)
        roof = [item for room in rooms for item in room.Surfaces if item.Type == "ROOF"]
        self.assertAlmostEqual(slab, sum(item.Area for item in roof))
        self.assertEqual({"H_0_0"}, {item.Orientation for item in roof})


class WiringTests(unittest.TestCase):
    def read(self, name):
        return (REPO_ROOT / "components" / name).read_text(encoding="utf-8-sig")

    def test_check_adjacent_is_gone(self):
        for path in (REPO_ROOT / "components").glob("Lizard_*.py"):
            self.assertNotIn("checkAdjacent", path.read_text(encoding="utf-8-sig"), path.name)

    def test_system_compiles_the_model_and_stops_on_errors(self):
        source = self.read("Lizard_System.py")
        self.assertIn('compileModel        = sc.sticky[sc.doc.Path]["compileModel"]', source)
        self.assertRegex(source, r"compileModel\(Airnodeinfo,library,dummyMulti\.autoadjacency,dummyMulti\.gaptolerance,RunSingleAirnodes == 1,dummyMulti\.constructionset\)")
        self.assertRegex(source, r"if modelerror:[\s\S]{0,200}sys\.exit\(\)")

    def test_component_registers_the_functions(self):
        source = self.read("Lizard_Component.py")
        for name in ("compileModel", "orientSurfaces"):
            self.assertIn('sc.sticky[sc.doc.Path]["%s"]' % name, source)

    def test_multizone_declares_the_inputs(self):
        source = self.read("Lizard_Multizone.py")
        self.assertRegex(source, r"\n    AutoAdjacency \(bool\): ")
        self.assertRegex(source, r"\n    GapTolerance \(float\): ")
        self.assertIn("self.autoadjacency = AutoAdjacency", source)
        self.assertIn("self.gaptolerance = GapTolerance", source)

    def test_airnode_orients_before_it_reads_the_orientation(self):
        source = self.read("Lizard_Thermal_Airnode.py")
        self.assertLess(source.index("orientSurfaces(SurfaceInfo)"), source.index("getSurfaceOrientation(SurfaceInfo)"))
        self.assertNotIn("error2", source)
        self.assertNotIn("defineGeosurf(", source)


if __name__ == "__main__":
    unittest.main()
