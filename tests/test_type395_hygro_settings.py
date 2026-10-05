"""Per-surface Type 395 settings from Lizard_Hygro: write_report, report_interval, add_heat_depth, add_heat, layer_min_div.

Type 395 (trnsys-hamt-rs, trnsys_type.rs ``validate_parameters``) reads its PARAMETERS 1-based as written in the deck:
5 = user-defined depth [m] (``params[4]``), 6 = write report (``params[5] > 0``), 7 = report interval [h] (``params[6]``,
rounded to 1e-4 h), 9 = n_div, the MINIMUM number of cells per material layer (``params[8]``).  Input 11 is
``QheatKJ_S<n>`` [kJ/h], the TOTAL heat of the wall that hamt-core puts into the cell at the user-defined depth
(``surface/step_jacobi.rs`` ``cell_sources``: multiplied by the interpolation weights of that cell, not by the area), so the
template writes it as a specific load [W per m2 of wall] * AREA395 * 3.6.

Defaults (inputs not connected, or surfaces of an older Lizard_Component without the attributes) must give the deck of
before these inputs existed: with the DCK template of before this change byte for byte, with the new template the same
values (only the comments of the PARAMETERS lines are new).  The real ``@s7#...@e7#`` template block, the real ``e7``
handler and the real ``qaddon`` block of ``getzonevariables`` of ``Lizard_System.py`` and the real ``Lizard_Hygro.py``
component are executed with mock objects (no Grasshopper, no TRNSYS).
"""

import contextlib
import io
import re
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_type395_side2_boundary import (  # noqa: E402
    SYSTEM_SOURCE,
    DeckWriter,
    Py2String,
    equation_blocks,
    execute_source_block,
    hamt_block_lines,
    load_template_lines,
    make_surface,
    render_hamt_block,
    run_source,
)
from test_updater_io_sync import load_updater  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
HYGRO_SOURCE = REPO_ROOT / "Lizard_Hygro.py"
COMPONENT_SOURCE = REPO_ROOT / "Lizard_Component.py"

# The ten PARAMETERS lines of the Type 395 block in the DCK template of d2a3ce8 (before this change), byte for byte.
# Existing Grasshopper definitions keep this template until the DCK template component is reloaded/updated.
OLD_PARAMETER_LINES = [
    "1\t\t! 1 number of wall layers\n",
    "AREA395_S@surface   ! 2 surface area\n",
    "@lu1\t! 3 logical unit cp-data file heat up\n",
    "20 !initial wall temperature     \n",
    "@udefdepth ! 4 user defined cell depth for additional heat load and output\n",
    "1 !print reports yes/no, 1/0\n",
    "1 !printing interval of results\n",
    "@unit395 !id for prefix of output filenames\n",
    "@udivnum\n",
    "1  ! 1=Use BlockTridiagonal Solver\n",
]

# What the generator of d2a3ce8 wrote for surface 9 of render_hamt_block([make_surface(9, "EXTCALBND")]) (t395_udepth not
# set, t395_udivnum = 30): QheatKJ, the UNIT line and the PARAMETERS block, byte for byte.
OLD_RENDERED_S9 = (
    "QheatKJ_S9   = -Q_al_A1*AREA_A1/Area_al1_A1*AREA395_S9*3.6\n"
    "UNIT 200 TYPE 395\t Type395\n"
    "PARAMETERS 10\n"
    "1\t\t! 1 number of wall layers\n"
    "AREA395_S9   ! 2 surface area\n"
    "800\t! 3 logical unit cp-data file heat up\n"
    "20 !initial wall temperature     \n"
    "0.02 ! 4 user defined cell depth for additional heat load and output\n"
    "1 !print reports yes/no, 1/0\n"
    "1 !printing interval of results\n"
    "200 !id for prefix of output filenames\n"
    "30\n"
    "1  ! 1=Use BlockTridiagonal Solver\n"
)

DEFAULT_QHEAT = "-Q_al_A1*AREA_A1/Area_al1_A1*AREA395_S{0}*3.6"


def parameter_section(lines):
    """(first, last + 1) line indices of the ten PARAMETERS lines of the (only or first) Type 395 block in ``lines``."""
    start = next(i for i, line in enumerate(lines) if line.startswith("PARAMETERS 10")) + 1
    return start, start + 10


def old_template_block(template_lines):
    """The Type 395 block of the current template with its PARAMETERS lines as in the template of d2a3ce8."""
    block = list(hamt_block_lines(template_lines))
    start, end = parameter_section(block)
    block[start:end] = OLD_PARAMETER_LINES
    return block


