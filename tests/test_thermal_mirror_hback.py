"""Regression checks for the back film (HBACK) of thermal (Type 56 only) mirror walls.

In the DIN models the W/N/E walls face neighbouring rooms under the mirror assumption (boundary temperature = the
zone's own TAIR).  Hygrothermal variants (Type 395, EXTCALBND, option A) give side 2 of such a wall an interior
convective film of 11 kJ/(h m2 K) plus a longwave exchange with the room (4 sigma eps T^3 = 18.5 kJ/(h m2 K) at 20 C).
The thermal variants carried the library default HBACK = 64 kJ/(h m2 K) (17.8 W/m2K, exterior convention, no longwave)
on the same walls.  The generator now gives BOUNDARY walls whose boundary temperature is the own TAIR, and whose
construction has the library default HBACK, the combined film of about 29.5 kJ/(h m2 K) through a derived wall type
``<name>_MIRROR`` (HBACK is a property of the WALL type and shared with the exterior wall, which needs 64).

The real b18 writer blocks of ``Lizard_System.py`` (the ``Walls definition`` block of ``printbuitoppart`` and the
BOUNDARY branch of ``printbuiZonepart``) and the real ``printSingleData`` of ``Lizard_Component.py`` are executed with
mock Grasshopper objects (no Grasshopper, no TRNBuild, no TRNSYS).  The b18 ``Template`` object lives in another
Grasshopper component; its ``Wall`` and ``Constr`` strings are reconstructed from the generated DIN reference b18.
"""

import ast
import copy
import re
import sys
import unittest
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_type395_side2_boundary as side2  # noqa: E402  (the option A harness: real e7 handler and template block)

REPO_ROOT = side2.REPO_ROOT
SYSTEM_SOURCE = side2.SYSTEM_SOURCE
TEMPLATE_SOURCE = side2.TEMPLATE_SOURCE
COMPONENT_SOURCE = REPO_ROOT / "Lizard_Component.py"

HELPER_START = "# ---- thermal mirror walls (begin)"
HELPER_END = "# ---- thermal mirror walls (end)"
WALLS_START = "    # Walls definition from the library\n    if TRNSYS == 17:"
WALLS_END = "    # Intermediate part directly from the template\n    lines.extend(printheader('W i n d o w s'))"
BOUNDARY_START = (
    "            elif surfaces.Boundarycond == 'BOUNDARY' or surfaces.Boundarycond == 'EXTFICALC'"
    " or surfaces.Boundarycond == 'BNDCALC' or surfaces.Boundarycond == 'EXTCALBND':\n"
)
BOUNDARY_END = "            elif surfaces.Boundarycond == 'ADJACENT' and surfaces.Type != 'WINDOW':"
PRINT_SINGLE_DATA_START = "@timing\ndef printSingleData(data_collection, *search_attr):"
PRINT_SINGLE_DATA_END = "@timing\ndef getDataParagraph("

# b18 Template strings reconstructed from the generated DIN reference (Thermisch_Big_GKP_WithFoil.b18)
TEMPLATE_WALL = (
    "CONSTRUCTION @self.Name\n"
    " LAYERS   = @self.Layers\n"
    " THICKNESS= @self.Thickness\n"
    " ABS-FRONT= @self.Abs_front   : ABS-BACK= @self.Abs_back\n"
    " EPS-FRONT= @self.Eps_front   : EPS-BACK= @self.Eps_back\n"
    " HFRONT   = @self.Hfront : HBACK= @self.Hback\n"
)
TEMPLATE_CONSTR = "@self.Type  =@self.Construction : SURF=  @self.Surfnum : AREA=        @self.Area"

