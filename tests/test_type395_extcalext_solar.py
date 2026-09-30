"""Exterior solar gain of the HAMT exterior walls (EXTCALEXT, Type 395 input 8 = qWG2).

Type 56 treats an EXTCALEXT wall as a BOUNDARY surface (``BOUNDARY = INPUT 1*TSI395_S<n>``) and computes no incident radiation
for it, so ``IT_S<n> * absorptance`` was zero for the whole year.  The solar term now uses the total radiation of a Type 15
tilted surface with the orientation of the wall (Type 15 and Type 56 call the same TRNSYS kernel routine, so this is Type 56's IT
of an EXTERNAL surface of that orientation), times ABS-BACK; the longwave emissivity is EPS-BACK of the construction.

The real ``@s7#...@e7#`` template block, the real ``e7`` handler, the real weather-reader block and the real helper functions of
``Lizard_System.py`` are executed with mock variables (no Grasshopper, no TRNSYS).
"""

import re
import sys
import unittest
import warnings
from pathlib import Path
from textwrap import dedent
from types import ModuleType, SimpleNamespace
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_SOURCE = REPO_ROOT / "Lizard_System.py"
TEMPLATE_SOURCE = REPO_ROOT / "Lizard_DCK_Template.py"

# The Type 15 block of a deck without EXTCALEXT walls, as generated before this change (must stay byte-identical).
TYPE15_BLOCK_WITHOUT_TILTED_SURFACES = """
*------------------------------------------------------------------------------
* Model "Type15-3" (Type 15)
*
UNIT 15 TYPE 15\t Type15-3
*$UNIT_NAME Type15-3
*$MODEL .\\Weather Data Reading and Processing\\Standard Format\\Energy+ Weather Files (EPW)\\Type15-3.tmf
*$POSITION 330 31
*$LAYER Weather - Data Files #
PARAMETERS 9
3\t\t! 1 File Type
36\t\t! 2 Logical unit
5\t\t! 3 Tilted Surface Radiation Mode
GRDREF\t\t! 4 Ground reflectance - no snow
0.2\t\t! 5 Ground reflectance - snow cover
1\t\t! 6 Number of surfaces
1\t\t! 7 Tracking mode
0.0\t\t! 8 Slope of surface
0\t\t! 9 Azimuth of surface
"""

LONGWAVE_ONLY_QWG2 = (
    "AREA395_S8 * 0.5 * SIGMA_S8 * 0.9 * ((273.15 + Tsky)^4 - (273.15 + TSO395_S8)^4)"
    " + AREA395_S8 * (1-0.5) * SIGMA_S8 * 0.9 * ((273.15 + Tamb)^4 - (273.15 + TSO395_S8)^4)"
)


class Py2String(str):
    """IronPython 2 ``str``: the generator calls ``.encode('string-escape')`` on it."""

    def encode(self, encoding="utf-8", errors="strict"):
        if encoding == "string-escape":
            escaped = str.encode(self, "unicode_escape").decode("ascii")
            return Py2String(escaped.replace("'", "\\'"))
        return str.encode(self, encoding, errors)


class DeckWriter:
    def __init__(self):
        self.text = ""

    def write(self, text):
        self.text += text


def read_source():
    return SYSTEM_SOURCE.read_text(encoding="utf-8-sig")


def compile_source(source, namespace, filename=SYSTEM_SOURCE):
    with warnings.catch_warnings():
        # The IronPython 2 sources use unescaped backslashes such as '\w' and '\Output'.
        warnings.simplefilter("ignore")
        code = compile(source, str(filename), "exec")
    exec(code, namespace)
    return namespace


def between(source, start, end):
    first = source.index(start)
    return source[first:source.index(end, first)]


def helper_namespace():
    """The real Type 15 / HAMT solar helper functions of Lizard_System.py."""
    block = between(read_source(), "TYPE15_FIRST_TILTED_OUTPUT = 24", "@timing\ndef printdck():")
    return compile_source(block, {"re": re})


