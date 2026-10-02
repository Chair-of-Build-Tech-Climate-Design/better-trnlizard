"""Regression checks for side 1 (room side) of the Type 395 (HAMT) walls.

Type 56 (longwave STANDARD, star network) exchanges heat with the inside surface of a wall as

    QCOMI = (Ts - TSTAR) / REQV                      [kJ/h]   (manual Eq. 5.4.1-10, NType 19 and 86)

and adds the absorbed gains QABSI at the surface node (Eq. 5.4.1-15, NType 21).  The HAMT wall is the pseudo-wall
HIGH_COND whose boundary temperature is TSI395, so Type 56 hands ``QABSI - QCOMI`` to the boundary node.  Type 395
has to receive exactly that.  With the 11-input layout (``has_separate_radiant_int`` is false) Type 395 applies ONE
film to its interior surface node, so ``TB1 = TSTAR`` and ``hconv1 = 1/(REQV*A)`` reproduce ``QCOMI`` and
``qWG1 = QABSI - QWG`` adds the absorbed gains: zone and wall exchange identical energy.

In that layout Type 395 takes the vapour pressure at the temperature of TB1 as well (hamt-core ``surface/boundary.rs``:
the interior Convection cell has ONE temperature for heat and vapour), so ``RH1`` is scaled to give the vapour pressure
of the room air (TAIR) and ``beta1`` stays the convective Lewis coefficient of HCONVI.

Longwave DETAILED / SIMPLE have no star node: the separated coupling (TAIR + HCONVI, TMR + linearised longwave film,
14 inputs) is kept and a warning is raised.  Side 2 is not touched.  The real ``@s7#...@e7#`` template block and the
real ``e7`` handler of ``Lizard_System.py`` are executed with mock variables (no Grasshopper, no TRNSYS).
"""

import math
import re
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_type395_side2_boundary import (  # noqa: E402
    TYPE56_ALIAS,
    equation_blocks,
    evaluate,
    hamt_block_lines,
    load_template_lines,
    make_surface,
    render_hamt_block,
)


def psat_hyland_wexler(celsius):
    """Saturation pressure [Pa] as in hamt-core ``physics::psy_psat_fn_temp`` (above freezing: over water)."""
    t = celsius + 273.15
    c8, c9, c10, c11, c12, c13 = -5800.2206, 1.3914993, -4.8640239e-2, 4.1764768e-5, -1.4452093e-8, 6.5459673
    return math.exp(c8 / t + c9 + t * (c10 + t * (c11 + t * c12)) + c13 * math.log(t))


def initial_input_values(deck_text):
    """The numbers of the ``*** INITIAL INPUT VALUES`` line of every Type 395 block (not of the Type 93 of an EXTCALEXT wall)."""
    lines = deck_text.splitlines()
    values, unit_type = [], None
    for i, line in enumerate(lines):
        unit = re.match(r"^UNIT\s+\S+\s+TYPE\s+(\d+)", line)
        if unit is not None:
            unit_type = int(unit.group(1))
        elif line.startswith("*** INITIAL INPUT VALUES") and unit_type == 395:
            values.append([float(value) for value in lines[i + 1].split()])
    return values


def active_text(deck_text):
    """The deck text without comment lines (``*``) and without trailing ``!`` comments."""
    kept = []
    for line in deck_text.splitlines():
        if line.lstrip().startswith("*"):
            continue
        kept.append(line.split("!")[0])
    return "\n".join(kept)


def resolve(token, equations, externals):
    """Value of a deck variable: an equation of the block (evaluated recursively) or an external Type 56 variable.

    ``externals`` maps lower-cased names (TRNSYS names are case-insensitive) to numbers.
    """
    lowered = {name.lower(): expression for name, expression in equations.items()}
    if token.lower() in lowered:
        expression = lowered[token.lower()]
        names = set(re.findall(r"[A-Za-z_]\w*", expression)) - {"EXP", "MAX", "MIN"}
        return evaluate(expression, **{name: resolve(name, equations, externals) for name in names})
    return externals[token.lower()]


STANDARD_INPUTS = (
    "TB1_S{0}", "TB2_S{0}", "RH1_S{0}", "RH2_S{0}", "hconv1_S{0}", "hconv2_S{0}",
    "qWG1_NoRad_S{0}", "qWG2_S{0}", "beta1_S{0}", "beta2_S{0}", "QheatKJ_S{0}",
)
DETAILED_EXTRA_INPUTS = ("TAIR_MOIST1_S{0}", "HCONVI_S{0}", "TMR_C1")


