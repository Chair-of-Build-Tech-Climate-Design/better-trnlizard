"""Regression check: generated decks must hide the Type65 online plotters by default.

TRNSYS Type65d parameter 9 ("Shut off Online w/o removing") is -1 to keep the
plotter hidden and >=0 to display it.  The deck used to carry ``showonline = 0``,
which kept every online plotter active: hidden ``TrnEXE64 /N /H`` batch runs
still redrew all plotters and crawled at roughly 5 % of the speed they reach
with ``showonline = -1`` (bit-identical results).
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

# Type65 plotters that Lizard_System.py writes through PrintOnline() into the deck.
ONLINE_PLOTTER_NAMES = (
    "Temperature",
    "HeatCool",
    "ElecBala",
    "AirQuality",
    "Irradiation",
    "Comfort",
    "AddOutput",
    "AddOutput2",
)
PARAMETER_9 = re.compile(r"^(\S+)[ \t]*! 9 Shut off Online w/o removing", re.MULTILINE)


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


def default_online_switch(system_source):
    """The module-level default of the online switch, executed from the real source."""
    namespace = {}
    execute_source_block(system_source, "Online = ", "Turn = 0", namespace)
    return namespace["Online"]


def map_online_variable(system_source, online):
    """Execute the real ``variables['online'] = Online`` statement of the System component."""
    namespace = {"Online": online, "variables": {}}
    execute_source_block(
        system_source,
        "            variables['online']",
        "            variables['ydaysim']",
        namespace,
    )
    return namespace["variables"]


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


def render_template_line(system_source, line, variables):
    """Substitute @variables exactly like the real printdck() does for plain template lines."""
    writer = DeckWriter()
    execute_source_block(
        system_source,
        "                p = re.compile('@(\\w+)')\n                m = p.search(lines)",
        "        dckout.close()\ndef runthermaldef",
        {
            "re": re,
            "lines": line,
            "variables": variables,
            "dckout": writer,
            "basestring": str,
            "str": Py2String,
        },
    )
    return writer.text


def load_print_online(system_source):
    namespace = {"lu_counter": 950}
    execute_source_block(system_source, "def PrintOnline(", "def PrintPrintegrator(", namespace)
    return namespace["PrintOnline"]


def trnsys_constant(deck_text, name):
    """Value TRNSYS assigns to an integer equation such as ``showonline = -1``."""
    match = re.search(r"^{}\s*=\s*(-?\d+)\b".format(re.escape(name)), deck_text, re.MULTILINE)
    if match is None:
        raise AssertionError("no integer assignment of {} in:\n{}".format(name, deck_text))
    return int(match.group(1))


class OnlinePlotterSwitchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.system_source = SYSTEM_SOURCE.read_text(encoding="utf-8-sig")
        cls.template_lines = load_template_lines()
        cls.print_online = staticmethod(load_print_online(cls.system_source))

    def render_deck(self, online=None):
        """Render the showonline equation and all PrintOnline plotters like the System component."""
        if online is None:
            online = default_online_switch(self.system_source)
        variables = map_online_variable(self.system_source, online)
        (template_line,) = [line for line in self.template_lines if line.startswith("showonline")]
        equation = render_template_line(self.system_source, template_line, variables)
        plotters = "".join(self.print_online(name=name) for name in ONLINE_PLOTTER_NAMES)
        return equation, plotters

    def test_default_deck_hides_online_plotters(self):
        equation, plotters = self.render_deck()

        self.assertRegex(equation, r"^showonline = -1\b")
        comment = equation.split("!", 1)[1]
        self.assertIn("-1", comment)
        self.assertIn(">=0", comment)

        switches = PARAMETER_9.findall(plotters)
        self.assertEqual(["showonline"] * len(ONLINE_PLOTTER_NAMES), switches)
        for switch in switches:
            self.assertEqual(-1, trnsys_constant(equation, switch))

    def test_explicitly_enabled_switch_shows_online_plotters(self):
        for online in (0, 1):
            with self.subTest(online=online):
                equation, plotters = self.render_deck(online)

                self.assertRegex(equation, r"^showonline = {}\b".format(online))
                for switch in PARAMETER_9.findall(plotters):
                    self.assertGreaterEqual(trnsys_constant(equation, switch), 0)

    def test_every_type65_plotter_reads_the_shared_switch(self):
        # PrintOnline() and the BSDF plotter are the only Type65 writers of the System component.
        switches = PARAMETER_9.findall(self.system_source)

        self.assertGreaterEqual(len(switches), 2)
        self.assertEqual({"showonline"}, set(switches))

    def test_online_placeholder_is_only_a_plain_assignment(self):
        # A negative value after an operator ('+ -1') cannot be parsed by TRNSYS.
        uses = [line for line in self.template_lines if "@online" in line]

        self.assertEqual(1, len(uses))
        self.assertRegex(uses[0], r"^showonline\s*=\s*@online\s*(!.*)?$")


if __name__ == "__main__":
    unittest.main()
