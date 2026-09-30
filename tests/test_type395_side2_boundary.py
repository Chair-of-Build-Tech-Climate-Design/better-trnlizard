"""Regression checks for side 2 of the Type 395 (HAMT) walls.

Type 395 applies the side-2 heat transfer coefficient ``hconv2`` ONCE and as a CONVECTIVE film only; any longwave / solar
exchange of side 2 has to enter through ``qWG2`` or be linearised into that one film.  For an EXTCALBND (internal) wall the
far side faces a (mirror) neighbour room, so option A is used, in its IMPLICIT form:

* ``h_c`` = interior convective coefficient (TRNBuild default 11 kJ/(h m2 K)) instead of the library ``HBACK`` default 64
  (exterior, wind-exposed convention), unless the wall carries an explicit value;
* ``h_r`` = ``4*SIGMA*0.9*293.15^3`` (18.51 kJ/(h m2 K)): the longwave exchange with the neighbour room, linearised at
  T_ref = 20 C (RTEMP of Type 56);
* ``hconv2 = h_c + h_r`` and ``TB2 = (h_c*TAIR + h_r*TMR)/hconv2`` for a mirror wall (TB2 = own TAIR), or the boundary
  temperature itself (its own radiant reference) for any other boundary;
* ``qWG2 = 0`` and ``beta2`` from ``h_c`` only (the Lewis relation belongs to the convective coefficient).

The explicit form (``qWG2 = AREA395*SIGMA*0.9*((273.15 + TMR)^4 - (273.15 + TSO395)^4)``) fed Type 395's own output TSO395 back
as its input 8: an algebraic loop through TRNSYS (QWG2_STABILITY_TEST_2026-09-30.md: 2.6x run time and non-converged steps).

EXTCALEXT must stay exactly as it was.  The real ``@s7#...@e7#`` template block and the real ``e7`` handler
of ``Lizard_System.py`` are executed with mock variables (no Grasshopper, no TRNSYS).
"""

import math
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

# Longwave terms of the generated DIN deck (Hygrothermisch_Big_GKP_WithFoil.d18, EXTCALEXT surface 8). The exterior solar term in
# front of them comes from a Type 15 tilted surface and is tested in test_type395_extcalext_solar.py; this harness maps none.
REFERENCE_EXTCALEXT_QWG2 = (
    "AREA395_S8 * 0.5 * SIGMA_S8 * 0.9 * ((273.15 + Tsky)^4 - (273.15 + TSO395_S8)^4)"
    " + AREA395_S8 * (1-0.5) * SIGMA_S8 * 0.9 * ((273.15 + Tamb)^4 - (273.15 + TSO395_S8)^4)"
)

# Side-2 equations of the implicit option A, copied from the deck that TRNSYS ran (QWG2_STABILITY_TEST_2026-09-30.md, variant
# "implicit option A"): E:\HyHole\20260930_Calibration\qwg2_stability\optAimp_0.1h\Hygrothermisch_Big_GKP_WithFoil.d18, S9 lines
# 1098, 1101, 1116 and 1120 (S10 and S11 are the same with their surface number). {0} = surface number, zone A1.
# RH2 (line 1118 there: plain Rh_A1) was scaled afterwards so that RH2*psat(TB2) is the vapour pressure of the room air
# (TB2 is the weighted air/radiant temperature; see REFERENCE_SIDE2_RH2 and the vapour-pressure test).
REFERENCE_IMPLICIT_SIDE2 = {
    "hconv2_S{0}": "11 + 4*SIGMA_S{0}*0.9*293.15^3",
    "TB2_S{0}": "(11*TAIR_A1 + 4*SIGMA_S{0}*0.9*293.15^3*TMR_C1) / hconv2_S{0}",
    "qWG2_S{0}": "0",
    "RH2_S{0}": "Rh_A1*EXP(17.62*(TAIR_A1/(243.12+TAIR_A1)-TB2_S{0}/(243.12+TB2_S{0})))",
    "beta2_S{0}": "0.000000007*11/3.6",
}

