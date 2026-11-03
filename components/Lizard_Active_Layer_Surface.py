"""
Use this component to add an active surface layer into building.
Replace regular BuildingSurface component.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.

Args:
    BRep (Brep): set one/multiple surfaces in Rhino (right click brep)
        Access: list
        Required: False
    ------------------- ActiveLayer
    SetTemperatureCooling (object): define a set temperature in ?C at which the cooling process starts
        Access: item
        Required: False
    SupplyTempCoolFluid (float): define a supply temperture in ?C for the cooling fluid
        Access: item
        Required: False
    ScheduleCoolFluid (object): define a schedule for the cooling fluid (refer to schedule library)
        Access: item
        Required: False
    MaxSpecCoolPower (object): power limitation for the hydronic loop
        Access: item
        Required: False
    SetTemperatureHeating (object): define a set temperature in ?C at which the heating process starts
        Access: item
        Required: False
    SupplyTempHeatFluid (float): define a supply temperture in ?C for the heating fluid
        Access: item
        Required: False
    ScheduleHeatFluid (object): Script input schedule_heat_fluid.
        Access: item
        Required: False
    MaxSpecHeatPower (object): power limitation for the hydronic loop
        Access: item
        Required: False
    CoolingTairOutside24hAbove (float): seasonal temperature switch in between heating and cooling mode
        Access: item
        Required: False
    TemperatureControl (str): define which information is tracked in order to have the system running
        Access: item
        Required: False
    DewpointControl (int): if True a dewpoint control is activated
        Access: item
        Required: False
    SupplyMode (str): define a supply mode: chiller (0), dry cooler (1), hybrid cooler (2)
        Access: item
        Required: False
    HeatingOn (int): if True, allowing active layer to work during heating mode
        Access: item
        Required: False
    CoolingOn (int): if True, allowing active layer to work during cooling mode
        Access: item
        Required: False
    ControlledBasedOn (object): You can link either an existing airnode name or a type of place holder variable name in order to make a userdefined control temperature. If you are using a non existing airnode or zone name you will have to add at least those variables Tair_dummyname in AIR mode, Top_dummyname in OPERATIVE mode and TSI_Sdummyname in surface mode as setpoint temperature
        Access: item
        Required: False
    SetBackHeating (object): Contains a collection of script-friendly data
        Access: item
        Required: False
    Circuit (object): Contains a collection of script-friendly data
        Access: item
        Required: False

Returns:
    SurfaceInfo (object): connect to corresponding airnode - HINT: Press shift key in order to connect multiple outputs to one input node
        Access: item
"""
version='2.2.1'
ghenv.Component.Name = "Lizard_Active_Layer_Surface"
"""
ghenv.Component.NickName = 'Active Surface'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "2 | Construction"
"""
import rhinoscriptsyntax as rs
import re
import scriptcontext as sc
import Rhino as rc
import uuid
import string
import math
import sys
import Grasshopper as gh
w = gh.Kernel.GH_RuntimeMessageLevel.Warning
err = gh.Kernel.GH_RuntimeMessageLevel.Error
#---- initial definition start
InputList = ["BRep","Circuit","SetTemperatureCooling","SupplyTempCoolFluid","ScheduleCoolFluid","MaxSpecCoolPower","SetTemperatureHeating","SetBackHeating","SupplyTempHeatFluid","ScheduleHeatFluid","MaxSpecHeatPower","CoolingTairOutside24hAbove","TemperatureControl","ControlledBasedOn","DewpointControl","SupplyMode","HeatingOn","CoolingOn"]
OutputList = ["out","SurfaceInfo"]
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
lizard_coll = sc.sticky[sc.doc.Path]["CONSTRUCTION"]()
library = sc.sticky[sc.doc.Path]["library"]
SurfaceInfo = []
data = []
faces = []
activelayer = 1
#ControlBasedOnTemperatureInAirnode = None
totalarea = 0
if Circuit is None:
    Circuit = 1
for items in BRep:
    faces.append(items)
    data.append(items)
    totalarea += rc.Geometry.Brep.GetArea(faces[-1], 0.0001, 0.0001)
for items in BRep:
    if 'Type' in locals() and Type:
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(items,'Type',Type)
    if 'Category' in locals() and Category:
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(items,'Boundarycond',Category)
        if Category == 'BOUNDARY':
            if BoundaryTemperature:
                sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(items,'Boundarytemp',BoundaryTemperature)
            else:
                sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(items,'Boundarytemp','Identical')
    if 'FrontBack' in locals() and FrontBack:
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(items,'Frontback',FrontBack)
    if 'Construction' in locals() and Construction:
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(items,'Construction',Construction)
    SurfaceInfo.append(items)