def type395_parameters(deck_text):
    """{unit number: [the ten PARAMETERS values (text before '!')]} of every Type 395 block of the rendered deck text."""
    lines = deck_text.splitlines()
    result = {}
    for i, line in enumerate(lines):
        unit = re.match(r"^UNIT\s+(\d+)\s+TYPE\s+395\b", line)
        if unit is None:
            continue
        j = next(k for k in range(i, len(lines)) if lines[k].startswith("PARAMETERS"))
        count = int(lines[j].split()[1])
        result[int(unit.group(1))] = [lines[j + 1 + k].split("!")[0].strip() for k in range(count)]
    return result


def hamt_surface(number, boundarycond="EXTCALBND", **settings):
    """A HAMT surface as the zone hands it to the e7 handler, with the Lizard_Hygro attributes given in ``settings``."""
    surface = make_surface(number, boundarycond)
    for name, value in settings.items():
        setattr(surface, name, value)
    return surface


class Type395TemplateDefaultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template_lines = load_template_lines()
        cls.walls_def = {"HHL_Wall": SimpleNamespace(Hback="64.0", Abs_back="0.7")}

    def render(self, surfaces, block=None, messages=None, namespace_out=None):
        return render_hamt_block(
            self.template_lines, surfaces, self.walls_def, block=block, messages=messages, namespace_out=namespace_out
        )

    def din_surfaces(self):
        return [hamt_surface(8, "EXTCALEXT"), hamt_surface(9), hamt_surface(10), hamt_surface(11)]

    def test_old_template_with_default_inputs_gives_the_deck_of_before_byte_for_byte(self):
        messages = []
        text = self.render([make_surface(9, "EXTCALBND")], block=old_template_block(self.template_lines), messages=messages)

        start = text.index("QheatKJ_S9   =")
        self.assertEqual(OLD_RENDERED_S9, text[start:text.index("\n\nINPUTS", start) + 1])
        self.assertEqual([], messages)
        self.assertNotIn("@", text)

    def test_new_template_with_default_inputs_changes_only_the_comments_of_the_parameter_lines(self):
        old = self.render(self.din_surfaces(), block=old_template_block(self.template_lines)).splitlines()
        new = self.render(self.din_surfaces()).splitlines()
        parameter_lines = set()
        for i, line in enumerate(new):
            if line.startswith("PARAMETERS 10"):
                parameter_lines.update(range(i + 1, i + 11))

        self.assertEqual(4 * 10, len(parameter_lines))
        self.assertEqual(len(old), len(new))
        changed = {i for i, (a, b) in enumerate(zip(old, new)) if a != b}
        self.assertTrue(changed)
        self.assertEqual(set(), changed - parameter_lines)
        for i in sorted(parameter_lines):
            with self.subTest(old=old[i], new=new[i]):
                # same value in front of the '!' comment
                self.assertEqual(old[i].split("!")[0].strip(), new[i].split("!")[0].strip())

    def test_new_template_defaults_are_the_values_of_before(self):
        text = self.render(self.din_surfaces())
        parameters = type395_parameters(text)

        self.assertEqual([200, 201, 202, 203], sorted(parameters))
        for unit, number in zip((200, 201, 202, 203), (8, 9, 10, 11)):
            with self.subTest(surface=number):
                self.assertEqual(
                    ["1", "AREA395_S%d" % number, str(800 + unit - 200), "20", "0.02", "1", "1", str(unit), "30", "1"],
                    parameters[unit],
                )
        blocks = {number: block for number, block in zip((8, 9, 10, 11), equation_blocks(text))}
        for number in (8, 9, 10, 11):
            self.assertEqual(DEFAULT_QHEAT.format(number), blocks[number][1]["QheatKJ_S%d" % number])
        self.assertNotIn("@", text)

    def test_system_inputs_t395_udepth_and_t395_udivnum_are_still_the_defaults(self):
        surfaces = [hamt_surface(9), hamt_surface(10, Addheatdepth=0.005, Layermindiv=4)]
        writer = DeckWriter()
        namespace = {
            "re": re, "str": Py2String, "variables": {}, "dckout": writer,
            "zone": [SimpleNamespace(Airnode=SimpleNamespace(Name="A1", Ecalsurfaces=[9, 10], Surfaces=surfaces))],
            "walls_def": self.walls_def, "blockdata": hamt_block_lines(self.template_lines),
            "t395_udepth": 0.04, "t395_udivnum": 12,   # the System inputs of the same name
        }
        execute_source_block(
            SYSTEM_SOURCE.read_text(encoding="utf-8-sig"),
            "                    variables['unitno']   = 800\n                    unit395_counter = 200",
            "                if 'e8' in  match_search.group(0):",
            namespace,
        )
        parameters = type395_parameters(writer.text)

        self.assertEqual("0.04", parameters[200][4])   # System input, Lizard_Hygro not set
        self.assertEqual("12", parameters[200][8])
        self.assertEqual("0.005", parameters[201][4])  # Lizard_Hygro wins over the System input
        self.assertEqual("4", parameters[201][8])

    def test_parameter_comments_are_numbered_one_to_ten_and_name_the_type395_meaning(self):
        block = hamt_block_lines(self.template_lines)
        start, end = parameter_section(block)
        lines = block[start:end]

        for number, line in enumerate(lines, 1):
            with self.subTest(parameter=number, line=line):
                self.assertRegex(line, r"^\S+\s*! %d \S" % number)
        self.assertTrue(lines[4].startswith("@udefdepth "))
        self.assertTrue(lines[5].startswith("@writereport "))
        self.assertTrue(lines[6].startswith("@reportinterval "))
        self.assertTrue(lines[8].startswith("@layer_min_div "))
        self.assertIn("side-2", lines[4])
        self.assertIn("-1", lines[5])
        self.assertIn("minimum", lines[8])
        for line in lines:
            self.assertNotRegex(line, r"[{}]")  # the template text goes through str.format in the DCK template component

    def test_every_placeholder_of_the_block_is_set_for_every_surface(self):
        out = {}
        self.render(self.din_surfaces(), namespace_out=out)
        placeholders = set(re.findall(r"@(\w+)", "".join(hamt_block_lines(self.template_lines))))

        self.assertTrue({"writereport", "reportinterval", "layer_min_div", "udefdepth", "specload"} <= placeholders)
        self.assertEqual(set(), placeholders - set(out["variables"]) - {"d395"})  # d395 lines are skipped with the star link
        # the parameter 9 placeholder of templates written before layer_min_div keeps its value
        self.assertEqual(out["variables"]["layer_min_div"], out["variables"]["udivnum"])


