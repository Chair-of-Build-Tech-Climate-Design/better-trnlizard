"""
Define building heating controls.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    ------------------ Heating
    SetTemperature (object): minimum temperature in zone
        Access: item
        Required: True
    ControlledTemperature (object): temperature being control by ideal heating
        Access: item
        Required: True
    MaxSpecHeatPower (object): maximum specific heating power
        Access: item
        Required: True
    MinRelHum (object): minimum relative humidity in zone
        Access: item
        Required: True
    RadiativeFraction (object): Script variable Heating
        Access: item
        Required: True
    NightSetBack (object): temperature setback in zone at nighttime
        Access: item
        Required: True
    Schedule (object): schedule for heating control (Refer to Schedule Library)
        Access: item
        Required: True
    OnTairOutside24hBelow (object): Script input on_tairoutside24h_below.
        Access: item
        Required: True
    ControlledBasedOn (object): You can link either an existing airnode name or a type of place holder variable name in order to make a userdefined control temperature. If you are using a non existing airnode or zone name you will have to add at least those variables Tair_dummyname, Top_dummyname in OPERATIVE mode and Tset_ht_red_dummyname as setpoint temperature
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    -------------
    Heating (object): connect to heating input in Thermal Zone component
        Access: item
"""
"""
version = '2.3.1'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "3 | Regime"
"""
ghenv.Component.Name = "Lizard_Heating"
ghenv.Component.NickName = 'Heating'
import scriptcontext as sc
import Grasshopper as gh
rem = gh.Kernel.GH_RuntimeMessageLevel.Remark
bla = gh.Kernel.GH_RuntimeMessageLevel.Blank
warn = gh.Kernel.GH_RuntimeMessageLevel.Warning
#---- initial definition start
InputList = ["------------------ Heating","SetTemperature","ControlledTemperature","ControlledBasedOn","MaxSpecHeatPower","MinRelHum","NightSetBack","Schedule","OnTairOutside24hBelow"]
OutputList = ["out","-------------","Heating"]
def findInOut(info, pararray):
    oldpar = []
    newpar = []
    unusedpar = []
    if info == "INP":
        for item in ghenv.Component.Params.Input:
            oldpar.append(item.NickName)
    else:
        for item in ghenv.Component.Params.Output:
            oldpar.append(item.NickName)
    for item in pararray:
        if item in oldpar:
            pass
        else:
            newpar.append(item)
    for item in oldpar:
        if item in pararray:
            pass
        else:
            unusedpar.append(item)
    return newpar, unusedpar
def addPar(info, pararray):
    for item in pararray:
        paramString = gh.Kernel.Parameters.Param_ScriptVariable()
        paramString.Name = item
        paramString.NickName = item
        if info == "INP":
            inputindex = ghenv.Component.Params.Input.Count
            ghenv.Component.Params.RegisterInputParam(paramString,inputindex)
        else:
            outputindex = ghenv.Component.Params.Output.Count
            ghenv.Component.Params.RegisterOutputParam(paramString,outputindex)
newpari, unusedpari = findInOut("INP",InputList)
newparo, unusedparo = findInOut("OUT",OutputList)
#for item in unusedpari:
#    ghenv.Component.AddRuntimeMessage(warn, "Input %s is not required anymore, please delete!"%item)
#for item in unusedparo:
#    ghenv.Component.AddRuntimeMessage(rem, "Output %s is not required anymore, please delete!"%item)
if len(newpari)>0:
    addPar("INP",newpari)
if len(newparo)>0:
    addPar("OUT",newparo)
ghenv.Component.Params.OnParametersChanged()
#---- initial definition end
class HEATING:
    def __init__(self):
        # Building file input
        self.Name           = 'HEAT_@aname'
        self.Humidity       = 0
        self.On             = 'INPUT 1*TAIR_SET_HT_@aname'
        self.Power          = 'INPUT 1*HT_BUI_@aname'
        self.Area_related_power = 1
        self.Elpowerfrac    = 0
        self.Rrad           = 0.1
        # Lizard dependent definitions
        self.Settemperature = 20
        self.Schedule       = ''
        self.Maxpower       = 100
        self.Heating        = 1
        self.Type           = self.__class__.__name__
        self.Setback        = 3
        self.Tamb24hon      = 12
        self.Ctrl           = 'OPERATIVE'
        self.Space          = None
        self.CMF_LIMIT = '21'
    def __repr__(self):
        """Class representation."""
        return "{}:{}".format(self.__class__.__name__, self.Name)
# Read Class Gain
Heating = HEATING()
#Input Depending Settings
if 'MaxSpecHeatPower' in locals() and MaxSpecHeatPower != None:
    Heating.Maxpower = MaxSpecHeatPower
if 'ControlledTemperature' in locals():
    Heating.Ctrl = ControlledTemperature
if 'ControlledBasedOn' in locals() and ControlledBasedOn != None:
    Heating.Space = ControlledBasedOn
if 'MinRelHum' in locals() and MinRelHum != None:
    Heating.Humidity = MinRelHum
if 'SetTemperature' in locals() and SetTemperature != None:
    Heating.Settemperature = SetTemperature
if 'NightSetBack' in locals() and NightSetBack != None:
    Heating.Setback = NightSetBack
if 'OnTairOutside24hBelow' in locals() and OnTairOutside24hBelow != None:
    Heating.Tamb24hon = OnTairOutside24hBelow
if 'Schedule' in locals() and Schedule != None:
    Heating.Schedule = Schedule
else:
    Heating.On = SetTemperature
if 'RadiativeFraction' in locals() and RadiativeFraction != None:
    Heating.Rrad = RadiativeFraction

#Integration of dict storage for json output
dck = dict()
dck['EQU'] = dict()
dck['EQU']['Heating'] = dict()
dck['EQU']['Heating']['SetPointTemperature'] = SetTemperature
dck['EQU']['Heating']['ControlledBasedOn'] = ControlledTemperature
dck['EQU']['Heating']['MaximumPower'] = MaxSpecHeatPower
dck['EQU']['Heating']['TemperatureSetback'] = NightSetBack
dck['EQU']['Heating']['WeeklySchedule'] = Schedule
dck['EQU']['Heating']['ReleaseOutsideAirTemperature24hBelow'] = OnTairOutside24hBelow

dck['TYPES'] = dict()
Heating.Json   = dck

switchcomp = locals()
if '------------------ Heating' in switchcomp and switchcomp['------------------ Heating'] == False:
    Heating = None
