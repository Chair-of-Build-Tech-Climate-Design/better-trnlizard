"""Lizard_Infiltration: flow per person."""

import re
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
INFILTRATION = (ROOT / "components" / "Lizard_Infiltration.py").read_text(encoding="utf-8-sig")
SYSTEM = (ROOT / "components" / "Lizard_System.py").read_text(encoding="utf-8-sig")


def run_infiltration(**inputs):
    scriptcontext = ModuleType("scriptcontext")
    namespace = dict({"--------------- Infiltration": None, "ACH": 0, "Schedule": "Occ", "AnnualSchedule": None, "MinACH": 0.1}, **inputs)
    namespace["ghenv"] = SimpleNamespace(Component=SimpleNamespace())
    with patch.dict(sys.modules, {"scriptcontext": scriptcontext}):
        exec(compile(INFILTRATION, "Lizard_Infiltration.py", "exec"), namespace)
    return namespace["Infiltration"]


def infiltration_ach(infiltration_item, airnode):
    block = re.search(r"^def infiltrationAch.*?(?=^def )", SYSTEM, flags=re.M | re.S).group(0)
    namespace = {}
    exec(block, namespace)
    return namespace["infiltrationAch"](infiltration_item, airnode)


class InfiltrationTests(unittest.TestCase):
    airnode = SimpleNamespace(Floorarea=36.0, Areaperperson=1.8, Volume=100.0)

    def test_flow_per_person_gives_the_air_change(self):
        item = run_infiltration(OrPersonRelatedVolumeFlow=10)
        self.assertEqual(2.0, infiltration_ach(item, self.airnode))

    def test_the_higher_of_the_two_is_used(self):
        self.assertEqual(3.0, infiltration_ach(SimpleNamespace(Ach=3, Vflowppers=10), self.airnode))

    def test_without_flow_per_person_ach_stays_as_it_is(self):
        self.assertEqual("(1+x)", infiltration_ach(SimpleNamespace(Ach="(1+x)"), self.airnode))


if __name__ == "__main__":
    unittest.main()