# Reference lines of the generated DIN thermal b18 (trailing blanks removed).  Nothing below depends on the new behaviour.
REFERENCE_ROOF_FLOOR = [
    "CONSTRUCTION HHL_Roof",
    " LAYERS   =  GYPSUM       AIR_SUS      CONCRETE     INSULATION",
    " THICKNESS=  0.0125       0            0.25         0.2",
    " ABS-FRONT= 0.7   : ABS-BACK= 1.0",
    " EPS-FRONT= 0.9   : EPS-BACK= 0.9",
    " HFRONT   = 14.0 : HBACK= 9999.0",
    "CONSTRUCTION HHL_Floor",
    " LAYERS   =  WOOD         AIR_SUS      CONCRETE     INSULATION",
    " THICKNESS=  0.012        0            0.25         0.15",
    " ABS-FRONT= 0.7   : ABS-BACK= 1.0",
    " EPS-FRONT= 0.9   : EPS-BACK= 0.9",
    " HFRONT   = 36.0 : HBACK= 9999.0",
]
REFERENCE_WALL = [
    "CONSTRUCTION HHL_Wall_Gipskartonplatte",
    " LAYERS   =  HHL_Gipskartonplatte HHL_Holzfaserdaemmmatte HHL_LivingBoard HHL_Zellulosedaemmstoff HHL_AGEPAN_THD",
    " THICKNESS=  0.022        0.06         0.015        0.24         0.035",
    " ABS-FRONT= 0.3   : ABS-BACK= 0.7",
    " EPS-FRONT= 0.9   : EPS-BACK= 0.9",
    " HFRONT   = 23.0 : HBACK= 64.0",
]
REFERENCE_CEILING_FLOOR_LINES = [
    "CEILING  =HHL_Roof : SURF=  58 : AREA=        28.3 : BOUNDARY=INPUT 1*TAIR_A1 : GEOSURF=0",
    "FLOOR  =HHL_Floor : SURF=  56 : AREA=        28.3 : BOUNDARY=INPUT 1*TAIR_A1 : GEOSURF=0.6",
]
# What the thermal DIN b18 must contain after the change (derived type, HBACK 29.51, three zone lines renamed)
EXPECTED_MIRROR_WALL = [
    "CONSTRUCTION HHL_Wall_Gipskarto_MIRROR",
    " LAYERS   =  HHL_Gipskartonplatte HHL_Holzfaserdaemmmatte HHL_LivingBoard HHL_Zellulosedaemmstoff HHL_AGEPAN_THD",
    " THICKNESS=  0.022        0.06         0.015        0.24         0.035",
    " ABS-FRONT= 0.3   : ABS-BACK= 0.7",
    " EPS-FRONT= 0.9   : EPS-BACK= 0.9",
    " HFRONT   = 23.0 : HBACK= 29.51",
]
EXPECTED_MIRROR_ZONE_LINES = [
    "WALL  =HHL_Wall_Gipskarto_MIRROR : SURF=  68 : AREA=        15.848 : BOUNDARY=INPUT 1*TAIR_A1 : GEOSURF=0.12",
    "WALL  =HHL_Wall_Gipskarto_MIRROR : SURF=  69 : AREA=        14.0 : BOUNDARY=INPUT 1*TAIR_A1 : GEOSURF=0.106",
    "WALL  =HHL_Wall_Gipskarto_MIRROR : SURF=  70 : AREA=        15.848 : BOUNDARY=INPUT 1*TAIR_A1 : GEOSURF=0.12",
]

# Syntax that IronPython 2.7 (Grasshopper) cannot parse or that its unqualified-exec functions reject
PY3_ONLY_NODES = tuple(
    getattr(ast, name)
    for name in ("JoinedStr", "FormattedValue", "Nonlocal", "AnnAssign", "AsyncFunctionDef", "Await", "YieldFrom",
                 "NamedExpr", "GeneratorExp", "SetComp", "DictComp", "Lambda")
    if hasattr(ast, name)
)


def read_source(path):
    return path.read_text(encoding="utf-8-sig")


def source_slice(source, start, end):
    first = source.index(start)
    return dedent(source[first:source.index(end, first)])


def run(block, namespace):
    # dict.iteritems() is the only IronPython 2 construct of these blocks that CPython 3 cannot run
    return side2.run_source(block.replace(".iteritems()", ".items()"), SYSTEM_SOURCE, namespace)


def load_helpers():
    """Namespace of the thermal mirror wall helpers of Lizard_System.py, or {} when the source has none."""
    source = read_source(SYSTEM_SOURCE)
    if HELPER_START not in source:
        return {}
    namespace = {"re": re, "copy": copy}
    run(source_slice(source, HELPER_START, HELPER_END), namespace)
    return namespace


def load_print_single_data():
    """The real printSingleData of Lizard_Component.py with the reconstructed b18 Template."""
    source = read_source(COMPONENT_SOURCE)
    namespace = {"timing": lambda function: function, "Template": SimpleNamespace(Wall=TEMPLATE_WALL)}
    side2.run_source(
        source_slice(source, PRINT_SINGLE_DATA_START, PRINT_SINGLE_DATA_END).replace(".iteritems()", ".items()"),
        COMPONENT_SOURCE,
        namespace,
    )
    return namespace["printSingleData"]


def make_wall(name, layers, thickness, hfront, hback, abs_front="0.6", abs_back="0.6"):
    return SimpleNamespace(
        Name=name, Layers=layers, Wall=1, Thickness=thickness, Abs_front=abs_front, Abs_back=abs_back,
        Eps_front="0.9", Eps_back="0.9", Hfront=hfront, Hback=hback,
    )


def make_surface(number, boundarycond, construction, boundarytemp="INPUT 1*TAIR_@ANAME", area=15.848, geosurf=0.12,
                 surface_type="WALL"):
    return SimpleNamespace(
        Surfnum=number, Boundarycond=boundarycond, Construction=construction, Boundarytemp=boundarytemp,
        Area=area, Geosurf=geosurf, Type=surface_type, Fsky=0.5, Filemat="GKP.idf",
    )


def make_airnode(name, surfaces, zone="Z1"):
    return SimpleNamespace(Name=name, Zonename=zone, Surfaces=surfaces)


