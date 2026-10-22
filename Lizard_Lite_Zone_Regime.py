"""
Link buidling surface definitions, heating, cooling, gains, and ventilation outputs
to this Regime.
-
TRNLizard
Copyright (c) 2019 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.

Args:
    NamePeopleGain (float): Link persons gains for zone
        Access: item
        Required: False
    PowerComputerGain (float): Gain per computer (W)
        Access: item
        Required: False
    SpecPowerOtherGain (object): Other specific gain (W/m²)
        Access: item
        Required: False
    FreshAirPerPerson (object): Fresh air per person supplied by AHU
        Access: item
        Required: False
    SensibleHeatRecovery (object): Sensible heat recovery of AHU
        Access: item
        Required: False
    SetpointHeating (object): Set point for ideal heating
        Access: item
        Required: False
    SetpointCooling (object): Set point for ideal cooling
        Access: item
        Required: False
    NameOccupationSchedule (object): Name of Occupation schedule
        Access: item
        Required: False
    OccupationSchedule (object): Define Occupation schedule
        Access: list
        Required: False
    InfiltrationACH (object): Infiltration rate
        Access: item
        Required: False
    SpecPowerLightGain (object): Set point illuminance for artificial lighting
        Access: item
        Required: False
    ThermalBridgeFactor (object): Thermal bridge factor
        Access: item
        Required: False
    VentilationMode (object): Define ventilation mode: fully mechanical, hybrid, natural
        Access: item
        Required: False
    DaytimeFlushing (bool): Daytime stack ventilation
        Access: item
        Required: False
    NighttimeFlushing (object): Night time stact ventilation
        Access: item
        Required: False
    Sequence (object): Script variable Sequence
        Access: item
        Required: False

Returns:
    Regime (object): Connect to Zone Component
        Access: item
"""
version='2.1.2'
"""
ghenv.Component.Name = "Lizard_Zone_Regime"
ghenv.Component.NickName = 'Zone Regime'
ghenv.Component.Message = 'VER 2.1.2\n2019'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "3 | Regime"
"""
import scriptcontext as sc
class REGIME:
    def __init__(self):
        self.Name       = "REGIME"
        self.Persgain       = ""
        self.Compgain       = ""
        self.Lightgain      = ""
        self.Othergain      = ""
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
        Regime.Othergain = MiscGain
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
