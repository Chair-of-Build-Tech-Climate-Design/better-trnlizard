"""Several gains of one kind in a zone: own name, power and schedule in the b18 and the deck (issue #2)."""

import re
import sys
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SYSTEM = (ROOT / "Lizard_System.py").read_text(encoding="utf-8-sig")
TEMPLATE = (ROOT / "Lizard_DCK_Template.py").read_text(encoding="utf-8-sig")
AIRNODE = (ROOT / "Lizard_Thermal_Airnode.py").read_text(encoding="utf-8-sig")
REGIME = (ROOT / "Lizard_Zone_Regime.py").read_text(encoding="utf-8-sig")
UPDATER = (ROOT / "Lizard_Updater.py").read_text(encoding="utf-8-sig")


def run_block(source, start, end, namespace):
    """Run a real block of a script; Python 2 print statements become calls."""
    begin = source.index(start)
    block = dedent(source[begin:source.index(end, begin + len(start))])
    block = re.sub(r"^(\s*)print (.+)$", r"\1print(\2)", block, flags=re.M)
    exec(compile(block, "block", "exec"), namespace)
    return namespace


def helpers():
    return run_block(SYSTEM, "def gainInstances(airnode):", "# ---- Several gains of one kind in a zone (end)", {})


def gain(**fields):
    values = dict(Userdefined=0, Personsgain=0, Computergain=0, Lightinggain=0, Othergain=0, Schedule="", Annual="", Frac_refarea=-1,
                  Type="GAIN", Category="MISCELLANEOUS", Dctrl=None, Hum2=0, Humidity=0, Tamb24hon=12, Winterred=0, CO2=0, Heatbymisc=0,
                  Heatbycomp=0, Heatbylight=0, Specificpower=0)
    values.update(fields)
    return SimpleNamespace(**values)


def misc(power, schedule, conv=0.6, heating=0):
    return gain(Name="HUMID", Othergain=1, Userdefined=1, Specificpower=power, Schedule=schedule, Heatbymisc=heating,
                Convective="INPUT %s*Q_ADDON_KJ" % conv, Radiative="INPUT %s*Q_ADDON_KJ" % round(1 - conv, 2))


def people(sensible, schedule, annual="", co2=20, winter=0, tamb=12):
    return gain(Name="PEOPLE", Personsgain=1, Conv2=0.5 * sensible, Rad2=0.5 * sensible, Hum2=0.06, Schedule=schedule, Annual=annual, CO2=co2,
                Winterred=winter, Tamb24hon=tamb, Convective="INPUT 0.5*Q_PERS_KJ", Radiative="INPUT 0.5*Q_PERS_KJ", Category="PEOPLE", Frac_refarea=1)


def equipment(power, schedule, winter=0, tamb=12):
    return gain(Name="EQUIP", Computergain=1, Specificpower=power, Schedule=schedule, Winterred=winter, Tamb24hon=tamb, Convective="INPUT 0.6*Q_COMP_KJ",
                Radiative="INPUT 0.4*Q_COMP_KJ", Category="EQUIPMENT", Frac_refarea=1)


def light(power, schedule):
    return gain(Name="LIGHT", Lightinggain=1, Specificpower=power, Schedule=schedule, Convective="INPUT 0.4*Q_LIGHT_KJ",
                Radiative="INPUT 0.6*Q_LIGHT_KJ", Category="LIGHTS", Frac_refarea=1, Efflight=50, Dimming=0, Permlight=0, Daylightfactor=0.02)


def airnode(gains, name="Z"):
    return SimpleNamespace(Name=name, Gain=list(gains), Areaperperson=10, Daylightctrl=[])


def definitions(zones):
    """The GAIN definitions of printbuitoppart as (name, convective, radiative, humidity)."""
    written = []
    namespace = dict(helpers(), dataset=zones, lines=written,
                     printsingledata=lambda obj, kind: (obj.Name, obj.Convective, obj.Radiative, obj.Humidity))
    run_block(SYSTEM, "    for item in dataset:\n        for item2, suffix in gainInstances(item):",
              "    # Intermediate part directly from the template", namespace)
    return written


def regime_lines(zone):
    namespace = dict(helpers(), Airnodes=zone, regimelines="")
    run_block(SYSTEM, "        for gain_item, suffix in gainInstances(Airnodes):", "        hamt_gain_exists = False", namespace)
    return namespace["regimelines"].split("\r\n")[:-1]


def deck_variables(zone, zones=1):
    variables = dict(poweraddon=0, mischeat=0, sched_occ=1, co2ppers=0, gainredon=12, compredon=12, winterred_pers=0, winterred_comp=0, power_pers=0,
                     power_comp=0, power_light=10, appers=zone.Areaperperson)
    collected = []
    namespace = dict(helpers(), variables=variables, zone_item=SimpleNamespace(Airnode=zone), zone=[None] * zones, schedulescoll=collected,
                     library=SimpleNamespace(Annualschedules=[]))
    run_block(SYSTEM, "    #gains\n", "    #co2 coupling\n", namespace)
    return variables, collected


