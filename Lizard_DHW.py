"""
Define properties for Domestic Hot Water (DHW) demands of building.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    ------ DomesticHotWater
    FreshWaterTemperature (object): temperature of water source (system inlet)
        Access: item
        Required: True
    HotWaterTemperature (object): set point for water supply temperature (system outlet)
        Access: item
        Required: True
    -------------
    HotWaterPerPersonPerDay (object): amount of hot water used by one person in a day
        Access: item
        Required: True
    Schedule (object): select DHW schedule (matching full_load_hours)
        Access: item
        Required: True
    or ------------- (object): Script variable DHW
        Access: item
        Required: True
    HourlyValuesFileName (object): Script variable DHW
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    -------------
    Dhw (object): connect to DHW input in Thermal Zone component
        Access: item
"""
"""
version = '2.3.1'
ghenv.Component.Name = "Lizard_DHW"
ghenv.Component.NickName = 'DHW'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "Lizard"
ghenv.Component.SubCategory = "3 | Regime"
"""
import rhinoscriptsyntax as rs
import re
import Grasshopper as gh
import scriptcontext as sc
import ghpythonlib.components as ghcomp
import string
rem = gh.Kernel.GH_RuntimeMessageLevel.Remark
bla = gh.Kernel.GH_RuntimeMessageLevel.Blank
warn = gh.Kernel.GH_RuntimeMessageLevel.Warning
#---- initial definition start
InputList = ["------ DomesticHotWater","FreshWaterTemperature","HotWaterTemperature","HotWaterPerPersonPerDay","Schedule"]
OutputList = ["out","-------------","Dhw"]
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
class DHW:
    def __init__(self):
        self.Name = ''
        self.Tcw = 14
        self.Thw = 45
        self.Wwpperspday = 45
        self.Npers = 0
        self.Fhours = 2
        self.Schedule = ''
    def __repr__(self):
        """Class representation."""
        return "{}:{}".format(self.__class__.__name__, self.Name)
sched_library = sc.sticky[sc.doc.Path]['library'].Schedules
dailyarr = []
for sitem in sched_library:
    if sitem.Name == Schedule:
        for subitem in sitem.Hourly.split():
            for s2item in sched_library:
                if s2item.Name == subitem:
                    dailysum = 0
                    val = s2item.Values.split()
                    hour = s2item.Hours.split()
                    for vi,vitem in enumerate(val):
                        data = 0
                        if float(vitem) > 0 and vi < len(val) - 1:
                            data = (float(hour[vi+1])-float(hour[vi]))*float(vitem)
                        else:
                            continue
                        dailysum = dailysum + data
                    if dailysum == 0:
                        pass
                    else:
                        dailyarr.append(dailysum)

FullLoadHoursWater = sum(dailyarr)/(len(dailyarr))

Dhw         = DHW()
Dhw.Name    = 'DHW'
if Schedule:
    Dhw.Schedule = Schedule
if FreshWaterTemperature:
    Dhw.Tcw = FreshWaterTemperature
if HotWaterTemperature:
    Dhw.Thw = HotWaterTemperature
if HotWaterPerPersonPerDay:
    Dhw.Wwpperspday = HotWaterPerPersonPerDay
if FullLoadHoursWater:
    Dhw.Fhours = FullLoadHoursWater
if Schedule:
    Dhw.Schedule = Schedule
if "HourlyValuesFileName" in locals():
    if HourlyValuesFileName is not None:
        Dhw.Filename = HourlyValuesFileName
switchcomp = locals()
if '------ DomesticHotWater' is not None and switchcomp['------ DomesticHotWater'] == False:
    Dhw = None
