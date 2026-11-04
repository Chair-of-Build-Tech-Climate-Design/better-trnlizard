"""Lizard_Zone_Regime: one list input for every kind of ventilation."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
REGIME = (ROOT / "components" / "Lizard_Zone_Regime.py").read_text(encoding="utf-8-sig")


def run_regime(**inputs):
    namespace = dict(ghenv=SimpleNamespace(Component=SimpleNamespace()), **inputs)
    with patch.dict(sys.modules, {"scriptcontext": SimpleNamespace()}):
        exec(compile(REGIME, "Lizard_Zone_Regime.py", "exec"), namespace)
    return namespace["Regime"]


def infiltration():
    return SimpleNamespace(Type="INFILTRATION", Name="INF")


def mechanical():
    return SimpleNamespace(Type="VENTILATION", Name="VENT")


def stack(name):
    return SimpleNamespace(Type="STACKVENTILATION", Name=name)


class ListTests(unittest.TestCase):
    def test_every_kind_goes_to_its_place(self):
        inf, mech, first, second = infiltration(), mechanical(), stack("STVENT1"), stack("STVENT2")
        regime = run_regime(Ventilation=[second, inf, None, mech, first])
        self.assertEqual((inf, mech, first, second), (regime.Infiltration, regime.Mechvent, regime.Stvent1, regime.Stvent2))

    def test_single_definitions_on_the_old_inputs_still_work(self):
        inf, mech, first, second = infiltration(), mechanical(), stack("STVENT1"), stack("STVENT2")
        regime = run_regime(Infiltration=inf, Ventilation=mech, StackVentilation1=first, StackVentilation2=second)
        self.assertEqual((inf, mech, first, second), (regime.Infiltration, regime.Mechvent, regime.Stvent1, regime.Stvent2))

    def test_empty_list_sets_nothing(self):
        regime = run_regime(Ventilation=[])
        self.assertEqual(("", "", "", ""), (regime.Infiltration, regime.Mechvent, regime.Stvent1, regime.Stvent2))

    def test_two_of_one_kind_are_an_error(self):
        with self.assertRaisesRegex(ValueError, "Two ventilation definitions"):
            run_regime(Ventilation=[stack("STVENT1"), stack("STVENT1")])
        with self.assertRaisesRegex(ValueError, "Two ventilation definitions"):
            run_regime(Infiltration=infiltration(), Ventilation=[infiltration()])

    def test_other_objects_are_an_error(self):
        with self.assertRaisesRegex(ValueError, "Not a ventilation definition"):
            run_regime(Ventilation=[SimpleNamespace(Type="GAIN")])


if __name__ == "__main__":
    unittest.main()
