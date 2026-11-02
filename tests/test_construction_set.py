"""Default constructions from Lizard_Construction_Set and the meaning of AUTOMATIC.

Same harness as test_surface_model.py: the real blocks of Lizard_Component.py with stand-ins for Rhino.
"""

import unittest
from pathlib import Path
from types import SimpleNamespace

from test_surface_model import M, airnode, compile_model, errors, library, north, south, surface, warnings_of, walls_of


REPO_ROOT = Path(__file__).resolve().parents[1]


def infos(issues):
    return [issue["message"] for issue in issues if issue["level"] == "info"]


def floor(x0=0, x1=5, z=0.0, **options):
    return surface([(x0, 0, z), (x0, 4, z), (x1, 4, z), (x1, 0, z)], **options)


def ceiling(x0=0, x1=5, z=0.0, **options):
    return surface([(x0, 0, z), (x1, 0, z), (x1, 4, z), (x0, 4, z)], **options)


def constructions(**slots):
    return SimpleNamespace(**slots)


class AutomaticTests(unittest.TestCase):
    def test_automatic_is_the_same_as_empty(self):
        for category in ("AUTOMATIC", None):
            a, b = south(0, 5, category=category), north(0, 5, category=category)
            self.assertEqual([], compile_model(airnode("A1", a), airnode("A2", b)))
            self.assertEqual(("ADJACENT", "ADJACENT"), (a.Boundarycond, b.Boundarycond))

    def test_unmatched_automatic_wall_and_roof_are_external(self):
        wall, roof = south(0, 5, category="AUTOMATIC"), ceiling(z=3.0, category="AUTOMATIC")
        self.assertEqual([], errors(compile_model(airnode("A1", wall, roof))))
        self.assertEqual(("EXTERNAL", "EXTERNAL", "ROOF"), (wall.Boundarycond, roof.Boundarycond, roof.Type))

    def test_unmatched_automatic_floor_is_an_error(self):
        item = floor(category="AUTOMATIC")
        issues = compile_model(airnode("A1", item))
        self.assertEqual(1, len(errors(issues)))
        self.assertIn("Floor surface", errors(issues)[0])
        self.assertNotEqual("EXTERNAL", item.Boundarycond)

    def test_explicit_external_floor_stays(self):
        item = floor(category="EXTERNAL")
        self.assertEqual([], errors(compile_model(airnode("A1", item))))
        self.assertEqual("EXTERNAL", item.Boundarycond)


class SlotTests(unittest.TestCase):
    def slot(self, item):
        return M["constructionSlot"](item)

    def test_slots(self):
        wall = south(0, 5, category="EXTERNAL")
        self.assertEqual("ExteriorWall", self.slot(wall))
        wall.Boundarycond = "ADJACENT"
        self.assertEqual("InteriorWall", self.slot(wall))
        wall.Boundarycond = "BOUNDARY"
        self.assertEqual("InteriorWall", self.slot(wall))
        self.assertEqual("Roof", self.slot(ceiling(category="EXTERNAL", kind="ROOF")))
        self.assertEqual("InteriorCeiling", self.slot(ceiling(category="ADJACENT", kind="CEILING")))
        self.assertEqual("InteriorFloor", self.slot(floor(category="ADJACENT")))
        self.assertEqual("ExposedFloor", self.slot(floor(category="EXTERNAL")))

    def test_floor_boundary_is_ground_unless_it_mirrors_the_room(self):
        self.assertEqual("GroundFloor", self.slot(floor(category="BOUNDARY", temperature="INPUT 1*TGROUND")))
        self.assertEqual("GroundFloor", self.slot(floor(category="BOUNDARY", temperature="12")))
        self.assertEqual("InteriorFloor", self.slot(floor(category="BOUNDARY", temperature=0)))
        self.assertEqual("InteriorFloor", self.slot(floor(category="BOUNDARY", temperature="INPUT 1*TAIR_@ANAME")))

    def test_hygrothermal_categories_follow_the_side_they_stand_for(self):
        self.assertEqual("ExteriorWall", self.slot(south(0, 5, category="EXTCALEXT")))
        self.assertEqual("InteriorWall", self.slot(south(0, 5, category="EXTCALBND")))
        self.assertEqual("Roof", self.slot(ceiling(category="EXTCALEXT", kind="CEILING")))