class Type395PerSurfaceSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template_lines = load_template_lines()
        cls.walls_def = {"HHL_Wall": SimpleNamespace(Hback="64.0", Abs_back="0.7")}

    def render(self, surfaces, block=None, messages=None):
        """(deck text, {surface: equation block}, {surface: ten PARAMETERS values}); units 200, 201, ... follow the surfaces."""
        text = render_hamt_block(self.template_lines, surfaces, self.walls_def, block=block, messages=messages)
        blocks = {surface.Surfnum: block for surface, block in zip(surfaces, equation_blocks(text))}
        by_unit = type395_parameters(text)
        parameters = {surface.Surfnum: by_unit[200 + k] for k, surface in enumerate(surfaces)}
        return text, blocks, parameters

    def test_settings_land_in_parameters_5_6_7_9_and_in_qheat(self):
        surfaces = [
            hamt_surface(9, Writereport=True, Reportinterval=0.25, Addheatdepth=0.0125, Addheat="(QWALL_S9/3.6)", Layermindiv=7),
            hamt_surface(10, "EXTCALEXT", Reportinterval=24.0, Addheatdepth=0.1, Addheat=12.5, Layermindiv=3),
        ]
        text, blocks, parameters = self.render(surfaces)

        self.assertEqual(["0.0125", "1", "0.25", "7"], [parameters[9][i] for i in (4, 5, 6, 8)])
        self.assertEqual(["0.1", "1", "24.0", "3"], [parameters[10][i] for i in (4, 5, 6, 8)])
        self.assertEqual("(QWALL_S9/3.6)*AREA395_S9*3.6", blocks[9][1]["QheatKJ_S9"])
        self.assertEqual("12.5*AREA395_S10*3.6", blocks[10][1]["QheatKJ_S10"])
        # QheatKJ is still Type 395 input 11, and no placeholder is left
        self.assertEqual("QheatKJ_S9", blocks[9][3][10])
        self.assertNotIn("@", text)

    def test_write_report_false_gives_minus_one(self):
        _, _, parameters = self.render([hamt_surface(9, Writereport=False), hamt_surface(10, Writereport=True), hamt_surface(11)])

        self.assertEqual("-1", parameters[9][5])
        self.assertEqual("1", parameters[10][5])
        self.assertEqual("1", parameters[11][5])

    def test_settings_of_one_surface_do_not_leak_into_the_next_one(self):
        surfaces = [
            hamt_surface(9, Writereport=False, Reportinterval=0.5, Addheatdepth=0.03, Addheat="(Q9)", Layermindiv=5),
            hamt_surface(10),
        ]
        _, blocks, parameters = self.render(surfaces)

        self.assertEqual(["1", "AREA395_S10", "801", "20", "0.02", "1", "1", "201", "30", "1"], parameters[10])
        self.assertEqual(DEFAULT_QHEAT.format(10), blocks[10][1]["QheatKJ_S10"])

    def test_old_template_still_takes_depth_heat_and_minimum_divisions_per_surface(self):
        # @udefdepth, @specload and @udivnum exist in the template of before: only the report settings need the new template
        surfaces = [hamt_surface(9, Addheatdepth=0.0125, Addheat="(Q9)", Layermindiv=7)]
        messages = []
        text, blocks, parameters = self.render(surfaces, block=old_template_block(self.template_lines), messages=messages)

        self.assertEqual(["0.0125", "1", "1", "7"], [parameters[9][i] for i in (4, 5, 6, 8)])
        self.assertEqual("(Q9)*AREA395_S9*3.6", blocks[9][1]["QheatKJ_S9"])
        self.assertEqual([], messages)

    def test_old_template_with_report_settings_asks_for_a_reload(self):
        for settings in ({"Writereport": False}, {"Reportinterval": 0.5}, {"Writereport": True, "Reportinterval": 2.0}):
            with self.subTest(settings=settings):
                messages = []
                text, _, parameters = self.render(
                    [hamt_surface(9, **settings), hamt_surface(10, **settings)],
                    block=old_template_block(self.template_lines), messages=messages,
                )

                self.assertEqual(1, len(messages))   # once, not per surface
                self.assertEqual("WARNING", messages[0][0])
                for fragment in ("Reload", "DCK template", "write_report", "report_interval"):
                    self.assertIn(fragment, messages[0][1])
                self.assertEqual(["1", "1"], parameters[9][5:7])   # the old template writes its literal 1 and 1
                self.assertNotIn("@", text)

    def test_new_template_with_report_settings_does_not_warn(self):
        messages = []
        self.render([hamt_surface(9, Writereport=False, Reportinterval=0.5)], messages=messages)

        self.assertEqual([], messages)


