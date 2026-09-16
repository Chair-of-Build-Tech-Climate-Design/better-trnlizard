"""
Define properties of natural ventilation in system due
to window/chimney openings in building (drive by stack effect).
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    ----------- StackVentilation
    EffOpeningAreaBottom (object): define effective opening area of lower operable windows: total area of side and top openings when lower window(s) is fully open
        Access: item
        Required: True
    OrFloorRelatedEffOpAreaBottom (object): define effective opening area of lower operable windows as percentage related to the floor area
        Access: item
        Required: True
    EffOpeningAreaTop (object): define effective opening area of upper operable windows: total area of side and top opening when window is open
        Access: item
        Required: True
    OrFloorRelatedEffOpAreaTop (object): define effective opening area of upper operable windows as percentage related to the floor area
        Access: item
        Required: True
    HeightDifference (object): height (in meters) between bottom/lower windows and top/upper windows
        Access: item
        Required: True
    ONTemperatureAbove (object): windows open when air temperature exceeds this value / - / Hint: Windows will close if ambient air temperature is 3°C above room air temperature
        Access: item
        Required: True
    OFFTemperatureBelow (object): windows close when air temperature is below this value / - / Hint: Windows will also close if ambient air temperature is 3°C above room air temperature
        Access: item
        Required: True
    ONTairOutsideAbove (object): windows only open when ambient temperature is above this value
        Access: item
        Required: True
    ONTairOutside24hAbove (object): windows only open when daily mean ambient temperature is above this threshold
        Access: item
        Required: True
    Schedule (object): select schedule for natural ventilation (when operable windows will be used)
        Access: item
        Required: True
    MaxAirChange (object): define maximum air change allowed
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    -------------
    StackVentilation1 (object): connect to ventilation input in Thermal Zone component
        Access: item
"""
"""
version = '2.3.1'
ghenv.Component.Name = "Lizard_Stack_Ventilation_1"
ghenv.Component.NickName = 'Stack Ventilation 1'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "Lizard"
ghenv.Component.SubCategory = "3 | Regime"
"""
import re
import scriptcontext as sc
#Additional Inputs
OutsideTemp = None
OutsideHumidity = None
HumidityControl = 0
class VENTILATION:
    def __init__(self):
        self.Name           = 'VENT'
        self.Type           = 'VENTILATION'
        self.Class = "Ventilation"
        self.Ventilation    = 1
        self.Ach            = 0
        self.Achmin         = 0
        self.Vflow          = 0
        self.Vflowppers     = 0
        self.Aefftop        = 0
        self.Aeffbot        = 0
        self.Aefftopfl      = 0
        self.Aeffbotfl      = 0
        self.Hdiff          = 0.5
        self.Schedule       = ''
        self.Schedule2      = ''
        self.Tairon         = 25
        self.Tairoff        = 22
        self.Tambon         = 10
        self.Tamb24on       = 10
        self.Stack          = 1
        self.Toutside       = 'TAMB'
        self.Humoutside     = 'ABSHUM_AMB'
        self.Temperature    = 'INPUT 1*{0}'.format(self.Toutside)
        self.Airchange      = ''
        self.Humidity       = 'INPUT 1*{0}'.format(self.Humoutside)
        self.Maxach         = 3
        self.Hybrid         = 0
        self.Sfp            = 0.8    #W/(m?.h)
        self.Hrcsens        = 0
        self.Hrclat         = 0
        self.Tsummer        = 18
        self.Tsummer2       = 18
        self.Twinter        = 22
        self.Twinter2       = 22
        self.Humsummer      = -1
        self.Humwinter      = -1
        self.Tamb24hcl      = 12
        self.Hybrid         = 0
        self.Thyblow        = 10
        self.Thybhigh       = 26
        self.Winterred      = 0
        self.Toutsidemv     = 'TAMB'
        self.Humoutsidemv   = 'ABSHUM_AMB'
        self.On             = 0
        self.Specfanpower = 0
        self.Absminhum   = 'INPUT 1*ABSHUM_AMB'
        self.Absmaxhum   = 'INPUT 1*ABSHUM_AMB'
        self.Senshr = 0
        self.Calcqahu = 0
        self.Calcmode = "Standard"
        self.Humctrl = 0
        self.Tempctrl = 'AIR'
    def __repr__(self):
        """Class representation."""
        return "{}:{}".format(self.__class__.__name__, self.Name)
