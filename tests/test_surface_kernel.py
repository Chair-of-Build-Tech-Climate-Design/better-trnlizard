"""The plain geometry block of Lizard_Component.py: planar arrangement of coplanar faces and the direction of the normals.

The block runs without Rhino, so the real code is executed here. It must stay valid in both IronPython 2 and CPython 3.
"""

import ast
import math
import random
import re
import unittest
from itertools import permutations
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "Lizard_Component.py"
BEGIN = "# ---- Surface kernel (begin)"
END = "# ---- Surface kernel (end)"


def kernel_source():
    text = SOURCE.read_text(encoding="utf-8-sig")
    return text[text.index(BEGIN):text.index(END)]


def load_kernel():
    namespace = {"math": math}
    exec(compile(kernel_source(), str(SOURCE), "exec"), namespace)
    return namespace


K = load_kernel()


def rect(x0, y0, x1, y1):
    return [(float(x0), float(y0)), (float(x1), float(y0)), (float(x1), float(y1)), (float(x0), float(y1))]


def areas_by_key(regions):
    totals = {}
    for region in regions:
        for key in region["cover"]:
            totals[key] = totals.get(key, 0.0) + region["area"]
    return totals


def signature(regions):
    return sorted((region["cover"], round(region["area"], 6)) for region in regions)


class BlockTests(unittest.TestCase):
    def test_no_rhino_and_no_python3_only_syntax(self):
        source = kernel_source()
        self.assertNotRegex(source, r"\b(rc|sc|rs|ghcomp)\.")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            self.assertNotIsInstance(node, (ast.JoinedStr, ast.Nonlocal, ast.AnnAssign))
            if isinstance(node, ast.FunctionDef):
                self.assertFalse(node.args.kwonlyargs)


class ArrangePolygonsTests(unittest.TestCase):
    def check(self, polygons, tolerance=0.01):
        regions = K["arrangePolygons"](polygons, tolerance)
        totals = areas_by_key(regions)
        for key, loop in polygons:
            self.assertAlmostEqual(abs(K["polyArea2d"](loop)), totals.get(key, 0.0), places=6, msg=key)
        for region in regions:
            self.assertGreater(K["polyArea2d"](region["loop"]), 0)
            self.assertGreaterEqual(len(region["loop"]), 3)
        return regions

    def test_identical_rectangles_give_one_region(self):
        regions = self.check([("a", rect(0, 0, 5, 3)), ("b", rect(0, 0, 5, 3))])
        self.assertEqual([(("a", "b"), 15.0)], signature(regions))
        self.assertEqual(4, len(regions[0]["loop"]))

    def test_one_wall_against_two(self):
        regions = self.check([("a", rect(0, 0, 6, 3)), ("b", rect(0, 0, 2, 3)), ("c", rect(2, 0, 6, 3))])
        self.assertEqual([(("a", "b"), 6.0), (("a", "c"), 12.0)], signature(regions))

    def test_two_walls_against_two_with_a_shifted_joint(self):
        regions = self.check([("a", rect(0, 0, 3, 3)), ("b", rect(3, 0, 6, 3)), ("c", rect(0, 0, 4, 3)), ("d", rect(4, 0, 6, 3))])
        self.assertEqual([(("a", "c"), 9.0), (("b", "c"), 3.0), (("b", "d"), 6.0)], signature(regions))

    def test_partial_overlap_leaves_the_rest_with_its_own_source(self):
        regions = self.check([("a", rect(0, 0, 4, 3)), ("b", rect(1, 1, 6, 4))])
        self.assertEqual([(("a",), 6.0), (("a", "b"), 6.0), (("b",), 9.0)], signature(regions))

    def test_no_contact(self):
        self.assertEqual([(("a",), 1.0), (("b",), 1.0)], signature(self.check([("a", rect(0, 0, 1, 1)), ("b", rect(5, 5, 6, 6))])))

    def test_a_small_wall_inside_a_big_one_cuts_the_rest_into_simple_loops(self):
        regions = self.check([("a", rect(0, 0, 10, 4)), ("b", rect(4, 1, 6, 3))])
        inner = [region for region in regions if region["cover"] == ("a", "b")]
        outer = [region for region in regions if region["cover"] == ("a",)]
        self.assertEqual(1, len(inner))
        self.assertEqual(4.0, inner[0]["area"])
        self.assertEqual(2, len(outer))
        for region in outer:
            loop = region["loop"]
            for i in range(len(loop)):
                self.assertNotIn(loop[i], loop[:i])

    def test_two_small_walls_inside_a_big_one(self):
        regions = self.check([("a", rect(0, 0, 10, 4)), ("b", rect(1, 1, 3, 3)), ("c", rect(6, 1, 8, 3))])
        self.assertEqual(8.0, sum(region["area"] for region in regions if len(region["cover"]) == 2))
        self.assertEqual(32.0, sum(region["area"] for region in regions if region["cover"] == ("a",)))

    def test_l_shape_against_a_rectangle(self):
        l_shape = [(0.0, 0.0), (6.0, 0.0), (6.0, 2.0), (2.0, 2.0), (2.0, 5.0), (0.0, 5.0)]
        regions = self.check([("a", l_shape), ("b", rect(0, 0, 6, 5))])
        self.assertEqual([(("a", "b"), 18.0), (("b",), 12.0)], signature(regions))

    def test_snapping_closes_small_offsets(self):
        regions = K["arrangePolygons"]([("a", rect(0, 0, 5, 3)), ("b", rect(0.004, -0.003, 5.002, 3.004))], 0.01)
        self.assertEqual(1, len(regions))
        self.assertEqual(("a", "b"), regions[0]["cover"])

    def test_sliver_goes_to_the_neighbour(self):
        regions = K["arrangePolygons"]([("a", rect(0, 0, 5, 3)), ("b", rect(0, 0, 4.98, 3))], 0.01, 0.05)
        self.assertEqual([("a", "b")], [region["cover"] for region in regions])

    def test_sliver_is_kept_below_its_tolerance(self):
        regions = K["arrangePolygons"]([("a", rect(0, 0, 5, 3)), ("b", rect(0, 0, 4.9, 3))], 0.01, 0.05)
        self.assertEqual([("a",), ("a", "b")], sorted(region["cover"] for region in regions))

    def test_order_does_not_matter(self):
        polygons = [("a", rect(0, 0, 3, 3)), ("b", rect(3, 0, 6, 3)), ("c", rect(0, 0, 4, 3)), ("d", rect(4, 0, 6, 3)), ("e", rect(1, 1, 2, 2))]
        reference = K["arrangePolygons"](polygons, 0.01)
        for order in permutations(polygons):
            self.assertEqual(reference, K["arrangePolygons"](list(order), 0.01))

    def test_rotated_polygons(self):
        def turn(loop, angle=0.7):
            return [(x*math.cos(angle)-y*math.sin(angle), x*math.sin(angle)+y*math.cos(angle)) for x, y in loop]
        polygons = [("a", turn(rect(0, 0, 6, 3))), ("b", turn(rect(0, 0, 2, 3))), ("c", turn(rect(2, 0, 6, 3)))]
        regions = self.check(polygons)
        self.assertEqual([(("a", "b"), 6.0), (("a", "c"), 12.0)], signature(regions))

    def test_random_rectangles_keep_their_area(self):
        generator = random.Random(4)
        for _ in range(40):
            polygons = []
            for key in range(6):
                x, y = generator.uniform(0, 8), generator.uniform(0, 8)
                polygons.append((key, rect(x, y, x+generator.uniform(1, 5), y+generator.uniform(1, 5))))
            regions = K["arrangePolygons"](polygons, 0.001)
            totals = areas_by_key(regions)
            for key, loop in polygons:
                self.assertAlmostEqual(K["polyArea2d"](loop), totals[key], delta=0.05)