class FillTests(unittest.TestCase):
    def compile(self, *nodes, **options):
        return M["compileModel"](list(nodes), library(), constructionset=options.pop("model", None), **options)

    def test_no_set_gives_the_error_with_the_slot(self):
        item = south(0, 5, construction=None)
        issues = self.compile(airnode("A1", item))
        self.assertEqual(1, len(errors(issues)))
        self.assertIn("ExteriorWall", errors(issues)[0])

    def test_final_boundary_condition_chooses_the_slot(self):
        a, b = south(0, 6, construction=None, number=70), north(0, 2, construction=None, number=71)
        na, nb = airnode("A1", a), airnode("A2", b)
        issues = self.compile(na, nb, model=constructions(ExteriorWall="OUT", InteriorWall="WALL"))
        self.assertEqual([], errors(issues))
        pieces = dict((piece.Boundarycond, piece) for piece in walls_of(na))
        self.assertEqual(("OUT", "WALL"), (pieces["EXTERNAL"].Construction, pieces["ADJACENT"].Construction))
        self.assertEqual("WALL", b.Construction)

    def test_explicit_value_wins(self):
        item = south(0, 5, construction="WALL")
        self.compile(airnode("A1", item), model=constructions(ExteriorWall="OUT"))
        self.assertEqual("WALL", item.Construction)

    def test_airnode_set_before_model_set_slot_by_slot(self):
        wall, roof = south(0, 5, construction=None), ceiling(z=3.0, construction=None)
        node = airnode("A1", wall, roof)
        node.Constructionset = constructions(ExteriorWall="WALL")
        issues = self.compile(node, model=constructions(ExteriorWall="OUT", Roof="IFL"))
        self.assertEqual([], errors(issues))
        self.assertEqual(("WALL", "IFL"), (wall.Construction, roof.Construction))

    def test_explicit_side_decides_the_pair_and_is_the_front(self):
        a, b = south(0, 5, construction=None), north(0, 5, construction="OUT")
        issues = self.compile(airnode("A1", a), airnode("A2", b), model=constructions(InteriorWall="WALL"))
        self.assertEqual([], errors(issues))
        self.assertEqual(("OUT", "OUT"), (a.Construction, b.Construction))
        self.assertEqual(("BACK", "FRONT"), (a.Frontback, b.Frontback))

    def test_floor_and_ceiling_take_their_own_slots(self):
        top, bottom = floor(z=3.0, construction=None), ceiling(z=3.0, construction=None)
        issues = self.compile(airnode("A2", top), airnode("A1", bottom), model=constructions(InteriorFloor="IFL", InteriorCeiling="ICL"))
        self.assertEqual([], errors(issues))
        self.assertEqual(("IFL", "FRONT"), (top.Construction, top.Frontback))
        self.assertEqual(("ICL", "BACK"), (bottom.Construction, bottom.Frontback))

    def test_set_with_only_the_floor_is_followed_by_the_ceiling(self):
        top, bottom = floor(z=3.0, construction=None), ceiling(z=3.0, construction=None)
        issues = self.compile(airnode("A2", top), airnode("A1", bottom), model=constructions(InteriorFloor="IFL"))
        self.assertEqual([], errors(issues))
        self.assertEqual(("IFL", "IFL"), (top.Construction, bottom.Construction))

    def test_set_with_only_the_ceiling_cannot_be_used_for_the_front(self):
        top, bottom = floor(z=3.0, construction=None), ceiling(z=3.0, construction=None)
        issues = self.compile(airnode("A2", top), airnode("A1", bottom), model=constructions(InteriorCeiling="ICL"))
        self.assertEqual(1, len(errors(issues)))
        self.assertIn("InteriorFloor", errors(issues)[0])

    def test_rooms_with_different_sets_on_one_wall_are_an_error(self):
        a, b = south(0, 5, construction=None), north(0, 5, construction=None)
        na, nb = airnode("A1", a), airnode("A2", b)
        na.Constructionset, nb.Constructionset = constructions(InteriorWall="WALL"), constructions(InteriorWall="OUT")
        issues = self.compile(na, nb)
        self.assertEqual(1, len(errors(issues)))
        self.assertIn("different constructions", errors(issues)[0])

    def test_non_symmetric_wall_from_a_set_warns_about_the_direction(self):
        a, b = south(0, 5, construction=None), north(0, 5, construction=None)
        issues = self.compile(airnode("A1", a), airnode("A2", b), model=constructions(InteriorWall="OUT"))
        self.assertEqual([], errors(issues))
        self.assertEqual(1, len([message for message in warnings_of(issues) if "non-symmetric" in message]))

    def test_unknown_name_in_a_set_is_an_error(self):
        issues = self.compile(airnode("A1", south(0, 5, construction=None)), model=constructions(ExteriorWall="NOPE"))
        self.assertIn("not in the library", errors(issues)[0])

    def test_what_a_set_filled_is_reported(self):
        a, b = south(0, 5, construction=None, number=80), south(5, 9, construction=None, number=81)
        issues = self.compile(airnode("A1", a, b), model=constructions(ExteriorWall="OUT"))
        self.assertEqual(1, len(infos(issues)))
        self.assertIn("ExteriorWall", infos(issues)[0])
        self.assertIn("OUT", infos(issues)[0])
        self.assertIn("80", infos(issues)[0])

    def test_nothing_is_reported_without_a_set(self):
        self.assertEqual([], infos(self.compile(airnode("A1", south(0, 5, construction="WALL")))))

    def test_windows_and_virtual_surfaces_are_left_alone(self):
        virtual = south(0, 5, category="VIRTUAL", construction=None)
        self.compile(airnode("A1", virtual), model=constructions(ExteriorWall="OUT", InteriorWall="OUT"))
        self.assertIsNone(virtual.Construction)

    def test_converted_surface_without_construction_gets_no_warning(self):
        a, b = south(0, 5, category="EXTERNAL", construction=None), north(0, 5, category="EXTERNAL", construction=None)
        issues = self.compile(airnode("A1", a), airnode("A2", b), autoadjacency=True, model=constructions(InteriorWall="WALL"))
        self.assertEqual([], [message for message in warnings_of(issues) if "keep the construction" in message])
        self.assertEqual(("WALL", "WALL"), (a.Construction, b.Construction))


