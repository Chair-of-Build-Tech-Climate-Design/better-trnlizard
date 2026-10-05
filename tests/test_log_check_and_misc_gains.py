"""Lizard_Log_Check and Lizard_Misc_Gains against their instances in the user's definition (Hyhole_DIN16798.ghx).

Log_Check: the canvas copy that shows the log summary in a Panel has the output ``output``; the script assigns it, the
docstring now declares it.  The four outputs the script never assigned (iteration_reached_timestep_count,
total_warning_count, last_warning_timestep, running_time) are removed, so both canvas copies are replacement cases.
Misc_Gains: the canvas copy wired to the Zone Regime has the input ``conv_part`` (slider "Convective Part [%/100]"),
which the script did not read; it now sets the convective part like ``ConvectivePart``.
The real scripts are executed with mock Grasshopper objects; the updater decisions use the pure functions of
Lizard_Updater with the param lists of the canvas copies.
"""

import contextlib
import io
import sys
import tempfile
import unittest
import warnings
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_updater_io_sync import load_updater  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_CHECK_SOURCE = REPO_ROOT / "Lizard_Log_Check.py"
MISC_GAINS_SOURCE = REPO_ROOT / "Lizard_Misc_Gains.py"

# outputs of the canvas copy e7ae18b2 that the script never assigned (removed from the script)
LOG_CHECK_OUTPUTS = ["iteration_reached_timestep_count", "total_warning_count", "last_warning_timestep", "running_time"]
LOG_CHECK_SEPARATOR = ("-------------------------------------log file outputs-----------------------------------------"
                       "----------------------------")
MISC_SEPARATOR = "--------------- MiscGain"


def run_script(path, namespace):
    """Execute a GhPython script with mock scriptcontext / Grasshopper modules; ``namespace`` holds its inputs."""
    kernel = ModuleType("Grasshopper.Kernel")
    kernel.GH_RuntimeMessageLevel = SimpleNamespace(Warning="WARNING", Error="ERROR")
    grasshopper = ModuleType("Grasshopper")
    grasshopper.Kernel = kernel
    scriptcontext = ModuleType("scriptcontext")
    scriptcontext.sticky = {}
    modules = {"Grasshopper": grasshopper, "Grasshopper.Kernel": kernel, "scriptcontext": scriptcontext}
    messages = []
    component = SimpleNamespace(AddRuntimeMessage=lambda level, text: messages.append((level, text)))
    namespace.setdefault("ghenv", SimpleNamespace(Component=component))
    with mock.patch.dict(sys.modules, modules), contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        exec(compile(path.read_text(encoding="utf-8-sig"), str(path), "exec"), namespace)
    return namespace, messages