class QaddonTests(unittest.TestCase):
    """``qaddon`` = add-on heating/cooling demand of the zone (Q_addon_ht/cl -> Q_tot_ht/cl), not a Type 56 input.

    The default QheatKJ is the active-layer specific load of the zone: energy of a TRNLizard system, booked as add-on demand
    of the zone that owns the wall.  A Lizard_Hygro add_heat is a source the user prescribes (a heater, a calibration
    source, ...): it is not booked as demand.  ``getzonevariables(zone_item)`` builds it for one zone; it used to collect the
    HAMT walls of every zone, so in a multi-zone model each zone reported the wall heat of all zones.
    """

    START = "    variables['qaddon']         = '0'\n"
    END = "    #airnode definition"

    def qaddon(self, zone_item, zones):
        namespace = {"variables": {}, "zone": zones, "zone_item": zone_item}
        execute_source_block(SYSTEM_SOURCE.read_text(encoding="utf-8-sig"), self.START, self.END, namespace)
        return namespace["variables"]["qaddon"]

    def zones(self, **settings_of_9):
        a1 = [hamt_surface(8, "EXTCALEXT"), hamt_surface(9, **settings_of_9), make_surface(12, "EXTERNAL")]
        a2 = [hamt_surface(20)]
        a3 = [make_surface(30, "EXTERNAL")]
        return [
            SimpleNamespace(Airnode=SimpleNamespace(Name="A1", Ecalsurfaces=[8, 9], Surfaces=a1)),
            SimpleNamespace(Airnode=SimpleNamespace(Name="A2", Ecalsurfaces=[20], Surfaces=a2)),
            SimpleNamespace(Airnode=SimpleNamespace(Name="A3", Ecalsurfaces=[], Surfaces=a3)),
        ]

    def test_single_zone_is_booked_as_before(self):
        # byte-identical to the generator of before for a model with one zone
        a1 = self.zones()[0]
        self.assertEqual("0-QheatKJ_S8-QheatKJ_S9", self.qaddon(a1, [a1]))
        a1 = self.zones(Writereport=False, Layermindiv=4)[0]
        self.assertEqual("0-QheatKJ_S8-QheatKJ_S9", self.qaddon(a1, [a1]))

    def test_each_zone_books_only_its_own_hamt_walls(self):
        zones = self.zones()
        self.assertEqual("0-QheatKJ_S8-QheatKJ_S9", self.qaddon(zones[0], zones))
        self.assertEqual("0-QheatKJ_S20", self.qaddon(zones[1], zones))
        self.assertEqual("0", self.qaddon(zones[2], zones))

    def test_user_defined_add_heat_is_not_booked_as_add_on_demand(self):
        for add_heat in ("(Q9)", 12.5, 0):
            with self.subTest(add_heat=add_heat):
                zones = self.zones(Addheat=add_heat)
                self.assertEqual("0-QheatKJ_S8", self.qaddon(zones[0], zones))
                self.assertEqual("0-QheatKJ_S20", self.qaddon(zones[1], zones))