def din_walls(hback="64.0"):
    return [
        make_wall("HHL_Roof", " GYPSUM       AIR_SUS      CONCRETE     INSULATION  ",
                  " 0.0125       0            0.25         0.2         ", "14.0", "9999.0", "0.7", "1.0"),
        make_wall("HHL_Floor", " WOOD         AIR_SUS      CONCRETE     INSULATION  ",
                  " 0.012        0            0.25         0.15        ", "36.0", "9999.0", "0.7", "1.0"),
        make_wall("HHL_Wall_Gipskartonplatte",
                  " HHL_Gipskartonplatte HHL_Holzfaserdaemmmatte HHL_LivingBoard HHL_Zellulosedaemmstoff HHL_AGEPAN_THD",
                  " 0.022        0.06         0.015        0.24         0.035       ", "23.0", hback, "0.3", "0.7"),
        make_wall("HIGH_COND", " DIRECT", " 0.01", "11", "99999"),
        make_wall("HIGH_RES", " HIGH_RES", " 0.01", "11", "64"),
    ]


def din_airnode(wall_category="BOUNDARY", boundarytemp="INPUT 1*TAIR_@ANAME"):
    """Zone Z1 / airnode A1 of the DIN thermal model: S wall (exterior), ceiling, floor, W/N/E walls (mirror)."""
    wall = "HHL_Wall_Gipskartonplatte"
    return make_airnode("A1", [
        make_surface(67, "EXTERNAL", wall, boundarytemp=0, area=7.0, geosurf=0.053),
        make_surface(58, "BOUNDARY", "HHL_Roof", boundarytemp, 28.3, 0, "CEILING"),
        make_surface(56, "BOUNDARY", "HHL_Floor", boundarytemp, 28.3, 0.6, "FLOOR"),
        make_surface(68, wall_category, wall, boundarytemp, 15.848, 0.12),
        make_surface(69, wall_category, wall, boundarytemp, 14.0, 0.106),
        make_surface(70, wall_category, wall, boundarytemp, 15.848, 0.12),
    ])


def recorder(messages):
    return SimpleNamespace(
        Component=SimpleNamespace(AddRuntimeMessage=lambda level, text: messages.append((level, text)))
    )


def render_wall_definitions(walls, airnodes, helpers):
    """Run the real 'Walls definition from the library' block of printbuitoppart(); (text lines, runtime messages)."""
    source = read_source(SYSTEM_SOURCE)
    messages = []
    namespace = dict(helpers)
    namespace.update({
        "re": re,
        "copy": copy,
        "TRNSYS": 18,
        "lines": [],
        "printheader": lambda text: ["*---\n", "*  " + text + "\n", "*---\n"],
        "library": SimpleNamespace(Walls=walls),
        "dataset": airnodes,
        "surfaceinfo": [surface for airnode in airnodes for surface in airnode.Surfaces],
        "printsingledata": load_print_single_data(),
        "ghenv": recorder(messages),
        "rem": "REMARK",
        "w": "WARNING",
    })
    run(source_slice(source, WALLS_START, WALLS_END), namespace)
    text = "".join(namespace["lines"]).replace("\r", "")
    return [line.rstrip() for line in text.splitlines()], messages


def render_zone_lines(airnodes, walls, helpers):
    """Run the real BOUNDARY branch of printbuiZonepart() for every surface that takes it; list of b18 lines."""
    block = source_slice(read_source(SYSTEM_SOURCE), BOUNDARY_START, BOUNDARY_END)
    assert block.startswith("elif")
    block = block[len("elif"):]
    block = "if" + block
    thermal_mirror_names = helpers["plan_thermal_mirror_walls"](airnodes, walls)[0] if helpers else {}
    lines = []
    for airnode in airnodes:
        for surface in airnode.Surfaces:
            if "Virtual" in surface.Construction:
                continue
            if surface.Boundarycond not in ("BOUNDARY", "EXTFICALC", "BNDCALC", "EXTCALBND"):
                continue
            namespace = dict(helpers)
            namespace.update({
                "re": re,
                "surfaces": surface,
                "Airnodes": airnode,
                "templates": SimpleNamespace(Constr=TEMPLATE_CONSTR),
                "appendstring": "",
                "ecal_surfaces": [],
                "efical_surfaces": [],
                "constructionlines": "",
                "thermal_mirror_names": thermal_mirror_names,
                "ghenv": recorder([]),
                "w": "WARNING",
                "rem": "REMARK",
            })
            run(block, namespace)
            lines.append(namespace["constructionlines"].replace("\r\n", "\n").rstrip())
    return lines


def block_of(lines, name):
    """The six lines of the CONSTRUCTION block called ``name``."""
    start = lines.index("CONSTRUCTION " + name)
    return lines[start:start + 6]


def hback_of(lines, name):
    return float(re.search(r"HBACK=\s*(\S+)", block_of(lines, name)[5]).group(1))


class MirrorHelperCase(unittest.TestCase):
    """Base class: the helper block must exist (it does not before the change)."""

    @classmethod
    def setUpClass(cls):
        cls.helpers = load_helpers()

    def setUp(self):
        if not self.helpers:
            self.fail("Lizard_System.py has no '%s' helper block" % HELPER_START)


