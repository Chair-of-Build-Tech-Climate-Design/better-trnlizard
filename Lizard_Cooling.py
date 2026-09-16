"""
Define building Cooling controls.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    ------------------ Cooling
    SetTemperature (object): maximum temperature in zone
        Access: item
        Required: True
    MaxSpecCoolPower (object): maximum specific cooling power
        Access: item
        Required: True
    ControlledTemperature (object): temperature being control by ideal cooling
        Access: item
        Required: True
    MaxRelHum (object): maximum relative humidity in zone
        Access: item
        Required: True
    NightSetUp (object): allowed temperature increase in zone at nighttime
        Access: item
        Required: True
    Schedule (object): schedule for Cooling control (Refer to Schedule Library)
        Access: item
        Required: True
    OnTairOutside24hAbove (object): only start ideal cooling if Tamb_m24 above this value
        Access: item
        Required: True
    ControlledBasedOn (object): You can link either an existing airnode name or a type of place holder variable name in order to make a userdefined control temperature. If you are using a non existing airnode or zone name you will have to add at least those variables Tair_dummyname, Top_dummyname in OPERATIVE mode and Tset_cl_red_dummyname as setpoint temperature
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    -------------
    Cooling (object): connect to Cooling input in Thermal Zone component
        Access: item
"""
"""
version = '2.3.1'
ghenv.Component.Name = "Lizard_Cooling"
ghenv.Component.NickName = 'Cooling'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "Lizard"
ghenv.Component.SubCategory = "3 | Regime"
"""
import scriptcontext as sc
import Grasshopper as gh
rem = gh.Kernel.GH_RuntimeMessageLevel.Remark
bla = gh.Kernel.GH_RuntimeMessageLevel.Blank
warn = gh.Kernel.GH_RuntimeMessageLevel.Warning
#---- initial definition start
InputList = ["------------------ Cooling","SetTemperature","ControlledTemperature","ControlledBasedOn","MaxSpecCoolPower","MaxRelHum","NightSetUp","Schedule","OnTairOutside24hAbove"]
OutputList = ["out","-------------","Cooling"]
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
class COOLING:
    def __init__(self):
        # Building file input
        self.Name           = 'COOL_@aname'
        self.Humidity       = 100
        self.On             = 'INPUT 1*TAIR_SET_CL_@aname'
        self.Power          = 'INPUT 1*CL_BUI_@aname'
        self.Area_related_power = 1
        # Lizard dependent definitions
        self.Settemperature = 26
        self.Schedule       = ''
        self.Maxpower       = 100
        self.Cooling        = 1
        self.Elpowerfrac    = 0
        self.Setback        = 0
        self.Ctrl           = 'OPERATIVE'
        self.Tamb24hon      = 26
        self.Space          = None
        self.Type           = self.__class__.__name__
    def __repr__(self):
        """Class representation."""
        return "{}:{}".format(self.__class__.__name__, self.Name)
# Read Class Gain
Cooling = COOLING()
#Initial Settings
Cooling.Maxpower    = 100
Cooling.Settemperature = 26
Cooling.Setback     = 0
Cooling.Tamb24hon   = 12
#Input Depending Settings
if 'MaxSpecCoolPower' in locals() and MaxSpecCoolPower != None:
    Cooling.Maxpower = MaxSpecCoolPower
if 'ControlledTemperature' in locals():
    Cooling.Ctrl = ControlledTemperature
if 'ControlledBasedOn' in locals() and ControlledBasedOn != None:
    Cooling.Space = ControlledBasedOn
if 'MaxRelHum' in locals() and MaxRelHum != None:
    Cooling.Humidity = MaxRelHum
if 'SetTemperature' in locals() and SetTemperature != None:
    Cooling.Settemperature = SetTemperature
if 'NightSetUp' in locals() and NightSetUp != None:
    Cooling.Setback = NightSetUp
if 'OnTairOutside24hAbove' in locals() and OnTairOutside24hAbove != None:
    Cooling.Tamb24hon = OnTairOutside24hAbove
if 'Schedule' in locals() and Schedule != None:
    Cooling.Schedule = Schedule
else:
    Cooling.On = SetTemperature

#Integration of dict storage for json output
dck = dict()
dck['EQU'] = dict()
dck['EQU']['Cooling'] = dict()
dck['EQU']['Cooling']['SetPointTemperature'] = SetTemperature
dck['EQU']['Cooling']['ControlledBasedOn'] = ControlledTemperature
dck['EQU']['Cooling']['MaximumPower'] = MaxSpecCoolPower
dck['EQU']['Cooling']['TemperatureSetback'] = NightSetUp
dck['EQU']['Cooling']['WeeklySchedule'] = Schedule
dck['EQU']['Cooling']['ReleaseOutsideAirTemperature24hAbove'] = OnTairOutside24hAbove

dck['TYPES'] = dict()
Cooling.Json   = dck

switchcomp = locals()
if '------------------ Cooling' is not None and switchcomp['------------------ Cooling'] == False:
    Cooling = None
