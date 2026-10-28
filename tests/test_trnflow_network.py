"""TRNFlow: Type 56 parameters from the project altitude, the CRACK link type and the Lizard_Trnflow_Network component.

* Lizard_System.py used to write the Type 56 parameters 8 (altitude of the building) and 10 (altitude of the weather station) as
  the fixed values 318 and 0; they now come from the project input Altitude.
* A CRACKS object gives a CRACK link type (LINKTYPES) and an air link of the AIRLINK_NETWORK; before there was no crack at all
  (the @Cracks placeholder of the skeleton was always empty).
* Lizard_Trnflow_Network.py builds the network objects (external nodes, wind velocity profile, cracks, large openings).

The real helper block and the real CRACKS branch of Lizard_System.py, the real classes of Lizard_Component.py, the real BUI
templates of the Lizard building template and the real component script are executed with mock Grasshopper objects (no
Grasshopper, no TRNBuild, no TRNSYS).
"""

import json
import sys
import unittest
from pathlib import Path
from textwrap import dedent
from types import ModuleType, SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_type395_side2_boundary as side2  # noqa: E402  (run_source for the IronPython 2 sources)

REPO_ROOT = side2.REPO_ROOT
SYSTEM_SOURCE = REPO_ROOT / "Lizard_System.py"
COMPONENT_SOURCE = REPO_ROOT / "Lizard_Component.py"
NETWORK_SOURCE = REPO_ROOT / "Lizard_Trnflow_Network.py"
TEMPLATE_STRUCTURE = REPO_ROOT / "presets" / "_shared" / "Lizard_Building_Template" / "structure.json"

HELPERS_START = "# ---- TRNFlow helpers (begin)"
HELPERS_END = "# ---- TRNFlow helpers (end)"
CRACK_BRANCH_START = "            if subitem.__class__.__name__ == 'CRACKS':\n"
CRACK_BRANCH_END = "            if subitem.__class__.__name__ == 'STRAIGHTDUCTS':\n"
CLASSES_START = "class POLLUTANTS:"
CLASSES_END = "class LIBRARY:"
PRINT_SINGLE_DATA_START = "@timing\ndef printSingleData(data_collection, *search_attr):"
PRINT_SINGLE_DATA_END = "@timing\ndef getDataParagraph("

# panel nickName of the Lizard building template -> attribute of the Template object
TEMPLATE_PANELS = {
    "Trnflow Large Openings": "Largeopenings",
    "Trnflow External Nodes": "Externalnodes",
    "Trnflow Windvelocityprofile": "Windvelocityprofile",
    "Trnflow Airlinknetwork": "Airlinknetwork",
}


def read_source(path):
    return path.read_text(encoding="utf-8-sig")


def source_slice(source, start, end):
    first = source.index(start)
    return dedent(source[first:source.index(end, first)])


def load_classes():
    """The TRNFlow data classes of Lizard_Component.py, as registered in sc.sticky."""
    source = read_source(COMPONENT_SOURCE)
    namespace = {}
    side2.run_source(source_slice(source, CLASSES_START, CLASSES_END), COMPONENT_SOURCE, namespace)
    return {name: namespace[name] for name in (
        "CRACKS", "LARGEOPENINGS", "EXTERNALNODES", "WINDVELOCITYPROFILE", "AIRLINKNETWORK")}


def load_template():
    panels = {}

    def walk(node):
        if isinstance(node, dict):
            if node.get("nickName") in TEMPLATE_PANELS and isinstance(node.get("text"), str):
                panels[TEMPLATE_PANELS[node["nickName"]]] = node["text"]
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(json.loads(TEMPLATE_STRUCTURE.read_text(encoding="utf-8")))
    return SimpleNamespace(**panels)


def load_print_single_data(template):
    source = read_source(COMPONENT_SOURCE)
    namespace = {"timing": lambda function: function, "Template": template}
    side2.run_source(
        source_slice(source, PRINT_SINGLE_DATA_START, PRINT_SINGLE_DATA_END).replace(".iteritems()", ".items()"),
        COMPONENT_SOURCE,
        namespace,
    )
    return namespace["printSingleData"]