class ArrangeFacesTests(unittest.TestCase):
    def wall(self, key, x0, x1, y=0.0, sign=1):
        points = [(x0, y, 0.0), (x1, y, 0.0), (x1, y, 3.0), (x0, y, 3.0)]
        if sign < 0:
            points.reverse()
        return {"key": key, "points": points, "normal": K["vecUnit"](K["polyAreaVector"](points))}

    def test_opposite_faces_share_a_region_with_their_own_winding(self):
        a, b = self.wall(1, 0.0, 6.0), self.wall(2, 0.0, 2.0, sign=-1)
        c = self.wall(3, 2.0, 6.0, sign=-1)
        regions = K["arrangeFaces"]([a, b, c], 0.01, 0.02)
        self.assertEqual({(1, 2): 6.0, (1, 3): 12.0}, {region["cover"]: round(region["area"], 6) for region in regions})
        for region in regions:
            sides = region["sides"]
            self.assertEqual(-1, sides[region["cover"][0]]*sides[region["cover"][1]])
            for key, loop in region["loops"].items():
                face = {1: a, 2: b, 3: c}[key]
                self.assertGreater(K["vecDot"](K["polyAreaVector"](loop), face["normal"]), 0)
                self.assertTrue(all(abs(point[1]) < 1e-9 for point in loop))

    def test_gap_tolerance_decides_whether_parallel_planes_meet(self):
        a, b = self.wall(1, 0.0, 6.0), self.wall(2, 0.0, 6.0, y=0.2, sign=-1)
        self.assertEqual([(1,), (2,)], sorted(region["cover"] for region in K["arrangeFaces"]([a, b], 0.01, 0.02)))
        regions = K["arrangeFaces"]([a, b], 0.01, 0.3)
        self.assertEqual([(1, 2)], [region["cover"] for region in regions])
        self.assertTrue(all(abs(point[1]-0.2) < 1e-9 for point in regions[0]["loops"][2]))

    def test_other_planes_stay_apart(self):
        a = self.wall(1, 0.0, 6.0)
        floor = {"key": 2, "points": [(0.0, 0.0, 0.0), (0.0, 5.0, 0.0), (6.0, 5.0, 0.0), (6.0, 0.0, 0.0)], "normal": (0.0, 0.0, -1.0)}
        self.assertEqual([(1,), (2,)], sorted(region["cover"] for region in K["arrangeFaces"]([a, floor], 0.01, 0.02)))