class HamtZoneAggregationTests(unittest.TestCase):
    """The other per-zone HAMT sums are built per zone already (pinned here): the humidity gain of the @s8# block and the
    GAIN HAMT_Gain_<zone> of the b18 with its regime line."""

    def test_humidity_gain_of_a_zone_sums_only_its_own_walls(self):
        template_lines = load_template_lines()
        start = next(i for i, line in enumerate(template_lines) if "@s7#" in line)
        end = next(i for i, line in enumerate(template_lines) if "@e7#" in line)
        s8 = next(i for i, line in enumerate(template_lines) if "@s8#" in line)
        e8 = next(i for i, line in enumerate(template_lines) if "@e8#" in line)
        zones = [
            SimpleNamespace(Airnode=SimpleNamespace(Name="A1", Ecalsurfaces=[8, 9],
                                                    Surfaces=[hamt_surface(8, "EXTCALEXT"), hamt_surface(9)])),
            SimpleNamespace(Airnode=SimpleNamespace(Name="A2", Ecalsurfaces=[20], Surfaces=[hamt_surface(20)])),
        ]
        source = SYSTEM_SOURCE.read_text(encoding="utf-8-sig")
        namespace = {
            "re": re, "str": Py2String, "variables": {}, "zone": zones, "dckout": DeckWriter(),
            "walls_def": {"HHL_Wall": SimpleNamespace(Hback="64.0", Abs_back="0.7")},
            "blockdata": template_lines[start + 1:end], "t395_udepth": None, "t395_udivnum": 30,
        }
        execute_source_block(
            source,
            "                    variables['unitno']   = 800\n                    unit395_counter = 200",
            "                if 'e8' in  match_search.group(0):",
            namespace,
        )
        writer = DeckWriter()
        namespace.update({"blockdata": template_lines[s8 + 1:e8], "dckout": writer})
        execute_source_block(
            source,
            "                    for zname395, surfs395 in hamt_zone_surfaces.items():",
            "                if 'emulti1' in  match_search.group(0) and Multizone:",
            namespace,
        )
        sums = dict(re.findall(r"^HamtHumidityGain_KgPerHr_(A\d) = (.*)$", writer.text, re.M))

        self.assertEqual({"A1": "HamtHumidityGain_KgPerHr_S8 + HamtHumidityGain_KgPerHr_S9",
                          "A2": "HamtHumidityGain_KgPerHr_S20"}, sums)

    @staticmethod
    def hamt_gain_helpers(source):
        """The shared HAMT-gain condition of Lizard_System.py if the generator has it (the tests also run against the code before)."""
        try:
            return execute_source_block(source, "HAMT_GAIN_BOUNDARIES = ", "# ---- HAMT gain of a zone (end)", {})
        except ValueError:
            return {}

    @staticmethod
    def airnode(name, surfaces, gains=()):
        """A zone as printbuiZonepart leaves it: Ecalsurfaces = its EXTCALC, BNDCALC, EXTCALEXT and EXTCALBND surfaces."""
        ecal = [s.Surfnum for s in surfaces if s.Boundarycond in ("EXTCALC", "BNDCALC", "EXTCALEXT", "EXTCALBND")]
        return SimpleNamespace(Name=name, Surfaces=surfaces, Ecalsurfaces=ecal, Gain=list(gains))

    def gains_and_regime_lines(self, airnodes):
        """(GAIN HAMT_Gain_* definitions of printbuitoppart, {zone: auto regime line of printbuiZonepart})."""
        source = SYSTEM_SOURCE.read_text(encoding="utf-8-sig")
        namespace = dict(self.hamt_gain_helpers(source), dataset=airnodes, library=SimpleNamespace(Gain=[]), lines=[])
        execute_source_block(
            source,
            "    # Auto-define HAMT gains for zones with EXTCALEXT/EXTCALBND surfaces (multi-HAMT support)",
            "    for item in dataset:\n        for item2 in item.Gain:",
            namespace,
        )
        gains = re.findall(r"GAIN (HAMT_Gain_\w+)\r\n.*HUMIDITY=INPUT 1\*(\w+)", "".join(namespace["lines"]))
        regime = {}
        for airnode in airnodes:
            block = dict(self.hamt_gain_helpers(source), Airnodes=airnode, regimelines="")
            execute_source_block(source, "        hamt_gain_exists = False\n", "        if Airnodes.Comfort:", block)
            regime[airnode.Name] = block["regimelines"]
        return gains, regime

    def test_hamt_gain_and_regime_line_are_per_zone(self):
        gains, regime = self.gains_and_regime_lines([
            self.airnode("A1", [hamt_surface(8, "EXTCALEXT"), make_surface(12, "EXTERNAL")]),
            self.airnode("A2", [make_surface(30, "EXTERNAL")]),
            self.airnode("A3", [hamt_surface(20)]),
        ])

        self.assertEqual([("HAMT_Gain_A1", "HamtHumidityGain_KgPerHr_A1"), ("HAMT_Gain_A3", "HamtHumidityGain_KgPerHr_A3")], gains)
        self.assertEqual("GAIN = HAMT_Gain_A1 : SCALE= 1 : GEOPOS= 0 : SCALE2= 1 : FRAC_REFAREA= -1\r\n", regime["A1"])
        self.assertEqual("", regime["A2"])
        self.assertEqual("GAIN = HAMT_Gain_A3 : SCALE= 1 : GEOPOS= 0 : SCALE2= 1 : FRAC_REFAREA= -1\r\n", regime["A3"])

    def test_zone_with_only_extcalc_or_bndcalc_surfaces_gets_neither_the_gain_nor_its_regime_line(self):
        # EXTCALC/BNDCALC (external calculation) surfaces are in Ecalsurfaces but are no Type 395 walls: no HAMT_Gain definition
        gains, regime = self.gains_and_regime_lines([
            self.airnode("A4", [make_surface(40, "EXTCALC"), make_surface(41, "EXTERNAL")]),
            self.airnode("A5", [make_surface(50, "BNDCALC")]),
            self.airnode("A6", [make_surface(60, "EXTCALC"), hamt_surface(61)]),
        ])

        self.assertEqual([("HAMT_Gain_A6", "HamtHumidityGain_KgPerHr_A6")], gains)
        self.assertEqual({"A4": "", "A5": "", "A6": "GAIN = HAMT_Gain_A6 : SCALE= 1 : GEOPOS= 0 : SCALE2= 1 : FRAC_REFAREA= -1\r\n"},
                         regime)

    def test_zone_that_lists_a_hamt_gain_itself_gets_no_second_regime_line(self):
        _, regime = self.gains_and_regime_lines([
            self.airnode("A1", [hamt_surface(8, "EXTCALEXT")], gains=[SimpleNamespace(Name="HAMT_Gain_A1")]),
        ])
        self.assertEqual({"A1": ""}, regime)


