"""HAMT (Type 395) surfaces get the front films of their own construction.

A HAMT surface (EXTCALEXT, EXTCALBND) is written as a pseudo-wall of high conductance whose boundary temperature is the Type 395
surface temperature.  Type 56 computes HCONVI (beta1 of Type 395) and REQV (hconv1) of the surface with HFRONT, ABS-FRONT and EPS-FRONT
of the wall type the surface uses.  Before, all HAMT surfaces used the one library wall HIGH_COND, which was overwritten construction
by construction, so every HAMT surface got the films of the construction handled last.  Now each construction used by a HAMT surface
gets its own pseudo-wall type <construction>_HAMT (copy of the library HIGH_COND with the films of the construction, HBACK 99999).

The real b18 writer blocks of Lizard_System.py are executed with mock Grasshopper objects (harness of test_thermal_mirror_hback).
"""

import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_thermal_mirror_hback as mirror  # noqa: E402  (b18 writer harness)

EXTCALEXT_START = "                elif surfaces.Boundarycond == 'EXTCALEXT':\n"
EXTCALEXT_END = "                elif surfaces.Boundarycond == 'EXTVERTF':"


def base_walls():
    """Library pseudo-walls as in the DIN library (HIGH_COND: layer DIRECT, HFRONT 11, HBACK 99999)."""
    return [
        mirror.make_wall("HIGH_COND", " DIRECT", " 0.01", "11", "99999"),
        mirror.make_wall("HIGH_RES", " HIGH_RES", " 0.01", "11", "64"),
    ]


def worstcase_walls():
    """Four constructions with different front films (values of the WorstCase H_Front proposal)."""
    return [
        mirror.make_wall("HHL_WC_AW_Lehm", " HHL_WC_Lehmputz", " 0.005", "9.0", "64", "0.3", "0.7"),
        mirror.make_wall("HHL_WC_TW_Lehm", " HHL_WC_Lehmputz", " 0.005", "9.0", "64", "0.3", "0.3"),
        mirror.make_wall("HHL_WC_GD_Boden", " HHL_WC_Zementestrich", " 0.06", "2.52", "64", "0.5", "0.7"),
        mirror.make_wall("HHL_WC_FD_Dach", " HHL_WC_BSP", " 0.125", "2.52", "64", "0.4", "0.7"),
    ] + base_walls()


def worstcase_airnode():
    return mirror.make_airnode("A1", [
        mirror.make_surface(1, "EXTCALEXT", "HHL_WC_AW_Lehm", 0, 13.5, 0.1),
        mirror.make_surface(2, "EXTCALBND", "HHL_WC_TW_Lehm", "INPUT 1*TAIR_@ANAME", 36.0, 0.2),
        mirror.make_surface(3, "EXTCALBND", "HHL_WC_TW_Lehm", "INPUT 1*TAIR_@ANAME", 36.0, 0.2),
        mirror.make_surface(4, "EXTCALBND", "HHL_WC_GD_Boden", "INPUT 1*TAIR_@ANAME", 54.0, 0.3, "FLOOR"),
        mirror.make_surface(5, "EXTCALEXT", "HHL_WC_FD_Dach", 0, 54.0, 0.0, "ROOF"),
    ])


def film_of(block):
    """(ABS-FRONT, ABS-BACK, HFRONT, HBACK) of a six-line CONSTRUCTION block as text."""
    absorptance = block[3].split()
    films = block[5].split()
    return absorptance[1], absorptance[4], films[2], films[5]


def render_extcalext(surface, hamt_wall_names, helpers):
    """Run the real EXTCALEXT branch of printbuiZonepart for one surface; the surface after the branch."""
    block = mirror.source_slice(mirror.read_source(mirror.SYSTEM_SOURCE), EXTCALEXT_START, EXTCALEXT_END)
    block = "if" + block[len("elif"):]
    namespace = dict(helpers)
    namespace.update({
        "surfaces": surface,
        "srfnum": surface.Surfnum,
        "dummylines": "",
        "appendstring": "",
        "ecal_surfaces": [],
        "ori_construction": surface.Construction,
        "hamt_wall_names": hamt_wall_names,
    })
    mirror.run(block, namespace)
    return namespace


class HamtPseudoWallCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helpers = mirror.load_helpers()

    def render(self, airnode, walls):
        definitions, messages = mirror.render_wall_definitions(walls, [airnode], self.helpers)
        return definitions, messages, mirror.render_zone_lines([airnode], walls, self.helpers)


class WorstCaseRenderTests(HamtPseudoWallCase):
    """Walls, floor and roof of one zone, all HAMT, with different front films."""

    def setUp(self):
        self.walls = worstcase_walls()
        self.airnode = worstcase_airnode()
        self.definitions, self.messages, self.zone_lines = self.render(self.airnode, self.walls)

    def test_each_construction_gets_its_own_pseudo_wall_with_its_films(self):
        expected = {
            "HHL_WC_AW_Lehm_HAMT": ("0.3", "0.7", "9.0", "99999"),
            "HHL_WC_TW_Lehm_HAMT": ("0.3", "0.3", "9.0", "99999"),
            "HHL_WC_GD_Boden_HAMT": ("0.5", "0.7", "2.52", "99999"),
            "HHL_WC_FD_Dach_HAMT": ("0.4", "0.7", "2.52", "99999"),
        }
        for name, films in expected.items():
            with self.subTest(name=name):
                block = mirror.block_of(self.definitions, name)
                self.assertEqual(" LAYERS   =  DIRECT", block[1])
                self.assertEqual(films, film_of(block))

    def test_the_shared_library_pseudo_wall_is_no_longer_written(self):
        self.assertNotIn("CONSTRUCTION HIGH_COND", self.definitions)

    def test_boundary_hamt_surfaces_reference_the_type_of_their_construction(self):
        self.assertEqual(
            [
                "WALL  =HHL_WC_TW_Lehm_HAMT : SURF=  2 : AREA=        36.0 : BOUNDARY=INPUT 1*TSI395_S2 : GEOSURF=0.2",
                "WALL  =HHL_WC_TW_Lehm_HAMT : SURF=  3 : AREA=        36.0 : BOUNDARY=INPUT 1*TSI395_S3 : GEOSURF=0.2",
                "FLOOR  =HHL_WC_GD_Boden_HAMT : SURF=  4 : AREA=        54.0 : BOUNDARY=INPUT 1*TSI395_S4 : GEOSURF=0.3",
            ],
            self.zone_lines,
        )

    def test_exterior_hamt_surfaces_reference_the_type_of_their_construction(self):
        plan = self.helpers["plan_hamt_pseudo_walls"]([self.airnode], self.walls)
        for surface, expected in ((self.airnode.Surfaces[0], "HHL_WC_AW_Lehm_HAMT"), (self.airnode.Surfaces[4], "HHL_WC_FD_Dach_HAMT")):
            with self.subTest(surface=surface.Surfnum):
                namespace = render_extcalext(copy.copy(surface), plan, self.helpers)
                self.assertEqual(expected, namespace["surfaces"].Construction)
                self.assertIn("BOUNDARY = INPUT 1*TSI395_S@self.Surfnum", namespace["dummylines"])
                self.assertEqual([surface.Surfnum], namespace["ecal_surfaces"])

    def test_every_zone_wall_line_names_a_defined_wall_type(self):
        defined = [line.split()[1] for line in self.definitions if line.startswith("CONSTRUCTION ")]
        for line in self.zone_lines:
            with self.subTest(line=line):
                self.assertIn(line.split("=")[1].split(" :")[0], defined)

    def test_a_remark_lists_the_pseudo_walls_and_their_front_films(self):
        hamt = [text for (level, text) in self.messages if text.startswith("HAMT walls")]
        self.assertEqual(1, len(hamt))
        self.assertEqual("REMARK", [level for (level, text) in self.messages if text.startswith("HAMT walls")][0])
        self.assertIn("HHL_WC_FD_Dach_HAMT (from HHL_WC_FD_Dach: HFRONT 2.52, ABS-FRONT 0.4, EPS-FRONT 0.9)", hamt[0])
        self.assertIn("HHL_WC_AW_Lehm_HAMT (from HHL_WC_AW_Lehm: HFRONT 9.0, ABS-FRONT 0.3, EPS-FRONT 0.9)", hamt[0])

    def test_library_objects_are_not_modified(self):
        library = {}
        for wall in self.walls:
            library[wall.Name] = wall
        self.assertEqual("11", library["HIGH_COND"].Hfront)
        self.assertEqual("99999", library["HIGH_COND"].Hback)
        self.assertEqual("0.6", library["HIGH_COND"].Abs_front)
        self.assertEqual("64", library["HHL_WC_FD_Dach"].Hback)

    def test_a_second_zone_pass_gives_the_same_lines(self):
        # simplify == 1 calls printbuiZonepart twice; the branch restores the original construction after writing the line
        self.assertEqual(self.zone_lines, mirror.render_zone_lines([self.airnode], self.walls, self.helpers))
        self.assertEqual(
            ["HHL_WC_AW_Lehm", "HHL_WC_TW_Lehm", "HHL_WC_TW_Lehm", "HHL_WC_GD_Boden", "HHL_WC_FD_Dach"],
            [surface.Construction for surface in self.airnode.Surfaces],
        )


