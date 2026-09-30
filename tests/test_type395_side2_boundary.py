"""Regression checks for side 2 of the Type 395 (HAMT) walls.

Type 395 applies the side-2 heat transfer coefficient ``hconv2`` ONCE and as a CONVECTIVE film only; the
side-2 longwave / solar exchange has to enter through ``qWG2``.  For an EXTCALBND (internal) wall the far
side faces a (mirror) neighbour room, so option A is used:

* ``hconv2`` = interior convective coefficient (TRNBuild default 11 kJ/(h m2 K)) instead of the library
  ``HBACK`` default 64 (exterior, wind-exposed convention), unless the wall carries an explicit value;
* ``qWG2`` = longwave exchange with the mean radiant temperature of the neighbour room, in the form of the
  EXTCALEXT terms: ``AREA395 * SIGMA * 0.9 * ((273.15 + TMR)^4 - (273.15 + TSO395)^4)`` [kJ/h].

EXTCALEXT must stay exactly as it was.  The real ``@s7#...@e7#`` template block and the real ``e7`` handler
of ``Lizard_System.py`` are executed with mock variables (no Grasshopper, no TRNSYS).
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

# Reference lines of the generated DIN deck (Hygrothermisch_Big_GKP_WithFoil.d18, EXTCALEXT surface 8)
REFERENCE_EXTCALEXT_QWG2 = (
    "IT_S8 * 0.7 + AREA395_S8 * 0.5 * SIGMA_S8 * 0.9 * ((273.15 + Tsky)^4 - (273.15 + TSO395_S8)^4)"
    " + AREA395_S8 * (1-0.5) * SIGMA_S8 * 0.9 * ((273.15 + Tamb)^4 - (273.15 + TSO395_S8)^4)"
)

# Type 56 auto-output aliases that a user equation must never reuse (TRNSYS message 15)
TYPE56_ALIAS = re.compile(
    r"^(QWG|QABSI|QABSO|QABSILW|QCOMI|QSIAB|QRGAB|QSKY|TSI|TSO|REQV|IT|IB|ID|AREA|HCONVI|HCONVO)_S\d+$"
)


class Py2String(str):
    """IronPython 2 ``str``: the generator calls ``.encode('string-escape')`` on it."""

    def encode(self, encoding="utf-8", errors="strict"):
        if encoding == "string-escape":
            escaped = str.encode(self, "unicode_escape").decode("ascii")
            return Py2String(escaped.replace("'", "\\'"))
        return str.encode(self, encoding, errors)


class DeckWriter:
    """Stand-in for the deck file handle that printdck() writes to."""

    def __init__(self):
        self.text = ""

    def write(self, text):
        self.text += text


def run_source(source, filename, namespace):
    with warnings.catch_warnings():
        # The IronPython 2 sources use unescaped backslashes such as '\w' and '\Output'.
        warnings.simplefilter("ignore")
        code = compile(source, str(filename), "exec")
    exec(code, namespace)
    return namespace


def execute_source_block(source, start, end, namespace):
    """Run the actual IronPython generator block without loading Grasshopper."""
    first = source.index(start)
    block = dedent(source[first:source.index(end, first)])
    return run_source(block, SYSTEM_SOURCE, namespace)


def load_template_lines():
    """Execute the real DCK template component and return the deck template lines."""
    source = TEMPLATE_SOURCE.read_text(encoding="utf-8-sig")
    scriptcontext = ModuleType("scriptcontext")
    scriptcontext.doc = None  # the template-cache invalidation only runs inside Rhino
    scriptcontext.sticky = {}
    namespace = {
        "ghenv": SimpleNamespace(Component=SimpleNamespace()),
        "Tsoil": "20",
    }
    with mock.patch.dict(sys.modules, {"scriptcontext": scriptcontext}):
        run_source(source, TEMPLATE_SOURCE, namespace)
    return namespace["DckTemplate"]


def hamt_block_lines(template_lines):
    """The lines printdck() keeps as ``blockdata`` of the @s7# ... @e7# group."""
    start = next(i for i, line in enumerate(template_lines) if "@s7#" in line)
    end = next(i for i, line in enumerate(template_lines) if "@e7#" in line)
    return template_lines[start + 1:end]