SIGMA = 2.041e-07  # kJ/(h m2 K4) = 5.67e-8 W/(m2 K4), the literal of SIGMA_S<n> in the deck
T_REF = 293.15     # K, 20 C: reference temperature of the linearised longwave film (RTEMP of Type 56)
EPS = 0.9
H_CONV = 11.0      # kJ/(h m2 K), interior convective coefficient of the default wall

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
        Orientation="S_0_90",
        Type="WALL",
    )


def render_hamt_block(template_lines, surfaces, walls_def, zone_name="A1", longwave=None, messages=None, block=None,
                      namespace_out=None):
    """Execute the real ``e7`` handler of Lizard_System.py and return the rendered deck text.

    ``longwave`` is the TRNBuild longwave mode of the zone (default: not set, i.e. the library default STANDARD),
    ``messages`` collects the Grasshopper runtime messages, ``block`` replaces the template block lines and
    ``namespace_out`` (a dict) receives the variables of the handler afterwards (its ``t395_*`` constants).
    """
    airnode = SimpleNamespace(Name=zone_name, Ecalsurfaces=[s.Surfnum for s in surfaces], Surfaces=surfaces)
    if longwave is not None:
        airnode.Longwave = longwave
    if messages is None:
        messages = []
    writer = DeckWriter()
    namespace = {
        "re": re,
        "str": Py2String,
        "variables": {},
        "zone": [SimpleNamespace(Airnode=airnode)],
        "walls_def": walls_def,
        "blockdata": block if block is not None else hamt_block_lines(template_lines),
        "dckout": writer,
        "t395_udepth": None,
        "t395_udivnum": 30,
        "w": "WARNING",
        "ghenv": SimpleNamespace(
            Component=SimpleNamespace(AddRuntimeMessage=lambda level, text: messages.append((level, text)))
        ),
    }
    source = SYSTEM_SOURCE.read_text(encoding="utf-8-sig")
    execute_source_block(
        source,
        "                    variables['unitno']   = 800\n                    unit395_counter = 200",
        "                if 'e8' in  match_search.group(0):",
        namespace,
    )
    if namespace_out is not None:
        namespace_out.update(namespace)
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
    """Evaluate a TRNSYS equation right-hand side that only uses + - * / ^, parentheses, EXP, MAX and MIN."""
    names = dict(values, EXP=math.exp, MAX=max, MIN=min)
    return eval(expression.replace("^", "**"), {"__builtins__": {}}, names)


def referenced_names(expression):
    """Names a TRNSYS equation right-hand side refers to (numbers such as 2.041e-007 and EXP, MAX, MIN are left out)."""
    names = re.findall(r"(?<![\w.])[A-Za-z_]\w*", expression)
    return {name for name in names if name.upper() not in ("EXP", "MAX", "MIN")}


def dependency_closure(names, equations):
    """Lower-case names of everything ``names`` depend on through the equations of one block, themselves included.

    TRNSYS names are case-insensitive.  Names that are no equation of the block (Type 56 outputs, TAIR_A1, TMR_C1, ...) end the search.
    """
    known = {name.lower(): expression for name, expression in equations.items()}
    seen = set()
    todo = [name.lower() for name in names]
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        if name in known:
            todo.extend(reference.lower() for reference in referenced_names(known[name]))
    return seen


def reads_a_unit_output(expression):
    """True for an equation that reads an output of another unit, written ``[unit,output]`` in the deck (e.g. ``[200,2]``)."""
    return re.search(r"\[\s*\d+\s*,\s*\d+\s*\]", expression) is not None


def solve(name, equations, externals):
    """Value of a deck variable: an equation of the block (evaluated recursively) or an external variable.

    ``externals`` maps lower-case names (TRNSYS names are case-insensitive) to numbers, e.g. ``{"tair_a1": 22.0}``.
    """
    known = {key.lower(): expression for key, expression in equations.items()}
    if name.lower() not in known:
        return externals[name.lower()]
    expression = known[name.lower()]
    if reads_a_unit_output(expression):
        raise AssertionError("%s = %s reads an output of a unit (Type 395 itself): not a function of the room temperatures" % (name, expression))
    return evaluate(expression, **{reference: solve(reference, equations, externals) for reference in referenced_names(expression)})


