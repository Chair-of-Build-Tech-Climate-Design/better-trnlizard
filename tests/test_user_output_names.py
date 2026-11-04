"""UserDefName of the output components: new names of the outputs, written as equations of the deck."""

import re
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = (ROOT / "components" / "Lizard_System.py").read_text(encoding="utf-8-sig")


def functions():
    namespace = {"re": re}
    block = re.search(r"^def outputPairs.*?(?=^def infiltrationAch)", SYSTEM, flags=re.M | re.S).group(0)
    exec(block, namespace)
    return namespace


F = functions()


def surface(labels, numbers):
    return SimpleNamespace(Type="SURFACE", NtypesShort=["{0}_S{1}".format(label, number) for label in labels for number in numbers])


def renamed(output, username="Floor", airnode=None, okey=()):
    return F["renamedOutputs"](username, F["outputPairs"](output, airnode or SimpleNamespace(Name="A1"), list(okey)))


class RenameTests(unittest.TestCase):
    def test_outputs_of_one_surface_get_the_label_as_prefix(self):
        self.assertEqual([("TSI_Floor", "TSI_S17"), ("TALM_Floor", "TALM_S17"), ("QALFL_Floor", "QALFL_S17")],
                         renamed(surface(["TSI", "TALM", "QALFL"], [17])))

    def test_several_surfaces_get_the_number_as_suffix(self):
        self.assertEqual([("TSI_Floor_S1", "TSI_S1"), ("TSI_Floor_S2", "TSI_S2")], renamed(surface(["TSI"], [1, 2])))

    def test_a_label_that_holds_the_separator_stays_whole(self):
        self.assertEqual([("A_SUM_Floor", "A_SUM_S3")], renamed(surface(["A_SUM"], [3])))

    def test_airnode_outputs(self):
        output = SimpleNamespace(Type="AIRNODE", NtypesShort=["TAIR", "QHEAT"])
        self.assertEqual([("TAIR_Room", "TAIR_A1"), ("QHEAT_Room", "QHEAT_A1")], renamed(output, "Room"))

    def test_comfort_outputs(self):
        output = SimpleNamespace(Type="COMFORT", NtypesShort=["PMV"])
        self.assertEqual([("PMV_Room", "PMV_C4")], renamed(output, "Room", SimpleNamespace(ComfId=[4])))
        self.assertEqual([("PMV_Room_C4", "PMV_C4"), ("PMV_Room_C5", "PMV_C5")], renamed(output, "Room", SimpleNamespace(ComfId=[4, 5])))

    def test_only_comfort_outputs_read_the_comfort_points(self):
        # an airnode without comfort points has no ComfId at all
        self.assertEqual([("TSI_Floor", "TSI_S1")], renamed(surface(["TSI"], [1]), airnode=SimpleNamespace()))


class ProblemTests(unittest.TestCase):
    def test_good_names_pass(self):
        self.assertIsNone(F["outputNameProblem"](["TSI_Floor", "TALM_Floor"]))

    def test_a_name_used_twice_is_a_problem_also_in_another_case(self):
        self.assertIn("used twice", F["outputNameProblem"](["TSI_Floor", "tsi_floor"]))

    def test_a_blank_is_a_problem(self):
        self.assertIn("character", F["outputNameProblem"](["TSI_Floor Room"]))


class DeckTests(unittest.TestCase):
    def test_the_new_names_become_equations(self):
        self.assertIn("useroutputnames = list(renamedoutputnames)", SYSTEM)
        self.assertIn("userdefoutnames[newname] = [original]", SYSTEM)

    def test_the_equations_are_written_for_all_of_them(self):
        loop = SYSTEM.split("useroutputnames = list(renamedoutputnames)")[1]
        self.assertIn("for ix, key in enumerate(useroutputnames):", loop)


if __name__ == "__main__":
    unittest.main()