def make_surface(number, boundarycond, boundarytemp="INPUT 1*TAIR_@ANAME", construction="HHL_Wall"):
    return SimpleNamespace(
        Surfnum=number,
        Area=15.848,
        Boundarycond=boundarycond,
        Boundarytemp=boundarytemp,
        Construction=construction,
        Fsky=0.5,
        Filemat="GKP.idf",
    )


def render_hamt_block(template_lines, surfaces, walls_def, zone_name="A1"):
    """Execute the real ``e7`` handler of Lizard_System.py and return the rendered deck text."""
    airnode = SimpleNamespace(Name=zone_name, Ecalsurfaces=[s.Surfnum for s in surfaces], Surfaces=surfaces)
    writer = DeckWriter()
    namespace = {
        "re": re,
        "str": Py2String,
        "variables": {},
        "zone": [SimpleNamespace(Airnode=airnode)],
        "walls_def": walls_def,
        "blockdata": hamt_block_lines(template_lines),
        "dckout": writer,
        "t395_udepth": None,
        "t395_udivnum": 30,
    }
    source = SYSTEM_SOURCE.read_text(encoding="utf-8-sig")
    execute_source_block(
        source,
        "                    variables['unitno']   = 800\n                    unit395_counter = 200",
        "                if 'e8' in  match_search.group(0):",
        namespace,
    )
    return writer.text


def equation_blocks(deck_text):
    """(declared count, {name: expression}, [Type 395 input names]) for every rendered HAMT block."""
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
    """Evaluate a TRNSYS equation right-hand side that only uses + - * / ^ and parentheses."""
    return eval(expression.replace("^", "**"), {"__builtins__": {}}, values)