def optional_helpers():
    """The helper functions if the generator has them (the renders below also run against the code before this change)."""
    try:
        helpers = helper_namespace()
    except ValueError:
        return {}
    return {key: value for key, value in helpers.items() if key.startswith(("get", "TYPE15"))}


def load_template_lines():
    source = TEMPLATE_SOURCE.read_text(encoding="utf-8-sig")
    scriptcontext = ModuleType("scriptcontext")
    scriptcontext.doc = None
    scriptcontext.sticky = {}
    namespace = {"ghenv": SimpleNamespace(Component=SimpleNamespace()), "Tsoil": "20"}
    with mock.patch.dict(sys.modules, {"scriptcontext": scriptcontext}):
        compile_source(source, namespace, TEMPLATE_SOURCE)
    return namespace["DckTemplate"]


def hamt_block_lines(template_lines):
    start = next(i for i, line in enumerate(template_lines) if "@s7#" in line)
    end = next(i for i, line in enumerate(template_lines) if "@e7#" in line)
    return template_lines[start + 1:end]


def make_surface(number, boundarycond, orientation="S_0_90", boundarytemp="INPUT 1*TAIR_@ANAME", construction="HHL_Wall",
                 surface_type="WALL", area=8.0):
    return SimpleNamespace(
        Surfnum=number,
        Area=area,
        Boundarycond=boundarycond,
        Boundarytemp=boundarytemp,
        Construction=construction,
        Fsky=0.5,
        Filemat="GKP.idf",
        Orientation=orientation,
        Type=surface_type,
    )


def make_zone(name, surfaces):
    airnode = SimpleNamespace(
        Name=name,
        Ecalsurfaces=[s.Surfnum for s in surfaces if s.Boundarycond in ("EXTCALEXT", "EXTCALBND")],
        Surfaces=surfaces,
    )
    return SimpleNamespace(Airnode=airnode)


def render_hamt_block(template_lines, zones, walls_def, variables=None):
    """Execute the real ``e7`` handler of Lizard_System.py and return the rendered deck text."""
    writer = DeckWriter()
    namespace = {
        "re": re,
        "str": Py2String,
        "variables": {} if variables is None else variables,
        "zone": zones,
        "walls_def": walls_def,
        "blockdata": hamt_block_lines(template_lines),
        "dckout": writer,
        "t395_udepth": None,
        "t395_udivnum": 30,
    }
    namespace.update(optional_helpers())
    block = dedent(between(
        read_source(),
        "                    variables['unitno']   = 800\n                    unit395_counter = 200",
        "                if 'e8' in  match_search.group(0):",
    ))
    compile_source(block, namespace)
    return writer.text


def render_weather_reader(weather_file, zones, turn=0):
    """Execute the real weather-reader block of Lizard_System.py; returns (variables, runtime messages)."""
    messages = []
    variables = {}
    namespace = {
        "re": re,
        "variables": variables,
        "zone": zones,
        "Turn": turn,
        "weather_file": weather_file,
        "weather_file_name": weather_file.split("\\")[-1],
        "w": "WARNING",
        "ghenv": SimpleNamespace(Component=SimpleNamespace(AddRuntimeMessage=lambda level, text: messages.append((level, text)))),
    }
    namespace.update(optional_helpers())
    block = between(
        read_source(),
        "            variables['weatherfile']    = weather_file_name\n",
        "            variables['stadiacrossarea'] = 4000\n",
    )
    # IronPython 2 keeps an unknown escape such as "\User Format" as it is; Python 3 rejects "\U" unless the backslash is doubled
    compile_source("if True:\n" + block.replace("\\U", "\\\\U"), namespace)
    return variables, messages


