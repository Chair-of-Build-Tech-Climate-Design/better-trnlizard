"""
Link buidling surface definitions, heating, cooling, gains, and ventilation outputs
to this Regime.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
Modified by Junfeng Xiao, 2026.
-

Args:
    PeopleGain (object): Link people gains for zone; several gains each keep their own power and schedule
        Access: list
        Required: False
    EquipmentGain (object): Link computer gains for zone; several gains each keep their own power and schedule
        Access: list
        Required: False
    LightGain (object): Link lighting gains for zone; several gains each keep their own power and schedule
        Access: list
        Required: False
    MiscGain (object): Link other gains for zone; several gains each keep their own power and schedule
        Access: list
        Required: False
    HamtGain (object): Script variable Zone Regime
        Access: item
        Required: False
    ThbGain (object): Link thermal bridge gains for zone
        Access: item
        Required: False
    Heating (object): Link airnode heating definition
        Access: item
        Required: False
    Dhw (object): Link DHW Regime
        Access: item
        Required: False
    Cooling (object): Link airnode cooling definition
        Access: item
        Required: False
    Infiltration (object): Link airnode infiltration definition; can also go into Ventilation
        Access: item
        Required: False
    Ventilation (object): Link any of infiltration, mechanical ventilation and stack ventilation 1 and 2, at most one of each
        Access: list
        Required: False
    StackVentilation1 (object): Link airnode stack ventilation definition; can also go into Ventilation
        Access: item
        Required: False
    StackVentilation2 (object): Link airnode stack ventilation definition; can also go into Ventilation
        Access: item
        Required: False
    Comfort (object): Link comfort definition
        Access: item
        Required: False

Returns:
    out (object): Log Information!!!
        Access: item
    Regime (object): Connect to Zone Component
        Access: item
"""

version = '2.3.1'
ghenv.Component.Name = "Lizard_Zone_Regime"
ghenv.Component.NickName = 'Zone Regime'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "3 | Regime"

import scriptcontext as sc
class REGIME:
    def __init__(self):
        self.Name       = "REGIME"
        self.Persgain       = ""
        self.Compgain       = ""
        self.Lightgain      = ""
        self.Othergain      = []
        self.Udefgain       = ""
        self.Thbgain        = ""
        self.Heating        = ""
        self.Domestic       = ""
        self.Cooling        = ""
        self.Infiltration   = ""
        self.Mechvent       = ""
        self.Earthduct      = ""
        self.Stvent1        = ""
        self.Stvent2        = ""
        self.Pmvcomfort     = ""
        self.Setcomfort     = ""
    def __repr__(self):
        """Class representation."""
        return "{}:{}".format(self.__class__.__name__, self.Name)
Regime = REGIME()
def addVentilation(item):
    """Puts a definition of any kind of ventilation on its place in the regime. The deck has one place of each."""
    kind = getattr(item, 'Type', None)
    if kind == 'INFILTRATION':
        place = 'Infiltration'
    elif kind == 'VENTILATION':
        place = 'Mechvent'
    elif kind == 'STACKVENTILATION':
        place = 'Stvent1' if item.Name == 'STVENT1' else 'Stvent2'
    else:
        raise ValueError("Not a ventilation definition: {0}".format(item))
    if getattr(Regime, place) != "":
        raise ValueError("Two ventilation definitions of one kind in the regime: {0}".format(item))
    setattr(Regime, place, item)
if 'PeopleGain' in locals():
    if PeopleGain is not None:
        Regime.Persgain = PeopleGain
if 'EquipmentGain' in locals():
    if EquipmentGain is not None:
        Regime.Compgain = EquipmentGain
if 'LightGain' in locals():
    if LightGain is not None:
        Regime.Lightgain = LightGain
if 'MiscGain' in locals():
    if MiscGain is not None:
        Regime.Othergain += MiscGain
if 'HamtGain' in locals():
    if HamtGain is not None:
        Regime.Othergain.append(HamtGain)
if 'UdefGain' in locals():
    if UdefGain is not None:
        Regime.Udefgain = UdefGain
if 'ThbGain' in locals():
    if ThbGain is not None:
        Regime.Thbgain = ThbGain
if 'Heating' in locals():
    if Heating is not None:
        Regime.Heating = Heating
if 'Dhw' in locals():
    if Dhw is not None:
        Regime.Domestic = Dhw
if 'Cooling' in locals():
    if Cooling is not None:
        Regime.Cooling = Cooling
if 'Infiltration' in locals():
    if Infiltration is not None:
        addVentilation(Infiltration)
if 'MechanicalVentilation' in locals():
    if MechanicalVentilation is not None:
        addVentilation(MechanicalVentilation)
if 'Ventilation' in locals():
    if Ventilation is not None:
        for item in ([Ventilation] if hasattr(Ventilation, 'Type') else Ventilation):
            if item is not None:
                addVentilation(item)
if 'EarthDuct' in locals():
    if EarthDuct is not None:
        Regime.Earthduct = EarthDuct
if 'StackVentilation1' in locals():
    if StackVentilation1 is not None:
        addVentilation(StackVentilation1)
if 'StackVentilation2' in locals():
    if StackVentilation2 is not None:
        addVentilation(StackVentilation2)
if 'Comfort' in locals():
    if Comfort is not None:
        Regime.Pmvcomfort = Comfort
