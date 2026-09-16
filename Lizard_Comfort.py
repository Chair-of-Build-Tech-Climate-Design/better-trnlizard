"""
Define the comfort parameters and sensor points in the Thermal Zone.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    --------------- Comfort
    ClothingFactor (object): 
        Access: item
        Required: True
    MetabolicRate (object): 
        Access: item
        Required: True
    ExternalWork (object): 
        Access: item
        Required: True
    Mode (object): comfort evaluation mode, PMV or PMV-elevated air speed
        Access: item
        Required: True
    AirVelocity (object): in m/s
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    -------------
    Comfort (object): connect to comfort input of Thermal Zone
        Access: item
"""
"""
version = '2.3.1'
ghenv.Component.Name = "Lizard_Comfort"
ghenv.Component.NickName = 'Comfort'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "Lizard"
ghenv.Component.SubCategory = "5 | Tools"
"""
import rhinoscriptsyntax as rs
import re
import scriptcontext
import ghpythonlib.components as ghcomp
import Grasshopper.Kernel as gh
import System
from ghpythonlib.componentbase import executingcomponent as component
import Grasshopper, GhPython
import os
import System.Drawing as sd

comp = ghenv.Component
ghdoc = comp.OnPingDocument()

#major settings
compdict = {}
compdict['PMV'] = ["--------------- Comfort","ClothingFactor","MetabolicRate","ExternalWork","Mode","AirVelocity"]
compdict['SET'] = ["------- SET Parameters","AirVelocity2","AirVelocity3","AirVelocity4","Shading_Factor"]
compdict['UTCI'] = ["------- UTCI Parameters","AirTemperature", "AirVelocity_UTCI", "rel_Humidity","SwitchEvapoCooling","Efficiency","Setpoint","Shading_factor","Air_Velocity_Dry_Mist","Setpoint_Value"] 
#compdict['OC'] = ["------- UTCI Parameters","AirTemperature", "AirVelocity_UTCI", "rel_Humidity","SwitchEvapoCooling","Efficiency","Setpoint","Shading_factor","Air_Velocity_Dry_Mist","Setpoint_Value"] 
setdict = {}
setdict['AirVelocity2'] = {}
setdict['AirVelocity2']['value'] = 0.3
setdict['AirVelocity2']['min'] = 0
setdict['AirVelocity2']['max'] = 1.5
setdict['AirVelocity3'] = {}
setdict['AirVelocity3']['value'] = 0.6
setdict['AirVelocity3']['min'] = 0
setdict['AirVelocity3']['max'] = 1.5
setdict['AirVelocity4'] = {}
setdict['AirVelocity4']['value'] = 1.2
setdict['AirVelocity4']['min'] = 0
setdict['AirVelocity4']['max'] = 1.5
setdict['AirTemperature'] = {}
setdict['AirTemperature']['value'] = 20
setdict['AirTemperature']['min'] = 0
setdict['AirTemperature']['max'] = 30
setdict['AirVelocity_UTCI'] = {}
setdict['AirVelocity_UTCI']['value'] = 0.5
setdict['AirVelocity_UTCI']['min'] = 0
setdict['AirVelocity_UTCI']['max'] = 10
setdict['rel_Humidity'] = {}
setdict['rel_Humidity']['value'] = 50
setdict['rel_Humidity']['min'] = 0
setdict['rel_Humidity']['max'] = 100
setdict['SwitchEvapoCooling'] = {}
setdict['SwitchEvapoCooling']['value'] = 50
setdict['SwitchEvapoCooling']['min'] = 0
setdict['SwitchEvapoCooling']['max'] = 100
setdict['Efficiency'] = {}
setdict['Efficiency']['value'] = 0.5
setdict['Efficiency']['min'] = 0
setdict['Efficiency']['max'] = 1
setdict['Setpoint'] = {}
setdict['Setpoint']['value'] = 18
setdict['Setpoint']['min'] = 0
setdict['Setpoint']['max'] = 25
setdict['Shading_factor'] = {}
setdict['Shading_factor']['value'] = 0.5
setdict['Shading_factor']['min'] = 0
setdict['Shading_factor']['max'] = 1
setdict['Air_Velocity_Dry_Mist'] = {}
setdict['Air_Velocity_Dry_Mist']['value'] = 0.5
setdict['Air_Velocity_Dry_Mist']['min'] = 0
setdict['Air_Velocity_Dry_Mist']['max'] = 1
setdict['Setpoint_Value'] = {}
setdict['Setpoint_Value']['value'] = 18
setdict['Setpoint_Value']['min'] = 10
setdict['Setpoint_Value']['max'] = 25