def render_radiation_equations(zones, variables):
    """Execute the real 'Solar' equation block generation (IT_<ori>, IB_<ori>, ID_<ori>) of Lizard_System.py."""
    namespace = {
        "zone": zones,
        "variables": variables,
        "extwsurforicoll": [],
        "coll_ext_walls": [],
    }
    namespace.update(optional_helpers())
    block = between(
        read_source(),
        "            for zone_item in zone:\n                coll_ext_walls.extend(zone_item.Airnode.Extwallsurfacesori)",
        "                for items in zone_item.Airnode.Winsurfaces:\n",
    )
    compile_source("if True:\n" + block, namespace)
    return variables


def equation_blocks(deck_text):
    """(declared count, {name: expression}, [names in order], [Type 395 input names]) for every rendered HAMT block."""
    blocks = []
    lines = deck_text.splitlines()
    i = 0
    while i < len(lines):
        header = re.match(r"^EQUATIONS\s+(\d+)", lines[i])
        if header is None:
            i += 1
            continue
        equations = {}
        order = []
        i += 1
        while not lines[i].startswith("UNIT"):
            assignment = re.match(r"^\s*([A-Za-z_]\w*)\s*=\s*(.*?)\s*$", lines[i])
            if assignment is not None and not lines[i].lstrip().startswith("*"):
                order.append(assignment.group(1))
                equations[assignment.group(1)] = assignment.group(2)
            i += 1
        while not lines[i].startswith("INPUTS"):
            i += 1
        count = int(lines[i].split()[1])
        inputs = [re.split(r"[\s!]", lines[i + 1 + k].strip())[0] for k in range(count)]
        blocks.append((int(header.group(1)), equations, order, inputs))
    return blocks


def evaluate(expression, **values):
    """Evaluate a TRNSYS equation right-hand side; ``[15,25]`` is read from the value ``T15_25``."""
    expression = re.sub(r"\[15,(\d+)\]", r"T15_\1", expression)
    return eval(expression.replace("^", "**"), {"__builtins__": {}}, values)