class Type395Side2BoundaryTests(unittest.TestCase):
    # (0-based) positions of TB2, RH2, hconv2, qWG2 and beta2 in the input list of Type 395
    SIDE2_INPUTS = (1, 3, 5, 7, 9)
    AREA = 15.848  # area of make_surface()

    # (TAIR, TMR, Tso) [C]: no exchange, neighbour warmer / colder than the wall, TMR above / below TAIR, winter wall
    STATES = (
        (20.0, 20.0, 20.0),
        (22.0, 20.5, 19.0),
        (24.5, 27.0, 21.0),
        (15.0, 12.0, 18.5),
        (30.0, 33.0, 26.0),
        (20.0, 18.0, 5.0),
    )

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

    def side2_inputs(self, block, number):
        """Names wired to the side-2 inputs of Type 395 (TB2, RH2, hconv2, qWG2, beta2 = inputs 2, 4, 6, 8, 10); checks the wiring."""
        names = [block[3][index] for index in self.SIDE2_INPUTS]
        self.assertEqual(
            [name % number for name in ("TB2_S%d", "RH2_S%d", "hconv2_S%d", "qWG2_S%d", "beta2_S%d")], names
        )
        return names

    def side2_flux(self, equations, number, externals, tso):
        """Heat into the wall through side 2 [kJ/(h m2)] as Type 395 applies it: hconv2 * (TB2 - Tso) + qWG2 / area."""
        hconv2 = solve("hconv2_S%d" % number, equations, externals)
        tb2 = solve("TB2_S%d" % number, equations, externals)
        qwg2 = solve("qWG2_S%d" % number, equations, externals)
        return hconv2 * (tb2 - tso) + qwg2 / self.AREA

    # ------------------------------------------------------------------ the implicit form: equations

    def test_extcalbnd_side2_equations_are_the_ones_trnsys_ran_in_the_stability_test(self):
        _, blocks = self.render(self.din_surfaces())

        for number in (9, 10, 11):
            for template, expected in REFERENCE_IMPLICIT_SIDE2.items():
                name = template.format(number)
                with self.subTest(equation=name):
                    self.assertEqual(expected.format(number), blocks[number][1][name])

    def test_extcalbnd_side2_vapour_pressure_is_that_of_the_room_air_although_tb2_is_the_weighted_temperature(self):
        _, blocks = self.render(self.din_surfaces())
        equations = blocks[9][1]

        def psat_hyland_wexler(celsius):
            """Saturation pressure [Pa] as in hamt-core physics::psy_psat_fn_temp (above freezing: over water)."""
            t = celsius + 273.15
            c8, c9, c10, c11, c12, c13 = -5800.2206, 1.3914993, -4.8640239e-2, 4.1764768e-5, -1.4452093e-8, 6.5459673
            return math.exp(c8 / t + c9 + t * (c10 + t * (c11 + t * c12)) + c13 * math.log(t))

        for tair in (10.0, 15.0, 20.0, 25.0, 30.0):
            for tmr_minus_tair in (-2.0, -0.5, 0.0, 0.5, 1.5):
                for rh in (30.0, 55.0, 80.0):
                    with self.subTest(tair=tair, tmr_minus_tair=tmr_minus_tair, rh=rh):
                        tmr = tair + tmr_minus_tair
                        hconv2 = evaluate(equations["hconv2_S9"], SIGMA_S9=SIGMA)
                        tb2 = evaluate(equations["TB2_S9"], TAIR_A1=tair, TMR_C1=tmr, SIGMA_S9=SIGMA, hconv2_S9=hconv2)
                        rh2 = evaluate(equations["RH2_S9"], Rh_A1=rh, TAIR_A1=tair, TB2_S9=tb2)
                        # Type 395 (boundary.rs): side-2 vapour pressure = RH2/100 * psat(TB2)
                        ratio = (rh2 / 100.0 * psat_hyland_wexler(tb2)) / (rh / 100.0 * psat_hyland_wexler(tair))
                        self.assertAlmostEqual(1.0, ratio, delta=3e-4)
                        if tmr_minus_tair == 0.0:
                            self.assertAlmostEqual(rh, rh2, places=9)
        # unscaled, the vapour pressure would be off by about 6 % per kelvin of (TB2 - TAIR); TB2 moves 0.63 K per kelvin of TMR - TAIR
        self.assertGreater(abs(psat_hyland_wexler(20.0 + 0.63) / psat_hyland_wexler(20.0) - 1.0), 0.02)

    def test_extcalbnd_side2_film_is_the_interior_convective_coefficient_plus_the_linearised_longwave_film(self):
        _, blocks = self.render(self.din_surfaces())

        for number in (9, 10, 11):
            with self.subTest(surface=number):
                equations = blocks[number][1]
                # 64 kJ/(h m2 K) = 17.8 W/(m2 K) is the exterior (wind exposed) convention of the library: not used
                self.assertEqual("11 + 4*SIGMA_S%d*0.9*293.15^3" % number, equations["hconv2_S%d" % number])
                hconv2 = evaluate(equations["hconv2_S%d" % number], **{"SIGMA_S%d" % number: SIGMA})
                self.assertAlmostEqual(H_CONV + 4 * SIGMA * EPS * T_REF ** 3, hconv2, places=9)
                self.assertAlmostEqual(29.51, hconv2, delta=0.005)
                self.assertEqual("Rh_A1*EXP(17.62*(TAIR_A1/(243.12+TAIR_A1)-TB2_S{0}/(243.12+TB2_S{0})))".format(number), equations["RH2_S%d" % number])

    def test_extcalbnd_tb2_of_a_mirror_wall_is_the_film_weighted_mean_of_the_air_and_the_radiant_temperature(self):
        _, blocks = self.render(self.din_surfaces())

        for number in (9, 10, 11):
            with self.subTest(surface=number):
                equations = blocks[number][1]
                self.assertEqual(
                    "(11*TAIR_A1 + 4*SIGMA_S{0}*0.9*293.15^3*TMR_C1) / hconv2_S{0}".format(number),
                    equations["TB2_S%d" % number],
                )
                # known global-name limitation (comfort object 1), not made worse
                known = {name.lower() for name in equations}
                self.assertEqual({"tair_a1", "tmr_c1"}, dependency_closure(["TB2_S%d" % number], equations) - known)

    def test_extcalbnd_qwg2_is_zero_because_the_longwave_exchange_sits_in_the_film(self):
        _, blocks = self.render(self.din_surfaces())

        for number in (9, 10, 11):
            with self.subTest(surface=number):
                self.assertEqual("0", blocks[number][1]["qWG2_S%d" % number])

    def test_extcalbnd_side2_uses_the_same_radiant_temperature_variable_as_the_detailed_side_1(self):
        # longwave DETAILED/SIMPLE keeps the separated side-1 coupling, whose input 14 is the same variable
        surfaces = self.din_surfaces()
        text = render_hamt_block(self.template_lines, surfaces, self.walls_def, longwave="DETAILED")
        blocks = {surface.Surfnum: block for surface, block in zip(surfaces, equation_blocks(text))}

        for number in (9, 10, 11):
            with self.subTest(surface=number):
                equations, inputs = blocks[number][1], blocks[number][3]
                side_1_tmr = inputs[13]  # Type 395 input 14: mean radiant temperature for side 1
                self.assertEqual("TMR_C1", side_1_tmr)
                self.assertIn(side_1_tmr.lower(), dependency_closure(["TB2_S%d" % number], equations))
                self.assertEqual("0", equations["qWG2_S%d" % number])
                self.assertEqual("qWG2_S%d" % number, inputs[7])

    # ------------------------------------------------------------------ the loop is gone

    def test_extcalbnd_side2_no_longer_reads_tso395_so_type395_has_no_loop_through_its_own_output(self):
        # The explicit form held (273.15 + TSO395)^4 in qWG2, and TSO395 is output 2 of the very Type 395 that takes qWG2 as input 8:
        # an algebraic loop through TRNSYS (QWG2_STABILITY_TEST_2026-09-30.md: 2.6x run time, non-converged steps).
        _, blocks = self.render(self.din_surfaces())

        # the check is not vacuous: the exterior wall (unchanged) still has its outer surface temperature in the longwave terms
        exterior = dependency_closure(self.side2_inputs(blocks[8], 8), blocks[8][1])
        self.assertIn("tso395_s8", exterior)
        self.assertTrue(reads_a_unit_output({name.lower(): e for name, e in blocks[8][1].items()}["tso395_s8"]))

        for number in (9, 10, 11):
            with self.subTest(surface=number):
                equations = blocks[number][1]
                side2 = self.side2_inputs(blocks[number], number)
                for name in side2:
                    self.assertNotIn("TSO395", equations[name], name)
                known = {name.lower(): expression for name, expression in equations.items()}
                closure = dependency_closure(side2, equations)
                # neither the outer nor the inner surface temperature of this wall, nor any other output of a unit
                self.assertEqual([], sorted(name for name in closure if "tso395" in name or "tsi395" in name))
                self.assertEqual([], sorted(name for name in closure if name in known and reads_a_unit_output(known[name])))
                # what is left is the room: air temperature, mean radiant temperature and humidity of this zone
                self.assertEqual({"tair_a1", "tmr_c1", "rh_a1"}, closure - set(known))

    # ------------------------------------------------------------------ the implicit form: physics

    def test_side2_heat_exchange_is_convection_to_the_air_plus_linearised_longwave_to_the_radiant_temperature(self):
        _, blocks = self.render(self.din_surfaces())
        h_r = 4 * SIGMA * EPS * T_REF ** 3  # 18.51 kJ/(h m2 K)

        for number in (9, 10, 11):
            equations = blocks[number][1]
            for tair, tmr, tso in self.STATES:
                with self.subTest(surface=number, tair=tair, tmr=tmr, tso=tso):
                    externals = {"tair_a1": tair, "tmr_c1": tmr}
                    expected = H_CONV * (tair - tso) + h_r * (tmr - tso)
                    hconv2 = solve("hconv2_S%d" % number, equations, externals)
                    tb2 = solve("TB2_S%d" % number, equations, externals)
                    self.assertAlmostEqual(expected, hconv2 * (tb2 - tso), delta=1e-9)
                    self.assertAlmostEqual(expected, self.side2_flux(equations, number, externals, tso), delta=1e-9)

    def test_the_heat_exchange_has_the_sign_of_the_temperature_differences(self):
        _, blocks = self.render([make_surface(9, "EXTCALBND")])
        equations = blocks[9][1]

        def flux(tair, tmr, tso):
            return self.side2_flux(equations, 9, {"tair_a1": tair, "tmr_c1": tmr}, tso)

        self.assertAlmostEqual(0.0, flux(22.0, 22.0, 22.0), places=9)
        self.assertGreater(flux(25.0, 25.0, 20.0), 0.0)  # warmer room heats the wall (kJ/(h m2) into the wall)
        self.assertLess(flux(20.0, 20.0, 25.0), 0.0)
        # radiant temperature above the wall temperature: the longwave exchange heats the wall although the air is at its temperature
        self.assertGreater(flux(20.0, 24.0, 20.0), 0.0)
        # radiant temperature = wall temperature: convection only
        self.assertAlmostEqual(H_CONV * 5.0, flux(25.0, 20.0, 20.0), places=9)

    def test_linearised_film_is_the_tangent_of_the_explicit_longwave_exchange_at_the_reference_temperature(self):
        _, blocks = self.render([make_surface(9, "EXTCALBND")])
        h_r = evaluate(blocks[9][1]["hconv2_S9"], SIGMA_S9=SIGMA) - H_CONV

        def explicit(tmr, tso):
            """Longwave exchange per m2 of the superseded explicit form: SIGMA * 0.9 * ((273.15 + TMR)^4 - (273.15 + TSO395)^4)."""
            return SIGMA * EPS * ((273.15 + tmr) ** 4 - (273.15 + tso) ** 4)

        # slope against the wall temperature at wall temperature = radiant temperature = 20 C (central difference)
        self.assertAlmostEqual(h_r, (explicit(20.0, 19.95) - explicit(20.0, 20.05)) / 0.1, delta=1e-3)
        # about 5.1 W/(m2 K) = the radiation film 4 sigma eps T^3 of Type 395's own interior film (physical sigma)
        self.assertAlmostEqual(4 * 5.670374419e-8 * 0.9 * 293.15 ** 3, h_r / 3.6, delta=0.05)
        # away from 20 C the linearisation error stays below 6 % of the longwave exchange (room temperatures)
        for tmr, tso in ((21.0, 20.0), (20.0, 22.0), (23.0, 18.0), (16.0, 19.0), (24.0, 26.0)):
            with self.subTest(tmr=tmr, tso=tso):
                self.assertAlmostEqual(explicit(tmr, tso), h_r * (tmr - tso), delta=0.06 * abs(explicit(tmr, tso)))

    def test_beta2_follows_the_convective_coefficient_only(self):
        # Lewis: the vapour transfer coefficient belongs to the convective film, the longwave part of hconv2 has no vapour counterpart
        _, blocks = self.render(self.din_surfaces())

        for number in (9, 10, 11):
            with self.subTest(surface=number):
                beta2 = blocks[number][1]["beta2_S%d" % number]
                self.assertEqual("0.000000007*11/3.6", beta2)
                self.assertNotIn("hconv2", beta2)
                self.assertTrue(math.isclose(7e-9 * 11 / 3.6, evaluate(beta2), rel_tol=1e-12))
                # the combined coefficient 29.51 would give 2.7 times the vapour transfer
                self.assertLess(evaluate(beta2), 0.5 * 7e-9 * 29.51 / 3.6)

    def test_extcalext_film_boundary_and_longwave_are_unchanged(self):
        _, blocks = self.render(self.din_surfaces())
        equations = blocks[8][1]

        self.assertEqual("64.0", equations["hconv2_S8"])
        self.assertEqual("Tamb", equations["TB2_S8"])
        self.assertEqual("Rh_amb", equations["RH2_S8"])
        self.assertEqual(REFERENCE_EXTCALEXT_QWG2, equations["qWG2_S8"])
        self.assertEqual("0.000000007*hconv2_S8/3.6", equations["beta2_S8"])

    # ------------------------------------------------------------------ the convective part of the film

    def test_explicit_interior_back_side_value_of_the_wall_is_kept_as_the_convective_part(self):
        h_r = 4 * SIGMA * EPS * T_REF ** 3
        for hback, expected in (("9999.0", "9999.0"), ("8.5", "8.5"), (20, "20")):
            with self.subTest(hback=hback):
                walls_def = {"HHL_Wall": SimpleNamespace(Hback=hback, Abs_back="0.7")}
                _, blocks = self.render([make_surface(9, "EXTCALBND")], walls_def)
                equations = blocks[9][1]

                self.assertEqual("%s + 4*SIGMA_S9*0.9*293.15^3" % expected, equations["hconv2_S9"])
                self.assertEqual(
                    "(%s*TAIR_A1 + 4*SIGMA_S9*0.9*293.15^3*TMR_C1) / hconv2_S9" % expected, equations["TB2_S9"]
                )
                self.assertEqual("0", equations["qWG2_S9"])
                self.assertEqual("0.000000007*%s/3.6" % expected, equations["beta2_S9"])  # the convective part only
                for tair, tmr, tso in self.STATES:
                    externals = {"tair_a1": tair, "tmr_c1": tmr}
                    hconv2 = solve("hconv2_S9", equations, externals)
                    tb2 = solve("TB2_S9", equations, externals)
                    self.assertAlmostEqual(
                        float(expected) * (tair - tso) + h_r * (tmr - tso), hconv2 * (tb2 - tso), delta=1e-9 * float(expected)
                    )

    def test_library_default_or_unusable_back_side_value_gets_the_interior_coefficient(self):
        for hback in ("64.0", "64", 64, 64.0, "VERTICAL", "", None):
            with self.subTest(hback=hback):
                walls_def = {"HHL_Wall": SimpleNamespace(Hback=hback, Abs_back="0.7")}
                _, blocks = self.render([make_surface(9, "EXTCALBND")], walls_def)
                self.assertEqual("11 + 4*SIGMA_S9*0.9*293.15^3", blocks[9][1]["hconv2_S9"])
                self.assertEqual("0.000000007*11/3.6", blocks[9][1]["beta2_S9"])

    # ------------------------------------------------------------------ which neighbour is a mirror

    def test_non_mirror_boundary_temperature_is_its_own_radiant_reference(self):
        # TB2 is not this zone's TAIR: the neighbour is not a mirror, so this zone's TMR must not be used.  Convection and
        # longwave both exchange with the boundary temperature, so TB2 stays the boundary temperature (weighted mean = itself).
        h_r = 4 * SIGMA * EPS * T_REF ** 3
        for boundarytemp, externals, temperature in (
            ("INPUT 1*TAIR_A2", {"tair_a2": 19.0}, 19.0),
            ("INPUT 1*Tamb", {"tamb": -3.0}, -3.0),
            ("INPUT 1*18", {}, 18.0),
            ("INPUT 1*-5", {}, -5.0),
            ("INPUT 1*TAIR_A1 + 2", {"tair_a1": 21.0}, 23.0),  # the own air temperature plus an offset is no mirror either
        ):
            with self.subTest(boundarytemp=boundarytemp):
                _, blocks = self.render([make_surface(9, "EXTCALBND", boundarytemp)])
                equations, inputs = blocks[9][1], blocks[9][3]

                self.assertEqual(boundarytemp.split("*")[-1], equations["TB2_S9"])
                self.assertEqual("11 + 4*SIGMA_S9*0.9*293.15^3", equations["hconv2_S9"])
                self.assertEqual("0", equations["qWG2_S9"])
                self.assertEqual("0.000000007*11/3.6", equations["beta2_S9"])
                self.assertNotIn("tmr_c1", dependency_closure([inputs[index] for index in self.SIDE2_INPUTS], equations))
                for tso in (5.0, 20.0, 27.5):
                    hconv2 = solve("hconv2_S9", equations, externals)
                    tb2 = solve("TB2_S9", equations, externals)
                    self.assertAlmostEqual((H_CONV + h_r) * (temperature - tso), hconv2 * (tb2 - tso), delta=1e-9)

    def test_mirror_detection_ignores_case_and_follows_the_zone_name(self):
        _, blocks = self.render([make_surface(9, "EXTCALBND", "INPUT 1*Tair_Office")], zone_name="Office")

        equations = blocks[9][1]
        self.assertEqual("(11*TAIR_Office + 4*SIGMA_S9*0.9*293.15^3*TMR_C1) / hconv2_S9", equations["TB2_S9"])
        self.assertEqual("Rh_Office*EXP(17.62*(TAIR_Office/(243.12+TAIR_Office)-TB2_S9/(243.12+TB2_S9)))", equations["RH2_S9"])

    # ------------------------------------------------------------------ block bookkeeping

    def test_every_block_keeps_its_equation_count_and_no_placeholder_is_left(self):
        text, blocks = self.render(self.din_surfaces())

        self.assertNotIn("@", text)
        self.assertEqual(4, len(blocks))
        for number, (declared, equations, order, inputs) in blocks.items():
            with self.subTest(surface=number):
                self.assertEqual(declared, len(order))
                self.assertEqual(32, declared)
                self.assertEqual(11, len(inputs))  # side 1 = star link of Type 56 (longwave STANDARD)

    def test_no_equation_name_is_defined_twice_or_collides_with_type56_aliases(self):
        _, blocks = self.render(self.din_surfaces())

        names = [name for (_, _, order, _) in blocks.values() for name in order]
        self.assertEqual(len(names), len(set(names)))
        for name in names:
            self.assertIsNone(TYPE56_ALIAS.match(name), name)
        for number in (9, 10, 11):
            self.assertIn("qWG2_S%d" % number, blocks[number][2])
            self.assertIn("SIGMA_S%d" % number, blocks[number][2])
            self.assertIn("TSO395_S%d" % number, blocks[number][2])  # still defined (template unchanged), only side 2 no longer reads it


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
