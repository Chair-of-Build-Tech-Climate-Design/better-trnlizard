"""Lizard_Window_Settings: declared input types, and numeric inputs that arrive as text from a Panel."""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "components" / "Lizard_Window_Settings.py"


EXPECTED_TYPES = {
    "Name": "str", "WinID": "int",
    "FrameFraction": "float", "FrameConduction": "float",
    "ShadingMovable": "str", "ShadingFractionExt": "float", "ShadingFractionInt": "float",
    "ShadingActive": "float", "ShadingNonActive": "float", "ActiveIfTairRoomAbove": "float",
    "Hinside": "float", "Houtside": "float",
    "RadMaterial0": "str", "RadMaterial1": "str", "ShadingGroup": "str",
}


def run_script(**inputs):
    scope = dict(inputs)
    exec(compile(SCRIPT.read_text(encoding="utf-8-sig"), str(SCRIPT), "exec"), scope)
    return scope["Settings"]


def panel_inputs():
    return dict(Name="W", WinID="7300", FrameFraction="20", FrameConduction="1.3", ShadingMovable="NON",
                ShadingFractionExt="0", ShadingFractionInt="0", ShadingActive="300", ShadingNonActive="200",
                ActiveIfTairRoomAbove="22", Hinside="11", Houtside="64", RadMaterial0="glass_72",
                RadMaterial1="glass_72", ShadingGroup="A")


class DeclaredTypes(unittest.TestCase):
    def test_every_input_declares_its_type(self):
        doc = re.search(r'"""(.*?)"""', SCRIPT.read_text(encoding="utf-8-sig"), re.DOTALL).group(1)
        args = doc[doc.index("Args:"):doc.index("Returns:")]
        declared = dict(re.findall(r"^    (\w+) \((\w+)\):", args, re.MULTILINE))
        self.assertEqual(EXPECTED_TYPES, declared)


class PanelInputs(unittest.TestCase):
    """A Panel sends text; a component placed before the types were declared keeps its default hint."""

    def test_text_gives_the_same_settings_as_numbers(self):
        text = run_script(**panel_inputs())
        numbers = run_script(**dict(panel_inputs(), WinID=7300, FrameFraction=20.0, FrameConduction=1.3,
                                    ShadingFractionExt=0.0, ShadingFractionInt=0.0, ShadingActive=300.0,
                                    ShadingNonActive=200.0, ActiveIfTairRoomAbove=22.0, Hinside=11.0, Houtside=64.0))
        self.assertEqual(vars(numbers), vars(text))

    def test_written_values(self):
        s = run_script(**panel_inputs())
        self.assertEqual("WIN_W_7300", s.Construction)
        self.assertEqual(7300, s.Winid)
        self.assertAlmostEqual(0.2, s.Framefrac)
        self.assertEqual(1.3, s.Uframe)
        self.assertEqual(6.01, s.Cframe)
        self.assertAlmostEqual(300 * 3.6, s.Shadeclose)
        self.assertAlmostEqual(200 * 3.6, s.Shadeopen)
        self.assertEqual(22.0, s.Shdtairabove)
        self.assertEqual(11.0, s.Hinside)
        self.assertEqual(64.0, s.Houtside)

    def test_float_win_id_keeps_the_construction_name(self):
        self.assertEqual("WIN_W_7300", run_script(**dict(panel_inputs(), WinID=7300.0)).Construction)


if __name__ == "__main__":
    unittest.main()