class Type15TiltedSurfaceHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helpers = helper_namespace()

    def tilted(self, orientation, turn=0):
        return self.helpers["getType15TiltedSurface"](orientation, turn)

    def test_orientation_names_become_type15_slope_and_azimuth(self):
        # Type 15 azimuth: 0 facing the equator, 90 west, -90 east, 180 pole-ward (the TRNSYS convention of the orientation names)
        for orientation, expected in (
            ("S_0_90", (90.0, 0.0)),
            ("W_90_90", (90.0, 90.0)),
            ("N_180_90", (90.0, 180.0)),
            ("E_270_90", (90.0, -90.0)),
            ("S_315_90", (90.0, -45.0)),
            ("S_45_30", (30.0, 45.0)),
            ("H_0_0", (0.0, 0.0)),
            ("H_0_180", (180.0, 0.0)),
        ):
            with self.subTest(orientation=orientation):
                self.assertEqual(expected, self.tilted(orientation))

    def test_building_turn_rotates_the_surface_like_type56_rotates_the_solar_azimuth(self):
        # Type 56 receives AAZM - TURN, so a surface of orientation azimuth a sees the sun like a real surface of azimuth a + TURN
        self.assertEqual((90.0, 45.0), self.tilted("S_0_90", 45))
        self.assertEqual((90.0, 135.0), self.tilted("W_90_90", 45))
        self.assertEqual((90.0, -135.0), self.tilted("N_180_90", 45))
        self.assertEqual((90.0, 0.0), self.tilted("E_270_90", 90))
        self.assertEqual((90.0, -45.0), self.tilted("S_0_90", -45))

    def test_names_outside_the_standard_format_are_rejected(self):
        for orientation in ("SOUTH", "S_0", "S_0_190", "", None, "S__90", "0_0_90"):
            with self.subTest(orientation=orientation):
                self.assertIsNone(self.tilted(orientation))

    def test_type15_output_numbers_follow_the_layout_seen_in_the_type15_output_list(self):
        output = self.helpers["getType15TiltedOutput"]
        # Probe run with 5 tilted surfaces (horizontal, S, W, N, E): total 24..28, beam 29..33, sky 34..38, ground 39..43,
        # total diffuse 44..48, incidence angle 49..53, slope 54..58, azimuth 59..63 (slope/azimuth read back from the run)
        self.assertEqual(24, output(0, 1, 5))
        self.assertEqual(25, output(0, 2, 5))
        self.assertEqual(30, output(1, 2, 5))
        self.assertEqual(35, output(2, 2, 5))
        self.assertEqual(40, output(3, 2, 5))
        self.assertEqual(45, output(4, 2, 5))
        self.assertEqual(55, output(6, 2, 5))
        self.assertEqual(63, output(7, 5, 5))
        # with the horizontal plane and one orientation only
        self.assertEqual(25, output(0, 2, 2))
        self.assertEqual(27, output(1, 2, 2))
        self.assertEqual(33, output(4, 2, 2))

    def test_extra_type15_parameter_lines(self):
        lines_for = self.helpers["getType15TiltedLines"]
        self.assertEqual((9, 1, ""), lines_for([]))
        npar, nsurf, text = lines_for([("S_0_90", 90.0, 0.0), ("E_270_90", 90.0, -90.0)])
        self.assertEqual((15, 3), (npar, nsurf))
        self.assertEqual(
            "1\t\t! 10 Tracking mode (exterior solar of the HAMT walls of orientation S_0_90)\n"
            "90\t\t! 11 Slope of surface\n"
            "0\t\t! 12 Azimuth of surface\n"
            "1\t\t! 13 Tracking mode (exterior solar of the HAMT walls of orientation E_270_90)\n"
            "90\t\t! 14 Slope of surface\n"
            "-90\t\t! 15 Azimuth of surface\n",
            text,
        )

    def test_hamt_solar_orientations_are_unique_ordered_and_only_from_extcalext_walls(self):
        orientations = self.helpers["getHamtSolarOrientations"]
        zones = [
            make_zone("A1", [
                make_surface(8, "EXTCALEXT", "S_0_90"),
                make_surface(4, "EXTERNAL", "E_270_90", surface_type="WINDOW"),
                make_surface(9, "EXTCALBND", "W_90_90"),
                make_surface(10, "EXTERNAL", "N_180_90"),
                make_surface(11, "EXTCALEXT", "W_90_90", construction="Virtual_Wall"),
            ]),
            make_zone("A2", [
                make_surface(20, "EXTCALEXT", "W_90_90"),
                make_surface(21, "EXTCALEXT", "S_0_90"),
                make_surface(22, "EXTCALEXT", "H_0_0", surface_type="ROOF"),
            ]),
        ]
        self.assertEqual(["S_0_90", "W_90_90", "H_0_0"], orientations(zones))
        self.assertEqual([], orientations([make_zone("A1", [make_surface(9, "EXTCALBND"), make_surface(10, "EXTERNAL")])]))