ActiveLayerType = ''
def getLayerInfo(wallname):
    global ActiveLayerType
    global OutsideDiameterPipe
    global DistancePipe
    global WallThicknessPipe
    global ConductivityPipe
    global Layer
    global Thickness
    global MassflowFluid
    global PipeLength
    cleaned_layer = []
    thickness_layer = []
    for wall_item in library.Walls:
        if wallname == wall_item.Name:
            cleaned_layer = wall_item.Layers.split()
            thickness_layer = wall_item.Thickness.split()
    #cleaned_layer = list(set(cleaned_layer))
    Layer = cleaned_layer
    Thickness = thickness_layer
    Wallthickness = 0
    for item in Thickness:
        Wallthickness += float(item)
    for layer_item in library.Layers:
        for cleaned_item in cleaned_layer:
            if layer_item.Name == cleaned_item:
                if layer_item.Pdiameter != '' or ('Cc_pidiameter' in dir(layer_item) and layer_item.Cc_pidiameter !=''):
                    if layer_item.Type == 'AL':
                        ActiveLayerType = layer_item.Name
                        OutsideDiameterPipe = layer_item.Pdiameter
                        DistancePipe = layer_item.Pspacing
                        WallThicknessPipe = layer_item.Pwallthickness
                        ConductivityPipe = layer_item.Pconductivity
                        PipeLength = layer_item.Plength
                        type = 'AL'
                        MassflowFluid = layer_item.Mflow
                    elif layer_item.Type == 'CL':
                        ActiveLayerType = layer_item.Name
                        OutsideDiameterPipe = layer_item.Cc_pidiameter
                        DistancePipe = layer_item.Cc_pspacing
                        WallThicknessPipe = 0
                        ConductivityPipe = 0
                        type = 'CL'
                        MassflowFluid = layer_item.Mflow
                        PipeLength = layer_item.Plength
if activelayer == 1:
    counter = 0
    for items in range(len(SurfaceInfo)):
        ObjectsFromLz = lizard_coll.callFromConstruction([SurfaceInfo[items]])
        getLayerInfo(ObjectsFromLz[0].__dict__['Construction'])
        if items == 0:
            sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Intemp','INPUT 1*TSUP_AL%s'%Circuit)
        else:
            LastObjectsFromLz = lizard_coll.callFromConstruction([SurfaceInfo[items-1]])
            sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Intemp','INPUT 1*TOFL_S{0}'.format(LastObjectsFromLz[0].__dict__['Surfnum']))
        if ActiveLayerType == '':
            ghenv.Component.AddRuntimeMessage(err, "Define active layer in wall assembly!")
            sys.exit()
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Name',ActiveLayerType)
        if type == 'AL':
            sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Pdiameter',OutsideDiameterPipe)
            sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Pspacing',DistancePipe)
        else:
            sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Cc_pidiameter',OutsideDiameterPipe)
            sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Cc_pspacing',DistancePipe)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Pwallthickness',WallThicknessPipe)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Pconductivity',ConductivityPipe*3.6)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Massflow',MassflowFluid)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Tempcooling',SupplyTempCoolFluid)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Schedulecooling',ScheduleCoolFluid)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Tempheating',SupplyTempHeatFluid)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Scheduleheating',ScheduleHeatFluid)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Tamb24hcooling',CoolingTairOutside24hAbove)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Activelayer',Circuit)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Nloops',max(int(totalarea/(PipeLength*DistancePipe)),1))
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Theat',SetTemperatureHeating)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Tcool',SetTemperatureCooling)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Shp',MaxSpecHeatPower)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Scp',MaxSpecCoolPower)
        if re.search('al',TemperatureControl):
            sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Tempctrl',re.sub('al','al%s'%Circuit,TemperatureControl))
        else:
            sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Tempctrl',TemperatureControl)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Space',ControlledBasedOn)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Tdpctrl',DewpointControl)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Supplymode',SupplyMode)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Yheat',HeatingOn)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Ycool',CoolingOn)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Wallthickness',Thickness)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Layer',Layer)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Allyearcl',0)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Schedcl',0)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(SurfaceInfo[items],'Setback',SetBackHeating)
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().getWallThickness(SurfaceInfo[items])
        "Druckverlustberechnung"
        C=21164
        n=1.68
        l=totalarea/(max(int(totalarea/(120*float(DistancePipe))),1)*float(DistancePipe))
        dP = C * MassflowFluid**n  * float(DistancePipe)**n * l**(n+1)/(3600)**n /1000
        counter = counter + 1