def power_block(variables, zone="Z"):
    """The equations of the template with these variables, as printdck fills them in."""
    begin = TEMPLATE.index("EQUATIONS @ngainpower")
    text = TEMPLATE[begin:TEMPLATE.index("*$UNIT_NAME Specific Power Inputs", begin)].replace("@aname", zone)
    for name in sorted(set(re.findall(r"@(\w+)", text)), key=len, reverse=True):
        text = text.replace("@" + name, str(variables[name]))
    return text


class OneGainOfAKindTests(unittest.TestCase):
    """A definition with one gain of each kind writes what it wrote before."""

    def test_b18_names_are_kept(self):
        zone = airnode([people(100, "OCC"), equipment(140, "EQ"), light(8, "LI"), misc(1.5, "MI")])
        self.assertEqual(["PEOPLE_Z", "EQUIP_Z", "LIGHT_Z", "HUMID_Z"], [line[0] for line in definitions([zone])])
        self.assertEqual("INPUT 0.6*Q_ADDON_KJ_Z", definitions([zone])[3][1])
        self.assertEqual("GAIN = HUMID_Z : SCALE= SCHEDULE 1*MI : GEOPOS= 0 : SCALE2= 1 : FRAC_REFAREA= -1", regime_lines(zone)[3])

    def test_deck_is_kept(self):
        zone = airnode([people(100, "OCC", annual="YEAR", co2=20), equipment(140, "EQ"), light(8, "LI"), misc(1.5, "MI")])
        variables, _ = deck_variables(zone)
        self.assertEqual(4, variables["ngainpower"])
        self.assertEqual("", variables["moregainpower"])
        self.assertEqual("0+1.5", variables["poweraddon"])
        self.assertEqual("SCHED_OCC*SCHED_YEAR", variables["sched_occ"])
        self.assertEqual("SCHED_OCC*SCHED_YEAR", variables["sched_co2"])
        self.assertEqual(20, variables["co2ppers"])
        self.assertTrue(power_block(variables).startswith("EQUATIONS 4\nQ_pers_kJ_Z"))

    def test_template_uses_the_co2_schedule_only_for_co2(self):
        self.assertIn("Area_@aname / @appers * @sched_co2 * 1 / Vol_@aname", TEMPLATE)
        self.assertIn("OCCUPATION_@aname = gt(@sched_occ,0)", TEMPLATE)
        self.assertIn("scheduleocc_@aname       = @sched_occ", TEMPLATE)


class SeveralMiscGainsTests(unittest.TestCase):
    def setUp(self):
        self.zone = airnode([misc(100, "S1", conv=0.6), misc(40, "S2", conv=0.2, heating=1)])

    def test_each_definition_has_its_own_name_and_power_variable(self):
        self.assertEqual([("HUMID_Z", "INPUT 0.6*Q_ADDON_KJ_Z", "INPUT 0.4*Q_ADDON_KJ_Z", 0),
                          ("HUMID2_Z", "INPUT 0.2*Q_ADDON_KJ2_Z", "INPUT 0.8*Q_ADDON_KJ2_Z", 0)], definitions([self.zone]))

    def test_each_regime_line_has_its_own_schedule(self):
        lines = regime_lines(self.zone)
        self.assertIn("GAIN = HUMID_Z : SCALE= SCHEDULE 1*S1", lines[0])
        self.assertIn("GAIN = HUMID2_Z : SCALE= SCHEDULE 1*S2", lines[1])

    def test_each_power_has_its_own_equation_and_the_count_matches(self):
        variables, collected = deck_variables(self.zone)
        self.assertEqual("0+100", variables["poweraddon"])
        self.assertEqual(0, variables["mischeat"])
        block = power_block(variables)
        equations = [line for line in block.split("\n")[1:] if "=" in line.split("!")[0]]
        self.assertEqual("EQUATIONS 5", block.split("\n")[0])
        self.assertEqual(5, len(equations))
        self.assertIn("Q_addon_KJ2_Z = (0+40 * (max(not(1), lt(Tamb_m24,12)))) * 3.6", block)
        self.assertIn("SCHED_S2", collected)

    def test_names_do_not_collide_with_a_zone_called_2_z(self):
        names = [line[0] for line in definitions([self.zone, airnode([misc(1, "S")], name="2_Z")])]
        self.assertEqual(len(names), len(set(names)))

    def test_gains_are_left_as_they_were(self):
        definitions([self.zone])
        self.assertEqual(["HUMID", "HUMID"], [item.Name for item in self.zone.Gain])
        self.assertEqual("INPUT 0.2*Q_ADDON_KJ", self.zone.Gain[1].Convective)