class WeatherReaderTiltedSurfaceTests(unittest.TestCase):
    EPW = "C:\\Weather\\Munich.epw"

    def din_zones(self):
        return [make_zone("A1", [
            make_surface(8, "EXTCALEXT", "S_0_90"),
            make_surface(9, "EXTCALBND", "W_90_90"),
        ])]

    def test_type15_block_is_unchanged_without_extcalext_walls(self):
        for zones in ([], [make_zone("A1", [make_surface(10, "EXTERNAL"), make_surface(9, "EXTCALBND")])]):
            with self.subTest(zones=len(zones)):
                variables, messages = render_weather_reader(self.EPW, zones)
                self.assertEqual(TYPE15_BLOCK_WITHOUT_TILTED_SURFACES, variables["weather_data_reader"])
                self.assertEqual({}, variables["hamt_solar_output"])
                self.assertEqual(1, variables["hamt_solar_nsurf"])
                self.assertEqual([], messages)

    def test_one_tilted_surface_per_extcalext_orientation_is_added_after_the_horizontal_plane(self):
        zones = self.din_zones() + [make_zone("A2", [
            make_surface(20, "EXTCALEXT", "E_270_90"),
            make_surface(21, "EXTCALEXT", "S_0_90"),
        ])]
        variables, messages = render_weather_reader(self.EPW, zones)
        block = variables["weather_data_reader"]

        self.assertEqual([], messages)
        self.assertIn("PARAMETERS 15\n", block)
        self.assertIn("3\t\t! 6 Number of surfaces\n", block)
        self.assertTrue(block.endswith(
            "0\t\t! 9 Azimuth of surface\n"
            "1\t\t! 10 Tracking mode (exterior solar of the HAMT walls of orientation S_0_90)\n"
            "90\t\t! 11 Slope of surface\n"
            "0\t\t! 12 Azimuth of surface\n"
            "1\t\t! 13 Tracking mode (exterior solar of the HAMT walls of orientation E_270_90)\n"
            "90\t\t! 14 Slope of surface\n"
            "-90\t\t! 15 Azimuth of surface\n"
        ))
        # surface 1 is the horizontal plane, so the orientations are surfaces 2 and 3
        self.assertEqual({"S_0_90": 2, "E_270_90": 3}, variables["hamt_solar_output"])
        self.assertEqual(3, variables["hamt_solar_nsurf"])
        # the links to the weather data that every deck uses are below the tilted-surface outputs and unchanged
        self.assertEqual(("15,16", "15,17", "15,18", "15,19", "15,20"), tuple(
            variables[key] for key in ("azen_link", "aazm_link", "ith_link", "ibh_link", "idh_link")))

    def test_building_turn_is_applied_to_the_type15_azimuth(self):
        variables, _ = render_weather_reader(self.EPW, self.din_zones(), turn=45)

        self.assertIn("45\t\t! 12 Azimuth of surface\n", variables["weather_data_reader"])

    def test_tmy2_and_tmy3_files_use_the_same_parameter_layout(self):
        for weather_file, file_type in (("C:\\W\\x.tm2", "2"), ("C:\\W\\x.tmy3", "7")):
            with self.subTest(weather_file=weather_file):
                variables, _ = render_weather_reader(weather_file, self.din_zones())
                self.assertIn("PARAMETERS 12\n" + file_type + "\t\t! 1 File Type\n", variables["weather_data_reader"])
                self.assertEqual({"S_0_90": 2}, variables["hamt_solar_output"])

    def test_unparsable_orientation_is_reported_and_gets_no_tilted_surface(self):
        zones = [make_zone("A1", [make_surface(8, "EXTCALEXT", "SOUTH"), make_surface(9, "EXTCALEXT", "W_90_90")])]
        variables, messages = render_weather_reader(self.EPW, zones)

        self.assertEqual({"W_90_90": 2}, variables["hamt_solar_output"])
        self.assertEqual(1, len(messages))
        self.assertIn("SOUTH", messages[0][1])
        self.assertIn("PARAMETERS 12\n", variables["weather_data_reader"])

    def test_weather_readers_without_type15_tilted_surface_support_warn_and_map_nothing(self):
        for weather_file in ("C:\\W\\TRY2015_x.dat", "C:\\W\\user_format.csv"):
            with self.subTest(weather_file=weather_file):
                variables, messages = render_weather_reader(weather_file, self.din_zones())
                self.assertEqual({}, variables["hamt_solar_output"])
                self.assertEqual(1, len(messages))
                self.assertIn("EPW, TMY2 or TMY3", messages[0][1])
                variables, messages = render_weather_reader(weather_file, [])
                self.assertEqual([], messages)


class ExtcalextSolarGainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template_lines = load_template_lines()

    def render(self, zones, walls_def=None, variables=None):
        walls_def = walls_def or {"HHL_Wall": SimpleNamespace(Hback="64.0", Abs_back="0.7", Eps_back="0.9")}
        text = render_hamt_block(self.template_lines, zones, walls_def, variables)
        surfaces = [s for z in zones for s in z.Airnode.Surfaces if s.Boundarycond in ("EXTCALEXT", "EXTCALBND")]
        return text, {s.Surfnum: block for s, block in zip(surfaces, equation_blocks(text))}

    def din_zones(self):
        return [make_zone("A1", [
            make_surface(8, "EXTCALEXT", "S_0_90"),
            make_surface(9, "EXTCALBND", "W_90_90"),
            make_surface(10, "EXTCALBND", "N_180_90"),
            make_surface(11, "EXTCALBND", "E_270_90"),
        ])]

    def din_variables(self):
        return {"hamt_solar_output": {"S_0_90": 2}, "hamt_solar_nsurf": 2}

    def test_solar_term_is_the_type15_radiation_of_the_wall_orientation_times_the_exterior_absorptance(self):
        _, blocks = self.render(self.din_zones(), variables=self.din_variables())

        self.assertEqual(
            "AREA395_S8 * [15,25] * 0.7 + " + LONGWAVE_ONLY_QWG2,
            blocks[8][1]["qWG2_S8"],
        )

    def test_type56_incident_radiation_of_the_boundary_wall_is_no_longer_used(self):
        # IT_S8 of a BOUNDARY-type wall is 0 for the whole year: any term built on it is a dead term
        _, blocks = self.render(self.din_zones(), variables=self.din_variables())

        self.assertNotIn("IT_S8", blocks[8][1]["qWG2_S8"])

    def test_clear_summer_noon_gives_a_positive_gain_even_though_type56_reports_zero_incident_radiation(self):
        # South wall, 8 m2, noon in July: about 1800 kJ/(h m2) incident, sky 10 C, air 25 C, wall surface 40 C (qWG2 in kJ/h into the wall)
        _, blocks = self.render(self.din_zones(), variables=self.din_variables())
        expression = blocks[8][1]["qWG2_S8"]
        sigma = 2.041e-07
        conditions = dict(AREA395_S8=8.0, SIGMA_S8=sigma, Tsky=10.0, Tamb=25.0, TSO395_S8=40.0)

        with_sun = evaluate(expression, T15_25=1800.0, **conditions)
        without_sun = evaluate(expression, T15_25=0.0, **conditions)

        self.assertAlmostEqual(8.0 * 1800.0 * 0.7, with_sun - without_sun, places=6)
        self.assertGreater(with_sun, 0.0)   # the old deck had only the (negative) longwave term: -631 kJ/h at noon in the Sep-23 run
        self.assertLess(without_sun, 0.0)

    def test_absorptance_comes_from_abs_back_of_the_construction(self):
        for abs_back in ("0.45", 0.3, "0.92"):
            with self.subTest(abs_back=abs_back):
                walls_def = {"HHL_Wall": SimpleNamespace(Hback="64.0", Abs_back=abs_back, Eps_back="0.9")}
                _, blocks = self.render(self.din_zones(), walls_def, self.din_variables())
                expression = blocks[8][1]["qWG2_S8"]
                sigma = 2.041e-07
                gain = evaluate(expression, T15_25=1000.0, AREA395_S8=8.0, SIGMA_S8=sigma, Tsky=20.0, Tamb=20.0, TSO395_S8=20.0)
                self.assertAlmostEqual(8.0 * 1000.0 * float(abs_back), gain, places=6)

    def test_longwave_emissivity_comes_from_eps_back_of_the_construction(self):
        sigma = 2.041e-07
        for eps_back in ("0.85", 0.6, "1"):
            with self.subTest(eps_back=eps_back):
                walls_def = {"HHL_Wall": SimpleNamespace(Hback="64.0", Abs_back="0.7", Eps_back=eps_back)}
                _, blocks = self.render(self.din_zones(), walls_def, self.din_variables())
                expression = blocks[8][1]["qWG2_S8"]
                # no sun; sky 0 C, air 10 C, wall 5 C, Fsky 0.5: sigma eps A [0.5 (Tsky^4 - Tso^4) + 0.5 (Tamb^4 - Tso^4)]
                gain = evaluate(expression, T15_25=0.0, AREA395_S8=8.0, SIGMA_S8=sigma, Tsky=0.0, Tamb=10.0, TSO395_S8=5.0)
                expected = 8.0 * sigma * float(eps_back) * (
                    0.5 * (273.15 ** 4 - 278.15 ** 4) + 0.5 * (283.15 ** 4 - 278.15 ** 4))
                self.assertAlmostEqual(expected, gain, places=6)

    def test_missing_or_unusable_eps_back_falls_back_to_0_9(self):
        for walls_def in (
            {"HHL_Wall": SimpleNamespace(Hback="64.0", Abs_back="0.7")},
            {"HHL_Wall": SimpleNamespace(Hback="64.0", Abs_back="0.7", Eps_back=None)},
            {"HHL_Wall": SimpleNamespace(Hback="64.0", Abs_back="0.7", Eps_back="")},
        ):
            with self.subTest(walls_def=walls_def["HHL_Wall"].__dict__):
                _, blocks = self.render(self.din_zones(), walls_def, self.din_variables())
                self.assertEqual("AREA395_S8 * [15,25] * 0.7 + " + LONGWAVE_ONLY_QWG2, blocks[8][1]["qWG2_S8"])

    def test_each_orientation_reads_its_own_type15_surface_also_across_zones(self):
        zones = self.din_zones() + [make_zone("A2", [
            make_surface(20, "EXTCALEXT", "E_270_90"),
            make_surface(21, "EXTCALEXT", "S_0_90"),
        ])]
        variables = {"hamt_solar_output": {"S_0_90": 2, "E_270_90": 3}, "hamt_solar_nsurf": 3}
        _, blocks = self.render(zones, variables=variables)

        self.assertIn("AREA395_S8 * [15,25] * 0.7 + ", blocks[8][1]["qWG2_S8"])
        self.assertIn("AREA395_S20 * [15,26] * 0.7 + ", blocks[20][1]["qWG2_S20"])
        self.assertIn("AREA395_S21 * [15,25] * 0.7 + ", blocks[21][1]["qWG2_S21"])

    def test_wall_without_a_mapped_type15_surface_has_no_solar_term(self):
        for variables in ({}, {"hamt_solar_output": {}, "hamt_solar_nsurf": 1}, {"hamt_solar_output": {"W_90_90": 2}, "hamt_solar_nsurf": 2}):
            with self.subTest(variables=variables):
                _, blocks = self.render(self.din_zones(), variables=dict(variables))
                self.assertEqual(LONGWAVE_ONLY_QWG2, blocks[8][1]["qWG2_S8"])

    def test_inner_walls_and_the_other_extcalext_equations_are_not_touched(self):
        _, blocks = self.render(self.din_zones(), variables=self.din_variables())
        equations = blocks[8][1]

        self.assertEqual("64.0", equations["hconv2_S8"])
        self.assertEqual("Tamb", equations["TB2_S8"])
        self.assertEqual("Rh_amb", equations["RH2_S8"])
        self.assertEqual("0.000000007*hconv2_S8/3.6", equations["beta2_S8"])
        for number in (9, 10, 11):
            self.assertNotIn("[15,", blocks[number][1]["qWG2_S%d" % number])
            # the boundary of the inner walls is the room (mirror: air and radiant temperature of the zone), never the weather;
            # the exact side-2 film of these walls is pinned in test_type395_side2_boundary.py
            tb2 = blocks[number][1]["TB2_S%d" % number]
            self.assertIn("TAIR_A1", tb2)
            self.assertNotIn("Tamb", tb2)

    def test_equation_counts_and_names_are_unchanged(self):
        # no equation is added (the Type 15 output is written inline as [15,k]), so the declared count still equals the assignments
        text, blocks = self.render(self.din_zones(), variables=self.din_variables())
        _, blocks_without_solar = self.render(self.din_zones(), variables={})

        self.assertNotIn("@", text)
        names = [name for (_, _, order, _) in blocks.values() for name in order]
        self.assertEqual(len(names), len(set(names)))
        for number, (declared, equations, order, inputs) in blocks.items():
            with self.subTest(surface=number):
                self.assertEqual(declared, len(order))
                self.assertEqual("qWG2_S%d" % number, inputs[7])   # Type 395 input 8 is qWG2
                self.assertEqual(blocks_without_solar[number][2], order)   # the solar term adds no equation and no name
                self.assertEqual(blocks_without_solar[number][0], declared)

    def test_referenced_type15_output_exists_in_the_generated_weather_block(self):
        # The e7 handler and the weather reader must agree: render both for the same zones
        zones = self.din_zones() + [make_zone("A2", [make_surface(20, "EXTCALEXT", "W_90_90"), make_surface(21, "EXTCALEXT", "H_0_0")])]
        variables, _ = render_weather_reader("C:\\Weather\\Munich.epw", zones)
        block = variables["weather_data_reader"]
        nsurf = int(re.search(r"^(\d+)\t\t! 6 Number of surfaces$", block, re.M).group(1))
        npar = int(re.search(r"^PARAMETERS (\d+)$", block, re.M).group(1))
        _, blocks = self.render(zones, variables=variables)

        self.assertEqual(4, nsurf)
        self.assertEqual(6 + 3 * nsurf, npar)
        declared = re.findall(r"^[-\d.]+\t\t! (\d+) (?:Tracking mode|Slope of surface|Azimuth of surface)", block, re.M)
        self.assertEqual(3 * nsurf, len(declared))
        for surface_number, tilted_surface in ((8, 2), (20, 3), (21, 4)):
            expression = blocks[surface_number][1]["qWG2_S%d" % surface_number]
            output = int(re.search(r"\[15,(\d+)\]", expression).group(1))
            self.assertEqual(23 + tilted_surface, output)
            self.assertLessEqual(output, 23 + nsurf)   # inside the block of "total radiation on tilted surface i"