class Type395Side1CouplingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template_lines = load_template_lines()
        cls.walls_def = {"HHL_Wall": SimpleNamespace(Hback="64.0", Abs_back="0.7")}

    def din_surfaces(self):
        return [
            make_surface(8, "EXTCALEXT"),
            make_surface(9, "EXTCALBND"),
            make_surface(10, "EXTCALBND"),
            make_surface(11, "EXTCALBND"),
        ]

    def render(self, surfaces=None, zone_name="A1", longwave=None, block=None):
        surfaces = surfaces or self.din_surfaces()
        messages = []
        text = render_hamt_block(
            self.template_lines, surfaces, self.walls_def, zone_name, longwave=longwave, messages=messages, block=block
        )
        blocks = {surface.Surfnum: block for surface, block in zip(surfaces, equation_blocks(text))}
        return text, blocks, messages

    # ------------------------------------------------------------------ STANDARD longwave: the star link of Type 56

    def test_heat_link_is_the_star_link_of_type56_and_there_is_no_separate_longwave_film(self):
        text, blocks, messages = self.render()

        self.assertEqual([], messages)
        for number in (8, 9, 10, 11):
            with self.subTest(surface=number):
                declared, equations, order, inputs = blocks[number]
                self.assertEqual("TSTAR_A1", equations["TB1_S%d" % number])
                self.assertEqual(
                    "(1/ MAX(REQV_S{0}*AREA395_S{0},0.001))".format(number), equations["hconv1_S%d" % number]
                )
                # 11 inputs: Type 395 then has ONE interior film (no HCONVI / TMR inputs, has_separate_radiant_int = false)
                self.assertEqual([token.format(number) for token in STANDARD_INPUTS], inputs)
        self.assertIn("INPUTS 11\n", text)
        self.assertNotIn("INPUTS 14", text)
        self.assertEqual(4, len(initial_input_values(text)))
        for values in initial_input_values(text):
            self.assertEqual(11, len(values))

    def test_the_star_node_of_the_zone_is_used(self):
        _, blocks, _ = self.render([make_surface(9, "EXTCALBND")], zone_name="Office")

        equations = blocks[9][1]
        self.assertEqual("TSTAR_Office", equations["TB1_S9"])
        self.assertTrue(equations["RH1_S9"].startswith("Rh_Office*EXP("), equations["RH1_S9"])
        self.assertIn("TSTAR_Office", equations["RH1_S9"])
        self.assertIn("TAIR_Office", equations["RH1_S9"])

    def test_wall_receives_exactly_what_type56_gives_up_at_the_surface(self):
        """Zone side: QABSI - QCOMI with QCOMI = (Ts - TSTAR)/REQV.  Wall side: the single Type 395 film plus qWG1."""
        _, blocks, _ = self.render()
        area = 15.848

        for number in (8, 9, 10, 11):
            equations, inputs = blocks[number][1], blocks[number][3]
            for tstar, ts, qabsi, qwg in (
                (19.4, 18.9, 250.0, 0.0),
                (21.3, 22.0, -35.0, 0.0),
                (20.0, 20.0, 0.0, 0.0),
                (17.0, 12.5, 1800.0, 0.0),
                (19.4, 18.9, 250.0, 40.0),
            ):
                with self.subTest(surface=number, tstar=tstar, ts=ts, qabsi=qabsi, qwg=qwg):
                    externals = {
                        "tstar_a1": tstar, "tair_a1": 20.0, "rh_a1": 50.0, "hconvi_s%d" % number: 29.77,
                        "reqv_s%d" % number: 1.0 / (57.84 * area),
                        "qabsi_s%d" % number: qabsi, "qwg_s%d" % number: qwg,
                    }

                    def value(index):
                        return resolve(inputs[index], equations, externals)

                    # Type 56: energy from the inside surface to the zone, and what is left for the boundary node
                    qcomi = (ts - tstar) / externals["reqv_s%d" % number]
                    type56_into_wall = qabsi - qcomi
                    # Type 395 (11 inputs): one film hconv1*(TB1 - Ts) over the area, plus the absorbed gains (input 7)
                    type395_into_wall = value(4) * area * (value(0) - ts) + value(6)

                    # the only difference is the wall gain QWG, which Type 56 has applied itself (NType 82)
                    self.assertAlmostEqual(
                        type56_into_wall - qwg, type395_into_wall, delta=1e-9 * max(1.0, abs(type56_into_wall))
                    )

    def test_absorbed_gains_are_handed_over_once_without_the_longwave_exchange(self):
        text, blocks, _ = self.render()

        for number in (8, 9, 10, 11):
            with self.subTest(surface=number):
                equations, inputs = blocks[number][1], blocks[number][3]
                # QABSI = solar + internal radiative gains + wall gains, WITHOUT the longwave exchange (inside the star link);
                # QWG is a wall gain Type 56 has applied itself.  No QABSILW, QRGAB, QSIAB or QCOMI term on top of it.
                self.assertEqual("QABSI_S{0} - QWG_S{0}".format(number), equations["qWG1_NoRad_S%d" % number])
                self.assertEqual("qWG1_NoRad_S%d" % number, inputs[6])
                # no radiant temperature input (the longwave exchange is inside the star link): no second longwave film
                self.assertNotIn("TMR_C1", inputs)
                self.assertFalse([token for token in inputs if token.upper().startswith(("TMR", "TAIR_MOIST1", "HCONVI"))])
        for name in ("QABSILW", "QCOMI", "QRGAB", "QSIAB"):
            self.assertNotIn(name, active_text(text))

    def test_moisture_film_is_convective_with_an_explicit_beta(self):
        _, blocks, _ = self.render()

        for number in (8, 9, 10, 11):
            with self.subTest(surface=number):
                equations, inputs = blocks[number][1], blocks[number][3]
                # explicit and non-zero (beta1 = 0 would make Type 395 derive it from hconv1, i.e. from the combined coefficient)
                self.assertEqual("0.000000007*HCONVI_S%d/3.6" % number, equations["beta1_S%d" % number])
                self.assertEqual("beta1_S%d" % number, inputs[8])
                beta1 = evaluate(equations["beta1_S%d" % number], **{"HCONVI_S%d" % number: 31.14})
                self.assertAlmostEqual(6.057e-8, beta1, delta=1e-10)

    def test_vapour_pressure_is_that_of_the_room_air_although_type395_uses_one_temperature_for_heat_and_vapour(self):
        _, blocks, _ = self.render()
        expression = blocks[9][1]["RH1_S9"]

        for tair in (10.0, 15.0, 20.0, 22.0, 25.0, 30.0):
            for difference in (-2.0, -0.5, -0.3, 0.0, 0.3, 1.5):
                for rh in (30.0, 55.0, 80.0):
                    with self.subTest(tair=tair, tstar_minus_tair=difference, rh=rh):
                        tstar = tair + difference
                        rh1 = evaluate(expression, Rh_A1=rh, TAIR_A1=tair, TSTAR_A1=tstar)
                        # Type 395 (boundary.rs): VP_bc = RH1/100 * psat(TB1) with TB1 = TSTAR
                        vapour_pressure = rh1 / 100.0 * psat_hyland_wexler(tstar)
                        room_air = rh / 100.0 * psat_hyland_wexler(tair)
                        self.assertAlmostEqual(1.0, vapour_pressure / room_air, delta=3e-4)
                        if difference == 0.0:
                            self.assertAlmostEqual(rh, rh1, places=9)

        # without the scaling the boundary vapour pressure would be off by several percent for a star node 0.3 K below the air
        self.assertGreater(abs(psat_hyland_wexler(19.7) / psat_hyland_wexler(20.0) - 1.0), 0.015)

    def test_side_2_is_identical_with_and_without_the_star_link(self):
        _, standard, _ = self.render()
        _, detailed, _ = self.render(longwave="DETAILED")

        for number in (8, 9, 10, 11):
            for name in ("hconv2_S%d", "TB2_S%d", "RH2_S%d", "beta2_S%d", "qWG2_S%d", "SIGMA_S%d", "TSO395_S%d"):
                with self.subTest(surface=number, name=name):
                    self.assertEqual(detailed[number][1][name % number], standard[number][1][name % number])
            # Type 395 inputs 2, 6, 8 and 10 (TB2, hconv2, qWG2, beta2) sit at the same positions in both layouts
            for index in (1, 5, 7, 9):
                self.assertEqual(detailed[number][3][index], standard[number][3][index])

    def test_walls_without_a_bnd_neighbour_need_no_comfort_object(self):
        text, _, _ = self.render([make_surface(8, "EXTCALEXT")])

        self.assertNotIn("TMR_C1", active_text(text))

    def test_counts_and_names_of_the_standard_layout(self):
        text, blocks, _ = self.render()

        self.assertNotIn("@", text)
        names = [name for (_, _, order, _) in blocks.values() for name in order]
        self.assertEqual(len(names), len(set(names)))
        for name in names:
            self.assertIsNone(TYPE56_ALIAS.match(name), name)
        for number, (declared, equations, order, inputs) in blocks.items():
            with self.subTest(surface=number):
                self.assertEqual(declared, len(order))
                self.assertEqual(32, declared)
                self.assertEqual(11, len(inputs))

    # ------------------------------------------------------------------ longwave DETAILED / SIMPLE: no star node

    def test_detailed_and_simple_longwave_keep_the_separated_coupling_and_warn(self):
        for mode, expected_name in (("DETAILED", "DETAILED"), ("SIMPLE", "SIMPLE"), (" detailed ", "DETAILED")):
            with self.subTest(mode=mode):
                text, blocks, messages = self.render(longwave=mode)

                self.assertEqual(1, len(messages))
                level, message = messages[0]
                self.assertEqual("WARNING", level)
                for fragment in ("Zone A1", expected_name, "8, 9, 10, 11", "TSTAR", "energy-consistent"):
                    self.assertIn(fragment, message)
                self.assertEqual(expected_name == "SIMPLE", "counted twice" in message)

                # no TSTAR / REQV in the active deck lines (they do not exist without the star network)
                for name in ("TSTAR", "REQV"):
                    self.assertNotIn(name, active_text(text))
                # the old coupling: TAIR + HCONVI for the convective film, TMR for the longwave film, 14 inputs
                for number in (8, 9, 10, 11):
                    declared, equations, order, inputs = blocks[number]
                    self.assertEqual(32, declared)
                    self.assertEqual(declared, len(order))
                    self.assertEqual([token.format(number) for token in STANDARD_INPUTS + DETAILED_EXTRA_INPUTS], inputs)
                    self.assertEqual("TAIR_A1", equations["TB1_S%d" % number])
                    self.assertEqual("TAIR_A1", equations["TAIR_MOIST1_S%d" % number])
                    self.assertEqual("Rh_A1", equations["RH1_S%d" % number])
                    self.assertEqual("HCONVI_S%d" % number, equations["hconv1_S%d" % number])
                    self.assertEqual("QABSI_S{0} - QWG_S{0}".format(number), equations["qWG1_NoRad_S%d" % number])
                    self.assertEqual("0.000000007*HCONVI_S%d/3.6" % number, equations["beta1_S%d" % number])
                self.assertIn("INPUTS 14\n", text)
                self.assertNotIn("INPUTS 11", text)
                for values in initial_input_values(text):
                    self.assertEqual(14, len(values))
                self.assertNotIn("@", text)

    def test_the_warning_is_raised_per_zone_and_not_for_the_star_network(self):
        messages = []
        render_hamt_block(self.template_lines, [make_surface(9, "EXTCALBND")], self.walls_def, "A1", longwave="STANDARD", messages=messages)
        render_hamt_block(self.template_lines, [make_surface(9, "EXTCALBND")], self.walls_def, "A1", messages=messages)
        self.assertEqual([], messages)

        render_hamt_block(self.template_lines, [make_surface(9, "EXTCALBND")], self.walls_def, "Office", longwave="DETAILED", messages=messages)
        self.assertEqual(1, len(messages))
        self.assertIn("Zone Office", messages[0][1])

    def test_stale_dck_template_is_reported(self):
        stale_block = [line.replace("@nin395", "14") for line in hamt_block_lines(self.template_lines)]
        messages = []
        render_hamt_block(
            self.template_lines, [make_surface(9, "EXTCALBND")], self.walls_def, "A1", messages=messages, block=stale_block
        )

        self.assertEqual(1, len(messages))
        self.assertIn("Reload", messages[0][1])

        messages = []
        render_hamt_block(self.template_lines, [make_surface(9, "EXTCALBND")], self.walls_def, "A1", messages=messages)
        self.assertEqual([], messages)

        # a project without HAMT walls is not bothered by a stale template
        messages = []
        render_hamt_block(self.template_lines, [], self.walls_def, "A1", messages=messages, block=stale_block)
        self.assertEqual([], messages)


if __name__ == "__main__":
    unittest.main()