class ThermalMirrorDinRenderTests(unittest.TestCase):
    """The DIN thermal model (Thermisch_Big_GKP_WithFoil): S wall exterior, ceiling/floor 9999, W/N/E mirror walls."""

    @classmethod
    def setUpClass(cls):
        cls.helpers = load_helpers()
        cls.walls = din_walls()
        cls.airnodes = [din_airnode()]
        cls.definitions, cls.messages = render_wall_definitions(cls.walls, cls.airnodes, cls.helpers)
        cls.zone_lines = render_zone_lines(cls.airnodes, cls.walls, cls.helpers)

    def test_mock_reproduces_the_unchanged_reference_blocks(self):
        # harness fidelity: these parts of the DIN reference b18 do not depend on the change
        self.assertEqual(REFERENCE_ROOF_FLOOR, self.definitions[3:15])
        self.assertEqual(REFERENCE_WALL, block_of(self.definitions, "HHL_Wall_Gipskartonplatte"))
        self.assertEqual(REFERENCE_CEILING_FLOOR_LINES, self.zone_lines[0:2])

    def test_mirror_walls_get_a_derived_wall_type_with_the_combined_back_film(self):
        self.assertEqual(EXPECTED_MIRROR_WALL, block_of(self.definitions, "HHL_Wall_Gipskarto_MIRROR"))

    def test_the_original_wall_type_keeps_hback_64_for_the_exterior_wall(self):
        self.assertEqual(REFERENCE_WALL, block_of(self.definitions, "HHL_Wall_Gipskartonplatte"))
        self.assertEqual(64.0, hback_of(self.definitions, "HHL_Wall_Gipskartonplatte"))

    def test_the_three_mirror_wall_lines_use_the_derived_type(self):
        self.assertEqual(EXPECTED_MIRROR_ZONE_LINES, self.zone_lines[2:5])

    def test_only_one_derived_type_is_emitted_and_nothing_else_changes(self):
        names = [line.split()[1] for line in self.definitions if line.startswith("CONSTRUCTION ")]
        self.assertEqual(
            ["HHL_Roof", "HHL_Floor", "HHL_Wall_Gipskartonplatte", "HHL_Wall_Gipskarto_MIRROR"], names
        )
        self.assertEqual(len(self.definitions), 3 + 12 + 6 + 6)

    def test_roof_and_floor_with_explicit_hback_9999_are_untouched(self):
        self.assertEqual(9999.0, hback_of(self.definitions, "HHL_Roof"))
        self.assertEqual(9999.0, hback_of(self.definitions, "HHL_Floor"))
        self.assertEqual(REFERENCE_CEILING_FLOOR_LINES, self.zone_lines[0:2])

    def test_runtime_message_lists_the_affected_walls(self):
        self.assertEqual(1, len(self.messages))
        level, text = self.messages[0]
        self.assertEqual("REMARK", level)
        for expected in ("68 (A1)", "69 (A1)", "70 (A1)", "HHL_Wall_Gipskarto_MIRROR", "HHL_Wall_Gipskartonplatte", "29.51"):
            self.assertIn(expected, text)
        self.assertNotIn("67 (", text)  # the exterior wall
        self.assertNotIn("58 (", text)  # ceiling, explicit HBACK 9999
        self.assertNotIn("56 (", text)  # floor, explicit HBACK 9999

    def test_rendering_does_not_modify_the_shared_library_walls_or_the_surfaces(self):
        self.assertEqual(din_walls()[2].__dict__, self.walls[2].__dict__)
        self.assertEqual("64.0", self.walls[2].Hback)
        self.assertEqual("HHL_Wall_Gipskartonplatte", self.airnodes[0].Surfaces[3].Construction)
        again = render_zone_lines(self.airnodes, self.walls, self.helpers)
        self.assertEqual(self.zone_lines, again)  # the simplify mode calls the zone writer twice