class SeveralOtherGainsTests(unittest.TestCase):
    def test_people(self):
        zone = airnode([people(100, "S1", co2=20), people(60, "S2", annual="Y2", co2=10, winter=50, tamb=8)])
        self.assertEqual(["PEOPLE_Z", "PEOPLE2_Z"], [line[0] for line in definitions([zone])])
        self.assertEqual("INPUT 0.5*Q_PERS_KJ2_Z", definitions([zone])[1][1])
        variables, collected = deck_variables(zone)
        self.assertIn("SCHED_Y2", collected)
        self.assertEqual("(SCHED_S1 + SCHED_S2*SCHED_Y2)", variables["sched_occ"])
        self.assertEqual("(20.0*SCHED_S1 + 10.0*SCHED_S2*SCHED_Y2)", variables["sched_co2"])
        self.assertEqual(1, variables["co2ppers"])
        self.assertEqual(10.0, variables["power_pers"])
        self.assertIn("Q_pers_kJ2_Z = ( 6.0 * (1 - lt(Tamb_m24,8 ) * 0.5)) * 3.6", variables["moregainpower"])

    def test_people_in_a_multizone_model_produce_no_co2(self):
        variables, _ = deck_variables(airnode([people(100, "S1", co2=20), people(60, "S2", co2=10)]), zones=2)
        self.assertEqual(0, variables["co2ppers"])

    def test_equipment(self):
        zone = airnode([equipment(140, "S1"), equipment(70, "S2")])
        self.assertEqual("INPUT 0.6*Q_COMP_KJ2_Z", definitions([zone])[1][1])
        variables, _ = deck_variables(zone)
        self.assertEqual(14.0, variables["power_comp"])
        self.assertIn("Q_comp_kJ2_Z = ( 7.0 * (1 - lt(Tamb_m24,12 ) * 0.0)) * 3.6", variables["moregainpower"])

    def test_equipment_uses_its_own_threshold_not_the_one_of_people(self):
        variables, _ = deck_variables(airnode([people(100, "S1", tamb=10), equipment(140, "S2", winter=30, tamb=5)]))
        block = power_block(variables)
        self.assertIn("Q_pers_kJ_Z    = ( 10.0 * (1 - lt(Tamb_m24,10 ) * 0.0)) * 3.6", block)
        self.assertIn("Q_comp_kJ_Z    = ( 14.0 * (1 - lt(Tamb_m24,5 ) * 0.3)) * 3.6", block)

    def test_light(self):
        zone = airnode([light(8, "S1"), light(3, "S2")])
        self.assertEqual("INPUT 0.4*Q_LIGHT_KJ2_Z", definitions([zone])[1][1])
        self.assertIn("GAIN = LIGHT2_Z : SCALE= SCHEDULE 1*S2", regime_lines(zone)[1])
        variables, _ = deck_variables(zone)
        self.assertEqual(8, variables["power_light"])
        self.assertIn("Q_light_kJ2_Z = 3 * 3.6", variables["moregainpower"])

    def test_a_further_gain_of_another_kind_writes_no_equation(self):
        other = gain(Name="HUMID", Othergain=0)
        variables, _ = deck_variables(airnode([misc(1, "S1"), other]))
        self.assertEqual(4, variables["ngainpower"])
        self.assertEqual("", variables["moregainpower"])

    def test_trnflow_co2_stops_with_several_people_gains(self):
        messages = []
        namespace = dict(helpers(), Airnode=airnode([people(100, "S1"), people(60, "S2")]), err="err", sys=SimpleNamespace(exit=lambda: messages.append("exit")),
                         ghenv=SimpleNamespace(Component=SimpleNamespace(AddRuntimeMessage=lambda level, text: messages.append(text))))
        run_block(SYSTEM, "                        if countPeopleGains(Airnode) > 1:", "                        for gitem in Airnode.Gain:", namespace)
        self.assertIn("Airnode Z: TRNFlow takes one CO2 source schedule", messages[0])
        self.assertEqual("exit", messages[1])