class Type395Side2BoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template_lines = load_template_lines()
        cls.walls_def = {"HHL_Wall": SimpleNamespace(Hback="64.0", Abs_back="0.7")}

    def render(self, surfaces, walls_def=None, zone_name="A1"):
        text = render_hamt_block(self.template_lines, surfaces, walls_def or self.walls_def, zone_name)
        return text, {
            surface.Surfnum: block
            for surface, block in zip(surfaces, equation_blocks(text))
        }

    def din_surfaces(self):
        return [
            make_surface(8, "EXTCALEXT"),
            make_surface(9, "EXTCALBND"),
            make_surface(10, "EXTCALBND"),
            make_surface(11, "EXTCALBND"),
        ]

    def test_extcalbnd_side2_film_is_interior_convective_coefficient(self):
        _, blocks = self.render(self.din_surfaces())

        for number in (9, 10, 11):
            with self.subTest(surface=number):
                equations = blocks[number][1]
                # 64 kJ/(h m2 K) = 17.8 W/(m2 K) is the exterior (wind exposed) convention of the library
                self.assertEqual("11", equations["hconv2_S%d" % number])
                self.assertEqual("TAIR_A1", equations["TB2_S%d" % number])
                self.assertEqual("Rh_A1", equations["RH2_S%d" % number])
                # the side-2 vapour coefficient follows the convective coefficient (Lewis relation)
                self.assertEqual("0.000000007*hconv2_S%d/3.6" % number, equations["beta2_S%d" % number])

    def test_extcalbnd_qwg2_is_longwave_exchange_with_the_neighbour_room_radiant_temperature(self):
        _, blocks = self.render(self.din_surfaces())

        for number in (9, 10, 11):
            with self.subTest(surface=number):
                self.assertEqual(
                    "AREA395_S{0} * SIGMA_S{0} * 0.9 * ((273.15 + TMR_C1)^4 - (273.15 + TSO395_S{0})^4)".format(number),
                    blocks[number][1]["qWG2_S%d" % number],
                )

    def test_extcalbnd_side2_uses_the_same_radiant_temperature_variable_as_side_1(self):
        _, blocks = self.render(self.din_surfaces())

        for number in (9, 10, 11):
            with self.subTest(surface=number):
                equations, inputs = blocks[number][1], blocks[number][3]
                side_1_tmr = inputs[13]  # Type 395 input 14: mean radiant temperature for side 1
                self.assertIn("(273.15 + %s)^4" % side_1_tmr, equations["qWG2_S%d" % number])
                self.assertEqual("TMR_C1", side_1_tmr)  # known global-name limitation, not made worse
                self.assertEqual("qWG2_S%d" % number, inputs[7])

    def test_extcalbnd_qwg2_has_the_sign_and_size_of_a_longwave_exchange(self):
        _, blocks = self.render(self.din_surfaces())
        expression = blocks[9][1]["qWG2_S9"]
        sigma = 2.041e-07  # kJ/(h m2 K4) = 5.67e-8 W/(m2 K4)
        area = 15.848

        def qwg2(tmr, tso):
            return evaluate(expression, AREA395_S9=area, SIGMA_S9=sigma, TMR_C1=tmr, TSO395_S9=tso)

        self.assertAlmostEqual(0.0, qwg2(22.0, 22.0), places=9)
        self.assertGreater(qwg2(25.0, 20.0), 0.0)  # warmer room heats the wall (kJ/h into the wall)
        self.assertLess(qwg2(20.0, 25.0), 0.0)
        self.assertAlmostEqual(
            area * sigma * 0.9 * (298.15 ** 4 - 293.15 ** 4), qwg2(25.0, 20.0), places=6
        )
        # linearised, it is the interior radiation film of Type 395 (4 sigma eps T^3, about 5.1 W/(m2 K))
        h_rad = (qwg2(20.0, 20.0) - qwg2(20.0, 20.1)) / 0.1 / area / 3.6
        self.assertAlmostEqual(4 * 5.670374419e-8 * 0.9 * 293.15 ** 3, h_rad, delta=0.05)

    def test_extcalext_is_unchanged(self):
        _, blocks = self.render(self.din_surfaces())
        equations = blocks[8][1]

        self.assertEqual("64.0", equations["hconv2_S8"])
        self.assertEqual("Tamb", equations["TB2_S8"])
        self.assertEqual("Rh_amb", equations["RH2_S8"])
        self.assertEqual(REFERENCE_EXTCALEXT_QWG2, equations["qWG2_S8"])
        self.assertEqual("0.000000007*hconv2_S8/3.6", equations["beta2_S8"])

    def test_explicit_interior_back_side_value_of_the_wall_is_kept(self):
        for hback, expected in (("9999.0", "9999.0"), ("8.5", "8.5"), (20, "20")):
            with self.subTest(hback=hback):
                walls_def = {"HHL_Wall": SimpleNamespace(Hback=hback, Abs_back="0.7")}
                _, blocks = self.render([make_surface(9, "EXTCALBND")], walls_def)
                self.assertEqual(expected, blocks[9][1]["hconv2_S9"])

    def test_library_default_or_unusable_back_side_value_gets_the_interior_coefficient(self):
        for hback in ("64.0", "64", 64, 64.0, "VERTICAL", "", None):
            with self.subTest(hback=hback):
                walls_def = {"HHL_Wall": SimpleNamespace(Hback=hback, Abs_back="0.7")}
                _, blocks = self.render([make_surface(9, "EXTCALBND")], walls_def)
                self.assertEqual("11", blocks[9][1]["hconv2_S9"])

    def test_non_mirror_boundary_temperature_is_its_own_radiant_reference(self):
        # TB2 is not this zone's TAIR: the neighbour is not a mirror, so this zone's TMR must not be used
        for boundarytemp, reference in (
            ("INPUT 1*TAIR_A2", "TAIR_A2"),
            ("INPUT 1*Tamb", "Tamb"),
            ("INPUT 1*18", "18"),
            ("INPUT 1*-5", "(-5)"),  # the TRNSYS parser rejects '+ -5'
        ):
            with self.subTest(boundarytemp=boundarytemp):
                _, blocks = self.render([make_surface(9, "EXTCALBND", boundarytemp)])
                equations = blocks[9][1]
                self.assertEqual(boundarytemp.split("*")[-1], equations["TB2_S9"])
                self.assertEqual(
                    "AREA395_S9 * SIGMA_S9 * 0.9 * ((273.15 + %s)^4 - (273.15 + TSO395_S9)^4)" % reference,
                    equations["qWG2_S9"],
                )

    def test_mirror_detection_ignores_case_and_follows_the_zone_name(self):
        _, blocks = self.render([make_surface(9, "EXTCALBND", "INPUT 1*Tair_Office")], zone_name="Office")

        self.assertIn("(273.15 + TMR_C1)^4", blocks[9][1]["qWG2_S9"])

    def test_every_block_keeps_its_equation_count_and_no_placeholder_is_left(self):
        text, blocks = self.render(self.din_surfaces())

        self.assertNotIn("@", text)
        self.assertEqual(4, len(blocks))
        for number, (declared, equations, order, inputs) in blocks.items():
            with self.subTest(surface=number):
                self.assertEqual(declared, len(order))
                self.assertEqual(32, declared)
                self.assertEqual(14, len(inputs))

    def test_no_equation_name_is_defined_twice_or_collides_with_type56_aliases(self):
        _, blocks = self.render(self.din_surfaces())

        names = [name for (_, _, order, _) in blocks.values() for name in order]
        self.assertEqual(len(names), len(set(names)))
        for name in names:
            self.assertIsNone(TYPE56_ALIAS.match(name), name)
        for number in (9, 10, 11):
            self.assertIn("qWG2_S%d" % number, blocks[number][2])
            self.assertIn("SIGMA_S%d" % number, blocks[number][2])
            self.assertIn("TSO395_S%d" % number, blocks[number][2])