def prism(plan, height=3.0, splitwall=None):
    """Closed faces of a counter-clockwise plan, all normals pointing outward."""
    faces = [[(x, y, 0.0) for x, y in reversed(plan)], [(x, y, height) for x, y in plan]]
    for i in range(len(plan)):
        a, b = plan[i], plan[(i+1) % len(plan)]
        if i == splitwall:
            middle = ((a[0]+b[0])/2.0, (a[1]+b[1])/2.0)
            parts = [(a, middle), (middle, b)]
        else:
            parts = [(a, b)]
        for p, q in parts:
            faces.append([(p[0], p[1], 0.0), (q[0], q[1], 0.0), (q[0], q[1], height), (p[0], p[1], height)])
    return faces


def normals_of(faces):
    return [K["vecUnit"](K["polyAreaVector"](face)) for face in faces]


BOX = [(0.0, 0.0), (5.0, 0.0), (5.0, 4.0), (0.0, 4.0)]
L_PLAN = [(0.0, 0.0), (8.0, 0.0), (8.0, 3.0), (3.0, 3.0), (3.0, 7.0), (0.0, 7.0)]
U_PLAN = [(0.0, 0.0), (9.0, 0.0), (9.0, 6.0), (6.0, 6.0), (6.0, 2.0), (3.0, 2.0), (3.0, 6.0), (0.0, 6.0)]
ROOMS = {"box": prism(BOX), "L": prism(L_PLAN), "U": prism(U_PLAN), "U with a T-junction": prism(U_PLAN, splitwall=2)}


class OrientClosedPolygonsTests(unittest.TestCase):
    def test_correct_room_needs_no_flip(self):
        for name, faces in ROOMS.items():
            with self.subTest(name):
                self.assertEqual(([], True), K["orientClosedPolygons"](faces, normals_of(faces)))

    def test_any_mix_of_wrong_normals_is_found(self):
        generator = random.Random(1)
        for name, faces in ROOMS.items():
            normals = normals_of(faces)
            for _ in range(30):
                wrong = sorted(i for i in range(len(faces)) if generator.random() < 0.5)
                given = [tuple(-c for c in normals[i]) if i in wrong else normals[i] for i in range(len(faces))]
                with self.subTest(name, wrong=wrong):
                    self.assertEqual((wrong, True), K["orientClosedPolygons"](faces, given))

    def test_all_normals_reversed(self):
        faces = ROOMS["U"]
        given = [tuple(-c for c in normal) for normal in normals_of(faces)]
        self.assertEqual((list(range(len(faces))), True), K["orientClosedPolygons"](faces, given))

    def test_an_open_room_is_not_corrected(self):
        faces = list(ROOMS["U"])
        del faces[1]  # no ceiling
        given = normals_of(faces)
        given[0] = tuple(-c for c in given[0])  # the floor now points up, where nothing is left to cross
        self.assertEqual(([], False), K["orientClosedPolygons"](faces, given))

    def test_symmetric_room_with_rays_through_the_opposite_diagonal(self):
        # A centred sample hits the opposite wall on the diagonal of any triangulation: one polygon counts once.
        faces = prism(BOX)
        self.assertIs(False, K["rayCrossesPolygon"]((2.5, 4.0, 1.5), (0.0, 1.0, 0.0), faces[2]))
        self.assertIs(True, K["rayCrossesPolygon"]((2.5, 2.0, 1.5), (0.0, -1.0, 0.0), faces[2]))

    def test_ray_on_a_boundary_is_not_counted(self):
        faces = prism(BOX)
        self.assertIsNone(K["rayCrossesPolygon"]((0.0, 2.0, 1.5), (0.0, -1.0, 0.0), faces[2]))


class RotateConvexStartTests(unittest.TestCase):
    def test_starts_at_a_convex_vertex(self):
        points = [(3.0, 2.0, 0.0), (3.0, 6.0, 0.0), (0.0, 6.0, 0.0), (0.0, 0.0, 0.0), (9.0, 0.0, 0.0), (9.0, 6.0, 0.0), (6.0, 6.0, 0.0), (6.0, 2.0, 0.0)]
        rotated = K["rotateConvexStart"](points, (0.0, 0.0, 1.0))
        self.assertEqual((3.0, 6.0, 0.0), rotated[0])
        self.assertEqual(sorted(points), sorted(rotated))


if __name__ == "__main__":
    unittest.main()
