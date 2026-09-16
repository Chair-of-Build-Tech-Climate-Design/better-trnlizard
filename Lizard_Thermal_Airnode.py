"""
Link building surface definitions and regime data
to this Thermal Zone to generate building and other airnode information needed for thermal simulations.
-
TRNLizard 
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    ZoneName (object): define zone name, if you have multiple airnodes give different Airnodes the same Zone name.
        Access: item
        Required: True
    AirnodeName (object): define airnode name
        Access: item
        Required: True
    SurfaceInfo (Brep): link all airnode related surface definitions
        Access: list
        Required: True
    Regime (object): connect the regime component
        Access: item
        Required: True
    AreaPerPerson (object): define the area per person in order to quantify the regime definitions
        Access: item
        Required: True
    VolumeUserDef (object): define a value if the volume is different from the geometrical volume
        Access: item
        Required: True
    RefAreaBRepUserDef (Brep): set geometry for reference floor area calculation
        Access: list
        Required: True
    TotAirnodeAreaBRep (Brep): set geometry for reference of the total load calculation to p_tot_1h.prn
        Access: list
        Required: True
    ComfortPts (object): define the geometrical points for those a comfort evaluation would be possible by the regime definition
        Access: list
        Required: True
    DaylightCtrl (object): Script variable Thermal Airnode
        Access: list
        Required: True
    OutputInfo (object): link additional userdefined output information
        Access: list
        Required: True
    ComplexShade (object): Script variable Thermal Airnode
        Access: item
        Required: True
    Sequence (object): Script variable Thermal Airnode
        Access: item
        Required: True
    BeamMode (object): Contains a collection of script-friendly data
        Access: item
        Required: True
    DiffuseMode (object): Contains a collection of script-friendly data
        Access: item
        Required: True
    LongwaveMode (object): Contains a collection of script-friendly data
        Access: item
        Required: True
    Wcapr (object): Script variable Thermal Airnode
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    Airnode (object): 
        Access: item
    Center (object): 
        Access: item
    OriToCheck (object): Script variable Thermal Airnode
        Access: item
    PtsToCheck (object): Script variable Thermal Airnode
        Access: item
"""
import rhinoscriptsyntax as rs
import re
import scriptcontext as sc
import sys
import Grasshopper as gh
import uuid
import Rhino as rc
import os
import copy
version = '2.3.2'
date = sc.sticky[sc.doc.Path]["date"]
ghenv.Component.Name = "Lizard_Thermal_Airnode"
ghenv.Component.NickName = 'Thermal Airnode'
ghenv.Component.Message = 'VER %s\n%s'%(version,date)
ghenv.Component.Category = "Lizard"
ghenv.Component.SubCategory = "0 | Project"
rem = gh.Kernel.GH_RuntimeMessageLevel.Remark
bla = gh.Kernel.GH_RuntimeMessageLevel.Blank
warn = gh.Kernel.GH_RuntimeMessageLevel.Warning
#---- initial definition start
InputList = ["ZoneName","AirnodeName","SurfaceInfo","Regime","AreaPerPerson","VolumeUserDef","RefAreaBRepUserDef","BeamMode","DiffuseMode","LongwaveMode","ComfortPts","DaylightCtrl","OutputInfo","ComplexShade","Sequence"]
OutputList = ["Out","Airnode","Center","OriToCheck","PtsToCheck"]
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
w = gh.Kernel.GH_RuntimeMessageLevel.Warning
err = gh.Kernel.GH_RuntimeMessageLevel.Error
warn = '*** Warning *** '
if len(SurfaceInfo) > 0:
    rs.EnableRedraw(False)
    getVolume = sc.sticky[sc.doc.Path]["getVolume"]
    timing = sc.sticky[sc.doc.Path]["timing"]
    getSurfaceOrientation = sc.sticky[sc.doc.Path]["getSurfaceOrientation"]
    getOrientation = sc.sticky[sc.doc.Path]["getOrientation"]
    getSurfaceType = sc.sticky[sc.doc.Path]["getSurfaceType"]
    checkWindowsInWalls = sc.sticky[sc.doc.Path]["checkWindowsInWalls"]
    defineGeosurf = sc.sticky[sc.doc.Path]["defineGeosurf"]
    lizard_coll = sc.sticky[sc.doc.Path]["CONSTRUCTION"]()
    AIRNODE = sc.sticky[sc.doc.Path]["AIRNODE"]
    getFloorArea = sc.sticky[sc.doc.Path]["getFloorArea"]
    DaylightInfo = None
    GeoMode = '3D_DATA_CONCAVE' #options are 3D_DATA_CONCAVE or 3D_DATA
    FSolAir = 0.1
    if 'Trnflow' in locals():
        pass
    else:
        Trnflow = None #define as list
    #Modifications for simplified Zone
    Airnode_name    = AirnodeName
    #VolumeUserDef  = 0
    capacitance_fact_userdef = 1
    #radiation_mode  = RadiationMode
    ComfortPoints  = ComfortPts
    #Modifications for simplified Zone
    if BeamMode == 'DETAILED':
        geosurf_floor   = 0
    else:
        geosurf_floor   = 0.6
    ObjectsFromLz   = lizard_coll.callFromConstruction(SurfaceInfo)
    SurfaceInfo = []
