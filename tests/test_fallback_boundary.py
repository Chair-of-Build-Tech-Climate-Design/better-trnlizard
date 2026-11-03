"""FallbackBoundary, GroundLevel and the category GROUND (issue #3): the real blocks of the scripts with stand-ins for Rhino."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from test_construction_set import ceiling, floor
from test_surface_model import FakeSurfaceBrep, M, airnode, compile_model, errors, load_construction, south, surface, window_in, warnings_of


ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return (ROOT / "components" / name).read_text(encoding="utf-8-sig")


def wall(z0, z1, **options):
    return surface([(0, 0, z0), (5, 0, z0), (5, 0, z1), (0, 0, z1)], **options)


class Settings(unittest.TestCase):
    def setUp(self):
        patches = [mock.patch.dict(M, {"GROUND_LEVEL": 0.0, "FALLBACK_BOUNDARY": True})]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)


class FallbackOnTests(Settings):
    def test_floor_at_the_ground_level_is_ground(self):
        item = floor(z=0.0)
        issues = compile_model(airnode("A1", item))
        self.assertEqual(("BOUNDARY", "INPUT 1*Tsoil"), (item.Boundarycond, item.Boundarytemp))
        self.assertEqual([], errors(issues))
        self.assertEqual(1, len(warnings_of(issues)))

    def test_floor_above_the_ground_level_is_external_with_a_warning(self):
        item = floor(z=3.0)
        issues = compile_model(airnode("A1", item))
        self.assertEqual("EXTERNAL", item.Boundarycond)
        self.assertIn("EXTERNAL is used", warnings_of(issues)[0])

    def test_wall_above_the_ground_is_external_without_a_warning(self):
        item = wall(0.0, 3.0)
        issues = compile_model(airnode("A1", item))
        self.assertEqual("EXTERNAL", item.Boundarycond)
        self.assertEqual([], warnings_of(issues))

    def test_wall_below_the_ground_is_ground(self):
        item = wall(-3.0, 0.0)
        issues = compile_model(airnode("A1", item))
        self.assertEqual(("BOUNDARY", "INPUT 1*Tsoil"), (item.Boundarycond, item.Boundarytemp))
        self.assertIn("GROUND is used", warnings_of(issues)[0])

    def test_ground_level_moves_the_rule(self):
        with mock.patch.dict(M, {"GROUND_LEVEL": 4.0}):
            low, high = floor(z=3.0), floor(z=5.0)
            compile_model(airnode("A1", low))
            compile_model(airnode("A2", high))
        self.assertEqual(("BOUNDARY", "EXTERNAL"), (low.Boundarycond, high.Boundarycond))

    def test_a_vertex_above_the_tolerance_makes_it_external(self):
        item = wall(-3.0, M["ADJACENCY_TOLERANCE"] * 2)
        compile_model(airnode("A1", item))
        self.assertEqual("EXTERNAL", item.Boundarycond)

    def test_a_vertex_within_the_tolerance_is_at_the_ground_level(self):
        item = wall(-3.0, M["ADJACENCY_TOLERANCE"] / 2)
        compile_model(airnode("A1", item))
        self.assertEqual("BOUNDARY", item.Boundarycond)

    def test_a_wall_with_a_window_stays_external(self):
        item = wall(-3.0, 0.0)
        window = window_in(item, 1, 2, -2.0, -1.0)
        issues = compile_model(airnode("A1", item, window))
        self.assertEqual(("EXTERNAL", "EXTERNAL"), (item.Boundarycond, window.Boundarycond))
        self.assertIn("has a window", warnings_of(issues)[0])

    def test_addwindow_stays_external_without_a_warning(self):
        item = wall(-3.0, 0.0, kind="ADDWINDOW")
        issues = compile_model(airnode("A1", item))
        self.assertEqual("EXTERNAL", item.Boundarycond)
        self.assertEqual([], warnings_of(issues))

    def test_each_piece_of_a_split_wall_has_its_own_height(self):
        host = wall(-3.0, 3.0)
        partner = surface([(0, 0, 0), (0, 0, 3), (5, 0, 3), (5, 0, 0)])
        node = airnode("A1", host)
        compile_model(node, airnode("A2", partner))
        categories = {}
        for piece in node.Surfaces:
            categories[max(point.Z for point in piece.Vertices)] = (piece.Boundarycond, piece.Boundarytemp)
        self.assertEqual("ADJACENT", categories[3][0])
        self.assertEqual(("BOUNDARY", "INPUT 1*Tsoil"), categories[0])

    def test_standalone_uses_the_same_rule(self):
        upper = floor(z=3.0)
        issues = compile_model(airnode("A1", upper), standalone=True)
        self.assertEqual("EXTERNAL", upper.Boundarycond)
        self.assertIn("EXTERNAL is used", warnings_of(issues)[0])

    def test_a_partner_goes_first(self):
        below, above = ceiling(z=0.0), floor(z=0.0)
        issues = compile_model(airnode("A1", below), airnode("A2", above))
        self.assertEqual(("ADJACENT", "ADJACENT"), (below.Boundarycond, above.Boundarycond))
        self.assertEqual([], warnings_of(issues))

    def test_explicit_categories_are_left_alone(self):
        external, boundary = floor(z=0.0, category="EXTERNAL"), floor(z=-1.0, category="BOUNDARY")
        boundary.Boundarytemp = 24
        issues = compile_model(airnode("A1", external), airnode("A2", boundary))
        self.assertEqual([], errors(issues))
        self.assertEqual(("EXTERNAL", "BOUNDARY", 24), (external.Boundarycond, boundary.Boundarycond, boundary.Boundarytemp))

    def test_explicit_adjacent_without_a_partner_stays_an_error(self):
        issues = compile_model(airnode("A1", floor(z=0.0, category="ADJACENT")))
        self.assertIn("No adjacent surface found", errors(issues)[0])


class FallbackOffTests(Settings):
    def off(self, *items):
        with mock.patch.dict(M, {"FALLBACK_BOUNDARY": False}):
            return compile_model(airnode("A1", *items))

    def test_every_surface_without_a_category_is_an_error(self):
        issues = self.off(floor(z=0.0), wall(0.0, 3.0), ceiling(z=3.0))
        self.assertEqual(3, len(errors(issues)))
        self.assertIn("FallbackBoundary is off", errors(issues)[0])

    def test_a_partner_and_an_explicit_category_are_no_error(self):
        with mock.patch.dict(M, {"FALLBACK_BOUNDARY": False}):
            issues = compile_model(airnode("A1", ceiling(z=0.0), wall(0.0, 3.0, category="EXTERNAL")), airnode("A2", floor(z=0.0)))
        self.assertEqual([], errors(issues))


class SlotTests(Settings):
    def slots(self, item):
        return M["constructionSlot"](item)

    def test_ground_uses_the_slots_against_the_soil(self):
        for category in ("BOUNDARY", "EXTCALBND"):
            for kind, slot in (("FLOOR", "GroundFloor"), ("WALL", "ExteriorWall"), ("CEILING", "Roof"), ("ROOF", "Roof")):
                item = SimpleNamespace(Type=kind, Boundarycond=category, Boundarytemp="INPUT 1*Tsoil", Airnode="A1")
                self.assertEqual(slot, self.slots(item))

    def test_other_boundaries_keep_the_interior_slots(self):
        for temperature in (24, "INPUT 1*TAIR_A2", "Identical", "INPUT 1*Tsoil_measured"):
            wall_item = SimpleNamespace(Type="WALL", Boundarycond="BOUNDARY", Boundarytemp=temperature, Airnode="A1")
            ceiling_item = SimpleNamespace(Type="CEILING", Boundarycond="BOUNDARY", Boundarytemp=temperature, Airnode="A1")
            self.assertEqual(("InteriorWall", "InteriorCeiling"), (self.slots(wall_item), self.slots(ceiling_item)))


class ComponentInputTests(unittest.TestCase):
    def inputs(self, **values):
        source = read("Lizard_Component.py")
        begin = source.index("if 'GroundLevel' in locals()")
        block = source[begin:source.index("checkUnits()", begin)]
        namespace = dict(GROUND_LEVEL=0.0, FALLBACK_BOUNDARY=True, **values)
        exec(block, namespace)
        return namespace["GROUND_LEVEL"], namespace["FALLBACK_BOUNDARY"]

    def test_not_connected_keeps_the_defaults(self):
        self.assertEqual((0.0, True), self.inputs())
        self.assertEqual((0.0, True), self.inputs(GroundLevel=None, FallbackBoundary=None))

    def test_connected_values_are_used(self):
        self.assertEqual((2.5, False), self.inputs(GroundLevel=2.5, FallbackBoundary=False))
        self.assertEqual((0.0, True), self.inputs(GroundLevel=0, FallbackBoundary=True))

    def test_docstring_declares_the_inputs(self):
        source = read("Lizard_Component.py")
        self.assertRegex(source, r"    GroundLevel \(float\): .*\n        Access: item\n        Required: False\n")
        self.assertRegex(source, r"    FallbackBoundary \(bool\): .*\n        Access: item\n        Required: False\n")


class GroundCategoryTests(unittest.TestCase):
    def settings(self, category, temperature=None):
        messages = []
        component = SimpleNamespace(AddRuntimeMessage=lambda level, text: messages.append(text))
        namespace = dict(ghenv=SimpleNamespace(Component=component), Category=category, BoundaryTemperature=temperature, Construction=None, FrontBack=None)
        kernel = SimpleNamespace(GH_RuntimeMessageLevel=SimpleNamespace(Error="error"))
        with mock.patch.dict(sys.modules, {"Grasshopper": SimpleNamespace(Kernel=kernel), "Grasshopper.Kernel": kernel}):
            exec(compile(read("Lizard_Surface_Settings.py"), "Lizard_Surface_Settings.py", "exec"), namespace)
        return namespace["Settings"], messages

    def test_ground_is_boundary_with_tsoil(self):
        settings, messages = self.settings("GROUND")
        self.assertEqual(("BOUNDARY", "Tsoil", []), (settings.Boundarycond, settings.Boundarytemp, messages))

    def test_ground_with_tsoil_is_fine(self):
        self.assertEqual([], self.settings("GROUND", "Tsoil")[1])

    def test_ground_with_another_temperature_is_an_error(self):
        self.assertIn("GROUND means BoundaryTemperature Tsoil", self.settings("GROUND", 24)[1][0])

    def test_other_categories_are_left_alone(self):
        settings, _ = self.settings("BOUNDARY", 24)
        self.assertEqual(("BOUNDARY", 24), (settings.Boundarycond, settings.Boundarytemp))

    def test_settings_become_the_temperature_of_the_b18(self):
        construction, sticky = load_construction()
        settings = self.settings("GROUND")[0]
        breps = construction.addToConstruction([FakeSurfaceBrep("a")], "c1")
        construction.updateConstructionNew(breps, settings)
        record = sticky["Const_coll"][breps[0].UserDictionary["LID"]]
        self.assertEqual(("BOUNDARY", "INPUT 1*Tsoil"), (record.Boundarycond, record.Boundarytemp))


if __name__ == "__main__":
    unittest.main()
