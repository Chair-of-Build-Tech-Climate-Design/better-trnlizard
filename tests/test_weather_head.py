"""The location block of Lizard_System.py reads only the head of the weather file: the file can lie on a slow drive.

The real helpers and the real block run on small files in which every line after the head would fail the parsing.
"""

import re
import tempfile
import unittest
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "components" / "Lizard_System.py"


def run_location_block(filename):
    text = SOURCE.read_text(encoding="utf-8-sig")
    first = text.index("def readWeatherHead(")
    helpers = text[first:text.index("def printtype9(", first)]
    start = text.index("        #Get location information")
    block = dedent(text[start:text.index("        #Library should be disconnected", start)])
    helpers, block = [re.sub(r"^(\s*)print (.*)$", r"\1print(\2)", part, flags=re.M) for part in (helpers, block)]
    opened = []
    closed = []

    class StreamReader:
        def __init__(self, path):
            self.file = open(path, "r")

        def ReadLine(self):
            line = self.file.readline()
            if not line:
                return None
            opened.append(line)
            return line.rstrip("\n")

        def Close(self):
            closed.append(True)
            self.file.close()

    def no_open(path, mode):
        raise AssertionError("open() of IronPython can fail in Rhino 8")

    scope = {"re": re, "weather_file": str(filename), "open": no_open, "System": SimpleNamespace(IO=SimpleNamespace(StreamReader=StreamReader)), "convertTry2017ETRS892WSG84": lambda x, y: (x, y)}
    exec(helpers, scope)
    exec(block, scope)
    return scope, opened


class WeatherHeadTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name)

    def location(self, name, head):
        path = self.folder/name
        path.write_text(head+"data line 1\ndata line 2\ndata line 3\n")
        scope, read = run_location_block(path)
        return scope, len(read)

    def test_epw(self):
        scope, read = self.location("a.epw", "LOCATION,Munich,BY,DEU,MIM,108660,48.14,11.57,1.0,520.0\n")
        self.assertEqual(("520.0", "-11.57", "48.14", "1.0", "-15.0"), (scope["altitude"], scope["longitude"], scope["latitude"], scope["gmt"], scope["timezone"]))
        self.assertEqual(1, read)

    def test_tmy3(self):
        scope, read = self.location("a.tm3", "690150,TWENTYNINE PALMS,CA,-8.0,34.3,-116.2,626\n")
        self.assertEqual(("626", "-8.0"), (scope["altitude"], scope["gmt"]))
        self.assertEqual(1, read)

    def test_tmy2(self):
        scope, read = self.location("a.tm2", " 14944 SIOUX_FALLS SD -6 N 43 34 W 96 44 435\n")
        self.assertEqual(("435", "96.44", "43.34", "-6"), (scope["altitude"], scope["longitude"], scope["latitude"], scope["gmt"]))
        self.assertEqual(1, read)

    def test_dwd_try(self):
        head = "header\nRechtswert : 4339500\nHochwert : 2730500\nHoehenlage : 515\n"
        scope, read = self.location("TRY2015_a.dat", head)
        self.assertEqual(("515", "4339500", "2730500"), (scope["altitude"], scope["longitude"], scope["latitude"]))
        self.assertEqual(4, read)

    def test_other_format_stops_at_the_data(self):
        head = "<userdefined> 520 m\n<longitude> -11.57\n<latitude> 48.14\n<gmt> 1\n<data>\n"
        scope, read = self.location("a.tmy", head)
        self.assertEqual(("520", "-11.57", "48.14", "1"), (scope["altitude"], scope["longitude"], scope["latitude"], scope["gmt"]))
        self.assertEqual(5, read)


if __name__ == "__main__":
    unittest.main()