class LogCheckTests(unittest.TestCase):
    def test_docstring_declares_only_output(self):
        inputs, outputs = load_updater().parseIONames(LOG_CHECK_SOURCE.read_text(encoding="utf-8-sig"))

        self.assertEqual(["Variant", "start_time"], inputs)   # start_time is not used by the script (kept as it is)
        self.assertEqual(["output"], outputs)

    def test_the_never_assigned_outputs_are_gone_from_the_script(self):
        source = LOG_CHECK_SOURCE.read_text(encoding="utf-8-sig")
        self.assertEqual([], [name for name in LOG_CHECK_OUTPUTS if name in source])

    def test_output_is_the_summary_of_the_logs(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            (project / "Daylight").mkdir()
            (project / "Daylight" / "trnRAD.log").write_text("start\nsuccessfully finished\n")
            (project / "Var1.lst").write_text("TRNSYS\nno problems\n")
            namespace, messages = run_script(LOG_CHECK_SOURCE, {"Variant": "x\tVar1\tx\t" + folder})

            self.assertEqual([], messages)
            self.assertEqual(
                "Variant: Var1\nDAYLIGHT PREPROCESSING COMPLETED!\n---------------------------------------------\n"
                "THERMAL SIMULATION COMPLETED!\n",
                namespace["output"],
            )
            self.assertEqual(namespace["output"], namespace["ghenv"].Component.Message)

            (project / "Var1.lst").write_text("a\n*** Fatal Error at time 12.0\nline 1\nline 2\nline 3\nline 4\nline 5\n")
            namespace, messages = run_script(LOG_CHECK_SOURCE, {"Variant": "x\tVar1\tx\t" + folder})
            self.assertIn("THERMAL SIMULATION CRASHED!", namespace["output"])
            self.assertIn("Fatal Error at time 12.0", namespace["output"])
            self.assertIn("line 4", namespace["output"])
            self.assertNotIn("line 5", namespace["output"])
            self.assertEqual("ERROR", messages[0][0])

    def test_the_copy_with_the_four_outputs_is_replaced(self):
        updater = load_updater()
        inputs, outputs = updater.parseIONames(LOG_CHECK_SOURCE.read_text(encoding="utf-8-sig"))
        plan = updater.planIOUpdate(["Variant", "start_time"], LOG_CHECK_OUTPUTS, inputs, outputs, False)

        self.assertEqual("remove", plan["kind"])
        self.assertEqual(LOG_CHECK_OUTPUTS, plan["removedOutputs"])
        self.assertEqual(["output"], plan["addedOutputs"])
        self.assertEqual([], plan["addedInputs"] + plan["removedInputs"])
        # wired by name: Variant and start_time keep their sources; no output keeps a name, so no recipient moves
        self.assertEqual([], updater.wiringPlan(LOG_CHECK_OUTPUTS, ["output"]))

    def test_the_copy_with_output_and_a_separator_output_is_replaced(self):
        # the separator output is not wanted in the script
        updater = load_updater()
        inputs, outputs = updater.parseIONames(LOG_CHECK_SOURCE.read_text(encoding="utf-8-sig"))
        plan = updater.planIOUpdate(["Variant"], ["output", LOG_CHECK_SEPARATOR], inputs, outputs, False)

        self.assertEqual("remove", plan["kind"])
        self.assertEqual([LOG_CHECK_SEPARATOR], plan["removedOutputs"])
        self.assertEqual(["start_time"], plan["addedInputs"])
        self.assertEqual([], plan["addedOutputs"])
        self.assertEqual([("output", 0, 0)], updater.wiringPlan(["output", LOG_CHECK_SEPARATOR], ["output"]))


MISC_DEFAULT = {
    "Name": "HUMID", "Othergain": 1, "Userdefined": 1, "Specificpower": 1.5, "Schedule": "", "Convaux": 0.6,
    "Convective": "INPUT 0.6*Q_ADDON_KJ", "Radiative": "INPUT 0.4*Q_ADDON_KJ", "Hum2": 0, "Annual": "", "Elpowerfrac": 1,
    "Context": "ABSOLUTE", "Category": "MISCELLANEOUS", "Heatbymisc": 0,
}


class MiscGainsTests(unittest.TestCase):
    def gain(self, **inputs):
        namespace = {MISC_SEPARATOR: None}
        namespace.update(inputs)
        namespace, messages = run_script(MISC_GAINS_SOURCE, namespace)
        self.assertEqual([], messages)
        return namespace["MiscGain"]

    def attributes(self, gain):
        return {key: getattr(gain, key) for key in MISC_DEFAULT}

    def test_docstring_declares_conv_part_after_convective_part(self):
        inputs, outputs = load_updater().parseDocstringIO(MISC_GAINS_SOURCE.read_text(encoding="utf-8-sig"))
        names = [spec["name"] for spec in inputs]

        self.assertEqual([MISC_SEPARATOR, "SpecificPower", "Schedule", "ConvectivePart", "conv_part", "Humidity",
                          "AnnualSchedule"], names)
        conv_part = inputs[names.index("conv_part")]
        self.assertEqual(("float", "item", False), (conv_part["type"], conv_part["access"], conv_part["required"]))
        self.assertEqual(["out", "-------------", "MiscGain"], [spec["name"] for spec in outputs])

    def test_convective_part_is_described_as_a_fraction(self):
        inputs, _ = load_updater().parseDocstringIO(MISC_GAINS_SOURCE.read_text(encoding="utf-8-sig"))
        description = [spec for spec in inputs if spec["name"] == "ConvectivePart"][0]["description"]

        self.assertIn("fraction (0-1)", description)
        self.assertNotIn("Watt", description)

    def test_both_canvas_copies_are_updated_in_place(self):
        updater = load_updater()
        inputs, outputs = updater.parseIONames(MISC_GAINS_SOURCE.read_text(encoding="utf-8-sig"))
        canvas_outputs = ["out", "-------------", "MiscGain"]
        wired = updater.planIOUpdate([MISC_SEPARATOR, "conv_part", "AnnualSchedule"], canvas_outputs, inputs, outputs, True)
        unwired = updater.planIOUpdate(
            [MISC_SEPARATOR, "SpecificPower", "Schedule", "ConvectivePart", "Humidity", "AnnualSchedule"],
            canvas_outputs, inputs, outputs, True,
        )

        self.assertEqual("add", wired["kind"])
        self.assertEqual([("SpecificPower", 1), ("Schedule", 2), ("ConvectivePart", 3), ("Humidity", 5)], wired["inputInsertions"])
        self.assertEqual("add", unwired["kind"])
        self.assertEqual([("conv_part", 4)], unwired["inputInsertions"])

    def test_defaults_are_unchanged(self):
        for inputs in ({}, {"SpecificPower": None, "Schedule": None, "ConvectivePart": None, "conv_part": None, "Humidity": None}):
            with self.subTest(inputs=inputs):
                self.assertEqual(MISC_DEFAULT, self.attributes(self.gain(**inputs)))

    def test_conv_part_sets_the_convective_and_radiative_part(self):
        for value, convective, radiative in ((0.9, "INPUT 0.9*Q_ADDON_KJ", "INPUT 0.1*Q_ADDON_KJ"),
                                             (0.25, "INPUT 0.25*Q_ADDON_KJ", "INPUT 0.75*Q_ADDON_KJ"),
                                             (1.0, "INPUT 1.0*Q_ADDON_KJ", "INPUT 0.0*Q_ADDON_KJ")):
            with self.subTest(conv_part=value):
                gain = self.gain(conv_part=value)
                self.assertEqual((value, convective, radiative), (gain.Convaux, gain.Convective, gain.Radiative))
                # the same as the input of the newer copies
                other = self.gain(ConvectivePart=value)
                self.assertEqual((other.Convaux, other.Convective, other.Radiative), (gain.Convaux, gain.Convective, gain.Radiative))

    def test_convective_part_wins_over_conv_part(self):
        gain = self.gain(ConvectivePart=0.7, conv_part=0.9)
        self.assertEqual((0.7, "INPUT 0.7*Q_ADDON_KJ", "INPUT 0.3*Q_ADDON_KJ"), (gain.Convaux, gain.Convective, gain.Radiative))
        gain = self.gain(ConvectivePart=None, conv_part=0.9)
        self.assertEqual("INPUT 0.9*Q_ADDON_KJ", gain.Convective)

    def test_specific_power_is_read(self):
        self.assertEqual(4.0, self.gain(SpecificPower=4.0).Specificpower)
        self.assertEqual(3.0, self.gain(Power=3.0).Specificpower)               # input name of older copies
        self.assertEqual(4.0, self.gain(SpecificPower=4.0, Power=3.0).Specificpower)
        self.assertEqual(3.0, self.gain(SpecificPower=None, Power=3.0).Specificpower)

    def test_switched_off_gain_is_none(self):
        namespace, _ = run_script(MISC_GAINS_SOURCE, {MISC_SEPARATOR: False, "conv_part": 0.9})
        self.assertIsNone(namespace["MiscGain"])


if __name__ == "__main__":
    unittest.main()