class ExtcalbndWallGainGuardTests(unittest.TestCase):
    """A user WAGAIN on the HIGH_COND pseudo-wall is not passed to Type 395 (input 7 = QABSI - QWG)."""

    START = "                if surfaces.Boundarycond == 'EXTCALBND':\n                    #dummylines=dummylines + ' : WAGAIN=INPUT 1*WGAIN_I_S@self.Surfnum"
    END = "                for attr, value in surfaces.__dict__.iteritems():"

    def run_block(self, **surface_attributes):
        source = SYSTEM_SOURCE.read_text(encoding="utf-8-sig")
        messages = []
        surfaces = SimpleNamespace(Boundarycond="EXTCALBND", Construction="HHL_Wall", **surface_attributes)
        namespace = {
            "surfaces": surfaces,
            "srfnum": 9,
            "dummylines": "WALL  =HHL_Wall",
            "ecal_surfaces": [],
            "w": "WARNING",
            "ghenv": SimpleNamespace(
                Component=SimpleNamespace(AddRuntimeMessage=lambda level, text: messages.append((level, text)))
            ),
        }
        execute_source_block(source, self.START, self.END, namespace)
        return namespace, messages

    def test_user_wall_gain_on_an_extcalbnd_wall_raises_a_warning(self):
        for attributes in ({"Wagain": "INPUT 1*WGAIN_I_S9"}, {"Wagaino": "INPUT 1*X"}, {"Wagain": 50.0, "Wagaino": 10.0}):
            with self.subTest(attributes=attributes):
                namespace, messages = self.run_block(**attributes)

                self.assertEqual(1, len(messages))
                self.assertEqual("WARNING", messages[0][0])
                self.assertIn("Surface 9", messages[0][1])
                self.assertIn("QABSI-QWG", messages[0][1])
                # the guard only warns: the generated b18 line and the HAMT registration are unchanged
                if "Wagain" in attributes:
                    self.assertIn(" : WAGAIN=%s" % attributes["Wagain"], namespace["dummylines"])
                if "Wagaino" in attributes:
                    self.assertIn(" : WAGAINO=%s" % attributes["Wagaino"], namespace["dummylines"])
                self.assertEqual([9], namespace["ecal_surfaces"])
                self.assertEqual("HIGH_COND", namespace["surfaces"].Construction)

    def test_no_warning_without_a_user_wall_gain(self):
        for attributes in ({}, {"Wagain": None, "Wagaino": ""}, {"Wagain": 0}):
            with self.subTest(attributes=attributes):
                namespace, messages = self.run_block(**attributes)

                self.assertEqual([], messages)
                self.assertNotIn("WAGAIN", namespace["dummylines"])


if __name__ == "__main__":
    unittest.main()
