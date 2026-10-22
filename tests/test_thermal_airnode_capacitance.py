"""Lizard_Thermal_Airnode writes the zone CAPACITANCE as a number (volume * CapacitanceFactor, default 3 kJ/(m3 K)),
not as a Type 56 input that only a hand-edited deck defines."""

import re
import unittest
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "Lizard_Thermal_Airnode.py"


def capacitance(volume, factor_input):
    """Run the capacitance lines of the script with a volume and the CapacitanceFactor input (None = not connected)."""
    lines = SOURCE.read_text(encoding="utf-8-sig").replace("\r\n", "\n").split("\n")
    start = next(i for i, line in enumerate(lines) if line.strip().startswith("capacitance_fact_userdef = "))
    end = next(i for i, line in enumerate(lines) if line.strip().startswith("Airnode.Capacitance = "))
    block = [lines[i] for i in range(start, start + 6)] + [lines[end]]
    code = "\n".join(line[4:] for line in block)
    messages = []
    scope = {"CapacitanceFactor": factor_input, "w": "Warning",
             "Airnode": type("Airnode", (), {"Volume": volume})(),
             "ghenv": type("Env", (), {"Component": type("C", (), {
                 "AddRuntimeMessage": staticmethod(lambda level, text: messages.append(text))})()})()}
    if factor_input is None:
        del scope["CapacitanceFactor"]
    exec(compile(code, "capacitance", "exec"), scope)
    return scope["Airnode"].Capacitance, messages


class AirnodeCapacitanceTests(unittest.TestCase):
    def test_no_external_input(self):
        source = SOURCE.read_text(encoding="utf-8-sig")
        self.assertNotIn("NodeHeatCapacitance", source)
        self.assertNotRegex(source, r"Capacitance\s*=\s*['\"]INPUT")

    def test_volume_times_factor(self):
        self.assertEqual((237.72, []), capacitance(79.24, None))          # not connected: 3 kJ/(m3 K)
        self.assertEqual((95.088, []), capacitance(79.24, 1.2))
        self.assertEqual((237.72, []), capacitance(79.24, "3"))          # a panel gives text
        value, messages = capacitance(10.0, 0)
        self.assertEqual(30.0, value)
        self.assertEqual(1, len(messages))

    def test_declared_input(self):
        source = SOURCE.read_text(encoding="utf-8-sig")
        self.assertRegex(source, r"\n    CapacitanceFactor \(float\): .*Not connected = 3")
        self.assertIn('"CapacitanceFactor"]', source)


if __name__ == "__main__":
    unittest.main()