class RadiationEquationTests(unittest.TestCase):
    """The 'Solar' equations IT_<ori>, IB_<ori>, ID_<ori> [W/m2] that feed the Irradiation plotter."""

    def zones(self, extcalext_first=True):
        surfaces = [make_surface(8, "EXTCALEXT", "S_0_90"), make_surface(12, "EXTERNAL", "W_90_90")]
        airnode = SimpleNamespace(
            Name="A1",
            Surfaces=surfaces,
            Extwallsurfaces=[8, 12],
            Extwallsurfacesori=["S_0_90", "W_90_90"],
            Winsurfaces=[],
        )
        return [SimpleNamespace(Airnode=airnode)]

    def test_hamt_representative_uses_the_type15_radiation_of_its_orientation(self):
        variables = {"radnr": 2, "radoutputs": "", "hamt_solar_output": {"S_0_90": 2}, "hamt_solar_nsurf": 2}
        render_radiation_equations(self.zones(), variables)
        lines = variables["radoutputs"].splitlines()

        # Extwallsurfaces is reversed by this block (as before): the W wall comes first
        self.assertEqual("IT_W_90_90 = IT_S12/(3.6*AREA_S12+0.00000001)", lines[0])
        self.assertEqual(
            ["IT_S_0_90 = [15,25]/3.6", "IB_S_0_90 = [15,27]/3.6", "ID_S_0_90 = [15,33]/3.6"],
            lines[3:6],
        )
        self.assertEqual(8, variables["radnr"])

    def test_without_a_mapped_type15_surface_the_old_type56_equations_are_kept(self):
        variables = {"radnr": 2, "radoutputs": "", "hamt_solar_output": {}, "hamt_solar_nsurf": 1}
        render_radiation_equations(self.zones(), variables)

        self.assertEqual(
            ["IT_S_0_90 = IT_S8/(3.6*AREA_S8+0.00000001)", "IB_S_0_90 = IB_S8/(3.6*AREA_S8+0.00000001)",
             "ID_S_0_90 = ID_S8/(3.6*AREA_S8+0.00000001)"],
            variables["radoutputs"].splitlines()[3:6],
        )


if __name__ == "__main__":
    unittest.main()