class PARAMETERS:
    def __init__(self, bmode, actmode, datadict):
        self.Mode = actmode
        self.Bmode = bmode
        self.Delarr = []
        self.Datdict = datadict
        if bmode == actmode:
            self.Inparr = self.Datdict[bmode]
        else:
            self.Inparr = self.Datdict[bmode] + self.Datdict[actmode]
        self.Oldpar = []
        self.Unusedpar = []
        self.Newpar = []
    def cleanArray(self):
        for ditem in self.Datdict:
            if ditem == self.Bmode:
                continue
            elif ditem == self.Mode:
                pass
            else:
                self.Delarr.extend(self.Datdict[ditem])
    def cleanInOut(self):
        #ghenv.Component.ExpireSolution(False)
        for ditem in self.Delarr:
            try:
                for item in ghenv.Component.Params.Input:
                    if item.NickName == ditem:
                        ghenv.Component.Params.UnregisterInputParameter(item,False)
                        ghenv.Component.Params.OnParametersChanged()
                        #ghenv.Component.ExpireSolution(True)
                        break
            except:
                pass
    def addPar(self):
        info = 'INP'
        for item in self.Newpar:
            paramString = gh.Parameters.Param_ScriptVariable()
            paramString.Name = item
            paramString.NickName = item
            paramString.Optional = True
            if info == "INP":
                inputindex = ghenv.Component.Params.Input.Count
                ghenv.Component.Params.RegisterInputParam(paramString,inputindex)
            #else:
            #    outputindex = ghenv.Component.Params.Output.Count
            #    ghenv.Component.Params.RegisterOutputParam(paramString,outputindex)
            ghenv.Component.Params.OnParametersChanged()
        #ghenv.Component.ExpireSolution(True)
    def findInOut(self):
        info = 'INP'
        if info == "INP":
            for item in ghenv.Component.Params.Input:
                self.Oldpar.append(item.NickName)
        for item in self.Inparr:
            if item in self.Oldpar:
                pass
            else:
                self.Newpar.append(item)
        for item in self.Oldpar:
            if item in self.Inparr and item not in self.Delarr:
                pass
            else:
                self.Unusedpar.append(item)

class dynInput:
    def __init__(self, comp, maxy):
        self.Comp = comp
        self.Maxy = maxy
        if len(test.Newpar)>0:
            for ci,citem in enumerate(comp.Params.Input):
                for item in test.Newpar:
                    if re.match("^-",item):
                        continue
                    else:
                        if citem.NickName == item:
                            self.make_Slider(citem,citem.Attributes.Pivot.X, citem.Attributes.Pivot.Y, ci)
        else:
            pass
            
    def make_Slider(self, citem, locX, locY, index):
        #try:
        if 1 > 0:
            #instantiate  new slider
            
            slid = Grasshopper.Kernel.Special.GH_NumberSlider()
            slid.CreateAttributes() #sets up default values, and makes sure your slider doesn't crash rhino
            #add the slider
            inputcount = index
            slid.Attributes.Pivot = sd.PointF(self.Comp.Attributes.DocObject.Attributes.Pivot.X - slid.Attributes.Bounds.Width - 300, self.Maxy)
            self.Maxy += 20
            slid.Slider.DecimalPlaces = 2
            if citem.NickName in setdict:
                slid.Slider.Maximum = setdict[citem.NickName]['max']
                slid.Slider.Minimum = setdict[citem.NickName]['min']
                slid.SetSliderValue((setdict[citem.NickName]['value']));
            else:
                slid.Slider.Maximum = 10
                slid.Slider.Minimum = 0
                slid.SetSliderValue(10);
    
            #add slider to canvas.
            ghdoc = self.Comp.OnPingDocument()
            ghdoc.AddObject(slid, False)
    
            #Connect the new slider to this component
            citem.AddSource(slid)
                
        #except Exception, ex:
        #    self.Comp.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, str(ex))
        #    print ex

test = PARAMETERS('PMV',Mode, compdict)
test.cleanArray()
test.findInOut()
test.addPar()
test.cleanInOut()

maxy = 0
#ghenv.Component.Params.Input.Item
for ci, citem in enumerate(ghenv.Component.Params.Input):
    maxy = max(maxy, citem.Attributes.Pivot.Y)


test2 = dynInput(comp, maxy)

SwitchEvapoCooling = False 
class COMFORT:
    def __init__(self):
        self.Name = 'CMF'
        self.Type = 'COMFORT'
        self.Class = "Comfort"
        self.Clothing = ClothingFactor
        self.Met = MetabolicRate
        self.Work = ExternalWork
        self.Velocity = AirVelocity
        #self.sensor_points = sensor_points
        self.Comfort = 1
        self.Velocity2 = 0.3
        self.Velocity3 = 0.6
        self.Velocity4 = 1.2
        self.Elvairspeed = 0
        # @OC START
        self.Tair_UTCI = 20
        self.vWind_UTCI = 0
        self.relHum_UTCI = 50
        if SwitchEvapoCooling == True:
            self.EVA_CL_SW = 1
        else:
            self.EVA_CL_SW = 0
        self.EVA_CL_EFF = 0
        self.EVA_CL_SETP = 20
        self.v_UTCI_DM = 0
        self.UTCI_Setpoint = 20
        # @OC END
        self.Fshade = 0
        self.Fproject = 0
    def __repr__(self):
        """Class representation."""
        return "{}:{}".format(self.__class__.__name__, self.Name)
Comfort         = COMFORT()
if Mode == 'SET':
    Comfort.Elvairspeed = 1
    Comfort.Fshade = Shading_factor
if 'AirTemperature' in locals():
    Comfort.Tair_UTCI = AirTemperature
    Comfort.vWind_UTCI = AirVelocity_UTCI
    Comfort.relHum_UTCI = rel_Humidity
    if SwitchEvapoCooling == True:
        Comfort.EVA_CL_SW = 1
    else:
        Comfort.EVA_CL_SW = 0
    Comfort.EVA_CL_EFF = Efficiency
    Comfort.EVA_CL_SETP = Setpoint
    Comfort.Fshade = Shading_factor
    Comfort.v_UTCI_DM = Air_Velocity_Dry_Mist
    Comfort.UTCI_Setpoint = Setpoint_Value
if 'AirVelocity2' in locals():
    Comfort.Velocity2 = AirVelocity2
if 'AirVelocity3' in locals():
    Comfort.Velocity3 = AirVelocity3
if 'AirVelocity4' in locals():
    Comfort.Velocity4 = AirVelocity4
switchcomp = locals()

if switchcomp['--------------- Comfort'] is not None and switchcomp['--------------- Comfort'] == False:
    Comfort = None