# Read Class Ventilation
StackVentilation1 = VENTILATION()
# Initial Settings
StackVentilation1.Name     = 'STVENT1'
StackVentilation1.Type     = 'STACKVENTILATION'
StackVentilation1.Airchange= 'INPUT 1*ACR_SV1'
StackVentilation1.Schedule = ''
StackVentilation1.Hdiff    = 1
StackVentilation1.Tairon   = 25
StackVentilation1.Tairoff  = 23
StackVentilation1.Tambon   = 5
StackVentilation1.Tamb24on = 5
StackVentilation1.Maxach   = 3
StackVentilation1.Aefftopfl = 0
StackVentilation1.Aeffbotfl = 0
# Input Depending Settings
if 'HeightDifference' in locals() and HeightDifference != None:
    StackVentilation1.Hdiff    = HeightDifference
if 'Schedule' in locals() and Schedule != None:
    StackVentilation1.Schedule = Schedule
if 'ONTemperatureAbove' in locals() and ONTemperatureAbove != None:
    StackVentilation1.Tairon = ONTemperatureAbove
if 'OFFTemperatureBelow' in locals() and OFFTemperatureBelow != None:
    StackVentilation1.Tairoff = OFFTemperatureBelow
if 'ONTairOutsideAbove' in locals() and ONTairOutsideAbove != None:
    StackVentilation1.Tambon = ONTairOutsideAbove
if 'ONTairOutside24hAbove' in locals() and ONTairOutside24hAbove != None:
    StackVentilation1.Tamb24on = ONTairOutside24hAbove
if 'MaxAirChange' in locals() and MaxAirChange != None:
    StackVentilation1.Maxach = MaxAirChange
if 'OutsideTemp' in locals() and OutsideTemp != None:
    StackVentilation1.Toutside = OutsideTemp
    StackVentilation1.Temperature = 'INPUT 1*{0}'.format(StackVentilation1.Toutside)
if 'OutsideHumidity'  in locals() and OutsideHumidity != None:
    StackVentilation1.Humoutside = OutsideHumidity
    StackVentilation1.Humidity = 'INPUT 1*{0}'.format(StackVentilation1.Humoutside)
    StackVentilation1.Absminhum  = 'INPUT 1*{0}'.format(StackVentilation1.Humoutside)
    StackVentilation1.Absmaxhum  = 'INPUT 1*{0}'.format(StackVentilation1.Humoutside)
if 'OrFloorRelatedEffOpAreaTop'  in locals() and OrFloorRelatedEffOpAreaTop != None:
    StackVentilation1.Aefftopfl = OrFloorRelatedEffOpAreaTop / 100
if 'OrFloorRelatedEffOpAreaBottom'  in locals() and OrFloorRelatedEffOpAreaBottom is not None:
    StackVentilation1.Aeffbotfl = OrFloorRelatedEffOpAreaBottom / 100
if 'EffOpeningAreaTop'  in locals() and EffOpeningAreaTop is not None:
    StackVentilation1.Aefftop = EffOpeningAreaTop
if 'EffOpeningAreaBottom'  in locals() and EffOpeningAreaBottom is not None:
    StackVentilation1.Aeffbot = EffOpeningAreaBottom
if 'HumidityControl'  in locals() and HumidityControl != None:
    StackVentilation1.Humctrl  = HumidityControl
if 'TemperatureControl'  in locals() and TemperatureControl != None:
    StackVentilation1.Tempctrl  = TemperatureControl

#Integration of dict storage for json output
dck = dict()
dck['EQU'] = dict()
dck['EQU']['StackVentilation1'] = dict()
dck['EQU']['StackVentilation1']['OpeningAreaBottom'] = 'max(%s, %s*AirnodeFloorArea)'%(EffOpeningAreaBottom,OrFloorRelatedEffOpAreaBottom)
dck['EQU']['StackVentilation1']['OpeningAreaTop'] = 'max(%s, %s*AirnodeFloorArea)'%(EffOpeningAreaTop,OrFloorRelatedEffOpAreaTop)
dck['EQU']['StackVentilation1']['HeightDifference'] = HeightDifference 
dck['EQU']['StackVentilation1']['ActivedAirTemperatureAbove'] = ONTemperatureAbove
dck['EQU']['StackVentilation1']['DisabledAirTemperatureBelow'] = OFFTemperatureBelow
dck['EQU']['StackVentilation1']['ReleaseOutsideAirTemperatureAbove'] = ONTairOutsideAbove
dck['EQU']['StackVentilation1']['ReleaseOutsideAir24hTemperatureAbove'] = ONTairOutside24hAbove
dck['EQU']['StackVentilation1']['WeeklySchedule'] = Schedule
dck['EQU']['StackVentilation1']['MaximumAirChange'] = MaxAirChange

print dck['EQU']['StackVentilation1']['OpeningAreaBottom']

dck['TYPES'] = dict()
StackVentilation1.Json   = dck

switchcomp = locals()
if switchcomp['----------- StackVentilation'] is not None and switchcomp['----------- StackVentilation'] is False:
    StackVentilation1 = None
