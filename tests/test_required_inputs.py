"""The line of required inputs that Lizard_Updater writes into a script, and requireInputs of Lizard_Component behind it."""

import ast
import re
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

from test_updater_gh_glue import Document, LegacyGhPython, Param, ScriptVariable, UpdaterGlueTests
from test_updater_io_sync import load_updater


COMPONENT = Path(__file__).resolve().parents[1] / "components" / "Lizard_Component.py"
SCRIPT = '''"""
Test component.

Args:
    a (float): first
        Access: item
        Required: True
    --------- part
    b (str): second
        Access: list
        Required: False
    c (str): third
        Access: item
        Required: True

Returns:
    r (object): output
        Access: item
"""
ghenv.Component.Name = "Lizard_Req"
r = a
'''
OPTIONAL_ONLY = SCRIPT.replace("Required: True", "Required: False")


class LineTests(unittest.TestCase):
    updater = load_updater()

    def test_the_line_names_the_required_inputs_after_the_docstring(self):
        lines = self.updater.stampCode(SCRIPT).split("\n")
        self.assertTrue(lines[0].startswith("# Lizard_Updater hash"))
        at = [i for i, line in enumerate(lines) if '"requireInputs"' in line]
        self.assertEqual(1, len(at))
        self.assertIn('(ghenv.Component, ["a", "c"])', lines[at[0]])
        self.assertEqual('"""', lines[at[0] - 1])

    def test_the_docstring_stays_the_docstring(self):
        self.assertEqual(ast.get_docstring(ast.parse(SCRIPT)), ast.get_docstring(ast.parse(self.updater.stampCode(SCRIPT))))

    def test_a_script_without_required_inputs_has_no_line(self):
        self.assertNotIn("requireInputs", self.updater.stampCode(OPTIONAL_ONLY))

    def test_the_hash_is_that_of_the_script_alone(self):
        stamped = self.updater.stampCode(SCRIPT)
        stored, body = self.updater.splitScriptHash(stamped)
        self.assertEqual(SCRIPT, body)
        self.assertEqual(self.updater.getHash(SCRIPT), stored)
        self.assertFalse(self.updater.isChangedByHand(stamped))
        self.assertFalse(self.updater.isChangedByHand(stamped.replace("\n", "\r\n")))
        self.assertEqual(stamped, self.updater.stampCode(stamped))

    def test_a_change_by_hand_in_the_script_is_still_found(self):
        stamped = self.updater.stampCode(SCRIPT).replace("r = a", "r = 2 * a")
        self.assertTrue(self.updater.isChangedByHand(stamped))

    def test_a_script_without_docstring_has_the_line_at_its_top(self):
        code = 'import os\n"""\nArgs:\n    a (float): first\n        Access: item\n        Required: True\n"""\n'
        lines = self.updater.stampCode(code).split("\n")
        self.assertIn('"requireInputs"', lines[1])
        self.assertEqual("import os", lines[2])

    def test_the_line_does_nothing_without_the_shared_function(self):
        line = self.updater.requiredLine(SCRIPT)
        scriptcontext = ModuleType("scriptcontext")
        scriptcontext.doc = SimpleNamespace(Path="doc")
        for sticky in ({}, {"doc": {}}):
            scriptcontext.sticky = sticky
            with mock.patch.dict(sys.modules, {"scriptcontext": scriptcontext}):
                exec(line, {"ghenv": SimpleNamespace(Component=None)})

    def test_the_line_calls_the_shared_function(self):
        calls = []
        scriptcontext = ModuleType("scriptcontext")
        scriptcontext.doc = SimpleNamespace(Path="doc")
        scriptcontext.sticky = {"doc": {"requireInputs": lambda component, names: calls.append((component, names))}}
        with mock.patch.dict(sys.modules, {"scriptcontext": scriptcontext}):
            exec(self.updater.requiredLine(SCRIPT), {"ghenv": SimpleNamespace(Component="comp")})
        self.assertEqual([("comp", ["a", "c"])], calls)


class RepositoryTests(unittest.TestCase):
    updater = load_updater()

    def required(self, script):
        code = (COMPONENT.parent / (script + ".py")).read_text(encoding="utf-8")
        return [p["name"] for p in self.updater.parseDocstringIO(code)[0] or [] if p["required"]]

    def test_the_updater_needs_no_shared_function(self):
        self.assertEqual([], self.required("Lizard_Updater"))

    def test_a_required_input_has_no_default(self):
        for path in COMPONENT.parent.glob("Lizard_*.py"):
            for param in self.updater.parseDocstringIO(path.read_text(encoding="utf-8"))[0] or []:
                self.assertFalse(param["required"] and param["default"] is not None, (path.name, param["name"]))

    def test_inputs_the_scripts_work_without_stay_optional(self):
        for script, name in (("Lizard_Component", "Hemisphere"), ("Lizard_Hygro", "Settings"), ("Lizard_Equipment_Gains", "ScheduleEquipmentGain"),
                             ("Lizard_System", "Multizone"), ("Lizard_Thermal_Airnode", "SurfaceInfo")):
            self.assertNotIn(name, self.required(script), script)


