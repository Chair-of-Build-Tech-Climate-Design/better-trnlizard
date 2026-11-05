"""Default and Options lines of the docstrings: parsing, the mouse-over text, and the Default stored on an empty input."""

import re
import unittest
from pathlib import Path

from test_updater_gh_glue import Document, LegacyGhPython, Param, Python3Script, RhinoCodeParam, ScriptVariable, UpdaterGlueTests
from test_updater_io_sync import load_updater


SCRIPTS = Path(__file__).resolve().parents[1] / "components"
SCRIPT = '''"""
Test component with a default and options.

Args:
    a (float): first
        Access: item
        Required: False
        Default: 0.5
    b (str): second
        Access: item
        Required: False
        Options: X, Y
    c (bool): third
        Access: item
        Required: False

Returns:
    r (object): output
        Access: item
"""
ghenv.Component.Name = "Lizard_Dflt"
'''


class ParsingTests(unittest.TestCase):
    updater = load_updater()

    def specs(self, lines):
        doc = '"""\nArgs:\n    a %s: text\n        Access: item\n        Required: False\n%s"""\n'
        return self.updater.parseDocstringIO(doc % ("(float)", lines))[0][0]

    def test_default_and_options_are_read(self):
        spec = self.specs("        Options: X, Y ,Z\n        Default: X Y\n")
        self.assertEqual(["X", "Y", "Z"], spec["options"])
        self.assertEqual("X Y", spec["default"])

    def test_a_param_without_them_has_neither(self):
        spec = self.specs("")
        self.assertEqual((None, []), (spec["default"], spec["options"]))

    def test_the_tooltip_adds_them_to_the_description(self):
        spec = dict(self.specs("        Default: 1\n        Options: 1, 2\n"))
        self.assertEqual("text\nOptions: 1, 2\nDefault: 1", self.updater.paramTooltip(spec))
        self.assertEqual("text", self.updater.paramTooltip(self.specs("")))

    def test_the_value_follows_the_type(self):
        cases = [("float", "1", ("float", 1.0)), ("int", "3", ("int", 3)), ("bool", "true", ("bool", True)), ("bool", "False", ("bool", False)),
                 ("str", "0 90", ("str", "0 90")), ("str", "1", ("str", "1")), ("object", "2", ("int", 2)), ("object", "0.5", ("float", 0.5)),
                 ("object", "False", ("bool", False)), ("object", "CRACK", ("str", "CRACK")), ("", "CRACK", ("str", "CRACK"))]
        for kind, text, expected in cases:
            spec = {"name": "a", "type": kind, "default": text}
            self.assertEqual(expected, self.updater.defaultValue(spec), (kind, text))

    def test_a_value_that_does_not_fit_is_refused(self):
        for kind, text in (("float", "abc"), ("int", "1.5"), ("bool", "yes"), ("Brep", "x")):
            with self.assertRaises(ValueError, msg=(kind, text)):
                self.updater.defaultValue({"name": "a", "type": kind, "default": text})


