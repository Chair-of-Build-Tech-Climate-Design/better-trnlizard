"""Lizard_Stack_Ventilation_1 / _2 write the two stack ventilations of an airnode (STVENT1 / STVENT2).

Lizard_System and the deck template support two stack ventilations: STVENT1 runs during its schedule, STVENT2 in the
remaining hours (y_nfl uses not(sched_sv)), each with its own thresholds and maximum air change.  Lizard_System only
switches the second one on for a ventilation named STVENT2, so the second component must write that name (a copy of
component 1 that still writes STVENT1 leaves tambon_sv2 at 1000, i.e. off).

The real component scripts are executed with mock Grasshopper objects (Python 2 print statements are turned into calls).
"""

import re
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_SOURCE = REPO_ROOT / "Lizard_System.py"


def run_component(number, **inputs):
    path = REPO_ROOT / f"Lizard_Stack_Ventilation_{number}.py"
    source = re.sub(r"^(\s*)print (.+)$", r"\1print(\2)", path.read_text(encoding="utf-8-sig"), flags=re.M)
    scriptcontext = ModuleType("scriptcontext")
    scriptcontext.sticky = {}
    component = SimpleNamespace()
    namespace = {
        "ghenv": SimpleNamespace(Component=component),
        "----------- StackVentilation": None,
        "EffOpeningAreaBottom": 0, "OrFloorRelatedEffOpAreaBottom": 0, "EffOpeningAreaTop": 0,
        "OrFloorRelatedEffOpAreaTop": 0, "HeightDifference": 1, "ONTemperatureAbove": 23, "OFFTemperatureBelow": 22,
        "ONTairOutsideAbove": 0, "ONTairOutside24hAbove": 0, "Schedule": "NightVent", "MaxAirChange": 2.5,
    }
    namespace.update(inputs)
    saved = sys.modules.get("scriptcontext")
    sys.modules["scriptcontext"] = scriptcontext
    try:
        exec(compile(source, str(path), "exec"), namespace)
    finally:
        if saved is None:
            sys.modules.pop("scriptcontext", None)
        else:
            sys.modules["scriptcontext"] = saved
    return namespace[f"StackVentilation{number}"], component


class StackVentilationComponentTests(unittest.TestCase):
    def test_component_1_writes_stvent1(self):
        vent, component = run_component(1)
        self.assertEqual(("STVENT1", "INPUT 1*ACR_SV1", "STACKVENTILATION"), (vent.Name, vent.Airchange, vent.Type))
        self.assertEqual(("Lizard_Stack_Ventilation_1", "Stack Ventilation 1"), (component.Name, component.NickName))

    def test_component_2_writes_stvent2_with_its_own_inputs(self):
        vent, component = run_component(2)
        self.assertEqual(("STVENT2", "INPUT 1*ACR_SV2", "STACKVENTILATION"), (vent.Name, vent.Airchange, vent.Type))
        self.assertEqual(("Lizard_Stack_Ventilation_2", "Stack Ventilation 2"), (component.Name, component.NickName))
        self.assertEqual((23, 22, 0, 0, 2.5), (vent.Tairon, vent.Tairoff, vent.Tambon, vent.Tamb24on, vent.Maxach))

    def test_both_components_declare_the_same_inputs(self):
        def inputs(number):
            doc = (REPO_ROOT / f"Lizard_Stack_Ventilation_{number}.py").read_text(encoding="utf-8-sig").split('"""')[1]
            return re.findall(r"^\s{4}(\S+) \(object\)", doc.split("Args:")[1].split("Returns:")[0], flags=re.M)
        self.assertEqual(inputs(1), inputs(2))

    def test_system_reads_the_humidity_control_of_stvent2_into_its_own_variable(self):
        source = SYSTEM_SOURCE.read_text(encoding="utf-8-sig")
        branch = source.split("ventilation_item.Name == 'STVENT2':\n                variables['taircomp_sv2']")[1]
        branch = branch.split("elif ventilation_item.Type == 'VENTILATION':")[0]
        self.assertIn("variables['humctrl_sv2'] = ventilation_item.Humctrl", branch)
        self.assertNotIn("variables['humctrl_sv1']", branch)


if __name__ == "__main__":
    unittest.main()