class RequireInputsTests(unittest.TestCase):
    def setUp(self):
        text = COMPONENT.read_text(encoding="utf-8")
        first = text.rindex("def requireInputs(component, names):")
        block = text[first:text.index("def solidFaces(solid):", first)]
        self.exits = []
        self.scope = {"gh": SimpleNamespace(GH_RuntimeMessageLevel=SimpleNamespace(Error="Error")),
                      "sys": SimpleNamespace(exit=lambda: self.exits.append(True))}
        exec(block, self.scope)

    def component(self, **counts):
        self.messages = []
        params = [SimpleNamespace(Name=name, VolatileDataCount=count) for name, count in counts.items()]
        return SimpleNamespace(Params=SimpleNamespace(Input=params), AddRuntimeMessage=lambda level, text: self.messages.append((level, text)))

    def test_inputs_with_data_pass(self):
        self.scope["requireInputs"](self.component(a=1, b=0), ["a"])
        self.assertEqual(([], []), (self.messages, self.exits))

    def test_a_missing_input_stops_with_an_error_that_names_it(self):
        self.scope["requireInputs"](self.component(a=0, b=2, c=0), ["a", "b", "c"])
        self.assertEqual([("Error", "Required input without data: a, c")], self.messages)
        self.assertEqual([True], self.exits)

    def test_a_port_that_does_not_exist_is_not_reported(self):
        self.scope["requireInputs"](self.component(a=1), ["a", "gone"])
        self.assertEqual(([], []), (self.messages, self.exits))

    def test_the_function_is_shared(self):
        self.assertIn('sc.sticky[sc.doc.Path]["requireInputs"]', COMPONENT.read_text(encoding="utf-8"))


class GlueTests(UpdaterGlueTests):
    """Updates of a component whose code is current but whose line of required inputs is not."""

    def setUp(self):
        super().setUp()
        (self.folder / "Lizard_Req.py").write_text(SCRIPT, encoding="utf-8")
        for name in ("Lizard_Hygro.py", "Lizard_Rep.py"):
            (self.folder / name).unlink()

    def component(self, code):
        inputs = [ScriptVariable(name) for name in ("a", "--------- part", "b", "c")]
        component = LegacyGhPython("Lizard_Req", inputs, [Param("r")], code=code)
        component.CreateAttributes()
        return component

    def test_a_current_stamped_script_gets_the_line(self):
        old = "# Lizard_Updater hash of this script, do not edit: %s\n%s" % (self.updater.getHash(SCRIPT), SCRIPT)
        component = self.component(old)
        doc = Document([component])
        _, updated, _, errors = self.run_updater(doc)
        self.assertEqual(["Lizard_Req"], updated)
        self.assertEqual([], errors)
        self.apply_scheduled(doc)
        self.assertEqual(self.updater.stampCode(SCRIPT), component.Code)

    def test_a_script_with_the_line_is_left_alone(self):
        for code in (self.updater.stampCode(SCRIPT), self.updater.stampCode(SCRIPT).replace("\n", "\r\n")):
            doc = Document([self.component(code)])
            _, updated, skipped, _ = self.run_updater(doc)
            self.assertEqual(([], ["Lizard_Req"]), (updated, skipped))

    def test_the_line_follows_the_docstring(self):
        stale = self.updater.stampCode(SCRIPT.replace("Required: True", "Required: False", 1))
        stale = stale.replace(self.updater.getHash(SCRIPT.replace("Required: True", "Required: False", 1)), self.updater.getHash(SCRIPT))
        stale = stale.replace("Required: False\n    --------- part", "Required: True\n    --------- part")
        component = self.component(stale)
        doc = Document([component])
        _, updated, _, _ = self.run_updater(doc)
        self.assertEqual(["Lizard_Req"], updated)
        self.apply_scheduled(doc)
        self.assertIn('["a", "c"]', component.Code)


for _name in list(vars(UpdaterGlueTests)):
    if _name.startswith("test_") and _name not in vars(GlueTests):
        setattr(GlueTests, _name, None)
del UpdaterGlueTests


if __name__ == "__main__":
    unittest.main()
