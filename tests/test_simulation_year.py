"""SimulationYear of Lizard_System: the weekday of 1 January, the weekly schedules of the b18 and the equation WEEKDAY of the deck."""

import copy
import re
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = (ROOT / "components" / "Lizard_System.py").read_text(encoding="utf-8-sig")
TEMPLATE = (ROOT / "components" / "Lizard_DCK_Template.py").read_text(encoding="utf-8-sig")
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class Reader:
    def __init__(self, lines):
        self.lines = iter(lines)

    def ReadLine(self):
        return next(self.lines, None)

    def Close(self):
        pass


def functions(lines=()):
    fake = SimpleNamespace(IO=SimpleNamespace(StreamReader=lambda filename: Reader(lines)))
    namespace = {"System": fake, "datetime": datetime, "copy": copy}
    exec(re.search(r"^def weatherYear.*?(?=^def getparagraph)", SYSTEM, flags=re.M | re.S).group(0), namespace)
    return namespace


F = functions()


def epw(*years):
    return ["LOCATION,x", "DATA PERIODS,1,1,Data,Thursday,1/ 1,12/31"] + ["{0},1,1,1,0,x".format(year) for year in years]


class YearTests(unittest.TestCase):
    def test_an_epw_of_one_year_gives_the_year(self):
        self.assertEqual(2026, functions(epw(2026, 2026))["weatherYear"]("a.EPW"))

    def test_a_typical_year_mixes_years_and_gives_none(self):
        self.assertIsNone(functions(epw(2005, 2012))["weatherYear"]("a.epw"))

    def test_other_weather_files_give_none(self):
        self.assertIsNone(F["weatherYear"]("a.tmy3"))

    def test_the_input_goes_before_the_weather_file(self):
        self.assertEqual(2024, F["simulationYear"](2024, 2026))
        self.assertEqual(2024, F["simulationYear"]("2024", None))

    def test_an_empty_input_takes_the_weather_file(self):
        self.assertEqual(2026, F["simulationYear"](None, 2026))
        self.assertEqual(2026, F["simulationYear"](" ", 2026))
        self.assertIsNone(F["simulationYear"](None, None))

    def test_a_bad_input_is_an_error(self):
        for value in ("abc", 0, 10000):
            with self.assertRaises(ValueError):
                F["simulationYear"](value, 2026)

    def test_the_first_weekday(self):
        self.assertEqual(4, F["firstWeekdayOf"](2026))  # Thursday
        self.assertEqual(1, F["firstWeekdayOf"](2024))  # Monday
        self.assertEqual(1, F["firstWeekdayOf"](None))


class ScheduleTests(unittest.TestCase):
    def schedule(self):
        return SimpleNamespace(Name="S", Hourly=" ".join(DAYS), Hours="", Days="1 2 3 4 5 6 7")

    def test_a_thursday_start_puts_the_weekend_on_days_three_and_four(self):
        original = self.schedule()
        shifted = F["weeklyInSimulation"](original, 4).Hourly.split()
        self.assertEqual(["Thu", "Fri", "Sat", "Sun", "Mon", "Tue", "Wed"], shifted)
        self.assertEqual(" ".join(DAYS), original.Hourly)  # the library stays

    def test_every_day_of_the_year_gets_its_own_day(self):
        for year in (2023, 2026, 2027):
            first = F["firstWeekdayOf"](year)
            shifted = F["weeklyInSimulation"](self.schedule(), first).Hourly.split()
            for offset in range(365):
                self.assertEqual(DAYS[(datetime(year, 1, 1)+timedelta(days=offset)).weekday()], shifted[offset % 7])

    def test_a_monday_start_and_a_daily_schedule_stay(self):
        monday = self.schedule()
        self.assertIs(monday, F["weeklyInSimulation"](monday, 1))
        daily = SimpleNamespace(Hourly="", Hours="0 24")
        self.assertIs(daily, F["weeklyInSimulation"](daily, 4))

    def test_the_b18_writes_the_shifted_schedule(self):
        self.assertIn("printsingledata(weeklyInSimulation(schedule_items, FirstWeekday),'Hours','Days')", SYSTEM)


class DeckTests(unittest.TestCase):
    def weekday(self, time, first, step=1.0):
        right = re.search(r"^WEEKDAY\s*=\s*(.*?)\s*!", TEMPLATE, flags=re.M).group(1)
        return eval(right, {"mod": lambda a, b: a % b, "int": int, "TIME": time, "STEP": step, "FIRSTWEEKDAY": first})

    def test_the_equation_follows_the_calendar_hour_by_hour(self):
        for step in (1.0, 0.25):
            for hour in range(1, 8761):
                date = datetime(2026, 1, 1)+timedelta(hours=hour-1)
                self.assertEqual(date.isoweekday(), self.weekday(float(hour), 4, step))

    def test_the_initial_time_is_the_first_day(self):
        self.assertEqual(4, self.weekday(0.0, 4))

    def test_the_count_of_the_block_holds_the_new_equations(self):
        block = re.search(r"^EQUATIONS (\d+)\nGRDREF.*?(?=^\*)", TEMPLATE, flags=re.M | re.S)
        self.assertEqual(int(block.group(1)), len(re.findall(r"^\w+\s*=", block.group(0), flags=re.M)))

    def test_the_constant_comes_from_the_system(self):
        self.assertIn("FIRSTWEEKDAY = @firstweekday", TEMPLATE)
        self.assertIn("variables['firstweekday']   = FirstWeekday", SYSTEM)


if __name__ == "__main__":
    unittest.main()