def load_helpers():
    namespace = {}
    side2.run_source(source_slice(read_source(SYSTEM_SOURCE), HELPERS_START, HELPERS_END), SYSTEM_SOURCE, namespace)
    return namespace


def make_sticky(classes, template):
    sticky = dict(classes)
    sticky["printsingledata"] = load_print_single_data(template)
    return sticky


def run_network_component(sticky, **inputs):
    source = read_source(NETWORK_SOURCE)
    scriptcontext = ModuleType("scriptcontext")
    scriptcontext.doc = SimpleNamespace(Path="doc")
    scriptcontext.sticky = {"doc": sticky}
    kernel = ModuleType("Grasshopper.Kernel")
    kernel.GH_RuntimeMessageLevel = SimpleNamespace(Error="Error")
    grasshopper = ModuleType("Grasshopper")
    grasshopper.Kernel = kernel
    messages = []
    component = SimpleNamespace(AddRuntimeMessage=lambda level, text: messages.append((level, text)))
    namespace = dict(inputs)
    namespace["ghenv"] = SimpleNamespace(Component=component)
    saved = {name: sys.modules.get(name) for name in ("scriptcontext", "Grasshopper", "Grasshopper.Kernel")}
    sys.modules.update({"scriptcontext": scriptcontext, "Grasshopper": grasshopper, "Grasshopper.Kernel": kernel})
    try:
        side2.run_source(source, NETWORK_SOURCE, namespace)
    finally:
        for name, module in saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
    return namespace, component, messages


def run_crack_branch(sticky, helpers, subitems):
    """The CRACKS branch of the TRNFlow loop of Lizard_System.py for a list of network items."""
    branch = source_slice(read_source(SYSTEM_SOURCE), CRACK_BRANCH_START, CRACK_BRANCH_END)
    code = "for subitem in subitems:\n" + "\n".join(("    " + line if line else line) for line in branch.splitlines()) + "\n"
    namespace = dict(helpers)
    namespace.update({
        "sc": SimpleNamespace(sticky={"doc": sticky}, doc=SimpleNamespace(Path="doc")),
        "printsingledata": sticky["printsingledata"],
        "subitems": subitems, "cracks": "", "crackdefined": [], "airlinknetwork": "", "linkid": 0,
        "addouttempllines": "", "linkoutarray": [],
    })
    side2.run_source(code, SYSTEM_SOURCE, namespace)
    return namespace


class Type56ParameterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helpers = load_helpers()

    def test_altitude_of_the_project_is_used_for_building_and_weather_station(self):
        lines = self.helpers["trnflow_parameters"](520).splitlines()
        self.assertEqual(11, len(lines))
        self.assertEqual("520\t\t! 8 Altitude of building", lines[4])
        self.assertEqual("520\t\t! 10 Altitude of weather station", lines[6])

    def test_other_parameters_are_unchanged(self):
        lines = self.helpers["trnflow_parameters"](520).splitlines()
        self.assertEqual(
            ["-1\t\t! 4 Not used - Logical unit for monthly summary",
             "-1\t\t! 5 Not used - Logical unit for hourly temperatures",
             "-1\t\t! 6 Not used - Logical unit for hourly loads",
             "1\t\t! 7 Comis output / Tste"], lines[:4])
        self.assertEqual(
            ["10\t\t! 9 Height of meteo pylon", "0.14\t\t! 11 Velocity profile at weather station",
             "0.01\t\t! 12 Tolerance for internal iterations", "100\t\t! 13 Maximum number of internal iterations",
             "0.1\t\t! 14 Minimum relaxation factor"], [lines[5]] + lines[7:])

    def test_system_takes_the_altitude_from_the_project_not_a_constant(self):
        source = read_source(SYSTEM_SOURCE)
        self.assertIn("trnflow_parameters(sc.sticky[sc.doc.Path][\"Altitude\"])", source)
        self.assertNotIn("318\t\t! 8 Altitude of building", source)


class CrackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helpers = load_helpers()
        cls.classes = load_classes()
        cls.template = load_template()
        cls.sticky = make_sticky(cls.classes, cls.template)

    def crack(self, name, frnode, tonode, **values):
        crack = self.classes["CRACKS"]()
        crack.Name, crack.Frnode, crack.Tonode = name, frnode, tonode
        for key, value in values.items():
            setattr(crack, key, value)
        return crack

    def test_crack_type_block_follows_the_manual(self):
        crack = self.crack("CR_FACADE", "EN_S", "ROOM", Cs=0.01, Expn=0.65)
        self.assertEqual(
            "CRACK CR_FACADE\n DESC= -\n CS= 0.01 : EXPN= 0.65\n"
            " FILTER1= 0 : FILTER2= 0 : FILTER3= 0 : FILTER4= 0 : FILTER5= 0\n",
            self.helpers["trnflow_crack_type"](crack))

    def test_link_and_type_are_written_once_per_name(self):
        first = self.crack("CR_FACADE", "EN_S", "ROOM_1", Frheight=0, Toheight=1.5)
        second = self.crack("CR_FACADE", "EN_S", "ROOM_2", Fscale="INPUT 1*CRACK_OPEN")
        result = run_crack_branch(self.sticky, self.helpers, [first, second])
        self.assertEqual(1, result["cracks"].count("CRACK CR_FACADE\n"))
        links = [" ".join(line.split()) for line in result["airlinknetwork"].splitlines()]
        self.assertEqual(
            ["LINK CR_FACADE : ID= 1 : FRNODE= EN_S : TONODE= ROOM_1 : FRHEIGHT= 0 : TOHEIGHT= 1.5 : WIOWNHF= 0 : FSCALE= 1",
             "LINK CR_FACADE : ID= 2 : FRNODE= EN_S : TONODE= ROOM_2 : FRHEIGHT= 0 : TOHEIGHT= 0 : WIOWNHF= 0"
             " : FSCALE= INPUT 1*CRACK_OPEN"], links)
        self.assertEqual(2, result["linkid"])


class NetworkComponentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classes = load_classes()
        cls.template = load_template()
        cls.sticky = make_sticky(cls.classes, cls.template)
        cls.print_single_data = staticmethod(cls.sticky["printsingledata"])

    def run_component(self, **inputs):
        return run_network_component(self.sticky, **inputs)

    def test_external_nodes_and_wind_profile(self):
        namespace, component, messages = self.run_component(
            ExternalNodes=["S", "EN_N"], CpValues=["0.8 -0.2 -0.2 -0.2", "-0.2 -0.2 0.8 -0.2"], WindExponent=0.3)
        self.assertEqual([], messages)
        network = namespace["Network"]
        nodes = [item for item in network if item.__class__.__name__ == "EXTERNALNODES"]
        profiles = [item for item in network if item.__class__.__name__ == "WINDVELOCITYPROFILE"]
        self.assertEqual(["EN_S", "EN_N"], [node.Name for node in nodes])
        self.assertEqual(["0", "90", "180", "270"], [profile.Winddir for profile in profiles])
        self.assertEqual({"0.3"}, {profile.Veloexp for profile in profiles})
        text = self.print_single_data(nodes[0], "Externalnodes")
        self.assertEqual(
            "ENODE EN_S : CONCENTRATION= 1 : CP= 0.8 -0.2 -0.2 -0.2 REFHEIGHT= 10 : WINDDIR= 0 90 180 270", " ".join(text.split()))
        self.assertEqual("WINDDIR=0\nVELOEXP=0.3 \n", self.print_single_data(profiles[0], "Windvelocityprofile"))

    def test_cp_values_must_match_the_wind_directions(self):
        namespace, component, messages = self.run_component(ExternalNodes=["S"], CpValues=["0.8 -0.2"])
        self.assertEqual([], namespace["Network"])
        self.assertTrue(namespace["out"].startswith("ERROR: External node EN_S: 2 Cp values for 4 wind directions"))
        self.assertEqual("Error", messages[0][0])

    def test_one_cp_text_is_used_for_all_nodes(self):
        namespace, _, _ = self.run_component(ExternalNodes=["S", "N"], CpValues="0.5 0.5 0.5 0.5")
        nodes = [item for item in namespace["Network"] if item.__class__.__name__ == "EXTERNALNODES"]
        self.assertEqual(2, len(nodes))
        self.assertTrue(all("CP= 0.5 0.5 0.5 0.5" in node.Data for node in nodes))

    def test_crack_and_opening_links(self):
        namespace, _, messages = self.run_component(
            ExternalNodes=["S"], CpValues=["0.8 -0.2 -0.2 -0.2"],
            LinkNames=["facade_1", "balcony door", "stairwell"], LinkTypes=["CRACK", "OPENING", "CRACK"],
            FromNodes=["S", "S", "Floor_0"], ToNodes=["Floor_0", "Floor_1", "Floor_1"],
            FromHeights=[0, 0.1, 3], ToHeights=[1, 0, 0], Factors=[1, "INPUT 1*OPEN_DOOR", 1],
            CrackCs=[0.01], OpeningWidth=0.9, OpeningHeight=2.1, OpeningCd=0.65)
        self.assertEqual([], messages)
        links = [item for item in namespace["Network"] if item.__class__.__name__ in ("CRACKS", "LARGEOPENINGS")]
        self.assertEqual(["CR_facade_1", "WI_balcony_door", "CR_stairwell"], [link.Name for link in links])
        # from/to external node names get the EN_ prefix, airnodes keep their name
        self.assertEqual(("EN_S", "Floor_0"), (links[0].Frnode, links[0].Tonode))
        self.assertEqual(("EN_S", "Floor_1"), (links[1].Frnode, links[1].Tonode))
        self.assertEqual(("Floor_0", "Floor_1", 3, 0), (links[2].Frnode, links[2].Tonode, links[2].Frheight, links[2].Toheight))
        # data matching: the single crack coefficient is used for the second crack too
        self.assertEqual((0.01, 0.01), (links[0].Cs, links[2].Cs))
        opening = links[1]
        self.assertEqual(("INPUT 1*OPEN_DOOR", 0.9, 2.1, 0.65, 0.65, 1), (
            opening.Fscale, opening.Lowidth, opening.Loheight, opening.Cdopen, opening.Cdclose, opening.Wiownhf))
        text = self.print_single_data(opening, "Largeopenings")
        self.assertIn("LOPENING WI_balcony_door", text)
        flat = " ".join(text.split())
        self.assertIn("LOTYPE= 1 : LO1TYPE= 4 : LOWIDTH= 0.9 : LOHEIGHT= 2.1", flat)
        self.assertIn("CDCLOSE= 0.65 : CDOPEN= 0.65", flat)
        self.assertNotIn("@self", text)

    def test_defaults_crack_open_opening_closed(self):
        namespace, _, _ = self.run_component(
            LinkNames=["a", "b"], LinkTypes=["CRACK", "OPENING"], FromNodes="EXT", ToNodes="Room")
        crack, opening = [item for item in namespace["Network"]]
        self.assertEqual((1, 0.002, 0.66), (crack.Fscale, crack.Cs, crack.Expn))
        self.assertEqual((0, 0.6, 1), (opening.Fscale, opening.Cdopen, opening.Wiownhf))

    def test_wrong_input_is_reported_not_raised(self):
        for inputs, message in (
            (dict(LinkNames=["a", "a"], FromNodes="X", ToNodes="Y"), "Link name CR_a is used twice."),
            (dict(LinkNames=["a"], LinkTypes=["DUCT"], FromNodes="X", ToNodes="Y"), "LinkTypes must be CRACK or OPENING"),
            (dict(LinkNames=["a"], FromNodes="X"), "Link CR_a needs a From and a To node."),
        ):
            with self.subTest(message=message):
                namespace, _, messages = self.run_component(**inputs)
                self.assertEqual([], namespace["Network"])
                self.assertIn(message, namespace["out"])
                self.assertEqual(1, len(messages))

    def test_component_needs_the_project_component_to_have_run(self):
        sticky = {}
        namespace, _, messages = run_network_component(sticky, LinkNames=["a"], FromNodes="X", ToNodes="Y")
        self.assertIn("run the Lizard project component", namespace["out"])
        self.assertEqual(1, len(messages))


if __name__ == "__main__":
    unittest.main()