class ThermalMirrorRuleTests(unittest.TestCase):
    """Which walls are left alone."""

    def render(self, airnode, walls=None):
        walls = walls if walls is not None else din_walls()
        helpers = load_helpers()
        definitions, messages = render_wall_definitions(walls, [airnode], helpers)
        return definitions, messages, render_zone_lines([airnode], walls, helpers)

    def assertNothingDerived(self, definitions, messages, zone_lines):
        self.assertEqual([], [line for line in definitions if "MIRROR" in line])
        self.assertEqual([], [line for line in zone_lines if "MIRROR" in line])
        self.assertEqual([], messages)

    def one_wall(self, boundarycond="BOUNDARY", boundarytemp="INPUT 1*TAIR_@ANAME", construction="HHL_Wall_Gipskartonplatte"):
        return make_airnode("A1", [make_surface(68, boundarycond, construction, boundarytemp)])

    def test_explicit_non_default_hback_is_kept(self):
        for hback in ("9999.0", "8.5", "20", 20, "29.5", "64.5", "0.0001"):
            with self.subTest(hback=hback):
                results = self.render(self.one_wall(), din_walls(hback))
                self.assertNothingDerived(*results)
                self.assertTrue(results[2][0].startswith("WALL  =HHL_Wall_Gipskartonplatte : SURF=  68"))

    def test_non_numeric_hback_keywords_are_kept(self):
        for hback in ("VERTICAL", "FLOOR", "CEILING", "", None):
            with self.subTest(hback=hback):
                self.assertNothingDerived(*self.render(self.one_wall(), din_walls(hback)))

    def test_every_numeric_spelling_of_the_library_default_is_replaced(self):
        for hback in ("64.0", "64", 64, 64.0, " 64.0 "):
            with self.subTest(hback=hback):
                definitions, messages, zone_lines = self.render(self.one_wall(), din_walls(hback))
                self.assertEqual(29.51, hback_of(definitions, "HHL_Wall_Gipskarto_MIRROR"))
                self.assertIn("WALL  =HHL_Wall_Gipskarto_MIRROR : SURF=  68", zone_lines[0])

    def test_non_mirror_boundary_walls_are_untouched(self):
        for boundarytemp in ("INPUT 1*TAIR_A2", "INPUT 1*Tamb", "INPUT 1*18", "INPUT 1*-5", "18", "Identical",
                             "INPUT 1*TAIR_A10", "INPUT 1*TSOIL"):
            with self.subTest(boundarytemp=boundarytemp):
                self.assertNothingDerived(*self.render(self.one_wall(boundarytemp=boundarytemp)))

    def test_external_and_adjacent_walls_are_untouched(self):
        for category in ("EXTERNAL", "ADJACENT", "EXTBOUNDARY", "EXTSKYBND", "EXTVERTF", "EXTBOUNDADJ"):
            with self.subTest(category=category):
                self.assertNothingDerived(*self.render(self.one_wall(category)))

    def test_hamt_pseudo_walls_and_special_boundary_categories_are_untouched(self):
        for category in ("EXTCALBND", "EXTCALEXT", "EXTCALC", "BNDCALC", "EXTFICALC"):
            with self.subTest(category=category):
                definitions, messages, zone_lines = self.render(self.one_wall(category))
                self.assertEqual([], [line for line in definitions if "MIRROR" in line])
                self.assertEqual([], [line for line in zone_lines if "MIRROR" in line])
                self.assertEqual([], messages)
        _, _, zone_lines = self.render(self.one_wall("EXTCALBND"))
        self.assertEqual(
            ["WALL  =HIGH_COND : SURF=  68 : AREA=        15.848 : BOUNDARY=INPUT 1*TSI395_S68 : GEOSURF=0.12"], zone_lines
        )

    def test_a_construction_used_by_mirror_and_non_mirror_walls_keeps_both_types(self):
        airnode = make_airnode("A1", [
            make_surface(67, "EXTERNAL", "HHL_Wall_Gipskartonplatte", 0, 7.0, 0.053),
            make_surface(68, "BOUNDARY", "HHL_Wall_Gipskartonplatte", "INPUT 1*TAIR_A1", 15.848, 0.12),
            make_surface(69, "BOUNDARY", "HHL_Wall_Gipskartonplatte", "INPUT 1*TAIR_A2", 14.0, 0.106),
            make_surface(70, "BOUNDARY", "HHL_Wall_Gipskartonplatte", "INPUT 1*TAIR_A1", 15.848, 0.12),
        ])
        definitions, messages, zone_lines = self.render(airnode)
        self.assertEqual(1, len([line for line in definitions if line == "CONSTRUCTION HHL_Wall_Gipskarto_MIRROR"]))
        self.assertIn("=HHL_Wall_Gipskarto_MIRROR : SURF=  68", zone_lines[0])
        self.assertIn("=HHL_Wall_Gipskartonplatte : SURF=  69", zone_lines[1])
        self.assertIn("=HHL_Wall_Gipskarto_MIRROR : SURF=  70", zone_lines[2])
        self.assertIn("68 (A1), 70 (A1)", messages[0][1])
        self.assertNotIn("69 (", messages[0][1])

    def test_a_hamt_wall_sharing_its_construction_with_a_mirror_wall_stays_on_the_pseudo_wall(self):
        airnode = make_airnode("A1", [
            make_surface(9, "EXTCALBND", "HHL_Wall_Gipskartonplatte", "INPUT 1*TAIR_@ANAME", 15.848, 0.12),
            make_surface(10, "BOUNDARY", "HHL_Wall_Gipskartonplatte", "INPUT 1*TAIR_@ANAME", 14.0, 0.106),
        ])
        definitions, messages, zone_lines = self.render(airnode)
        self.assertEqual(1, len([line for line in definitions if line == "CONSTRUCTION HHL_Wall_Gipskarto_MIRROR"]))
        self.assertEqual(99999.0, hback_of(definitions, "HIGH_COND"))
        self.assertEqual(
            [
                "WALL  =HIGH_COND : SURF=  9 : AREA=        15.848 : BOUNDARY=INPUT 1*TSI395_S9 : GEOSURF=0.12",
                "WALL  =HHL_Wall_Gipskarto_MIRROR : SURF=  10 : AREA=        14.0 : BOUNDARY=INPUT 1*TAIR_A1 : GEOSURF=0.106",
            ],
            zone_lines,
        )
        self.assertIn("surface 10 (A1)", messages[0][1])
        self.assertNotIn("9 (A1)", messages[0][1])

    def test_mirror_is_the_walls_own_airnode_and_ignores_case(self):
        for airnode_name, boundarytemp in (("A1", "INPUT 1*TAIR_A1"), ("Office", "INPUT 1*Tair_Office"),
                                           ("A2", "INPUT 1*TAIR_@ANAME")):
            with self.subTest(airnode=airnode_name, boundarytemp=boundarytemp):
                airnode = make_airnode(airnode_name, [make_surface(68, "BOUNDARY", "HHL_Wall_Gipskartonplatte", boundarytemp)])
                definitions, messages, zone_lines = self.render(airnode)
                self.assertIn("CONSTRUCTION HHL_Wall_Gipskarto_MIRROR", definitions)
                self.assertIn("=HHL_Wall_Gipskarto_MIRROR : SURF=  68", zone_lines[0])
        # TAIR of another airnode of the zone is not a mirror
        airnode = make_airnode("A1", [make_surface(68, "BOUNDARY", "HHL_Wall_Gipskartonplatte", "INPUT 1*TAIR_A2")])
        self.assertNothingDerived(*self.render(airnode))

    def test_no_derived_type_when_no_mirror_wall_exists(self):
        airnode = make_airnode("A1", [make_surface(67, "EXTERNAL", "HHL_Wall_Gipskartonplatte", 0, 7.0, 0.053)])
        definitions, messages, zone_lines = self.render(airnode)
        self.assertEqual([], messages)
        self.assertEqual(REFERENCE_WALL, block_of(definitions, "HHL_Wall_Gipskartonplatte"))
        self.assertEqual(["CONSTRUCTION HHL_Wall_Gipskartonplatte"], [l for l in definitions if l.startswith("CONSTRUCTION")])

    def test_virtual_surfaces_and_unknown_constructions_are_skipped(self):
        airnode = make_airnode("A1", [
            make_surface(68, "BOUNDARY", "Virtual_Wall", "INPUT 1*TAIR_A1"),
            make_surface(69, "BOUNDARY", "NotInTheLibrary", "INPUT 1*TAIR_A1"),
        ])
        walls = din_walls() + [make_wall("Virtual_Wall", " GYPSUM", " 0.0125", "11", "64.0")]
        definitions, messages, zone_lines = self.render(airnode, walls)
        self.assertEqual([], [line for line in definitions if "MIRROR" in line])
        self.assertEqual([], messages)
        self.assertEqual(["WALL  =NotInTheLibrary : SURF=  69 : AREA=        15.848 : BOUNDARY=INPUT 1*TAIR_A1 : GEOSURF=0.12"],
                         zone_lines)

    def test_hygrothermal_din_model_is_unchanged(self):
        # S wall EXTCALEXT, W/N/E EXTCALBND (HIGH_COND pseudo-wall), ceiling/floor BOUNDARY with explicit HBACK 9999
        airnode = din_airnode("EXTCALBND")
        airnode.Surfaces[0].Boundarycond = "EXTCALEXT"
        definitions, messages, zone_lines = self.render(airnode)
        self.assertEqual([], [line for line in definitions if "MIRROR" in line])
        self.assertEqual([], messages)
        self.assertEqual(
            [
                "CEILING  =HHL_Roof : SURF=  58 : AREA=        28.3 : BOUNDARY=INPUT 1*TAIR_A1 : GEOSURF=0",
                "FLOOR  =HHL_Floor : SURF=  56 : AREA=        28.3 : BOUNDARY=INPUT 1*TAIR_A1 : GEOSURF=0.6",
                "WALL  =HIGH_COND : SURF=  68 : AREA=        15.848 : BOUNDARY=INPUT 1*TSI395_S68 : GEOSURF=0.12",
                "WALL  =HIGH_COND : SURF=  69 : AREA=        14.0 : BOUNDARY=INPUT 1*TSI395_S69 : GEOSURF=0.106",
                "WALL  =HIGH_COND : SURF=  70 : AREA=        15.848 : BOUNDARY=INPUT 1*TSI395_S70 : GEOSURF=0.12",
            ],
            zone_lines,
        )
        self.assertEqual(99999.0, hback_of(definitions, "HIGH_COND"))