class RepositoryDocstringTests(unittest.TestCase):
    updater = load_updater()

    def declared(self):
        for path in sorted(SCRIPTS.glob("Lizard_*.py")):
            code = path.read_text(encoding="utf-8")
            for spec in self.updater.parseDocstringIO(code)[0] or []:
                if spec["default"] is not None or spec["options"]:
                    yield path.name, code, spec

    def test_every_default_is_usable(self):
        found = 0
        for name, code, spec in self.declared():
            if spec["default"] is None:
                continue
            found += 1
            where = (name, spec["name"])
            self.assertFalse(spec["required"], where)
            kind, value = self.updater.defaultValue(spec)
            if spec["options"]:
                self.assertIn(spec["default"], spec["options"], where)
            body = code.split('"""', 2)[2] + (SCRIPTS / "Lizard_Component.py").read_text(encoding="utf-8")  # shared defaults live there
            if kind in ("int", "float"):
                numbers = [float(n) for n in re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", body)]
                self.assertIn(float(value), numbers, where)
            elif kind == "str":
                self.assertIn(value, body, where)
        self.assertGreater(found, 0)


class GlueTests(UpdaterGlueTests):
    """The glue of Default and Options; only these tests, not the inherited ones."""

    def setUp(self):
        super().setUp()
        (self.folder / "Lizard_Dflt.py").write_text(SCRIPT, encoding="utf-8")
        for name in ("Lizard_Hygro.py", "Lizard_Rep.py"):
            (self.folder / name).unlink()

    def component(self, params=None, code=SCRIPT):
        inputs = params or [ScriptVariable(name) for name in "abc"]
        component = LegacyGhPython("Lizard_Dflt", inputs, [Param("r")], code=code)
        component.CreateAttributes()
        return component

    def update(self, component):
        doc = Document([component])
        result = self.run_updater(doc)
        self.apply_scheduled(doc)
        return result

    def test_an_input_that_is_not_optional_becomes_optional_in_a_current_component(self):
        component = self.component()
        self.update(component)
        self.run_updater(Document([component]))  # shows the report of the update before
        component.Params.Input[0].Optional = False
        self.update(component)
        self.assertTrue(component.Params.Input[0].Optional)

    def test_an_empty_input_of_a_current_component_gets_its_default_and_tooltip(self):
        component = self.component()
        self.update(component)
        a, b, c = component.Params.Input
        self.assertEqual([("GH_Number", 0.5)], a.Persistent)
        self.assertEqual("first\nDefault: 0.5", a.Description)
        self.assertEqual("second\nOptions: X, Y", b.Description)
        self.assertEqual(([], []), (b.Persistent, c.Persistent))
        self.assertEqual("", c.Description)

    def test_a_wired_input_stays_empty(self):
        component = self.component()
        component.Params.Input[0].AddSource(Param("wire"))
        self.update(component)
        self.assertEqual([], component.Params.Input[0].Persistent)

    def test_stored_data_is_kept(self):
        component = self.component()
        component.Params.Input[0].Persistent = [("GH_Number", 7.0)]
        self.update(component)
        self.assertEqual([("GH_Number", 7.0)], component.Params.Input[0].Persistent)

    def test_a_second_run_finds_nothing_to_do(self):
        component = self.component()
        self.update(component)
        doc = Document([component])
        self.run_updater(doc)
        self.assertEqual([], doc.scheduled)

    def test_a_locked_component_is_left_alone(self):
        component = self.component()
        self.update(component)
        component.Params.Input[0].Persistent = []
        component.Locked = True
        doc = Document([component])
        self.run_updater(doc)
        self.assertEqual([], doc.scheduled)
        self.assertEqual([], component.Params.Input[0].Persistent)

    def test_a_param_that_holds_no_data_is_reported_and_does_not_update_every_run(self):
        class NoData(ScriptVariable):
            PersistentDataCount = property(lambda self: (_ for _ in ()).throw(AttributeError("PersistentDataCount")))

        component = self.component([NoData("a"), ScriptVariable("b"), ScriptVariable("c")])
        self.update(component)
        doc = Document([component])
        log = self.run_updater(doc)[0]
        self.assertEqual([], doc.scheduled)
        self.assertTrue(any("cannot store its Default" in line for line in log), log)

    def test_a_new_input_gets_its_default_on_rhino8_with_the_tooltip_property(self):
        param = RhinoCodeParam("b")
        component = Python3Script("Lizard_Dflt", [param, RhinoCodeParam("c")], [Param("r")], code="old")
        component.CreateAttributes()
        self.update(component)
        a = component.Params.Input[0]
        self.assertEqual("a", a.Name)
        self.assertEqual("first\nDefault: 0.5", a.ToolTip)
        self.assertEqual([("GH_Number", 0.5)], a.Persistent)
        self.assertEqual("second\nOptions: X, Y", param.ToolTip)

    def test_a_userobject_component_has_the_default_stored(self):
        comp = self.updater.buildUserObjectComponent(
            "410755b1-224a-4c1e-a407-bf32fb45ea7e",
            {"code": SCRIPT, "info": self.updater.parseComponentInfo(SCRIPT, "Lizard_Dflt")}, [])
        self.assertEqual([("GH_Number", 0.5)], comp.Params.Input[0].Persistent)


# only the tests of this file, not those of the base class again
for _name in list(vars(UpdaterGlueTests)):
    if _name.startswith("test_") and _name not in vars(GlueTests):
        setattr(GlueTests, _name, None)
del UpdaterGlueTests


if __name__ == "__main__":
    unittest.main()