#collect first the additional windows
    for LO in ObjectsFromLz:
        #print LO.Type
        if LO.Type == 'ADDWINDOW': 
            SurfaceInfo.append(LO)
    for LO in ObjectsFromLz:
        if LO.Type != 'ADDWINDOW': 
            SurfaceInfo.append(LO)
    Match = []
    orientations = []
    if len(SurfaceInfo) <= 3:
        print '!At least four surfaces have to be connected!'
        sys.exit()
    OriToCheck = []
    PtsToCheck = []
    Airnode             = AIRNODE(Airnode_name)
    Airnode.Orientations= getSurfaceOrientation(SurfaceInfo)
    getSurfaceType(SurfaceInfo)
    Match               = checkWindowsInWalls(SurfaceInfo,Match)
    Airnode.Surfaces    = SurfaceInfo
    Airnode.Zonename    = ZoneName
    Airnode.Beam        = BeamMode
    Airnode.Diffuse     = DiffuseMode
    Airnode.Longwave    = LongwaveMode
    Airnode.Geomode     = GeoMode
    Airnode.Fsolair     = FSolAir
    Airnode.Areaperperson  = AreaPerPerson
    if Wcapr is not None:
        Airnode.Wcapr = Wcapr
    error = 0
    error2 = 0
    if VolumeUserDef == 0 or VolumeUserDef =='Null' or VolumeUserDef is None:
        VolumeUserDef  = 0
        Airnode.Volume, Airnode.Center, error, box      = getVolume(SurfaceInfo)
        Center = Airnode.Center
        #check if ComfortPts are inside the volume
        ptsdummy = []
        cmfptserror = 0
        for point in ComfortPoints:
            dpts = point
            if type(point) is rc.Geometry.Brep:
                #print "found"
                pmassprop = rc.Geometry.AreaMassProperties.Compute(point)
                dpts = pmassprop.Centroid
            if box.IsPointInside(dpts, 0.00001, True):
                ptsdummy.append(point)
            else:
                PtsToCheck.append(point)
                cmfptserror = 1
        if cmfptserror == 1:
            print 'Some comfort pts are outside the volume and are automatically deleted!'
            ghenv.Component.AddRuntimeMessage(w, "Some comfort pts are outside the volume and are automatically deleted!")
        ComfortPoints = ptsdummy
        subsurfaces = []
        error2 = 0
        for ix,item in enumerate(box.Faces):
            subsurfaces.append(box.DuplicateSubBrep([ix]))
            for sitem in SurfaceInfo:
                dummyPolycurveX = rc.Geometry.PolylineCurve.JoinCurves(subsurfaces[ix].Edges)
                dummyPolycurveY = rc.Geometry.PolylineCurve.JoinCurves(sitem.Faces.Edges)
                dummy = rc.Geometry.PolyCurve.CreateBooleanIntersection(dummyPolycurveX[0],dummyPolycurveY[0])
                if dummy:
                    area_surf1 = rc.Geometry.AreaMassProperties.Compute(subsurfaces[ix].Faces[0]).Area
                    area_surf2 = rc.Geometry.AreaMassProperties.Compute(sitem.Faces.Faces[0]).Area
                    delta_area = abs(area_surf1 - area_surf2)
                    if delta_area < 0.000001:
                        if getOrientation(subsurfaces[ix]) != sitem.Orientation:
                            print "Check surface %s, normal vector in wrong direction!"%sitem.Surfnum
                            OriToCheck.append(sitem.Faces)
                            ghenv.Component.AddRuntimeMessage(err, "Check surface %s!"%sitem.Surfnum)
                            error2 = 1
        if error == 1:
            print 'Volume is not closed!'
            ghenv.Component.AddRuntimeMessage(err, "Volume is not closed!")
        elif error2 == 1:
            pass
            #sys.exit()
        else:
            pass
        if Airnode.Volume <= 1:
            ghenv.Component.AddRuntimeMessage(err, "Check Volume - Value is too small!")
    else:
        Airnode.Volume = VolumeUserDef
    zonevolume          = Airnode.Volume
    volume              = Airnode.Volume
    Airnode.Capacitance = "INPUT {}*NodeHeatCapacitance".format(capacitance_fact_userdef) # Airnode.Volume * capacitance_fact_userdef
    if RefAreaBRepUserDef:
        Airnode.Floorarea = 0
        for item in RefAreaBRepUserDef:
            Airnode.Floorarea = Airnode.Floorarea  + item.GetArea()
        print 'User defined reference area will be used!'
    else:
        Airnode.Floorarea   = getFloorArea(SurfaceInfo)
    Airnode.Refarea     = Airnode.Floorarea
    orientations        = Airnode.Orientations
    if 'TotAirnodeAreaBRep' in locals() and TotAirnodeAreaBRep:
        for item in TotAirnodeAreaBRep:
            Airnode.Totfloorarea += item.GetArea()
    if 'AreaTotalLoadCalc' in locals() and AreaTotalLoadCalc:
        Airnode.Totfloorarea = AreaTotalLoadCalc
    #if Airnode.Totfloorarea == 0:
    #    Airnode.Totfloorarea = Airnode.Refarea
    if Regime and Regime.Persgain != "":
        Airnode.Gain.append(Regime.Persgain)
    if Regime and Regime.Compgain  != "":
        Airnode.Gain.append(Regime.Compgain)
    if Regime and Regime.Lightgain != "":
        Airnode.Gain.append(Regime.Lightgain)
        if Regime.Lightgain.Dctrl == 'DLC':
            if DaylightCtrl:
                pass
            else:
                print 'Please link daylight ctrl component to use the feature of controling the artificial lighting!'
                ghenv.Component.AddRuntimeMessage(err, "Please link daylight ctrl component to use the feature of controling the artificial lighting!")
                sys.exit()
    if Regime and len(Regime.Othergain) != 0:
        other_gains = Regime.Othergain
        if isinstance(other_gains, str):
            other_gains = [other_gains]
        for gain in other_gains:
            if isinstance(other_gains, str):
                if len(gain)>0:
                    Airnode.Gain.append(gain)
            else:
                Airnode.Gain.append(gain)
    if Regime and Regime.Thbgain   != "":
        Airnode.Gain.append(Regime.Thbgain)
    if Regime and Regime.Udefgain != "":
        Airnode.Gain.append(Regime.Udefgain)
    if Regime and Regime.Mechvent != "":
        Airnode.Ventilation.append(Regime.Mechvent)
    if Regime and Regime.Stvent1 != "":
        Airnode.Ventilation.append(Regime.Stvent1)
    if Regime and Regime.Stvent2 != "":
        Airnode.Ventilation.append(Regime.Stvent2)
    if Regime and Regime.Infiltration != "":
        Airnode.Infiltration = Regime.Infiltration
    if Regime and Regime.Earthduct != "":
        Airnode.Earthduct   = Regime.Earthduct
    if Regime and Regime.Heating != "":
        Airnode.Heating     = Regime.Heating
    if Regime and Regime.Cooling != "":
        Airnode.Cooling     = Regime.Cooling
    if Regime and Regime.Domestic != "":
        Airnode.Dhw     = Regime.Domestic
        #Airnode.Dhw.Npers = Airnode.Floorarea / AreaPerPerson
        #print Airnode.Dhw.Npers
    if Regime and Regime.Pmvcomfort != "":
        if ComfortPoints:
            #Regime.Pmvcomfort.sensor_points = ComfortPoints
            Airnode.Comfort.append(Regime.Pmvcomfort)
            Airnode.Comfortpts = ComfortPoints
        else:
            print 'Please link comfortPts to the Airnode and in the same time the comfort component to the Regime!'
            ghenv.Component.AddRuntimeMessage(err, "Please link comfortPts to the Airnode and in the same time the comfort component to the Regime!")
            sys.exit()
    if Regime and Regime.Setcomfort != "":
        for item in Regime.Setcomfort:
            #item.sensor_points = ComfortPoints
            Airnode.Comfort.append(item)
            Airnode.Comfortpts = ComfortPoints
    if Regime and "Area" in dir(Regime):
        if Regime.Area:
            if abs(Regime.Area - float(Airnode.Floorarea)) > 1:
                ghenv.Component.AddRuntimeMessage(err, "Please check area definition of the 4108 Regime!")
    if Regime and "Volume" in dir(Regime):
        if Regime.Volume:
            if abs(Regime.Volume - float(Airnode.Volume)) > 1:
                ghenv.Component.AddRuntimeMessage(err, "Please check volume definition of the 4108 Regime!")
    if DaylightInfo:
        Airnode.Daylight = DaylightInfo
    if OutputInfo:
        Airnode.Output = OutputInfo
    if DaylightCtrl:
        Airnode.Daylightctrl = DaylightCtrl
        Airnode.Daylightpts = []
        Airnode.Daylight = []
        for item in DaylightCtrl:
            Airnode.Daylightpts.extend(item.Grid)
            Airnode.Daylight.append(item.Gridinfo)
    if 'ComplexShade' in locals() and ComplexShade:
        Airnode.Complexshade = ComplexShade
    if geosurf_floor > 0:
        defineGeosurf(geosurf_floor,SurfaceInfo)
    Airnode.Activelayer = []
    for items in Airnode.Surfaces:
        items.Airnode = Airnode_name
        if items.Activelayer == 1:
            Airnode.Activelayer.append('1')
        if items.Activelayer == 2:
            Airnode.Activelayer.append('2')
    if Airnode.Comfort:
        counter = 0
        for subitem in Airnode.Comfortpts:
            counter = counter + 1
        Airnode.comfortptsno = counter
    else:
        Airnode.comfortptsno = 0
    if 'Trnflow' in locals() and Trnflow:
        Airnode.Trnflow = copy.deepcopy(Trnflow)
        Airnode.Trnflow.Tnode = Airnode.Name
        zarray = []
        for sitem in SurfaceInfo:
            for vertices in sitem.Vertices:
                zarray.append(vertices.Z)
        minz = min(zarray)
        cpts = Airnode.Center
        node = rc.Geometry.Point3d(cpts.X, cpts.Y, minz)
        Airnode.Trnflow.Refheight = round(minz,2)
        Airnode.Trnflow.Refpoint = node
    # Print Information to the out Output of this component
    print 'Airnode name:    {0:s}'.format(Airnode.Name)
    print 'Floor area:  {0:16.2f} m2'.format(Airnode.Floorarea)
    print 'Airnode volume:  {0:16.3f} m2'.format(float(Airnode.Volume))
    # Starting from here the syntax checks and warnings are defined
    print '***********************************************'
    #starting from here information in translated into dictionary
    Airnode = sc.sticky[sc.doc.Path]["ZONECOLL"]().addToZones(ghenv.Component.InstanceGuid.ToString() + str(uuid.uuid4()),Airnode)
    SurfaceInfo = []
    gain = []
    comfort = []
    heating = []
    cooling = []
    infiltration = []
    ventilation = []
    earthduct = []
    domestic_hot_water = []
    DaylightInfo = []
    if error == 1 or error2 == 1:
        Airnode = None
    rs.EnableRedraw(True)