class GeometryDefaultsTests(unittest.TestCase):
    def test_surface_class_carries_the_five_settings_as_none(self):
        source = COMPONENT_SOURCE.read_text(encoding="utf-8-sig")
        block = source[source.index("class GEOMETRY:"):source.index("class AIRNODE:")]
        namespace = run_source(block, COMPONENT_SOURCE, {})
        surface = namespace["GEOMETRY"]()

        for name in ("Writereport", "Reportinterval", "Addheatdepth", "Addheat", "Layermindiv"):
            with self.subTest(attribute=name):
                self.assertIsNone(getattr(surface, name))
        self.assertIsNone(surface.Filemat)


class FakeConstruction:
    """sc.sticky[path]["CONSTRUCTION"] of Lizard_Component, recording what Lizard_Hygro stores per surface."""

    stored = {}

    def addToConstruction(self, breps, guid):
        return breps

    def updateConstructionNew(self, breps, surface):
        pass

    def updateConstruction(self, brep, attribute, value):
        FakeConstruction.stored.setdefault(brep, {})[attribute] = value

    def getWallThickness(self, breps):
        pass

    def callFromConstruction(self, breps):
        return [SimpleNamespace(Filemat=FakeConstruction.stored.get(brep, {}).get("Filemat")) for brep in breps]