class ThermalMirrorConsistencyTests(MirrorHelperCase):
    """The thermal value and the rules are tied to option A (Type 395 side 2 of EXTCALBND)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template_lines = side2.load_template_lines()

    def option_a_block(self, hback, boundarytemp="INPUT 1*TAIR_@ANAME", zone_name="A1"):
        walls_def = {"HHL_Wall": SimpleNamespace(Hback=hback, Abs_back="0.7")}
        surface = side2.make_surface(9, "EXTCALBND", boundarytemp, "HHL_Wall")
        text = side2.render_hamt_block(self.template_lines, [surface], walls_def, zone_name)
        return text, side2.equation_blocks(text)[0]

    def test_back_film_is_option_a_convective_film_plus_its_longwave_film(self):
        text, (_, equations, _, _) = self.option_a_block("64.0")
        h_conv = float(equations["hconv2_S9"])
        eps = float(re.search(r"SIGMA_S9 \* ([\d.]+) \* \(\(273\.15 \+ TMR_C1\)", equations["qWG2_S9"]).group(1))
        sigma = float(equations["SIGMA_S9"])
        h = self.helpers
        self.assertEqual(h_conv, h["MIRROR_HCONV_INTERIOR"])
        self.assertEqual(eps, h["MIRROR_EPS"])
        self.assertEqual(sigma, h["MIRROR_SIGMA"])
        self.assertEqual(64, h["MIRROR_HBACK_DEFAULT"])
        # 11 + 4 sigma eps T^3 at 20 C, in kJ/(h m2 K)
        expected = h_conv + 4 * sigma * eps * 293.15 ** 3
        self.assertAlmostEqual(expected, h["mirror_hback_value"](), delta=0.005)
        self.assertEqual(29.51, h["mirror_hback_value"]())
        self.assertAlmostEqual(29.5, h["mirror_hback_value"](), delta=0.05)
        self.assertAlmostEqual(8.2, h["mirror_hback_value"]() / 3.6, delta=0.01)  # W/(m2 K)

    def test_default_detection_agrees_with_option_a(self):
        # option A replaces exactly the library default (any numeric spelling) by the interior film of 11 and keeps an explicit value
        for hback in ("64.0", "64", 64, 64.0, "9999.0", "8.5", 20, "64.5", "29.5", "0.0001"):
            with self.subTest(hback=hback):
                _, (_, equations, _, _) = self.option_a_block(hback)
                option_a_replaces_it = equations["hconv2_S9"] == "11"
                self.assertEqual(option_a_replaces_it, self.helpers["is_default_hback"](hback))

    def test_mirror_detection_agrees_with_option_a(self):
        surface_for = lambda temp: make_surface(9, "BOUNDARY", "HHL_Wall_Gipskartonplatte", temp)  # noqa: E731
        for boundarytemp in ("INPUT 1*TAIR_@ANAME", "INPUT 1*TAIR_A1", "INPUT 1*Tair_a1", "INPUT 1*TAIR_A2",
                             "INPUT 1*Tamb", "INPUT 1*18", "INPUT 1*-5", "Identical", "INPUT 1*TAIR_A1 + 2"):
            with self.subTest(boundarytemp=boundarytemp):
                _, (_, equations, _, _) = self.option_a_block("64.0", boundarytemp)
                option_a_mirror = "(273.15 + TMR_C1)^4" in equations["qWG2_S9"]
                self.assertEqual(option_a_mirror,
                                 self.helpers["is_mirror_boundary_surface"](surface_for(boundarytemp), "A1"))


class ThermalMirrorNamingTests(MirrorHelperCase):
    def test_short_names_get_the_plain_suffix(self):
        self.assertEqual("Wall_A_MIRROR", self.helpers["mirror_type_name"]("Wall_A", []))

    def test_names_never_exceed_the_limit_and_keep_the_suffix(self):
        limit = self.helpers["MIRROR_NAME_MAX"]
        self.assertEqual(25, limit)  # longest wall type name known to work in TRNBuild here
        for length in range(1, 60):
            with self.subTest(length=length):
                original = "W" * length
                derived = self.helpers["mirror_type_name"](original, [])
                self.assertLessEqual(len(derived), limit)
                self.assertTrue(derived.endswith("_MIRROR"))
                self.assertTrue(re.match(r"^\w+$", derived))
                self.assertNotEqual(original.lower(), derived.lower())
                if length + 7 <= limit:
                    self.assertEqual(original + "_MIRROR", derived)
                else:
                    self.assertTrue(original.startswith(derived[:-len("_MIRROR")]))

    def test_the_din_wall_names_are_shortened_to_the_limit(self):
        name = self.helpers["mirror_type_name"]
        self.assertEqual("HHL_Wall_Gipskarto_MIRROR", name("HHL_Wall_Gipskartonplatte", []))
        self.assertEqual("HHL_Wall_Lehmplatt_MIRROR", name("HHL_Wall_Lehmplatte_V1", []))  # LP V1 and V2 (separate models)
        self.assertEqual("HHL_Wall_Lehmplatt_MIRROR", name("HHL_Wall_Lehmplatte_V2", []))

    def test_a_different_limit_can_be_passed(self):
        self.assertEqual("HHL_Wall_Gipskartonplatte_MIRROR",
                         self.helpers["mirror_type_name"]("HHL_Wall_Gipskartonplatte", [], 32))

    def test_colliding_names_are_made_unique_case_insensitively(self):
        name = self.helpers["mirror_type_name"]
        first = name("HHL_Wall_Gipskartonplatte", [])
        second = name("HHL_Wall_Gipskartonplatte", [first.lower()])
        third = name("HHL_Wall_Gipskartonplatte", [first.lower(), second.lower()])
        self.assertEqual(3, len({first.lower(), second.lower(), third.lower()}))
        for derived in (first, second, third):
            self.assertLessEqual(len(derived), 25)
            self.assertTrue(derived.endswith("_MIRROR"))

    def test_plan_gives_distinct_names_to_constructions_with_a_common_long_prefix(self):
        walls = din_walls()
        walls.append(make_wall("HHL_Wall_Gipskartonplatte_B", " GYPSUM", " 0.0125", "11", "64.0"))
        walls.append(make_wall("HHL_Wall_Gipskarto_MIRROR", " GYPSUM", " 0.0125", "11", "64.0"))  # a user type of that name
        airnode = make_airnode("A1", [
            make_surface(68, "BOUNDARY", "HHL_Wall_Gipskartonplatte", "INPUT 1*TAIR_A1"),
            make_surface(69, "BOUNDARY", "HHL_Wall_Gipskartonplatte_B", "INPUT 1*TAIR_A1"),
            make_surface(70, "BOUNDARY", "HHL_Wall_Gipskarto_MIRROR", "INPUT 1*TAIR_A1"),
        ])
        names = self.helpers["plan_thermal_mirror_walls"]([airnode], walls)[0]
        self.assertEqual(3, len(names))
        taken = [wall.Name.lower() for wall in walls]
        for derived in names.values():
            self.assertLessEqual(len(derived), 25)
            self.assertNotIn(derived.lower(), taken)
        self.assertEqual(3, len({derived.lower() for derived in names.values()}))
        # the result does not depend on the order of the surfaces
        airnode.Surfaces.reverse()
        self.assertEqual(names, self.helpers["plan_thermal_mirror_walls"]([airnode], walls)[0])


class ThermalMirrorStaticB18Tests(unittest.TestCase):
    """What can be checked without TRNBuild: the rendered DIN b18 fragment follows the syntax TRNBuild already reads."""

    @classmethod
    def setUpClass(cls):
        cls.helpers = load_helpers()
        cls.walls = din_walls()
        cls.airnodes = [din_airnode()]
        cls.definitions, _ = render_wall_definitions(cls.walls, cls.airnodes, cls.helpers)
        cls.zone_lines = render_zone_lines(cls.airnodes, cls.walls, cls.helpers)

    def constructions(self):
        return {line.split()[1]: block_of(self.definitions, line.split()[1])
                for line in self.definitions if line.startswith("CONSTRUCTION ")}

    def test_every_zone_wall_references_a_defined_construction(self):
        defined = self.constructions()
        for line in self.zone_lines:
            self.assertIn(re.match(r"^\w+\s*=(\w+)", line).group(1), defined, line)

    def test_construction_names_are_unique_short_and_plain(self):
        names = list(self.constructions())
        self.assertEqual(len(names), len({name.lower() for name in names}))
        for name in names:
            self.assertTrue(re.match(r"^\w+$", name), name)
            self.assertLessEqual(len(name), 25, name)  # the longest name known to work in TRNBuild here

    def test_derived_block_differs_from_the_original_only_in_name_and_hback(self):
        blocks = self.constructions()
        original, derived = blocks["HHL_Wall_Gipskartonplatte"], blocks["HHL_Wall_Gipskarto_MIRROR"]
        self.assertEqual(len(original), len(derived))
        differing = [i for i, (a, b) in enumerate(zip(original, derived)) if a != b]
        self.assertEqual([0, 5], differing)
        self.assertEqual(original[5].replace("HBACK= 64.0", "HBACK= 29.51"), derived[5])

    def test_hback_is_a_positive_plain_number_and_the_block_keeps_the_keyword_layout(self):
        block = self.constructions()["HHL_Wall_Gipskarto_MIRROR"]
        keywords = [re.findall(r"([A-Z-]+)\s*=", line) for line in block[1:]]
        self.assertEqual([["LAYERS"], ["THICKNESS"], ["ABS-FRONT", "ABS-BACK"], ["EPS-FRONT", "EPS-BACK"],
                          ["HFRONT", "HBACK"]], keywords)
        self.assertRegex(block[5], r"^ HFRONT   = \d+(\.\d+)? : HBACK= \d+\.\d\d$")
        self.assertGreater(hback_of(self.definitions, "HHL_Wall_Gipskarto_MIRROR"), 0)

    def test_a_row_of_the_b18_stays_within_trnbuild_limit_of_400_characters(self):
        for line in self.definitions + self.zone_lines:
            self.assertLessEqual(len(line), 400)

    def test_helper_and_edited_blocks_use_only_syntax_that_ironpython_2_accepts(self):
        source = read_source(SYSTEM_SOURCE)
        self.assertTrue(HELPER_START in source, "helper block missing")
        blocks = {
            "helpers": source_slice(source, HELPER_START, HELPER_END),
            "walls block": source_slice(source, WALLS_START, WALLS_END),
            "BOUNDARY branch": "if" + source_slice(source, BOUNDARY_START, BOUNDARY_END)[len("elif"):],
        }
        for label, block in blocks.items():
            tree = ast.parse(block.replace(".iteritems()", ".items()"))
            for node in ast.walk(tree):
                self.assertNotIsInstance(node, PY3_ONLY_NODES, "%s: line %s" % (label, getattr(node, "lineno", "?")))


if __name__ == "__main__":
    unittest.main()