class PseudoWallRuleTests(HamtPseudoWallCase):

    def test_one_type_per_construction_however_many_surfaces_use_it(self):
        airnode = mirror.make_airnode("A1", [
            mirror.make_surface(number, "EXTCALBND", "HHL_WC_TW_Lehm", "INPUT 1*TAIR_@ANAME") for number in (2, 3, 6, 7)
        ])
        definitions, messages, zone_lines = self.render(airnode, worstcase_walls())
        self.assertEqual(["CONSTRUCTION HHL_WC_TW_Lehm", "CONSTRUCTION HHL_WC_TW_Lehm_HAMT"],
                         [line for line in definitions if line.startswith("CONSTRUCTION")])
        self.assertEqual(4, len([line for line in zone_lines if line.startswith("WALL  =HHL_WC_TW_Lehm_HAMT :")]))

    def test_a_construction_missing_in_the_library_keeps_the_library_high_cond(self):
        airnode = mirror.make_airnode("A1", [
            mirror.make_surface(2, "EXTCALBND", "NotInTheLibrary", "INPUT 1*TAIR_@ANAME"),
            mirror.make_surface(3, "EXTCALBND", "HHL_WC_TW_Lehm", "INPUT 1*TAIR_@ANAME"),
        ])
        definitions, messages, zone_lines = self.render(airnode, worstcase_walls())
        self.assertEqual(("0.6", "0.6", "11", "99999"), film_of(mirror.block_of(definitions, "HIGH_COND")))
        self.assertTrue(zone_lines[0].startswith("WALL  =HIGH_COND : SURF=  2 "))
        self.assertTrue(zone_lines[1].startswith("WALL  =HHL_WC_TW_Lehm_HAMT : SURF=  3 "))

    def test_a_window_on_an_exterior_hamt_wall_adds_no_library_high_cond(self):
        # the window copies Boundarycond EXTCALEXT from its wall (Lizard_Component) but is written as a window, without a wall type
        airnode = mirror.make_airnode("A1", [
            mirror.make_surface(150, "EXTCALEXT", "HHL_WC_AW_Lehm", 0, 8.0, 0.06),
            mirror.make_surface(140, "EXTCALEXT", "WIN_W1_3304_S_0_90", 0, 6.0, 0.0, "WINDOW"),
        ])
        definitions, messages, zone_lines = self.render(airnode, worstcase_walls())
        self.assertEqual(["CONSTRUCTION HHL_WC_AW_Lehm", "CONSTRUCTION HHL_WC_AW_Lehm_HAMT"],
                         [line for line in definitions if line.startswith("CONSTRUCTION")])

    def test_a_virtual_hamt_surface_adds_no_library_high_cond(self):
        airnode = mirror.make_airnode("A1", [
            mirror.make_surface(2, "EXTCALBND", "Virtual_Opening", "INPUT 1*TAIR_@ANAME"),
            mirror.make_surface(3, "EXTCALBND", "HHL_WC_TW_Lehm", "INPUT 1*TAIR_@ANAME"),
        ])
        definitions, messages, zone_lines = self.render(airnode, worstcase_walls())
        self.assertNotIn("CONSTRUCTION HIGH_COND", definitions)
        self.assertEqual(1, len(zone_lines))

    def test_a_window_on_a_boundary_hamt_wall_keeps_the_library_high_cond(self):
        # the BOUNDARY branch of printbuiZonepart does not skip windows, so such a window line names HIGH_COND
        airnode = mirror.make_airnode("A1", [
            mirror.make_surface(3, "EXTCALBND", "HHL_WC_TW_Lehm", "INPUT 1*TAIR_@ANAME"),
            mirror.make_surface(4, "EXTCALBND", "WIN_W1_3304_S_0_90", "INPUT 1*TAIR_@ANAME", 2.0, 0.0, "WINDOW"),
        ])
        definitions, messages, zone_lines = self.render(airnode, worstcase_walls())
        defined = [line.split()[1] for line in definitions if line.startswith("CONSTRUCTION ")]
        self.assertIn("HIGH_COND", defined)
        for line in zone_lines:
            with self.subTest(line=line):
                self.assertIn(line.split("=")[1].split(" :")[0], defined)

    def test_without_hamt_surfaces_nothing_is_derived(self):
        airnode = mirror.make_airnode("A1", [
            mirror.make_surface(2, "BOUNDARY", "HHL_WC_TW_Lehm", "INPUT 1*TAIR_A2"),
            mirror.make_surface(3, "EXTCALC", "HHL_WC_AW_Lehm", 0),
        ])
        definitions, messages, zone_lines = self.render(airnode, worstcase_walls())
        self.assertEqual([], [line for line in definitions if "_HAMT" in line])
        self.assertEqual([], [text for (level, text) in messages if text.startswith("HAMT walls")])
        self.assertEqual({}, self.helpers["plan_hamt_pseudo_walls"]([airnode], worstcase_walls()))

    def test_missing_library_high_cond_raises_a_warning(self):
        walls = [wall for wall in worstcase_walls() if wall.Name != "HIGH_COND"]
        definitions, messages, zone_lines = self.render(worstcase_airnode(), walls)
        warnings = [text for (level, text) in messages if level == "WARNING"]
        self.assertEqual(1, len(warnings))
        self.assertIn("has no HIGH_COND", warnings[0])
        self.assertEqual([], [line for line in definitions if "_HAMT" in line])

    def test_names_stay_within_the_limit_and_unique(self):
        name_of = self.helpers["hamt_wall_type_name"]
        limit = self.helpers["MIRROR_NAME_MAX"]
        self.assertEqual("HHL_Wall_Gipskartonplatte_HAMT", name_of("HHL_Wall_Gipskartonplatte", []))
        long_name = "HHL_WC_Construction_With_A_Long_Name"
        self.assertLessEqual(len(name_of(long_name, [])), limit)
        self.assertTrue(name_of(long_name, []).endswith("_HAMT"))
        self.assertEqual("X1_HAMT", name_of("X", ["x_hamt"]))
        walls = [mirror.make_wall(long_name + "_A", " A", " 0.1", "9", "64"), mirror.make_wall(long_name + "_B", " A", " 0.1", "2", "64"),
                 mirror.make_wall("X", " A", " 0.1", "9", "64"), mirror.make_wall("X_HAMT", " A", " 0.1", "9", "64")] + base_walls()
        airnode = mirror.make_airnode("A1", [
            mirror.make_surface(1, "EXTCALBND", long_name + "_A", "INPUT 1*TAIR_@ANAME"),
            mirror.make_surface(2, "EXTCALBND", long_name + "_B", "INPUT 1*TAIR_@ANAME"),
            mirror.make_surface(3, "EXTCALBND", "X", "INPUT 1*TAIR_@ANAME"),
        ])
        plan = self.helpers["plan_hamt_pseudo_walls"]([airnode], walls)
        names = list(plan.values())
        self.assertEqual(len(names), len(set(names)))
        library = [wall.Name.lower() for wall in walls]
        for name in names:
            self.assertLessEqual(len(name), limit)
            self.assertNotIn(name.lower(), library)
        self.assertEqual("X1_HAMT", plan["X"])

    def test_extcalext_with_an_unknown_construction_keeps_the_library_high_cond(self):
        surface = mirror.make_surface(1, "EXTCALEXT", "NotInTheLibrary", 0)
        namespace = render_extcalext(surface, {}, self.helpers)
        self.assertEqual("HIGH_COND", namespace["surfaces"].Construction)


if __name__ == "__main__":
    unittest.main()