def run_hygro(**inputs):
    """Execute the real Lizard_Hygro.py; ``inputs`` are the Grasshopper inputs present on the component (an input port that
    does not exist is simply absent, exactly like in the GhPython script scope).  Returns (stored attributes per brep, messages).
    """
    FakeConstruction.stored = {}
    messages = []
    scriptcontext = ModuleType("scriptcontext")
    scriptcontext.doc = SimpleNamespace(Path="doc.gh")
    scriptcontext.sticky = {
        "doc.gh": {"CONSTRUCTION": FakeConstruction, "library": SimpleNamespace(Walls=[SimpleNamespace(Name="HHL_Wall")])}
    }
    grasshopper = ModuleType("Grasshopper")
    kernel = ModuleType("Grasshopper.Kernel")
    kernel.GH_RuntimeMessageLevel = SimpleNamespace(Warning="WARNING", Error="ERROR")
    grasshopper.Kernel = kernel
    ghpythonlib = ModuleType("ghpythonlib")
    ghpythonlib.components = ModuleType("ghpythonlib.components")
    modules = {
        "rhinoscriptsyntax": ModuleType("rhinoscriptsyntax"), "scriptcontext": scriptcontext, "Rhino": ModuleType("Rhino"),
        "Grasshopper": grasshopper, "Grasshopper.Kernel": kernel,
        "ghpythonlib": ghpythonlib, "ghpythonlib.components": ghpythonlib.components,
    }
    component = SimpleNamespace(
        InstanceGuid=SimpleNamespace(ToString=lambda: "guid"),
        AddRuntimeMessage=lambda level, text: messages.append((level, text)),
    )
    namespace = {
        "ghenv": SimpleNamespace(Component=component),
        "BRep": ["brep1", "brep2"],
        "Settings": SimpleNamespace(Boundarycond="BOUNDARY", Construction="HHL_Wall", Boundarytemp="TAIR_A1", Frontback="FRONT"),
        "datafile_assembly": "GKP.idf",
    }
    namespace.update(inputs)
    with mock.patch.dict(sys.modules, modules), contextlib.redirect_stdout(io.StringIO()):
        run_source(HYGRO_SOURCE.read_text(encoding="utf-8-sig"), HYGRO_SOURCE, namespace)
    return FakeConstruction.stored, messages


SETTING_ATTRIBUTES = ("Writereport", "Reportinterval", "Addheatdepth", "Addheat", "Layermindiv")