class ComponentTests(unittest.TestCase):
    def regime_gains(self):
        return run_block(AIRNODE, "def regimeGains(value):", "w = gh.Kernel.GH_RuntimeMessageLevel.Warning", {})["regimeGains"]

    def test_regime_inputs_are_lists(self):
        for name in ("PeopleGain", "EquipmentGain", "LightGain", "MiscGain"):
            self.assertRegex(REGIME, r"    %s \(object\): .*\n        Access: list\n" % name)

    def test_regime_gains_takes_nothing_one_or_a_list(self):
        regime_gains = self.regime_gains()
        one, other = object(), object()
        self.assertEqual([], regime_gains(""))
        self.assertEqual([], regime_gains(None))
        self.assertEqual([], regime_gains([]))
        self.assertEqual([one], regime_gains(one))
        self.assertEqual([one, other], regime_gains([one, None, other, ""]))

    def run_airnode(self, regime, daylight=None):
        messages = []
        node = SimpleNamespace(Gain=[])
        namespace = dict(regimeGains=self.regime_gains(), Regime=regime, Airnode=node, DaylightCtrl=daylight, err="err",
                         sys=SimpleNamespace(exit=lambda: messages.append("exit")),
                         ghenv=SimpleNamespace(Component=SimpleNamespace(AddRuntimeMessage=lambda level, text: messages.append(text))))
        run_block(AIRNODE, "    if Regime:\n        Airnode.Gain.extend(regimeGains(Regime.Persgain))", "    if Regime and Regime.Thbgain", namespace)
        return node.Gain, messages

    def test_airnode_keeps_the_order_of_the_kinds(self):
        a, b, c = people(1, "A"), people(1, "B"), equipment(1, "C")
        d, e = light(1, "D"), misc(1, "E")
        gains, messages = self.run_airnode(SimpleNamespace(Persgain=[a, b], Compgain=c, Lightgain=[d], Othergain=[e]))
        self.assertEqual([a, b, c, d, e], gains)
        self.assertEqual([], messages)

    def test_every_light_gain_asks_for_daylight_control(self):
        second = light(1, "B")
        second.Dctrl = "DLC"
        _, messages = self.run_airnode(SimpleNamespace(Persgain="", Compgain="", Lightgain=[light(1, "A"), second], Othergain=[]))
        self.assertIn("exit", messages)

    def updater(self):
        return run_block(UPDATER, "LIST_ACCESS_INPUTS = ", "def recordUndo(doc, obj", {"accessValue": lambda access: access})

    @staticmethod
    def component(name, *inputs):
        changed = []
        params = SimpleNamespace(Input=[SimpleNamespace(Name=n, Access=a) for n, a in inputs], OnParametersChanged=lambda: changed.append(1))
        return SimpleNamespace(Name=name, Params=params), changed

    def test_updater_gives_the_regime_inputs_list_access(self):
        updater = self.updater()
        comp, changed = self.component("Lizard_Zone_Regime", ("PeopleGain", "item"), ("MiscGain", "list"), ("Heating", "item"))
        notes = []
        updater["applyListAccess"](comp, notes)
        self.assertEqual(["list", "list", "item"], [p.Access for p in comp.Params.Input])
        self.assertEqual(["PeopleGain now has list access"], notes)
        self.assertEqual([1], changed)

    def test_updater_leaves_item_access_on_other_components(self):
        updater = self.updater()
        comp, changed = self.component("Lizard_Surface", ("BRep", "item"))
        updater["applyListAccess"](comp, [])
        self.assertEqual("item", comp.Params.Input[0].Access)
        self.assertEqual([], changed)

    def test_updater_does_not_skip_current_code_with_item_access(self):
        comp, _ = self.component("Lizard_Zone_Regime", ("PeopleGain", "item"))
        block = dict(self.updater(), decideAction=lambda *args: "skip", comp=comp, codeChanged=False, plan={}, cluster=None)
        block["comp"].Locked = False
        run_block(UPDATER, "    what = decideAction(codeChanged, plan, cluster is not None, bool(comp.Locked))", "    if what == 'skip':\n        return", block)
        self.assertEqual("code", block["what"])

    def test_regime_script_gives_the_airnode_every_gain(self):
        a, b, c, hamt = people(1, "A"), people(1, "B"), misc(1, "C"), misc(1, "D")
        namespace = dict(ghenv=SimpleNamespace(Component=SimpleNamespace()), PeopleGain=[a, b], EquipmentGain=[], LightGain=[None], MiscGain=[c], HamtGain=hamt)
        with patch.dict(sys.modules, {"scriptcontext": SimpleNamespace()}):
            exec(compile(REGIME, "Lizard_Zone_Regime.py", "exec"), namespace)
        regime = namespace["Regime"]
        gains, messages = self.run_airnode(regime)
        self.assertEqual([a, b, c, hamt], gains)
        self.assertEqual([], messages)

    def test_further_light_gain_refers_to_its_own_name_with_daylight_control(self):
        zone = airnode([light(8, "S1"), light(3, "S2")])
        zone.Gain[1].Dctrl = "DLC"
        zone.Daylightctrl = [SimpleNamespace(Frac_refarea=1)]
        self.assertEqual("GAIN = LIGHT2_Z : SCALE= SCHEDULE 1*S2 : GEOPOS= 0 : SCALE2= 1 : FRAC_REFAREA= 1 : DLIGHT_CTRL=DLC0_Z", regime_lines(zone)[1])


if __name__ == "__main__":
    unittest.main()
