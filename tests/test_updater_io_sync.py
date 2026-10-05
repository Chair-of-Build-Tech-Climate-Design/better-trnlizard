"""Lizard_Updater: keep existing script components in sync with the inputs/outputs declared in the docstring of their script.

The decision logic is pure Python (no Rhino/Grasshopper use) and is tested here directly; System, Rhino, Grasshopper and
scriptcontext are stubbed only so that the module can be imported.  The Grasshopper glue is exercised in
test_updater_gh_glue.py against fake Grasshopper objects.
"""

import ast
import importlib.util
import re
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
UPDATER_SOURCE = REPO_ROOT / "Lizard_Updater.py"


def load_updater(extra_modules=None):
    """Lizard_Updater.py as a module with System, Rhino, Grasshopper and scriptcontext stubbed (``ghenv`` is absent, so the
    plain-script entry point does not run)."""
    grasshopper = ModuleType("Grasshopper")
    grasshopper.Kernel = ModuleType("Grasshopper.Kernel")
    modules = {name: ModuleType(name) for name in ("System", "Rhino", "scriptcontext")}
    modules.update({"Grasshopper": grasshopper, "Grasshopper.Kernel": grasshopper.Kernel})
    modules["scriptcontext"].sticky = {}
    modules.update(extra_modules or {})
    with mock.patch.dict(sys.modules, modules):
        spec = importlib.util.spec_from_file_location("Lizard_Updater_under_test", UPDATER_SOURCE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


def old_parser(code):
    """The docstring parser of the updater before this change (Lizard_Updater._parseIOFromScript of d2a3ce8)."""
    match = re.search(r'"""(.*?)"""', code, re.DOTALL)
    if not match:
        return [], []
    inputs, outputs, section = [], [], None
    for line in match.group(1).split("\n"):
        if line.strip() == "Args:":
            section = "in"
            continue
        if line.strip() == "Returns:":
            section = "out"
            continue
        if section and re.match(r"^    \S", line):
            m = re.match(r"^    ([^(:]+?)(?:\s*\([^)]*\))?\s*:\s", line)
            name = m.group(1).strip() if m else line.strip()
            (inputs if section == "in" else outputs).append(name)
    return inputs, outputs


DOCSTRING = '''"""
Some component.
-

Args:
    BRep (Brep): surfaces
        Access: list
        Required: True
    ------------------ hygrothermal
    depth (float): depth in m: from side 2
        Access: item
        Required: False
    data (object): a tree
        Access: tree
    flag (bool): no metadata lines

Returns:
    out (object): log
        Access: item
    Result (str): result
        Access: item
"""
x = 1
'''


class UpdaterModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.updater = load_updater()

    # ------------------------------------------------------------------ docstring IO

    def test_docstring_specs_carry_name_type_description_access_required_and_separators(self):
        inputs, outputs = self.updater.parseDocstringIO(DOCSTRING)

        self.assertEqual(["BRep", "------------------ hygrothermal", "depth", "data", "flag"], [p["name"] for p in inputs])
        self.assertEqual(["Brep", "", "float", "object", "bool"], [p["type"] for p in inputs])
        self.assertEqual(["list", "item", "item", "tree", "item"], [p["access"] for p in inputs])
        self.assertEqual([True, False, False, False, False], [p["required"] for p in inputs])
        self.assertEqual([False, True, False, False, False], [p["separator"] for p in inputs])
        self.assertEqual("depth in m: from side 2", inputs[2]["description"])
        self.assertEqual(["out", "Result"], [p["name"] for p in outputs])

    def test_missing_sections_are_none_not_empty(self):
        self.assertEqual((None, None), self.updater.parseDocstringIO('"""no sections"""\n'))
        self.assertEqual((None, None), self.updater.parseDocstringIO("x = 1\n"))
        inputs, outputs = self.updater.parseDocstringIO('"""\nArgs:\n    a (int): x\n"""\n')
        self.assertEqual(["a"], [p["name"] for p in inputs])
        self.assertIsNone(outputs)
        self.assertEqual((["a"], []), self.updater.parseIONames('"""\nArgs:\n    a (int): x\n"""\n'))

    def test_names_are_the_ones_of_the_parser_of_before_for_every_script_of_the_repo(self):
        for path in sorted(REPO_ROOT.glob("Lizard_*.py")):
            with self.subTest(script=path.name):
                code = path.read_text(encoding="utf-8-sig")
                self.assertEqual(old_parser(code), self.updater.parseIONames(code))

    def test_crlf_scripts_parse_like_lf_scripts(self):
        self.assertEqual(self.updater.parseDocstringIO(DOCSTRING),
                         self.updater.parseDocstringIO(DOCSTRING.replace("\n", "\r\n")))

    # ------------------------------------------------------------------ code comparison

    def test_code_comparison_ignores_line_endings_bom_and_trailing_white_space(self):
        code = "a = 1\nb = 2\n"
        for variant in ("a = 1\r\nb = 2\r\n", "\ufeffa = 1\nb = 2", "a = 1\rb = 2\n\n  \n"):
            with self.subTest(variant=variant):
                self.assertEqual(self.updater.getHash(code), self.updater.getHash(variant))
                self.assertIsNone(self.updater.firstDiff(code, variant))
        self.assertNotEqual(self.updater.getHash(code), self.updater.getHash("a = 1\nb = 3\n"))
        self.assertIn("line 2", self.updater.firstDiff(code, "a = 1\nb = 3\n"))
        self.assertEqual(self.updater.getHash(""), self.updater.getHash(None))

    # ------------------------------------------------------------------ insertion indices

    def test_new_params_go_right_after_their_docstring_predecessor(self):
        plan = self.updater.insertionPlan
        self.assertEqual([("x", 1)], plan(["a", "b"], ["a", "x", "b"]))
        self.assertEqual([("x", 0)], plan(["a", "b"], ["x", "a", "b"]))
        self.assertEqual([("x", 2), ("y", 3)], plan(["a", "b"], ["a", "b", "x", "y"]))
        self.assertEqual([("x", 1), ("y", 2), ("z", 4)], plan(["a", "b"], ["a", "x", "y", "b", "z"]))
        self.assertEqual([("x", 0), ("y", 1)], plan([], ["x", "y"]))
        self.assertEqual([], plan(["a", "b"], ["a", "b"]))
        # existing params in another order stay where they are; the new one follows its predecessor
        self.assertEqual([("x", 2)], plan(["b", "a"], ["a", "x", "b"]))

    def test_applying_the_insertions_one_after_the_other_gives_the_docstring_order(self):
        for current, target in ((["a", "b", "c"], ["a", "x", "b", "y", "c", "z"]), (["a"], ["w", "a", "x"]), ([], ["p"])):
            with self.subTest(current=current, target=target):
                working = list(current)
                for name, index in self.updater.insertionPlan(current, target):
                    working.insert(index, name)
                self.assertEqual(target, working)

    # ------------------------------------------------------------------ IO plan

    def plan(self, current_in, current_out, target_in, target_out, standard_output=False):
        return self.updater.planIOUpdate(current_in, current_out, target_in, target_out, standard_output)

    def test_identical_io_needs_nothing(self):
        result = self.plan(["a", "b"], ["r"], ["a", "b"], ["r"])
        self.assertEqual("none", result["kind"])
        self.assertEqual([], result["inputInsertions"] + result["outputInsertions"])

    def test_additions_only_are_inserted_in_place(self):
        hygro_now = ["BRep", "Settings", "------------------ hygrothermal", "datafile_assembly"]
        new = ["write_report", "report_interval", "add_heat_depth", "add_heat", "layer_min_div"]
        result = self.plan(hygro_now, ["SurfaceInfo"], hygro_now + new, ["SurfaceInfo"])

        self.assertEqual("add", result["kind"])
        self.assertEqual(new, result["addedInputs"])
        self.assertEqual([(name, 4 + k) for k, name in enumerate(new)], result["inputInsertions"])
        self.assertEqual([], result["removedInputs"] + result["removedOutputs"] + result["outputInsertions"])

    def test_added_output_index_counts_the_standard_output_param(self):
        # the component shows the code output 'out' at index 0, the docstring does not list it
        result = self.plan(["a"], ["out", "r"], ["a"], ["r", "s"], standard_output=True)
        self.assertEqual("add", result["kind"])
        self.assertEqual([("s", 2)], result["outputInsertions"])
        result = self.plan(["a"], ["out", "r"], ["a"], ["s", "r"], standard_output=True)
        self.assertEqual([("s", 1)], result["outputInsertions"])
        # listed in the docstring: an ordinary param
        result = self.plan(["a"], ["out", "r"], ["a"], ["out", "r", "s"], standard_output=True)
        self.assertEqual("add", result["kind"])
        self.assertEqual([("s", 2)], result["outputInsertions"])

    def test_code_output_listed_in_the_docstring_but_hidden_on_the_component_is_not_added(self):
        result = self.plan(["a"], ["r"], ["a"], ["out", "r"], standard_output=False)
        self.assertEqual("none", result["kind"])
        self.assertTrue(any("out" in note for note in result["notes"]))

    def test_any_removal_or_rename_needs_a_replacement(self):
        result = self.plan(["a", "b", "c"], ["r"], ["a", "c", "d"], ["r"])
        self.assertEqual("remove", result["kind"])
        self.assertEqual(["b"], result["removedInputs"])
        self.assertEqual(["d"], result["addedInputs"])
        # insertions are counted on the list without the removed params
        self.assertEqual([("d", 2)], result["inputInsertions"])

        renamed = self.plan(["a"], ["r"], ["a"], ["result"])
        self.assertEqual("remove", renamed["kind"])
        self.assertEqual(["r"], renamed["removedOutputs"])
        self.assertEqual(["result"], renamed["addedOutputs"])

    def test_order_only_differences_keep_the_params(self):
        result = self.plan(["a", "b"], ["r", "s"], ["b", "a"], ["r", "s"])
        self.assertEqual("order", result["kind"])
        self.assertTrue(result["reorderedInputs"])
        self.assertFalse(result["reorderedOutputs"])
        added = self.plan(["b", "a"], ["r"], ["a", "x", "b"], ["r"])
        self.assertEqual("add", added["kind"])
        self.assertTrue(added["reorderedInputs"])

    def test_duplicate_names_cannot_be_mapped(self):
        self.assertEqual("ambiguous", self.plan(["a", "a"], ["r"], ["a"], ["r"])["kind"])
        self.assertEqual("ambiguous", self.plan(["a"], ["r"], ["a", "a"], ["r"])["kind"])

    def test_a_missing_docstring_section_leaves_that_side_alone(self):
        result = self.plan(["a", "b"], ["r"], None, ["r", "s"])
        self.assertEqual("add", result["kind"])
        self.assertEqual([], result["removedInputs"])
        self.assertEqual([("s", 1)], result["outputInsertions"])
        self.assertEqual("none", self.plan(["a"], ["r"], None, None)["kind"])

    # ------------------------------------------------------------------ action

    def test_action_per_case(self):
        decide = self.updater.decideAction
        none = {"kind": "none"}
        order = {"kind": "order"}
        add = {"kind": "add"}
        remove = {"kind": "remove"}
        ambiguous = {"kind": "ambiguous"}

        self.assertEqual("skip", decide(False, none, False, False))
        self.assertEqual("skip", decide(False, order, False, False))
        self.assertEqual("code", decide(True, none, False, False))
        self.assertEqual("code", decide(True, order, True, False))
        self.assertEqual("add", decide(True, add, False, False))
        self.assertEqual("add", decide(False, add, False, False))      # code already new, params missing
        self.assertEqual("add", decide(True, add, True, False))        # in place inside a cluster
        self.assertEqual("replace", decide(True, remove, False, False))
        self.assertEqual("replace", decide(False, remove, False, False))
        self.assertEqual("manual", decide(True, remove, True, False))  # no replacement inside clusters
        self.assertEqual("locked", decide(True, remove, False, True))  # the old copy left by an earlier replacement
        self.assertEqual("manual", decide(True, ambiguous, False, False))

    # ------------------------------------------------------------------ wiring and label

    def test_wires_follow_the_param_names(self):
        self.assertEqual(
            [("a", 0, 0), ("c", 2, 1), ("x", 3, 3)],
            self.updater.wiringPlan(["a", "b", "c", "x"], ["a", "c", "d", "x"]),
        )
        self.assertEqual([], self.updater.wiringPlan(["a"], ["b"]))
        self.assertEqual([("b", 2, 0)], self.updater.wiringPlan(["a", "a", "b"], ["b", "a", "a"]))  # duplicates are not wired

    def test_group_label_names_the_removed_params_and_asks_for_a_check(self):
        label = self.updater.replacementLabel("Lizard_Hygro", ["Settings", "old_in"], ["SurfaceInfo"])
        for fragment in ("Lizard_Hygro", "inputs removed: Settings, old_in", "outputs removed: SurfaceInfo", "locked", "delete"):
            self.assertIn(fragment, label)
        self.assertNotIn("outputs removed", self.updater.replacementLabel("X", ["a"], []))

    # ------------------------------------------------------------------ archive copy without wires

    def test_param_sources_are_removed_from_the_archive_xml_without_breaking_its_counts(self):
        xml = (
            '<chunk name="InputParam" index="0">\n'
            '  <items count="4">\n'
            '    <item name="Name" type_name="gh_string" type_code="10">BRep</item>\n'
            '    <item name="Source" index="0" type_name="gh_guid" type_code="9">ccf24e75-8176-42f7-ac26-ab202764eda1</item>\n'
            '    <item name="Source" index="1" type_name="gh_guid" type_code="9">0de43613-c601-4836-b19f-4fdd5af49109</item>\n'
            '    <item name="SourceCount" type_name="gh_int32" type_code="3">2</item>\n'
            '  </items>\n'
            '</chunk>\n'
            '<item name="CodeInput" type_name="gh_string" type_code="10">s = "&lt;item name=&quot;Source&quot; "</item>\n'
        )
        stripped = self.updater.stripParamSources(xml)

        self.assertNotIn('<item name="Source" ', stripped)
        self.assertIn('<item name="SourceCount" type_name="gh_int32" type_code="3">0</item>', stripped)
        self.assertEqual(xml.count("<item "), stripped.count("<item "))   # the items counts stay valid
        self.assertIn("BRep", stripped)
        self.assertIn('s = "&lt;item name=&quot;Source&quot; "', stripped)   # code text untouched

    # ------------------------------------------------------------------ component kinds and type hints

    def test_component_kinds(self):
        kind = self.updater.classifyScriptComponent
        self.assertEqual(self.updater.KIND_GHPYTHON, kind("ZuiPythonComponent", True, False))
        self.assertEqual(self.updater.KIND_PYTHON3, kind("Python3Component", False, True))
        self.assertEqual(self.updater.KIND_IRONPYTHON2, kind("IronPython2Component", False, True))
        self.assertIsNone(kind("CSharpComponent", False, True))   # never put Python code into another language
        self.assertIsNone(kind("GH_Component", False, False))

    def test_type_hint_lookup(self):
        hint = self.updater.typeHintSpec
        self.assertEqual("39fbc626-7a01-46ab-a18e-ec1c0c41685b", hint("float")["legacyId"])
        self.assertEqual("37261734-eec7-4f50-b6a8-b8d1f3c4396b", hint("str")["legacyId"])
        self.assertEqual("d60527f5-b5af-4ef6-8970-5f96fe412559", hint("bool")["legacyId"])
        self.assertEqual("48d01794-d3d8-4aef-990e-127168822244", hint("int")["legacyId"])
        self.assertEqual("2ceb0405-fdfe-403d-a4d6-8786da45fb9d", hint("Brep")["legacyId"])
        self.assertEqual("System.Double", hint("float")["clrType"])
        self.assertIsNone(hint("object"))   # keep the default hint of the component
        self.assertIsNone(hint(""))
        self.assertIsNone(hint("SomethingElse"))


PY3_ONLY_NODES = tuple(
    getattr(ast, name) for name in ("JoinedStr", "AnnAssign", "Nonlocal", "YieldFrom", "AsyncFunctionDef", "Await", "NamedExpr")
    if hasattr(ast, name)
)


class UpdaterPortabilityTests(unittest.TestCase):
    """The updater runs as a plain script in Rhino 7/8 GhPython (IronPython 2.7) and Rhino 8 Python 2/3 script components."""

    @classmethod
    def setUpClass(cls):
        cls.source = UPDATER_SOURCE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_no_python3_only_syntax(self):
        for node in ast.walk(self.tree):
            with self.subTest(line=getattr(node, "lineno", None), node=type(node).__name__):
                self.assertNotIsInstance(node, PY3_ONLY_NODES)
                if isinstance(node, ast.arguments):
                    self.assertEqual([], node.kwonlyargs)
                    self.assertTrue(all(arg.annotation is None for arg in node.args))
                if isinstance(node, (ast.FunctionDef,)):
                    self.assertIsNone(node.returns)
                if isinstance(node, ast.Starred):
                    self.assertNotIsInstance(getattr(node, "ctx", None), ast.Store)
                if isinstance(node, ast.Raise):
                    self.assertIsNone(node.cause, "raise ... from ... is Python 3 only")
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "super":
                    self.assertTrue(node.args, "super() without arguments is Python 3 only")
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
                    self.assertFalse(node.keywords, "open(..., encoding=...) is Python 3 only: use io.open")
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    self.assertNotIn("{}", node.value, "use numbered fields {0} for IronPython 2.7")

    def test_source_is_ascii(self):
        UPDATER_SOURCE.read_bytes().decode("ascii")

    def test_plain_script_contract(self):
        # no SDK class (GH_ScriptInstance / executingcomponent): inputs are globals, outputs are assigned at top level
        self.assertNotIn("GH_ScriptInstance", self.source)
        self.assertNotIn("executingcomponent", self.source)
        updater = load_updater()
        inputs, outputs = updater.parseIONames(self.source)
        self.assertEqual(["sourceFolder", "runUpdate"], inputs)
        self.assertEqual(["log", "updated", "skipped", "errors"], outputs)
        assigned = set()
        for node in self.tree.body:
            if isinstance(node, ast.If):
                for statement in node.body:
                    if isinstance(statement, ast.Assign):
                        for target in statement.targets:
                            for element in getattr(target, "elts", [target]):
                                assigned.add(getattr(element, "id", None))
        self.assertTrue({"log", "updated", "skipped", "errors"} <= assigned)


if __name__ == "__main__":
    unittest.main()