class LizardHygroComponentTests(unittest.TestCase):
    def settings(self, stored, brep="brep1"):
        return {name: stored[brep].get(name, "<not stored>") for name in SETTING_ATTRIBUTES}

    def test_inputs_not_connected_or_ports_missing_store_none(self):
        for inputs in ({}, dict.fromkeys(("write_report", "report_interval", "add_heat_depth", "add_heat", "layer_min_div")),
                       {"add_heat": "   ", "report_interval": ""}):
            with self.subTest(inputs=inputs):
                stored, messages = run_hygro(**inputs)

                self.assertEqual([], messages)
                for brep in ("brep1", "brep2"):
                    self.assertEqual(dict.fromkeys(SETTING_ATTRIBUTES), self.settings(stored, brep))
                    self.assertEqual("GKP.idf", stored[brep]["Filemat"])
                    self.assertEqual("EXTCALBND", stored[brep]["Boundarycond"])

    def test_values_are_stored_on_every_surface_of_the_component(self):
        stored, messages = run_hygro(write_report=False, report_interval=0.5, add_heat_depth=0.0125, add_heat=10.0, layer_min_div=8)

        self.assertEqual([], messages)
        expected = {"Writereport": False, "Reportinterval": 0.5, "Addheatdepth": 0.0125, "Addheat": 10.0, "Layermindiv": 8}
        self.assertEqual(expected, self.settings(stored, "brep1"))
        self.assertEqual(expected, self.settings(stored, "brep2"))

    def test_values_from_panels_and_sliders_are_normalised(self):
        cases = [
            ({"write_report": True}, "Writereport", True),
            ({"write_report": "false"}, "Writereport", False),
            ({"write_report": " No "}, "Writereport", False),
            ({"write_report": "1"}, "Writereport", True),
            ({"write_report": -1}, "Writereport", False),
            ({"write_report": 0}, "Writereport", False),
            ({"report_interval": "0.25"}, "Reportinterval", 0.25),
            ({"report_interval": 2}, "Reportinterval", 2.0),
            ({"add_heat_depth": "0.03"}, "Addheatdepth", 0.03),
            ({"add_heat_depth": 0}, "Addheatdepth", 0.0),
            ({"add_heat": 12}, "Addheat", 12),
            ({"add_heat": -7.5}, "Addheat", -7.5),
            ({"add_heat": " 5 "}, "Addheat", "5"),
            ({"add_heat": "QWALL_S9 / 3.6"}, "Addheat", "(QWALL_S9 / 3.6)"),
            ({"add_heat": "-SCHED_heat*20"}, "Addheat", "(-SCHED_heat*20)"),
            ({"layer_min_div": 8.0}, "Layermindiv", 8),
            ({"layer_min_div": "12"}, "Layermindiv", 12),
        ]
        for inputs, attribute, expected in cases:
            with self.subTest(inputs=inputs):
                stored, messages = run_hygro(**inputs)

                self.assertEqual([], messages)
                self.assertEqual(expected, stored["brep1"][attribute])
                self.assertIs(type(expected), type(stored["brep1"][attribute]))

    def test_invalid_values_warn_and_keep_the_default(self):
        cases = [
            ({"write_report": "maybe"}, "Writereport", "write_report"),
            ({"report_interval": 0}, "Reportinterval", "report_interval"),
            ({"report_interval": -1.0}, "Reportinterval", "report_interval"),
            ({"report_interval": 0.00004}, "Reportinterval", "0.0001"),   # Type 395 would round it to 0 h
            ({"report_interval": "abc"}, "Reportinterval", "report_interval"),
            ({"report_interval": True}, "Reportinterval", "report_interval"),
            ({"add_heat_depth": -0.01}, "Addheatdepth", "add_heat_depth"),
            ({"add_heat_depth": "deep"}, "Addheatdepth", "add_heat_depth"),
            ({"add_heat": True}, "Addheat", "add_heat"),
            ({"add_heat": "Q ! comment"}, "Addheat", "add_heat"),
            ({"add_heat": "@specload"}, "Addheat", "add_heat"),
            ({"layer_min_div": 0}, "Layermindiv", "layer_min_div"),
            ({"layer_min_div": 2.5}, "Layermindiv", "layer_min_div"),
            ({"layer_min_div": -3}, "Layermindiv", "layer_min_div"),
            ({"layer_min_div": "many"}, "Layermindiv", "layer_min_div"),
        ]
        for inputs, attribute, fragment in cases:
            with self.subTest(inputs=inputs):
                stored, messages = run_hygro(**inputs)

                self.assertIsNone(stored["brep1"][attribute])
                self.assertEqual(1, len(messages))
                self.assertEqual("WARNING", messages[0][0])
                self.assertIn(fragment, messages[0][1])


class HygroDocstringTests(unittest.TestCase):
    NEW_INPUTS = ["write_report", "report_interval", "add_heat_depth", "add_heat", "layer_min_div"]

    def test_updater_parser_returns_the_new_inputs_in_order(self):
        updater = load_updater()
        inputs, outputs = updater.parseIONames(HYGRO_SOURCE.read_text(encoding="utf-8-sig"))

        self.assertEqual(["BRep", "Settings", "------------------ hygrothermal", "datafile_assembly"] + self.NEW_INPUTS, inputs)
        self.assertEqual(["SurfaceInfo"], outputs)

    def test_new_inputs_are_optional_item_inputs_with_a_type(self):
        updater = load_updater()
        inputs, _ = updater.parseDocstringIO(HYGRO_SOURCE.read_text(encoding="utf-8-sig"))
        specs = {spec["name"]: spec for spec in inputs}

        expected_types = {"write_report": "bool", "report_interval": "float", "add_heat_depth": "float", "add_heat": "object",
                          "layer_min_div": "int"}
        for name in self.NEW_INPUTS:
            with self.subTest(input=name):
                self.assertEqual("item", specs[name]["access"])
                self.assertFalse(specs[name]["required"])
                self.assertEqual(expected_types[name], specs[name]["type"])
                self.assertTrue(specs[name]["description"])
        self.assertIn("side-2", specs["add_heat_depth"]["description"])
        self.assertIn("minimum", specs["layer_min_div"]["description"])
        self.assertIn("0.0001", specs["report_interval"]["description"])

    def test_ironpython_sources_stay_ascii(self):
        for path in (HYGRO_SOURCE, COMPONENT_SOURCE, SYSTEM_SOURCE, REPO_ROOT / "Lizard_DCK_Template.py"):
            with self.subTest(source=path.name):
                path.read_bytes().decode("ascii")


if __name__ == "__main__":
    unittest.main()
