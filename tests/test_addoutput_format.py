"""The sums Type 46 writes at the end of AddOutput_1h.prn must fit the format: a field of stars stops TRNSYS with message 431."""

import re
import unittest
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = (ROOT / "components" / "Lizard_System.py").read_text(encoding="utf-8-sig")


def printer(**options):
    block = re.search(r"^def PrintPrintegrator.*?^    return plotdata\n", SYSTEM, flags=re.M | re.S).group(0)
    block = block.replace("\\User", "\\\\User")  # IronPython 2 source: not an escape there, it is one in Python 3
    namespace = {"lu_counter": 900}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        exec(compile(block, "Lizard_System.py", "exec"), namespace)
    return namespace["PrintPrintegrator"](name="AddOutput", unit=959, content=["A", "B"], **options)


class FormatTests(unittest.TestCase):
    def test_the_standard_printers_keep_their_format(self):
        self.assertIn("FORMAT (1(F10.2,1X),2(F10.2,1X))", printer())

    def test_a_wider_printer(self):
        self.assertIn("FORMAT (1(F14.2,1X),2(F14.2,1X))", printer(width=14))

    def test_the_addoutput_printer_is_wide(self):
        self.assertRegex(SYSTEM, r"PrintPrintegrator\(name = 'AddOutput'.*width = 14\)")

    def test_the_sum_that_stopped_a_run_fits(self):
        self.assertGreater(len("%.2f" % -1446000.0), 10)
        self.assertLessEqual(len("%.2f" % -1446000.0), 14)


if __name__ == "__main__":
    unittest.main()