class ComponentTests(unittest.TestCase):
    def test_component_has_all_the_slots_and_their_docs(self):
        text = (REPO_ROOT / "Lizard_Construction_Set.py").read_text(encoding="utf-8-sig")
        self.assertIn('ghenv.Component.Name = "Lizard_Construction_Set"', text)
        for slot in M["CONSTRUCTION_SLOTS"]:
            self.assertIn("    {0} (str):".format(slot), text)
            self.assertIn("self.{0} = {0}".format(slot), text)

    def test_genmatrices_survives_an_empty_construction(self):
        text = (REPO_ROOT / "Lizard_GenMatrices.py").read_text(encoding="utf-8-sig")
        self.assertIn('"Virtual" in (item.Construction or \'\')', text)

    def test_inputs_are_registered(self):
        airnode_text = (REPO_ROOT / "Lizard_Thermal_Airnode.py").read_text(encoding="utf-8-sig")
        multizone_text = (REPO_ROOT / "Lizard_Multizone.py").read_text(encoding="utf-8-sig")
        self.assertIn('"ConstructionSet",', airnode_text)
        self.assertIn("ConstructionSet (object):", airnode_text)
        self.assertIn("ConstructionSet (object):", multizone_text)
        self.assertIn("self.constructionset = ConstructionSet", multizone_text)


if __name__ == "__main__":
    unittest.main()
