"""Regression check for schedule application on generated people moisture gains."""

from pathlib import Path
from types import SimpleNamespace
from textwrap import dedent
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "Lizard_System.py"


def execute_source_block(source, start, end, namespace):
    """Run the actual IronPython generator block without loading Grasshopper."""
    block = dedent(source[source.index(start):source.index(end, source.index(start))])
    exec(compile(block, str(SOURCE), "exec"), namespace)


class PeopleHumidityScalingTests(unittest.TestCase):
    def test_people_moisture_uses_weekly_and_annual_scales_once(self):
        source = SOURCE.read_text(encoding="utf-8-sig")
        for annual in ("", "Vacation"):
            with self.subTest(annual=annual):
                gain = SimpleNamespace(
                    Personsgain=1,
                    Name="PEOPLE",
                    Radiative="INPUT 0.5*Q_PERS_KJ",
                    Convective="INPUT 0.5*Q_PERS_KJ",
                    Hum2=0.06,
                    Humidity=None,
                    Schedule="DIN_People",
                    Annual=annual,
                    Category="PEOPLE",
                    Frac_refarea=1,
                    Type="GAIN",
                )
                rendered = []
                execute_source_block(
                    source,
                    "            if item2.Personsgain == 1:",
                    "            if item2.Computergain == 1:",
                    {
                        "item2": gain,
                        "item": SimpleNamespace(Name="A1", Areaperperson=30),
                        "lines": rendered,
                        "printsingledata": lambda obj, kind: "GAIN {} : HUMIDITY={}".format(obj.Name, obj.Humidity),
                    },
                )
                regime = {
                    "Airnodes": SimpleNamespace(Name="A1", Gain=[gain]),
                    "regimelines": "",
                }
                execute_source_block(
                    source,
                    "        for gain_item in Airnodes.Gain:",
                    "        hamt_gain_exists = False",
                    regime,
                )
                self.assertEqual("GAIN PEOPLE_A1 : HUMIDITY=0.002", rendered[0])
                self.assertIn("SCALE= SCHEDULE 1*DIN_People", regime["regimelines"])
                expected_annual = "SCALE2= SCHEDULE 1*Vacation" if annual else "SCALE2= 1"
                self.assertIn(expected_annual, regime["regimelines"])
                self.assertEqual("PEOPLE", gain.Name)


if __name__ == "__main__":
    unittest.main()
