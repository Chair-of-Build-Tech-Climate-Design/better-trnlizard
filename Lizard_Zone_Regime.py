"""
Link buidling surface definitions, heating, cooling, gains, and ventilation outputs
to this Regime.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    PeopleGain (object): Link people gain for zone
        Access: item
        Required: True
    EquipmentGain (object): Link computer gain for zone
        Access: item
        Required: True
    LightGain (object): Link lighting gain for zone
        Access: item
        Required: True
    MiscGain (object): Link other gain for zone
        Access: list
        Required: True
    HamtGain (object): Script variable Zone Regime
        Access: item
        Required: True
    ThbGain (object): Link thermal bridge gains for zone
        Access: item
        Required: True
    Heating (object): Link airnode heating definition
        Access: item
        Required: True
    Dhw (object): Link DHW Regime
        Access: item
        Required: True
    Cooling (object): Link airnode cooling definition
        Access: item
        Required: True
    Infiltration (object): Link airnode infiltration definition
        Access: item
        Required: True
    Ventilation (object): Link airnode ventilation definitions (mechanical, stack)
        Access: item
        Required: True
    StackVentilation1 (object): Link airnode stack ventilation definitions (mechanical, stack)
        Access: item
        Required: True
    StackVentilation2 (object): Link airnode stack ventilation definitions (mechanical, stack)
        Access: item
        Required: True
    Comfort (object): Link comfort definition
        Access: item
        Required: True

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
ghenv.Component.Category = "Lizard"
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
        Regime.Infiltration = Infiltration
if 'MechanicalVentilation' in locals():
    if MechanicalVentilation is not None:
        Regime.Mechvent = MechanicalVentilation
if 'Ventilation' in locals():
    if Ventilation is not None:
        Regime.Mechvent = Ventilation
if 'EarthDuct' in locals():
    if EarthDuct is not None:
        Regime.Earthduct = EarthDuct
if 'StackVentilation1' in locals():
    if StackVentilation1 is not None:
        Regime.Stvent1 = StackVentilation1
if 'StackVentilation2' in locals():
    if StackVentilation2 is not None:
        Regime.Stvent2 = StackVentilation2
if 'Comfort' in locals():
    if Comfort is not None:
        Regime.Pmvcomfort = Comfort
