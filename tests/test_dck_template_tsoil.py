"""Lizard_DCK_Template has no Tsoil input: the soil temperature is the built-in TRNLizard formula again."""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_type395_extcalext_solar import load_template_lines, TEMPLATE_SOURCE  # noqa: E402
from test_updater_io_sync import load_updater  # noqa: E402


class DckTemplateTsoilTests(unittest.TestCase):
    def test_built_in_soil_temperature(self):
        lines = load_template_lines()   # runs the script without a Tsoil global
        tsoil = [line for line in lines if line.startswith("Tsoil ")]
        self.assertEqual(1, len(tsoil))
        self.assertTrue(tsoil[0].startswith("Tsoil        = @Tmean_amb - 8 * COS(360/365*(TIME/24 - 43)) !"))

    def test_no_inputs_declared(self):
        inputs, outputs = load_updater().parseIONames(TEMPLATE_SOURCE.read_text(encoding="utf-8-sig"))
        self.assertEqual(([], ["DckTemplate"]), (inputs, outputs))


if __name__ == "__main__":
    unittest.main()
