"""
This is the key component to store model information
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    Template (object): link the TRNBUILD file template
        Access: item
        Required: True
    WindowLibrary (object): link the window library component that contains the window database
        Access: list
        Required: True
    TrnsysFolder (object): define the path to your TRNSYS installation folder
        Access: item
        Required: True
    ProjectFolder (object): define the path to your project folder; if nothing is defined the path of the saved gh file is used automatically
        Access: item
        Required: False
    ShortVariantName (object): that name is used in the path structure and should not have special signs or blanks
        Access: item
        Required: True
    LongVariantName (object): that name is used for description
        Access: item
        Required: True
    WeatherFile (object): link either *.epw or user-defined weather data in *.109, *.tmy3, *.tm2, *.tm3, *.try format
        Access: item
        Required: True
    Hemisphere (object): link either the string SOUTHERN or NORTHERN as string
        Access: item
        Required: True
    Altitude (object): define the building altitude for thermal simulation
        Access: item
        Required: True
    AnnualMeanOutsideTemp (object): Script variable Lizard
        Access: item
        Required: True
    AmbientPressure (object): Script variable Lizard
        Access: item
        Required: True
    AddSchedules (object): link the used schedules that are required for the regime components or the active layer
        Access: list
        Required: True
    AddLayers (object): link the layer definitions required for the wall assemblies
        Access: list
        Required: True
    AddConstructions (object): link the construction definitions containing the single layers
        Access: list
        Required: True
    AnnualSchedules (object): link the annual schedules definition in order to account e.g. for vacations, etc.
        Access: list
        Required: True
    Variants (object): Script variable Lizard
        Access: item
        Required: True
    Reload (object): define True if you added information to the library by walls, layers, etc. in order to update the library
        Access: item
        Required: True
    x (object): Script variable Lizard
        Access: item
        Required: True

Returns:
    out (object): Log Information!!!
        Access: item
    Sequence (object): Script variable Lizard
        Access: item
    Variants (object): Script variable Lizard
        Access: item
"""
import rhinoscriptsyntax as rs
import Rhino as rc
import scriptcontext as sc
import ghpythonlib.components as ghcomp
import Grasshopper.Kernel as gh
import math
import shutil
import sys
import os
import System
import time
import copy
import re
from copy import deepcopy
version = '2.3.1'
date = "2022"
if sc.doc.Path in sc.sticky.keys():
    pass
else:
    sc.sticky[sc.doc.Path] = {}
sc.sticky[sc.doc.Path] ["version"] = version
sc.sticky[sc.doc.Path] ["date"] = date
"""
vhoang 25.11.2016
Update:
- Adding "exe_mode" to switch between trnexe.exe and trnexe64.exe
vhoang 03.11.2016
Update: 
- Line 1474-1482: Adding switch between "BUI" and "BID" building mode, depending on the input Trnsysfolder (as Marion requested)
"""
ghenv.Component.Name = "Lizard_Component"
ghenv.Component.NickName = 'Lizard'
ghenv.Component.Message = 'VER %s\n%s'%(version,date)
ghenv.Component.Category = "Lizard"
ghenv.Component.SubCategory = "0 | Lizard"
try: ghenv.Component.AdditionalHelpFromDocStrings = "1"
except: pass
w = gh.GH_RuntimeMessageLevel.Warning
err = gh.GH_RuntimeMessageLevel.Error
warn = '*** Warning *** '
PI = math.pi
abs_tolerance = sc.doc.ModelAbsoluteTolerance
project_name = 'Model'
advanced_modeling = False
#OC_Tool Variant trigger
sc.sticky[sc.doc.Path]['variant_trigger'] = False
#OC_Tool END
"""
if 'e' in str(abs_tolerance):
    precision = str(abs_tolerance).split('-')
    print precision
    no_of_digits = int(precision[1])
else:
    no_of_digits = len(str(abs_tolerance).split('.')[1])
    print no_of_digits
"""
# userdefined variable name changes
AddWalls = AddConstructions
def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        #file = open(project_variants_folder + 'timing.txt','a')
        #file.write('%s function took %0.3f ms\n' % (f.func_name, (time2-time1)*1000.0))
        #file.close()
        #print '%s function took %0.3f ms' % (f.func_name, (time2-time1)*1000.0)
        return ret
    return wrap
@timing
def BrowseForFolder(folder=None, message=None, title=None):
    """Display browse-for-folder dialog allowing the user to select a folder
    Parameters:
    folder[opt] = a default folder
    message[opt] = a prompt or message
    title[opt] = a dialog box title
    Returns:
    selected folder
    None on error
    """
    message = 'Select here the Lizard project main folder or connect the input of the ProjectFolder definition to the lizard component in order to avoid this dialog to pop up'
    dlg = System.Windows.Forms.FolderBrowserDialog()
    if folder:
        if not isinstance(folder, str): folder = str(folder)
        dlg.SelectedPath = folder
    if message:
        if not isinstance(message, str): message = str(message)
        dlg.Description = message
    if dlg.ShowDialog()==System.Windows.Forms.DialogResult.OK:
        return dlg.SelectedPath
if ProjectFolder and os.path.isdir(ProjectFolder):
    pass
elif ProjectFolder and not os.path.isdir(ProjectFolder):
    pass
    print 'Directory is not existing, please create folder or rename directory'
    ghenv.Component.AddRuntimeMessage(err, "Directory is not existing, please create folder")
    sys.exit()
else:
    ProjectFolder = os.path.dirname(sc.doc.Path) + '\\'
ProjectFolder.encode('string-escape')
project_variants_folder = ProjectFolder + project_name + '\\'
project_variants_folder.encode('string-escape')
variants_folder = project_variants_folder + ShortVariantName + '\\'
variants_folder.encode('string-escape')
results_folder = ProjectFolder + 'Results\\' + ShortVariantName + '\\'
results_folder.encode('string-escape')
if not os.path.exists(project_variants_folder):
    os.mkdir(project_variants_folder)
if not os.path.exists(variants_folder):
    os.mkdir(variants_folder)
#if not os.path.exists(ProjectFolder + 'Results\\'):
#    os.mkdir(ProjectFolder + 'Results\\')
#if not os.path.exists(results_folder):
#    os.mkdir(results_folder)
class DEFAULTCONSTRUCTION:
    def __init__(self):
        self.Extroof1  = 'ERF_H'
        self.Extroof2  = 'ERF_L'
        self.Actroof   = 'ERF_ASL'
        self.Intceil1  = 'ICL_H'
        self.Intceil2  = 'ICL_SUS'
        self.Actceil   = 'ICL_ASL'
        self.Extwall   = 'EWL_L'
        self.Extwall2  = 'EWL_L'
        self.Intwall   = 'IWL_L'
        self.Intfloor  = 'IFL_L'
        self.Gndfloor  = 'GFL_L'
        self.Extwin    = '10001'
        self.Extwin1   = '10001'
        self.Extwin2   = '10001'
class GEOMETRY:
    def __init__(self, surface=0):
        self.Surface        = surface
        self.Vertices       = []
        self.Verticestest   = []
        self.VerticeNo      = ''
        self.Normalvector   = []
        self.Type           = 'WALL'
        self.Subsurface     = []
        self.Subsurfacedef  = []
        self.Boundarycond   = ''
        self.Boundarytemp   = 0
        self.Geosurf        = 0
        self.Faces          = []
        self.Orientation    = []
        self.Construction   = ''
        self.Area           = ''
        self.Insthick       = 0.2
        self.Surfnum        = ''
        self.Winid          = ''
        self.Windows        = ''
        self.Framefrac      = 0.2
        self.Uframe         = 1.2                   #in W/m?.K
        self.Cframe         = self.c_value()        #in kJ/hr.m?.K
        self.Mshade         = 'Non'                 #Out = Outside, Int = Inside, Non = Not existing
        self.Mshadeglazingcover = 0.8               #%/100 as part of the glazing that is covered by the shading
        self.Shadeopen      = 648
        self.Shadeclose     = 540
        self.Shdtairabove   = 22
        self.Intemp         = 'INPUT 1*Tinal' + str(1)
        #self.Pipediameter   = 0.02                  #m
        #self.Pipedistance   = 0.2                   #m
        #self.Pipewallthickness = 0.002              #m
        #self.Pipeconductivity = 0.35                #W/(m?.K)
        self.Massflow       = 12                    #kg/(h.m?)
        self.Mflowmin       = 11                    #kg/(h.m?)
        self.Tempheating    = 32                    #?C
        self.Scheduleheating = ''
        self.Tempcooling    = 18                    #?C
        self.Schedulecooling = ''
        self.Tamb24hcooling = 12                    #?C
        self.Activelayer    = 0
        self.Nloops         = 1
        self.Looplength     = 120
        self.Cpfluid        = 4.19
        self.Theat          = 21
        self.Tcool          = 25
        self.Shp            = 40
        self.Scp            = 50
        self.Adjsurf        = 0
        self.Airnode        = ''
        self.Adjairnode     = ''
        self.Frontback      = 'FRONT'
        self.Coupling       = 0
        self.Couplupper     = ''
        self.Coupllower     = ''
        self.Couplmode      = 'permanent'
        self.Couplacrinv    = 0
        self.Couplacrper    = 0
        self.Tempctrl       = 'OPERATIVE'
        self.Baseconfigid   = 0
        self.BSDFWindows    = ''
        self.Configids      = '0,'
        self.BSDFazimuth    = 0
        self.Adjsearch      = 0
        self.Extactivelayer = 0
        self.Pert = 0
        self.Penrt = 0
        self.Flowtoairnode = 1 #updated 20170626
        self.Radmaterial0 = 'undefined'
        self.Radmaterial1 = 'undefined'
        self.Fname_bsdf1 = ''
        self.Fname_bsdf2 = ''
        self.Fframe = 0
        self.Absframe = 0.6
        self.Gapvent1 = 0
        self.Gapmflow1 = 0
        self.Gapintemp1 = 18
        self.Psiedge = 0
        self.Spacid = 4
        self.Wwid = 1.35
        self.Wheig = 1.4
        self.Yheat = 1
        self.Ycool = 1
        self.Cshade = None
        self.Space = None
        self.Setback = 0
        self.Bndairnode = None
        self.Bndsearch = 0
        self.Filemat = None
        """
        self.Shd2 = None
        self.Shd3 = None
        self.Shd4 = None
        self.Shd5 = None
        self.Shd6 = None
        self.Shd7 = None
        self.Shd8 = None
        self.Shd9 = None
        """
    def c_value(self):
        return round(1/(1/self.Uframe - 0.17)*3.6,2)
class AIRNODE:
    #surfaces = []
    #comfortpts = 0
    def __init__(self, airnode_name = ''):
        self.Name           = airnode_name
        self.Zonename       = airnode_name
        self.Surfaces       = []
        self.Volume         = 0
        self.Capacitance    = 0
        self.Floorarea      = 0
        self.Areaperperson  = 0
        self.Orientations   = []
        self.Gain           = []
        self.Heating        = []
        self.Dhw            = []
        self.Cooling        = []
        self.Infiltration   = []
        self.Ventilation    = []
        self.Activelayer    = 0
        self.Comfort        = []
        self.Earthduct      = []
        self.Beam           = 'STANDARD'
        self.Diffuse        = 'STANDARD'
        self.Longwave       = 'STANDARD'
        self.Geomode        = '3D_DATA'
        self.Alsurfaces     = []
        self.Daylight       = ''
        self.BSDFWinsurfaces = []
        self.Output         = []
        self.Winsurfaces = []
        self.Extwallsurfaces = []
        self.Extwallsurfacesori = []
        self.Tbdsurfaces = []
        self.Ecalsurfaces = []
        self.Eficalsurfaces = []
        self.Totfloorarea = 0
        self.Daylightpts = []
        self.Daylightctrl = None
        self.Refarea = 1
        self.Comfortpts = []
        self.Wcapr = 3
    def __repr__(self):
        """Airnode representation."""
        return "{}:{}".format(self.__class__.__name__, self.Name)
class POLLUTANTS:
    def __init__(self):
        self.Pollutants     = 1
        self.Name           = 'CO2'
        self.Molmass        = 44.01
        self.Decay          = 0
class LARGEOPENINGS:
    def __init__(self):
        self.Largeopenings  = 1
        self.Name           = ''
        self.Lowidth        = 1
        self.Loheight       = 1
        self.Cdopen         = 0
        self.Cdclose        = 0
class STRAIGHTDUCTS:
    def __init__(self):
        self.Straightducts  = 1
        self.Name           = ''
        self.Diam1          = 1
        self.Diam2          = 1
        self.Roughness      = 0.1
        self.Length         = 10
        self.Fitting        = 5
        self.Param1         = 60
        self.Param2         = 0
        self.Cdopen         = 0
        self.Cdclose        = 0
class AUXILIARYNODES:
    def __init__(self):
        self.Auxiliarynodes  = 1
        self.Name           = ''
        self.Refheight      = 0
        self.Defcond        = "OFF"
        self.Temp           = 0
        self.Humidity       = 0
class FANS:
    def __init__(self):
        self.Fans  = 1
        self.Name           = ''
        self.Flowrate        = 0
class EXTERNALNODES:
    def __init__(self):
        self.Externalnodes  = 1
        self.Name           = ''
        self.Cp             = 0.6
        self.Refheight      = 10
        self.Winddir        = 0
        self.Data = ''
class WINDVELOCITYPROFILE:
    def __init__(self):
        self.Windvelocityprofile  = 1
        self.Winddir        = '0'
        self.Veloexp        = '0.18'
class THERMALZONES:
    def __init__(self):
        self.Thermalzones   = 1
        self.Tnode          = ''
        self.Refheight      = 0
        self.Theight        = 3
        self.Tdepth         = 5
        self.Iniconcentration = 0.000656
        self.Source         = 0
        self.Pollutant      = 'CO2'
class AIRLINKNETWORK:
    def __init__(self):
        self.Airlinknetwork = 1
        self.Link           = ''
        self.Id             = 0
        self.Frnode         = ''
        self.Tonode         = ''
        self.Frheight       = ''
        self.Toheight       = ''
        self.Wiownhf        = 1
        self.Fscale         = 0
class LIBRARY:
    windowdata = []
    windowlib  = []
    def __init__(self):
        self.Layers = []
        self.Walls = []
        self.Windows = []
        self.Schedules = []
        self.Gain = []
        self.Annualschedules = []
class LAYER:
    def __init__(self, name=''):
        self.Name           = name
        self.Pspacing       = ''
        self.Pdiameter      = ''
        self.Conductivity   = ''
        self.Capacity       = ''
        self.Density        = ''
        self.Pwallthickness = ''
        self.Pconductivity  = ''
        self.Cpfluid        = ''
        self.Resistance     = ''
        self.Pert           = 0
        self.Penrt          = 0
    def mymethod(self):
        pass
    def getlayerdefinition(self,paragraph):
        lines=paragraph
        for searchline in range(len(lines)):
            match_layer=re.search(r'LAYER\s{0}\s'.format(self.Name),lines[searchline])
            if match_layer is not None:
                data = lines[searchline+1]
                data = re.sub(":","",data)
                data = re.sub("=","",data)
                data = data.split( )
                if data[0] == 'RESISTANCE':
                    self.Resistance = data[1]
                if data[0] == 'CONDUCTIVITY':
                    self.Conductivity   = data[1]
                    self.Capacity       = data[3]
                    self.Density        = data[5]
                if data[0] == 'PSPACING':
                    self.Pspacing       = data[1]
                    self.Pdiameter      = data[3]
                    self.Pwallthickness = data[5]
                    self.Pconductivity  = data[7]
                    self.Cpfluid        = data[9]
class WALL:
    def __init__(self, name=''):
        self.Name = name
        self.Layers = ''
        self.Wall = 1
        self.Thickness   = ''
        self.Abs_front   = 0.6
        self.Abs_back    = 0.6
        self.Eps_front   = 0.9
        self.Eps_back    = 0.9
        self.Hfront      = 11
        self.Hback       = 64
    def getwalldefinition(self,paragraph):
        lines=paragraph
        for searchline in range(len(lines)):
            match_wall=re.search(r'^WALL\s{0}\s'.format(self.Name),lines[searchline])
            if match_wall is not None:
                data1 = lines[searchline+1]
                data1 = re.sub("\n","",data1)
                data1 = data1.split('=')
                self.Layers = data1[1]
                data2 = lines[searchline+2]
                data2 = re.sub("\n","",data2)
                data2 = data2.split('=')
                self.Thickness = data2[1]
                data3 = lines[searchline+3]
                data3 = re.sub("\n","",data3)
                data3 = my_split(data3, [':', '='])
                self.Abs_front = data3[1]
                self.Abs_back  = data3[3]
                data4 = lines[searchline+4]
                data4 = re.sub("\n","",data4)
                data4 = my_split(data4, [':', '='])
                self.Eps_front = data4[1]
                self.Eps_back  = data4[3]
                data5 = lines[searchline+5]
                data5 = re.sub("\n","",data5)
                data5 = my_split(data5, [':', '='])
                self.Hfront      = data5[1]
                self.Hback       = data5[3]
    def printwalldefinition(self):
        lines=Template.Wall
        for attr, value in self.__dict__.iteritems():
            lines=re.sub('@self.{0}'.format(attr), value, lines)
            walldefinition.append(lines)
class WINDOW:
    def __init__(self, name=''):
        self.Name = name
        self.Type = 'WINDOW'
        self.Winid = name
        self.Desc  = ''
        self.Data  = ''
        self.Shgc = None
        self.Uglas = None
        self.Tvis = None
    def getwindowsdefinition(self,paragraph):
        lines=paragraph
        for searchline in range(len(lines)):
            match_window=re.search(r'Desc\s{0}\s'.format(self.Name),lines[searchline])
            if match_window is not None:
                data = lines[searchline+1]
                data = re.sub("^\s+","",data)
                data = re.sub("\n","",data)
                data = re.sub("\w+="," ",data)
                data = data.split(":")
                self.Convective     = data[0]
                self.Radiative      = data[1]
                self.Humidity       = data[2]
    def getShgc(self):
        lines=self.Data.split('\n')
        for searchline in range(len(lines)):
            match_window=re.match(r'SHGC',lines[searchline])
            if match_window is not None:
                data = lines[searchline].split()
                self.Shgc     = data[1]
    def getTvis(self):
        lines=self.Data.split('\n')
        for searchline in range(len(lines)):
            match_window=re.match(r'Tvis_daylight',lines[searchline])
            if match_window is not None:
                data = lines[searchline].split()
                self.Tvis     = data[1]
    def getUglas(self):
        lines=self.Data.split('\n')
        for searchline in range(len(lines)):
            match_window=re.match(r'Overall and Center of Glass',lines[searchline])
            if match_window is not None:
                data = lines[searchline+5].split()
                self.Uglas     = data[9]
class SCHEDULE:
    def __init__(self, name=''):
        self.Name = name
        self.Hours = ''
        self.Values = ''
        self.Days = ''
        self.Hourly = ''
        self.Userdef = 0
    def getscheduledefinition(self,paragraph):
        lines=paragraph
        for searchline in range(len(lines)):
            match=re.search(r'SCHEDULE\s{0}\s'.format(self.Name),lines[searchline])
            if match is not None:
                data1 = lines[searchline+1]      #
                data2 = lines[searchline+2]      #
                data1 = re.sub("\n","",data1)
                data2 = re.sub("\n","",data2)
                data1 = data1.split("=")
                data2 = data2.split("=")
                data1[0] = re.sub(" ","",data1[0])
                data2[0] = re.sub(" ","",data2[0])
                if data1[0] == 'HOURS':
                    self.Hours  = data1[1]
                    self.Values = data2[1]
                if data1[0] == 'DAYS':
                    self.Days   = data1[1]
                    self.Hourly = data2[1]
    def printscheduledefinition(self):
        if self.Days != '':
            lines=Template.Weeklyschedule
            for attr, value in self.__dict__.iteritems():
                lines=re.sub('@self.{0}'.format(attr), value, lines)
            scheduledefinition.append(lines)
        if self.Hours != '':
            lines=Template.Dailyschedule
            for attr, value in self.__dict__.iteritems():
                lines=re.sub('@self.{0}'.format(attr), value, lines)
            scheduledefinition.append(lines)
class DAILYSCHEDULE:
    def __init__(self):
        self.Name   = ''
        self.Type   = 'daily'
        self.Hours  = ''
        self.Values = ''
        self.Data = []
    def setValues(self,definition):
        hour_view = []
        daytime_array = []
        inloop = 0
        for daytime in range(0,25):
            daytime_array.append(daytime)
            hour_view.append(0)
            for item in definition:
                fromto,value = item.split(';')
                dummy  = re.sub('to','',fromto)
                start,stop = dummy.split()
                if daytime >= float(start) and  daytime <= float(stop):
                    hour_view[-1] = value
                    if daytime == float(stop):
                        hour_view[-1] = 0
                    else:
                        break
        self.Hours    = ' '.join(map(str, daytime_array))
        self.Values   = ' '.join(map(str, hour_view))
        self.Data     = hour_view
        return hour_view
class WEEKLYSCHEDULE:
    def __init__(self):
        self.Name = ''
        self.Days = '1 2 3 4 5 6 7'
        self.Hourly = ''
        self.Daysarray = []
        self.Hoursarray = []
        self.Valuesarray = []
        self.Weekarray = []
def cleanVertices(Points):
    cleaned_points = []
    for pi, pitem in enumerate(Points):
        if pi == 0:
            lvec = rc.Geometry.Vector3d(Points[-1])
            cvec = rc.Geometry.Vector3d(Points[pi])
            nvec = rc.Geometry.Vector3d(Points[pi+1])
        elif pi == len(Points)-1:
            lvec = rc.Geometry.Vector3d(Points[pi-1])
            cvec = rc.Geometry.Vector3d(Points[pi])
            nvec = rc.Geometry.Vector3d(Points[0])
        else:
            lvec = rc.Geometry.Vector3d(Points[pi-1])
            cvec = rc.Geometry.Vector3d(Points[pi])
            nvec = rc.Geometry.Vector3d(Points[pi+1])
        lastdif = rc.Geometry.Vector3d.Subtract(cvec,lvec)
        factor = lastdif.Length
        maxdif = rc.Geometry.Vector3d.Subtract(nvec,lvec)
        maxdif.Unitize()
        newv = lvec + maxdif * factor
        if abs(newv.X - cvec.X) < 0.0000000001 and abs(newv.Y - cvec.Y) < 0.0000000001 and abs(newv.Z - cvec.Z) < 0.0000000001:
            print "cleaned surface vertices"
        else:
            cleaned_points.append(pitem)
    return cleaned_points
def checkVerticesOrder(Points, Normal):
    new_points = []
    attached_points = []
    quit = 0
    for pi, pitem in enumerate(Points):
        if pi == 0:
            rearrange = 0
            vec1 = rc.Geometry.Vector3d(Points[-1] - Points[pi])
            vec2 = rc.Geometry.Vector3d(Points[pi+1] - Points[pi])
            if math.degrees(rc.Geometry.Vector3d.VectorAngle(vec2, vec1, Normal)) < 180:
                quit = 1
                new_points.append(pitem)
            else:
                rearrange += 1
                attached_points.append(pitem)
        elif pi == len(Points)-1:
            new_points.append(pitem)
            pass
        else:
            vec1 = rc.Geometry.Vector3d(Points[pi-1] - Points[pi])
            vec2 = rc.Geometry.Vector3d(Points[pi+1] - Points[pi])
            if math.degrees(rc.Geometry.Vector3d.VectorAngle(vec2, vec1, Normal)) < 180 or quit == 1:
                quit = 1
                new_points.append(pitem)
            else:
                rearrange += 1
                attached_points.append(pitem)
    new_points.extend(attached_points)
    return new_points
class CONSTRUCTION:
    def addToConstruction(self, Brep, GHComponentID):
        # check if the lizarddictionary already existed
        # if not create the dictionary
        #if 'list' in str(type(Brep)):
        #    pass
        #else:
        #    Brep = [Brep]
        if not sc.sticky[sc.doc.Path].has_key('Const_coll'): sc.sticky[sc.doc.Path]['Const_coll'] = {}
        if not sc.sticky[sc.doc.Path].has_key('Surface_Counter'): sc.sticky[sc.doc.Path]['Surface_Counter'] = 0
        geometries = []
        info       = []
        itemcount = 0
        for obj_items in range(len(Brep)):
            info.append(sc.sticky[sc.doc.Path]["GEOMETRY"](Brep[obj_items]))
            info[-1].Faces         = Brep[obj_items]
            info[-1].Area          = Brep[obj_items].GetArea()
            ori_normal             = Brep[obj_items].Faces[0].NormalAt(0,0)
            info[-1].Vertices      = getSurfaceVertices(ori_normal,Brep[obj_items])
            info[-1].Normalvector  = ori_normal
            if len(info[-1].Vertices) > 4:
                info[-1].Vertices = cleanVertices(info[-1].Vertices)
            info[-1].Vertices = checkVerticesOrder(info[-1].Vertices, ori_normal)
            lizkey = ("%s"%Brep[obj_items]).split()[3]
            if sc.sticky[sc.doc.Path].has_key('Const_coll'):
                if sc.sticky[sc.doc.Path]['Const_coll'].has_key(lizkey):
                    info[obj_items].Surfnum = sc.sticky[sc.doc.Path]['Const_coll'][lizkey].Surfnum
                else:
                    sc.sticky[sc.doc.Path]['Surface_Counter'] = sc.sticky[sc.doc.Path]['Surface_Counter'] + 1
                    info[obj_items].Surfnum  = sc.sticky[sc.doc.Path]['Surface_Counter']
            sc.sticky[sc.doc.Path]['Const_coll'][lizkey] = info[obj_items]
            geometry = info[obj_items].Surface
            #for ditem in [a for a in dir(info[obj_items]) if not a.startswith('__')]:
            #    print ditem, getattr(info[obj_items], ditem)
            #    geometry.UserDictionary.Set(ditem, getattr(info[obj_items], ditem))
            geometry.UserDictionary.Set('LID', lizkey)
            geometry.UserDictionary.Set('ID', info[obj_items].Surfnum)
            geometries.append(geometry)
        return geometries
    def callFromConstruction(self, geometryList):
        Objects = []
        for geometry in geometryList:
            if 1 > 0:
                key = geometry.UserDictionary['LID']
                if sc.sticky[sc.doc.Path]['Const_coll'].has_key(key):
                    Objects.append(copy.deepcopy(sc.sticky[sc.doc.Path]['Const_coll'][key]))
            else:
                pass
        return Objects
    def getAllKeysFromConstruction(self):
        try:
            if len(sc.sticky[sc.doc.Path]['Const_coll'].keys()) > 0:
                return sc.sticky[sc.doc.Path]['Const_coll'].keys()
        except:
            pass
            return ''
    def clearKeys(self):
        try:
            if len(sc.sticky[sc.doc.Path]['Const_coll'].keys()) > 0:
                sc.sticky[sc.doc.Path]['Const_coll'].clear()
        except:
            pass
            return ''
    def updateConstruction(self, geometry, infoclass, data):
        try:
            key = geometry.UserDictionary['LID']
            if sc.sticky[sc.doc.Path]['Const_coll'].has_key(key):
                sc.sticky[sc.doc.Path]['Const_coll'][key].__dict__[infoclass] = data
        except:
            pass
    def getWallThickness(self,geometry):
        try:
            if 'list' in str(type(geometry)):
                for gitem in geometry:
                    key = gitem.UserDictionary['LID']
                    for wall_item in library.Walls:
                        if sc.sticky[sc.doc.Path]['Const_coll'][key].Construction == wall_item.Name:
                            thickness_layer = wall_item.Thickness.split()
                            sc.sticky[sc.doc.Path]['Const_coll'][key].Uvalue = wall_item.Uvalue
                            sc.sticky[sc.doc.Path]['Const_coll'][key].Abs_front = wall_item.Abs_front
                            sc.sticky[sc.doc.Path]['Const_coll'][key].Abs_back = wall_item.Abs_back
                    Wallthickness = 0
                    for item in thickness_layer:
                        Wallthickness += float(item)
                    sc.sticky[sc.doc.Path]['Const_coll'][key].Wallthickness = Wallthickness
            else:
                key = geometry.UserDictionary['LID']
                for wall_item in library.Walls:
                    if sc.sticky[sc.doc.Path]['Const_coll'][key].Construction == wall_item.Name:
                        thickness_layer = wall_item.Thickness.split()
                        sc.sticky[sc.doc.Path]['Const_coll'][key].Uvalue = wall_item.Uvalue
                        sc.sticky[sc.doc.Path]['Const_coll'][key].Abs_front = wall_item.Abs_front
                        sc.sticky[sc.doc.Path]['Const_coll'][key].Abs_back = wall_item.Abs_back
                Wallthickness = 0
                for item in thickness_layer:
                    Wallthickness += float(item)
                sc.sticky[sc.doc.Path]['Const_coll'][key].Wallthickness = Wallthickness
        except:
            pass
    def updateConstructionNew(self, geometry, dataclass):
        if 1 > 0:
            for gitem in geometry:
                key = gitem.UserDictionary['LID']
                if sc.sticky[sc.doc.Path]['Const_coll'].has_key(key):
                    datadict = vars(dataclass)
                    for keyitem in datadict.items():
                        pass
                        if keyitem[0] == 'Boundarycond':
                            if 'BOUNDARY' or 'EXTFICALC' or 'EXTBOUNDARY' or 'EXTSKYBND' in keyitem[1]:
                                if datadict['Boundarytemp'] and datadict['Boundarytemp'] !='':
                                    bnd_dummy = datadict['Boundarytemp']
                                    if re.search('^-?\d', str(bnd_dummy)):
                                        pass
                                    else:
                                        appendtxt = ''
                                        if keyitem[1] == 'EXTFICALC':
                                            information = 'Surfnum'
                                            lizard_coll = sc.sticky[sc.doc.Path]['CONSTRUCTION']()
                                            collection = [gitem]
                                            ObjectsFromLz = lizard_coll.callFromConstruction(collection)
                                            _brep = []
                                            for LO in range(len(ObjectsFromLz)):
                                                appendtxt = ObjectsFromLz[LO].__dict__[information]
                                        bnd_dummy = 'INPUT 1*{0}'.format(datadict['Boundarytemp'] + str(appendtxt))
                                    sc.sticky[sc.doc.Path]['Const_coll'][key].__dict__['Boundarytemp'] = bnd_dummy
                                else:
                                    sc.sticky[sc.doc.Path]['Const_coll'][key].__dict__['Boundarytemp'] = 'Identical'
                        if keyitem[0] == 'Construction' and 'WIN_' in keyitem[1]:
                            sc.sticky[sc.doc.Path]['Const_coll'][key].__dict__['Construction'] = keyitem[1] + '_' + getWinOrientation(gitem)
                        elif keyitem[0] == 'Construction':
                            sc.sticky[sc.doc.Path]['Const_coll'][key].__dict__['Construction'] = keyitem[1]
                        if keyitem[0] == 'Boundarytemp' or keyitem[0] == 'Construction':
                            pass
                        else:
                            sc.sticky[sc.doc.Path]['Const_coll'][key].__dict__[keyitem[0]] = keyitem[1]
                    #print vars(sc.sticky[sc.doc.Path]['Const_coll'][key])
        else:
            pass
class ZONECOLL():
    def addToZones(self,GHComponentID,info):
        # check if the lizardzonedictionary already existed
        # if not create the dictionary
        if not sc.sticky[sc.doc.Path].has_key('Zone_coll'): sc.sticky[sc.doc.Path]['Zone_coll'] = {}
        faces = rc.Geometry.Brep()
        boxes = []
        key = str(info.Name)
        for subitem in info.Surfaces:
            faces.Append(subitem.Faces)
        box = faces
        sc.sticky[sc.doc.Path]['Zone_coll'][key] = info
        box.UserDictionary.Set('LIZ', key)
        return box
    def callFromZones(self, geometry):
        Objects = []
        for data in geometry:
            try:
                key = data.UserDictionary['LIZ']
                if sc.sticky[sc.doc.Path]['Zone_coll'].has_key(key):
                    Objects.append(copy.deepcopy(sc.sticky[sc.doc.Path]['Zone_coll'][key]))
            except:
                print "key not found"
                pass
        return Objects
class MULTIZONECOLL():
    def addToZones(self,info):
        # check if the lizardzonedictionary already existed
        # if not create the dictionary
        if not sc.sticky[sc.doc.Path].has_key('Zone_coll'): sc.sticky[sc.doc.Path]['Zone_coll'] = {}
        faces = rc.Geometry.Brep()
        boxes = []
        key = 'Multizone'
        for zone in info:
            for subitem in zone.Airnode.Surfaces:
                faces.Append(subitem.Faces)
        box = faces
        sc.sticky[sc.doc.Path]['Zone_coll'][key] = info
        box.UserDictionary.Set('LIZ', key)
        return box
    def callFromZones(self, geometry):
        Objects = []
        try:
            key = geometry.UserDictionary['LIZ']
            if sc.sticky[sc.doc.Path]['Zone_coll'].has_key(key):
                Objects.append(copy.deepcopy(sc.sticky[sc.doc.Path]['Zone_coll'][key]))
        except:
            print "key not found"
            pass
        return Objects
def checkUnits():
    units = sc.doc.ModelUnitSystem
    if `units` == 'Rhino.UnitSystem.Meters' and abs_tolerance <= 0.000001: pass
    else:
        ghenv.Component.AddRuntimeMessage(err, "Set Rhino Units to Meter and tolerance to 0.000001")
        print "Set Rhino Units to Meter and tolerance to 0.000001"
        sys.exit()
#@timing
#this function returns the surface vertices for the building definition, updated 3.8.2016
"""
def getSurfaceVertices(refnormalvector,surface):
    ori_normal   = refnormalvector
    ori_edges    = surface.Edges
    dummyPolycurve = rc.Geometry.PolylineCurve.JoinCurves(ori_edges)
    polyline = dummyPolycurve[0].TryGetPolyline()[1]
    sort_vertices = []
    for point in polyline:
        sort_vertices.append(point)
    new_srf = rc.Geometry.Brep.CreatePlanarBreps(polyline.ToNurbsCurve())[0]
    new_normal = new_srf.Faces[0].NormalAt(0,0)
    vector_deviation = 1-rc.Geometry.Vector3d.Multiply(new_normal,ori_normal)
    sort_vertices.pop()
    if vector_deviation <= abs_tolerance:
        vertices = sort_vertices
    else:
        vertices = list(reversed(sort_vertices))
    #print vertices
    return vertices
"""
def getSurfaceVertices(refnormalvector,surface):
    ori_vertices = []
    dsurface = copy.deepcopy(surface)
    subbrep = dsurface.Faces.ExtractFace(0)
    for item in subbrep.Vertices:
        ori_vertices.append(item.Location)
    basecurve = []
    for edge in subbrep.Edges:
        basecurve.append(rc.Geometry.Line(edge.PointAtStart,edge.PointAtEnd).ToNurbsCurve())
    #dummyPolycurve = rc.Geometry.PolylineCurve.JoinCurves(subbrep.Edges)
    dummyPolycurve = rc.Geometry.PolylineCurve.JoinCurves(basecurve)
    polylinecurve = dummyPolycurve[0].ToPolyline(abs_tolerance,abs_tolerance,0,100000)
    polyline = polylinecurve.TryGetPolyline()[1]
    sort_vertices = []
    refined_vertices = []
    #curvedict = {}
    #for subvert in ori_vertices:
    #    curvedict[polyline.ClosestParameter(subvert)] = subvert
    #for key in curvedict:
    #    sort_vertices.append(curvedict[key])
    #print sort_vertices 
    for point in polyline:
        for subvert in ori_vertices:
            if point.X - abs_tolerance < subvert[0] and point.X + abs_tolerance > subvert[0]:
                if point.Y - abs_tolerance < subvert[1] and point.Y + abs_tolerance > subvert[1]:
                    if point.Z - abs_tolerance < subvert[2] and point.Z + abs_tolerance > subvert[2]:
                        refined_vertices.append(subvert)
                        #print point, subvert, "found"
                        break
        #sort_vertices.append(point)
    #cleaned_vertices = []
    #for ix, item in enumerate(refined_vertices):
    #    if len(cleaned_vertices)>0:
    #        if item == refined_vertices[ix-1]:
    #            pass
    #        else:
    #            cleaned_vertices.append(item)
    #    else:
    #        cleaned_vertices.append(item)
    sort_vertices = refined_vertices
    new_srf = rc.Geometry.Brep.CreatePlanarBreps(polyline.ToNurbsCurve(),abs_tolerance)[0]
    new_normal = new_srf.Faces[0].NormalAt(0,0)
    vector_deviation = 1-rc.Geometry.Vector3d.Multiply(new_normal,refnormalvector)
    if sort_vertices[-1] == sort_vertices[0]:
        sort_vertices.pop()
    if vector_deviation <= abs_tolerance:
        vertices = sort_vertices
    else:
        vertices = list(reversed(sort_vertices))
    return vertices
#this function searches trough AUTOMATIC defined constructions and searches the matching surface
@timing
def findMaxSurfNum(surfacecoll):
    maxNum = 0
    for item in surfacecoll:
        maxNum = max(maxNum,item.Surfnum)
    return maxNum
@timing
def checkWindowsInWalls(surfacecoll,match):
    #This block checks whether the windows are inside of the walls
    matchfound = 0
    for item2 in surfacecoll:
        if item2.Type == "WALL" or "CEILING" or "FLOOR" or "ROOF":
            item2.Subsurface = []
            item2.Subsurfacedef = []
            for item in surfacecoll:
                if item.Type == "WINDOW" or item.Type == "BSDFWINDOW":
                    dummy = rc.Geometry.Brep.CreateBooleanDifference(item2.Faces,item.Faces, abs_tolerance)
                    if dummy and len(dummy) > 0:
                        for ci, cutitem in enumerate(dummy):
                            if ci == 0:
                                matching_test = rc.Geometry.Brep.CreateBooleanDifference(item2.Faces,dummy[ci], abs_tolerance)
                            else:
                                matching_test = rc.Geometry.Brep.CreateBooleanDifference(matching_test[0],dummy[ci], abs_tolerance)
                        matchfound = matchfound  + 1
                        area_intersection = matching_test[0].GetArea()
                        dummy_area_window = rc.Geometry.AreaMassProperties.Compute(item.Faces)
                        area_window = dummy_area_window.Area
                        delta_area = abs(area_intersection - area_window)
                        if (delta_area<0.01):
                            item2.Area = rc.Geometry.Brep.GetArea(item2.Faces)
                            match.append(matching_test)
                            item2.Subsurface.append(item.Surface)
                            item2.Subsurfacedef.append(item)
                            for area_count in item2.Subsurfacedef:
                                item2.Area = item2.Area - area_count.Area
                            item.Boundarycond = item2.Boundarycond
                            if item.Orientation != item2.Orientation:
                                item.Orientation = item2.Orientation
                                #print 'Orientation mismatch from Wall and Window with orientation %s and %s!'%(item2.Orientation,item.Orientation)
                        else:
                            print '!Some windows are not enclosed or in the pane of the base surface!'
                            sys.exit()
                        if area_window > rc.Geometry.Brep.GetArea(item2.Faces):
                            print 'Window area is higher than wall area!'
                            sys.exit()
    print "%d Window(s) in Wall(s) found" % matchfound
    return match
@timing
def getInputs(Template):
    dummy = (', '.join(x for x in Template)).split('\r\n')
    collected = []
    last_match = ''
    for lines in dummy:
        match_search    = re.search('INPUT -?\d*\.*\d*\*(\w+)',lines)
        if match_search is not None:
            for variablename in list(set(re.findall('INPUT -?\d*\.*\d*\*(\w+)',lines))):
                collected.append(variablename)
    return list(set(collected))
# Constructions with the floor definition als summed up for the airnode
@timing
def getFloorArea(surfacecoll):
    floorarea = 0
    for item in surfacecoll:
        if item.Type == 'FLOOR':
            floorarea = floorarea + rc.Geometry.Brep.GetArea(item.Faces)
    print 'Geometrical floor area will be used!'
    return round(floorarea,2)
    if floorarea == 0:
        ghenv.Component.AddRuntimeMessage(w, "Attention floor area is zero!")
#this function searches through ADJACENT constructions and searches the matching surface
@timing
def checkAdjacent(surfacecoll,mismatched_adjacent):
    #This block checks whether adjacent walls are found
    match = []
    error = []
    matchfound = 0
    for item2 in surfacecoll:
        item2.Adjsearch = 0
        item2.Bndsearch = 0
    for item2 in surfacecoll:
        if (item2.Boundarycond == "ADJACENT" or item2.Boundarycond == "AUTOMATIC") and item2.Type != "WINDOW" and item2.Adjsearch == 0:
            item2.Adjsearch = 1
            found = 0
            for item in surfacecoll:
                if (item.Boundarycond == "ADJACENT" or item.Boundarycond == "AUTOMATIC") and (item.Type != "WINDOW") and item.Surfnum != item2.Surfnum and item.Adjsearch == 0:
                    orivec = item2.Faces.Faces[0].NormalAt(0,0)
                    orivec.Reverse()
                    compare = orivec.IsParallelTo(item.Faces.Faces[0].NormalAt(0,0))
                    if compare == 1 or compare == -1:
                        oricenter = rc.Geometry.AreaMassProperties.Compute(item2.Faces.Faces[0]).Centroid
                        secondcenter = rc.Geometry.AreaMassProperties.Compute(item.Faces.Faces[0]).Centroid
                        newvector = secondcenter - oricenter
                        #here it is looked for whether two surfaces with an inverse normal vector are the same
                        if newvector.Length < 0.5:
                            orisurface = copy.deepcopy(item2.Faces)
                            orisurface.Translate(newvector)
                            dummyPolycurveX = rc.Geometry.PolylineCurve.JoinCurves(item.Faces.Edges)
                            dummyPolycurveY = rc.Geometry.PolylineCurve.JoinCurves(orisurface.Edges)
                            dummy = rc.Geometry.PolyCurve.CreateBooleanIntersection(dummyPolycurveX[0],dummyPolycurveY[0])
                            if dummy:
                                matchfound = matchfound  + 1
                                area_surf1 = rc.Geometry.AreaMassProperties.Compute(orisurface.Faces[0]).Area
                                area_surf2 = rc.Geometry.AreaMassProperties.Compute(item.Faces.Faces[0]).Area
                                delta_area = abs(area_surf1 - area_surf2)
                                if (delta_area < abs_tolerance):
                                    item2.Boundarycond = "ADJACENT"
                                    item.Boundarycond = "ADJACENT"
                                    item.Adjsurf = item2.Surfnum
                                    item2.Adjsurf = item.Surfnum
                                    item.Adjairnode = item2.Airnode
                                    item2.Adjairnode = item.Airnode
                                    if item.Frontback == 'FRONT' and item2.Frontback == 'FRONT':
                                        item2.Frontback = 'BACK'
                                        mismatched_adjacent.append(item.Faces)
                                        message = "!Surfaces have the same FRONT/BACK definition!Surface {0} & {1}".format(item.Surfnum,item2.Surfnum)
                                        error.append(message)
                                    if item.Frontback == 'BACK' and item2.Frontback == 'BACK':
                                        item.Frontback = 'FRONT'
                                        mismatched_adjacent.append(item.Faces)
                                        message = "!Surfaces have the same FRONT/BACK definition!Surface {0} & {1}".format(item.Surfnum,item2.Surfnum)
                                        error.append(message)
                                    if item.Frontback == 'FRONT':
                                        item2.Orientation = item.Orientation
                                        if item.Type == "ADDWINDOW":
                                            item2.Construction = item.Construction
                                        if item.Activelayer == 1:
                                            item2.Activelayer = 1
                                            item2.Intemp = item.Intemp
                                    else:
                                        item.Orientation = item2.Orientation
                                        if item2.Type == "ADDWINDOW":
                                            item.Construction = item2.Construction
                                        if item2.Activelayer == 1:
                                            item.Activelayer = 1
                                            item.Intemp = item2.Intemp
                                    match.append(item.Faces)
                                    item.Adjsearch = 1
                                    found = 1
                                    if item.Coupling != 0 or item2.Coupling != 0:
                                        item.Coupling  = "INPUT 1*MF_{0}_{1}".format(item2.Airnode,item.Airnode)
                                        item2.Coupling = "INPUT 1*MF_{0}_{1}".format(item.Airnode,item2.Airnode)
                                        print 'found coupling'
                                    break
                                else:
                                    mismatched_adjacent.append(item.Faces)
                                    message = "!Some adjacent surfaces are not correct!Surface {0} & {1}".format(item.Surfnum,item2.Surfnum)
                                    error.append(message)
            if found == 0 and item2.Boundarycond == "ADJACENT":
                message = "!Adjacent surface not found for Surface {0}!\n Surface boundary condition is set to BOUNDARY!".format(item2.Surfnum)
                error.append(message)
                item2.Boundarycond = "BOUNDARY"
                item2.Boundarytemp = 'INPUT 1*TAIR_{0}'.format(item2.Airnode)
                mismatched_adjacent.append(item2.Faces)
            elif found == 0 and item2.Boundarycond == "AUTOMATIC":
                item2.Boundarycond = "EXTERNAL"
        if (item2.Boundarycond == "AUTOBOUND") and item2.Type != "WINDOW" and item2.Bndsearch == 0:
            item2.Bndsearch = 1
            bndfound = 0
            for item in surfacecoll:
                if (item.Boundarycond == "AUTOBOUND") and (item.Type != "WINDOW") and item.Surfnum != item2.Surfnum and item.Bndsearch == 0:
                    orivec = item2.Faces.Faces[0].NormalAt(0,0)
                    oricenter = rc.Geometry.AreaMassProperties.Compute(item2.Faces.Faces[0]).Centroid
                    curve = rc.Geometry.Line(oricenter,orivec).ToNurbsCurve()
                    compare = rc.Geometry.Intersect.Intersection.CurveBrep(curve,item.Faces,abs_tolerance)
                    if len(compare[2])>0:
                        item2.Boundarycond = "BOUNDARY"
                        item.Boundarycond = "BOUNDARY"
                        item.Bndairnode = item2.Airnode
                        item2.Bndairnode = item.Airnode
                        item2.Boundarytemp = 'INPUT 1*TAIR_{0}'.format(item.Airnode)
                        item.Boundarytemp = 'INPUT 1*TAIR_{0}'.format(item2.Airnode)
                        item.Bndsearch = 1
                        bndfound = 1
                        break
            if bndfound == 0 and item2.Boundarycond == "AUTOBOUND":
                message = "!Automatic airnode name not found for Surface {0}!\n Surface boundary condition is set to BOUNDARY!".format(item2.Surfnum)
                error.append(message)
                item2.Boundarycond = "BOUNDARY"
                item2.Boundarytemp = 'INPUT 1*TAIR_{0}'.format(item2.Airnode)
                mismatched_adjacent.append(item2.Faces)
        if (item2.Boundarycond == "ADJACENT" or item2.Boundarycond == "AUTOMATIC") and item2.Type == "WINDOW" and item2.Adjsearch == 0:
            item2.Adjsearch = 1
            for item in surfacecoll:
                if (item.Boundarycond == "ADJACENT" or item.Boundarycond == "AUTOMATIC") and item.Type == "WINDOW" and item.Surfnum != item2.Surfnum and item.Adjsearch == 0:
                    dummyPolycurveX = rc.Geometry.PolylineCurve.JoinCurves(item.Faces.Edges)
                    dummyPolycurveY = rc.Geometry.PolylineCurve.JoinCurves(item2.Faces.Edges)
                    dummy = rc.Geometry.PolyCurve.CreateBooleanIntersection(dummyPolycurveX[0],dummyPolycurveY[0])
                    if dummy:
                        matchfound = matchfound  + 1
                        area_surf1 = rc.Geometry.Brep.GetArea(item2.Faces)
                        area_surf2 = rc.Geometry.Brep.GetArea(item.Faces)
                        delta_area = abs(area_surf1 - area_surf2)
                        if (delta_area < abs_tolerance):
                            item.Adjsurf = item2.Surfnum
                            item2.Adjsurf = item.Surfnum
                            item.Adjairnode = item2.Airnode
                            item2.Adjairnode = item.Airnode
                            match.append(item.Faces)
                            item.Adjsearch = 1
                            if item.Frontback == 'FRONT':
                                item2.Orientation = item.Orientation
                                item2.Construction = item.Construction
                            else:
                                item.Orientation = item2.Orientation
                                item.Construction = item2.Construction
                        else:
                            mismatched_adjacent.append(item.Faces)
                            message = "!Some adjacent window surfaces are not correct!Surface {0} & {1}".format(item.Surfnum,item2.Surfnum)
                            error.append(message)
    return match, mismatched_adjacent, error
def HemisphereAzimuth(Hemisphere = 'SOUTHERN', azimuth = 225):
    if Hemisphere == 'SOUTHERN':
        if azimuth == 0:
            azimuthcorr = 180
        if azimuth == 180:
            azimuthcorr = 0
        if azimuth > 0 and azimuth < 180:
            azimuthcorr = 180 - azimuth
        if azimuth > 180 and azimuth < 360:
            azimuthcorr = 360 - (azimuth - 180)
    else:
        azimuthcorr = azimuth
    return azimuthcorr
# Surface orientations are defined according to their azimuth and slope
@timing
def getSurfaceOrientation(surfacecoll):
    orientations = ['H_0_0']
    dummy_array = []
    dummy_array.extend(surfacecoll)
    azimuth = 0
    slope = 0
    slope_vector = rc.Geometry.Vector3d(0,0,1)
    ori_point = rc.Geometry.Point3d(0,0,0)
    oriprefix = ''
    for item in dummy_array:
        facenormal = item.Faces.Faces[0].NormalAt(0,0)
        plane = rc.Geometry.Plane(ori_point,facenormal,slope_vector)
        slope_rad = rc.Geometry.Vector3d.VectorAngle(facenormal,slope_vector,plane)
        slope_deg = slope_rad * 180/math.pi
        slope = int(slope_deg)
        if slope == 180:
            azimuth     =  0
            oriprefix   = 'H'
        elif slope == 0:
            azimuth     =  0
            oriprefix   = 'H'
        else:
            azimuth_vector = rc.Geometry.Vector3d(0,-1,0)
            plane = rc.Geometry.Plane(ori_point,slope_vector)
            azimuth_rad = rc.Geometry.Vector3d.VectorAngle(facenormal,azimuth_vector,plane)
            azimuth_deg = azimuth_rad * 180/math.pi
            azimuth = int(azimuth_deg)
            if azimuth   < 45    or azimuth >=315: oriprefix = 'S'
            elif azimuth >= 45   and azimuth <135: oriprefix = 'W'
            elif azimuth >= 135 and azimuth  <225: oriprefix = 'N'
            elif azimuth >= 225  and azimuth <315: oriprefix = 'E'
        item.Fsky = round((180 - slope) / 180,2)
        fmtString = "%s_%d_%d"
        azimuth = HemisphereAzimuth(Hemisphere = Hemisphere, azimuth = azimuth)
        if slope == 180:
            azimuth     =  0
            oriprefix   = 'H'
        elif slope == 0:
            azimuth     =  0
            oriprefix   = 'H'
        vals = (oriprefix,azimuth,slope) # tuple, one value per marker
        myString = fmtString % vals
        item.Orientation = myString
        if item.Type == 'WINDOW':
            if slope > 90:
                item.Slope = 180 - slope
            else:
                item.Slope = slope
        else:
            item.Slope = slope
        if item.Boundarycond == 'EXTERNAL' or 'ADJACENT' or 'EXTBOUNDARY' or 'EXTCALC' or 'AUTOMATIC':
            orientations.append(item.Orientation)
    orientations = list(set(orientations))
    orientations.reverse()
    return orientations
@timing
def getOrientation(surfacebrep):
    azimuth = 0
    slope = 0
    slope_vector = rc.Geometry.Vector3d(0,0,1)
    ori_point = rc.Geometry.Point3d(0,0,0)
    oriprefix = ''
    if 1 > 0:
        item = surfacebrep
        facenormal = item.Faces[0].NormalAt(0,0)
        plane = rc.Geometry.Plane(ori_point,facenormal,slope_vector)
        slope_rad = rc.Geometry.Vector3d.VectorAngle(facenormal,slope_vector,plane)
        slope_deg = slope_rad * 180/math.pi
        slope = int(slope_deg)
        if slope == 180:
            azimuth     =  0
            oriprefix   = 'H'
        elif slope == 0:
            azimuth     =  0
            oriprefix   = 'H'
        else:
            azimuth_vector = rc.Geometry.Vector3d(0,-1,0)
            plane = rc.Geometry.Plane(ori_point,slope_vector)
            azimuth_rad = rc.Geometry.Vector3d.VectorAngle(facenormal,azimuth_vector,plane)
            azimuth_deg = azimuth_rad * 180/math.pi
            azimuth = int(azimuth_deg)
            if azimuth   < 45    or azimuth >=315: oriprefix = 'S'
            elif azimuth >= 45   and azimuth <135: oriprefix = 'W'
            elif azimuth >= 135 and azimuth  <225: oriprefix = 'N'
            elif azimuth >= 225  and azimuth <315: oriprefix = 'E'
        fmtString = "%s_%d_%d"
        azimuth = HemisphereAzimuth(Hemisphere = Hemisphere, azimuth = azimuth)
        if slope == 180:
            azimuth     =  0
            oriprefix   = 'H'
        elif slope == 0:
            azimuth     =  0
            oriprefix   = 'H'
        vals = (oriprefix,azimuth,slope) # tuple, one value per marker
        myString = fmtString % vals
        Orientation = myString
    return Orientation
#This subroutine defines whether the surface is a WALL or CEILING or ROOF or FLOOR or WINDOW or VIRTUAL
@timing
def getSurfaceType(breps):
    for item in breps:
        if item.Boundarycond == 'VIRTUAL':
            item.Type = 'VIRTUAL'
            continue
        if item.Type == 'WINDOW' or item.Type == 'ADDWINDOW':
            pass
        else:
            ori = item.Orientation.split('_')
            if float(ori[2]) < 50:
                if item.Boundarycond == 'EXTERNAL':
                    item.Type = 'ROOF'
                else:
                    item.Type = 'CEILING'
            if float(ori[2]) >= 50 and float(ori[2]) < 130:
                item.Type = 'WALL'
            if float(ori[2]) > 130:
                item.Type = 'FLOOR'
@timing
def getWinOrientation(items):
    orientations = []
    azimuth = 0
    slope = 0
    slope_vector = rc.Geometry.Vector3d(0,0,1)
    ori_point = rc.Geometry.Point3d(0,0,0)
    oriprefix = ''
    facenormal = items.Faces[0].NormalAt(0,0)
    plane = rc.Geometry.Plane(ori_point,facenormal,slope_vector)
    slope_rad = rc.Geometry.Vector3d.VectorAngle(facenormal,slope_vector,plane)
    slope_deg = slope_rad * 180/math.pi
    slope = int(slope_deg)
    if slope == 180:
        azimuth     =  0
        oriprefix   = 'H'
    elif slope == 0:
        azimuth     =  0
        oriprefix   = 'H'
    else:
        azimuth_vector = rc.Geometry.Vector3d(0,-1,0)
        plane = rc.Geometry.Plane(ori_point,slope_vector)
        azimuth_rad = rc.Geometry.Vector3d.VectorAngle(facenormal,azimuth_vector,plane)
        azimuth_deg = azimuth_rad * 180/math.pi
        azimuth = int(azimuth_deg)
        if azimuth   < 45    or azimuth >=315: oriprefix = 'S'
        elif azimuth >= 45   and azimuth <135: oriprefix = 'W'
        elif azimuth >= 135  and azimuth <225: oriprefix = 'N'
        elif azimuth >= 225  and azimuth <315: oriprefix = 'E'
    sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(items,'Fsky',round((180 - slope) / 180,2))
    azimuth = HemisphereAzimuth(Hemisphere = Hemisphere, azimuth = azimuth)
    fmtString = "%s_%d_%d"
    vals = (oriprefix,azimuth,slope) # tuple, one value per marker
    myString = fmtString % vals
    sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(items,'Orientation',myString)
    sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(items,'Slope',slope)
    return myString
@timing
def defineGeosurf(floorgeo,surfacecoll):
    total_area = 0
    geo_floor_area = 0
    for item in surfacecoll:
        if item.Type != 'WINDOW' and 'VIRTUAL' != item.Construction.upper() and item.Type != 'ROOF' and item.Type != 'CEILING':
            total_area = total_area + item.Area
            if item.Orientation == 'H_0_180':
                geo_floor_area = geo_floor_area + item.Area
    rest_area = total_area - geo_floor_area
    sum_geo = 0
    for item in surfacecoll:
        if item.Type != 'WINDOW' and 'VIRTUAL' != item.Construction.upper() and item.Type != 'ROOF' and item.Type != 'CEILING':
            if item.Orientation == 'H_0_180':
                item.Geosurf = round(item.Area / geo_floor_area * floorgeo,3)
            else:
                item.Geosurf = round(item.Area / rest_area * (1-floorgeo),3)
            sum_geo = sum_geo + item.Geosurf
            if sum_geo > 1:
                reduction = 1 - sum_geo
                item.Geosurf = item.Geosurf + reduction
                print 'The Geosurf of surface {0} has been reduced with {1}'.format(item.Construction,reduction)
            #print item.Geosurf
@timing
def getVolume(surfacecoll):
    faces = []
    for item in surfacecoll:
        if item.Type != "WINDOW":
            faces.append(item.Faces)
    joinedbox = rc.Geometry.Brep.JoinBreps(faces,0.1)
    error = 0
    if len(joinedbox) == 1 and joinedbox[0].IsSolid:
        capped_box = joinedbox[0].CapPlanarHoles(abs_tolerance)
        volumedummy = rc.Geometry.VolumeMassProperties.Compute(joinedbox[0])
        volume = volumedummy.Volume
        center = volumedummy.Centroid
        if volume is None or capped_box != None:
            error = 1
    else:
        error = 1
        volume = -9999
        center = [0,0,0]
    return (volume,center,error,joinedbox[0])
#this function runs through the first argument of type array and prints information
@timing
def printData(data_collection,*search_attr):
    datastorage = ''
    for item in data_collection:
        for attr_check in search_attr:
            if getattr(item, attr_check) != '':
                linedefinition=getattr(Template, attr_check)
                for attr, value in sorted(item.__dict__.iteritems(), key=lambda pair: len(pair[0]), reverse=True):
                    placeholder = '@self.{0}'.format(attr)
                    linedefinition = linedefinition.replace(placeholder, str(value))
                datastorage = datastorage + linedefinition
    return datastorage
#this function runs through the first argument and prints information
@timing
def printSingleData(data_collection, *search_attr):
    datastorage = ''
    data = []
    data.append(data_collection)
    for item in data:
        for attr_check in search_attr:
            if getattr(item, attr_check) != '':
                linedefinition=getattr(Template, attr_check)
                for attr, value in sorted(item.__dict__.iteritems(), key=lambda pair: len(pair[0]), reverse=True):
                    placeholder = '@self.{0}'.format(attr)
                    linedefinition = linedefinition.replace(placeholder, str(value))
                datastorage = datastorage + linedefinition
    return datastorage
@timing
def getDataParagraph(startpattern,stoppattern,datararray):
    output = []
    inparagraph = 'FALSE'
    lines=datararray
    data=lines[0].split( )
    for i in range(len(lines)):
        search_start=re.search(r'{0}'.format(startpattern),lines[i])
        if search_start is not None or inparagraph == 'TRUE':
            inparagraph = 'TRUE'
            output.append(lines[i])
            search_stop=re.search(r'{0}'.format(stoppattern),lines[i])
            if search_stop is not None:
                return output
                f.close()
                break
    print 'no match found!'
@timing
def readDataFileColumn(filename,searchinfo):
    outputnames = []
    f = open(filename, 'r')
    lines=f.readlines()
    data=lines[0].split( )
    datacoll = defaultdict(dict)
    for i in range(len(data)):
        outputnames.append(data[i])
    for i in range(len(outputnames)):
        if searchinfo in outputnames[i]:
            datacoll[searchinfo]['column'] = i
            datacoll[searchinfo]['data']   = []
    for i in range(len(lines)):
        if re.search('^\s*\d+',lines[i]) is not None:
            data    =lines[i].split()
            datacoll[searchinfo]['data'].append(float(data[datacoll[searchinfo]['column']]))
    return datacoll[searchinfo]['data']
    f.close()
@timing
def transformillfile(input0):
    index = 3
    w3 = open(input0 + '.ill_grid', 'r')
    lines3=w3.readlines()
    for u in range(len(lines3)):
        rundata =lines3[u].split()
        dummy_number = rundata[1]
        w = open(input0 + '_' + dummy_number + '.ill', 'w')
        f = open(rundata[0], 'r')
        lines=f.readlines()
        datastorage = []
        for i in range(len(lines)):
            datastorage.append('')
        f.close()
        mesh_len_collection = [int(rundata[2]),int(rundata[3]),int(rundata[4])]
        for len_item in range(len(mesh_len_collection)):
            startindex = index
            stopindex  = startindex + mesh_len_collection[len_item]
            f = open(rundata[0], 'r')
            lines=f.readlines()
            u = 0
            for i in range(len(lines)):
                data    =lines[i].split()
                sumdata = 0
                for i in range(len(data)):
                    if i >= startindex and i < stopindex:
                        sumdata = sumdata + float(data[i])
                if sumdata == 0:
                    pass
                else:
                    sumdata = sumdata/(stopindex - startindex)
                datastorage[u] = datastorage[u] + ' ' + str(sumdata)
                if len(rundata) > 5:
                    pass
                else:
                    if len_item + 1 == len(mesh_len_collection):
                        w.write(str(datastorage[u]) + '\n')
                u = u + 1
            f.close()
            if len(rundata) > 5:
                f2 = open(rundata[5], 'r')
                lines=f2.readlines()
                u = 0
                for i in range(len(lines)):
                    data    =lines[i].split()
                    sumdata = 0
                    for i in range(len(data)):
                        if i >= startindex and i < stopindex:
                            sumdata = sumdata + float(data[i])
                    if sumdata == 0:
                        pass
                    else:
                        sumdata = sumdata/(stopindex - startindex)
                    datastorage[u] = datastorage[u] + ' ' + str(sumdata)
                    if len_item + 1 == len(mesh_len_collection):
                        w.write(str(datastorage[u]) + '\n')
                    u = u + 1
                    f2.close()
            index = stopindex
        w.close()
    w3.close()
@timing
def adaptBoundaryTemp(brep,category,bnd_temp):
    if 'BOUNDARY' or 'EXTFICALC' or 'EXTBOUNDARY' in category:
        if bnd_temp:
            bnd_dummy = bnd_temp
            if re.search('^-?\d', str(bnd_dummy)):
                pass
            else:
                appendtxt = ''
                if category == 'EXTFICALC':
                    information = 'Surfnum'
                    lizard_coll = sc.sticky[sc.doc.Path]["CONSTRUCTION"]()
                    collection = []
                    collection.append(brep)
                    ObjectsFromLz = lizard_coll.callFromConstruction(collection)
                    _brep = []
                    for LO in range(len(ObjectsFromLz)):
                        appendtxt = ObjectsFromLz[LO].__dict__[information]
                bnd_dummy = 'INPUT 1*{0}'.format(bnd_temp + str(appendtxt))
        else:
            bnd_dummy = 'Identical'
        sc.sticky[sc.doc.Path]["CONSTRUCTION"]().updateConstruction(brep,'Boundarytemp',bnd_dummy)
    return bnd_dummy
@timing
def splitSurface(geometry,perc,dir):
    surface         = ghcomp.DeconstructBrep(rs.coercebrep(geometry)).faces
    basearea        = ghcomp.Area(surface).area
    length          = ghcomp.Dimensions(surface)
    new_length      = [0,0]
    domain          = [0,0]
    divdom          = [0,0]
    for i in range(0,2):
        new_length[i]   = length[i]
        new_length[i]   = new_length[i] + length[i] / 100
        domain[i]       = ghcomp.ConstructDomain(0,new_length[i])
        divdom[i]       = ghcomp.DivideDomain(domain[i],100)
    domain2 = []
    domainend = []
    if dir == 0:
        for item in divdom[dir]:
            domain2.append(ghcomp.ConstructDomain2(item[0],item[1],0,new_length[1]))
            domainend.append(ghcomp.DeconstructDomain2(domain2[-1])[dir][1])
    else:
        for item in divdom[dir]:
            domain2.append(ghcomp.ConstructDomain2(0,new_length[0],item[0],item[1]))
            domainend.append(ghcomp.DeconstructDomain2(domain2[-1])[dir][1])
    subsurfaces = ghcomp.Isotrim(surface,domain2)
    sum = 0
    for i in range(len(subsurfaces)):
        sum = ghcomp.Area(ghcomp.BoundarySurfaces(ghcomp.RegionIntersection(surface,subsurfaces[i]))).area + sum
        if sum >= basearea * perc / 100:
            found_domain = domainend[i]
            break
    if dir == 0:
        subdomain = ghcomp.ConstructDomain2(0,found_domain,0,new_length[1])
    else:
        subdomain = ghcomp.ConstructDomain2(0,new_length[0],0,found_domain)
    surface1 = ghcomp.Isotrim(surface,subdomain)
    surface1 = ghcomp.RegionIntersection(surface,surface1)
    surface1 = ghcomp.Flip(surface1,surface).surface
    surface2 = ghcomp.RegionDifference(surface,surface1)
    surface2 = ghcomp.BoundarySurfaces(surface2)
    surface2 = ghcomp.Flip(surface2,surface).surface
    return surface1,surface2
#this function will split up the surface into 3 equal elements if the active layer is linked
@timing
def surfaceSplitting(brep):
    srf = ghcomp.BoundarySurfaces(brep) # gives Brep not Surface
    srf = srf.Surfaces[0] # <-- Get surface. Otherwise no .SetDomain !
    srf.SetDomain(0, rc.Geometry.Interval(0, 1)) # reparameterize u
    srf.SetDomain(1, rc.Geometry.Interval(0, 1)) # reparameterize v
    surfaces_temp = ghcomp.DeconstructBrep(srf).faces
    nr_of_divisions = max(round(ghcomp.Area(surfaces_temp).area/10),3)
    argu1 = surfaces_temp
    uvtog        = True
    noofdivisions= nr_of_divisions  #This number cannot be changed, if you want to change then the subroutine has to be updated
    interval     = '0.0 To 1.0'
    series       = ghcomp.Series(1/noofdivisions,1/noofdivisions,noofdivisions-1)
    precision    = 150 #Number of divisions in order to find the matching subelements
    divdomain1   = ghcomp.DivideDomain(interval,precision)
    stream1      = ghcomp.StreamFilter(uvtog,interval,divdomain1)
    stream2      = ghcomp.StreamFilter(uvtog,divdomain1,interval)
    domain_end   = ghcomp.DeconstructDomain(divdomain1).end
    stream1start = ghcomp.DeconstructDomain(stream1).start
    stream1end   = ghcomp.DeconstructDomain(stream1).end
    stream2start = ghcomp.DeconstructDomain(stream2).start
    stream2end   = ghcomp.DeconstructDomain(stream2).end
    dom2d        = ghcomp.ConstructDomain2(stream1start,stream1end,stream2start,stream2end)
    splitsurface = ghcomp.Isotrim(argu1,dom2d)
    areasplit    = ghcomp.Area(splitsurface).area
    resmassadd   = ghcomp.MassAddition(areasplit).result
    partresmassadd= ghcomp.MassAddition(areasplit)._1
    simplify     = ghcomp.SimplifyTree(partresmassadd)
    res_multi1   = ghcomp.Multiplication(resmassadd,series)
    length_list  = []
    list         = [[],[],[]]
    for item in res_multi1:
        larger_than = ghcomp.LargerThan(item,partresmassadd)
        culled_list = ghcomp.CullPattern(simplify,larger_than[1])
        length_list.append(ghcomp.ListLength(culled_list))
    for item in range(len(length_list)):
        list[0].append(areasplit[length_list[item]])
        list[1].append(partresmassadd[length_list[item]-1])
        list[2].append(domain_end[length_list[item]-1])
    list1_it1 = areasplit[length_list[0]]
    list1_it2 = areasplit[length_list[1]]
    list2_it1 = partresmassadd[length_list[0]-1]
    list2_it2 = partresmassadd[length_list[1]-1]
    list3_it1 = domain_end[length_list[0]-1]
    list3_it2 = domain_end[length_list[1]-1]
    minus = []
    divpri = []
    divsec = []
    add = []
    for item in range(len(res_multi1)):
        minus.append(res_multi1[item]-list[1][item])
        divpri.append(minus[-1]/list[0][item])
        divsec.append(divpri[-1]/precision)
        add.append(list[2][item]+divsec[-1])
    minus1 = [res_multi1[0]-list2_it1,res_multi1[1]-list2_it2]
    div1   = [minus1[0]/list1_it1,minus1[1]/list1_it2]
    div2   = [div1[0]/precision,div1[1]/precision]
    addition = [list3_it1+div2[0],list3_it2+div2[1]]
    stream1 = [0]
    stream1.extend(add)
    stream2 = add
    stream2.extend([1])
    domain1 = ghcomp.ConstructDomain(stream1,stream2)
    filter1 = ghcomp.StreamFilter(uvtog,interval,domain1)
    filter2 = ghcomp.StreamFilter(uvtog,domain1,interval)
    filter1start = ghcomp.DeconstructDomain(filter1).start
    filter1end   = ghcomp.DeconstructDomain(filter1).end
    filter2start = ghcomp.DeconstructDomain(filter2).start
    filter2end   = ghcomp.DeconstructDomain(filter2).end
    final_domain = ghcomp.ConstructDomain2(filter1start,filter1end,filter2start,filter2end)
    final_splitsurface = ghcomp.Isotrim(argu1,final_domain)
    final_splitsurface = ghcomp.Flip(final_splitsurface,brep).surface
    return final_splitsurface
@timing
def getB17Paragraph(startpattern,stoppattern,dataset):
    output = []
    inparagraph = 'FALSE'
    lines=dataset
    data=lines[0].split( )
    for i in range(len(lines)):
        search_start=re.search(r'{0}'.format(startpattern),lines[i])
        if search_start is not None or inparagraph == 'TRUE':
            inparagraph = 'TRUE'
            output.append(lines[i])
            search_stop=re.search(r'{0}'.format(stoppattern),lines[i])
            if search_stop is not None:
                return output
                f.close()
                break
    print 'no match found!'
@timing
def my_split(s, seps):
    res = [s]
    for sep in seps:
        s, res = res, []
        for seq in s:
            res += seq.split(sep)
    return res
# this routine collects the available names that matched the searchpattern
@timing
def getdata(search_pattern,dataset):
    data_get=dataset
    output = []
    for line in data_get:
        search_data=re.search(r'{0}'.format(search_pattern),line)
        if search_data is not None:
            data=line.split( )
            output.append(data[1])
    return output
checkUnits()
if 'default_constructions' in locals() and default_constructions != None:
    defaultconstr = default_constructions
else:
    defaultconstr = DEFAULTCONSTRUCTION()
if Hemisphere:
    pass
else:
    Hemisphere = 'NORTHERN'
#sc.sticky[sc.doc.Path]["autoSurface"]        = autoSurface
#choosing correct TRNBuild based on input from TrnsysFolder
build_mode = ''
building_folder = TrnsysFolder + "Building\\"
for files in os.listdir(building_folder):
    if "TRNBID.exe" in files:
        build_mode = 'BID'
    elif "TRNBuild.exe" in files:
        build_mode = 'BUI'
if build_mode == '':
    print("Please check your TRNSYS/TRNLizard path!")
#choosing correct TRNEXE based on Trnsys Folder
exe_mode = ''
exe_folder = TrnsysFolder + "Exe\\"
for root, dirs, files in os.walk(exe_folder):
    if "TrnEXE64.exe" in files:
        exe_mode = 'exe64'
    elif "TrnEXE.exe" in files:
        exe_mode = 'exe32'
if exe_mode == '':
    print("Please check your TRNSYS/TRNLizard path!")
sc.sticky[sc.doc.Path]["Build_mode"]         = build_mode
sc.sticky[sc.doc.Path]["Exe_mode"]           = exe_mode
sc.sticky[sc.doc.Path]["findMaxSurfNum"]     = findMaxSurfNum
sc.sticky[sc.doc.Path]["checkAdjacent"]      = checkAdjacent
sc.sticky[sc.doc.Path]["checkWindowsInWalls"] = checkWindowsInWalls
sc.sticky[sc.doc.Path]["defineGeosurf"]      = defineGeosurf
sc.sticky[sc.doc.Path]["getFloorArea"]       = getFloorArea
sc.sticky[sc.doc.Path]["getSurfaceOrientation"] = getSurfaceOrientation
sc.sticky[sc.doc.Path]["getOrientation"] = getOrientation
sc.sticky[sc.doc.Path]["getSurfaceType"] = getSurfaceType
sc.sticky[sc.doc.Path]["getWinOrientation"]  = getWinOrientation
sc.sticky[sc.doc.Path]["getSurfaceVertices"] = getSurfaceVertices
sc.sticky[sc.doc.Path]["getVolume"]          = getVolume
sc.sticky[sc.doc.Path]["getInputs"]          = getInputs
sc.sticky[sc.doc.Path]["readDataFileColumn"] = readDataFileColumn
sc.sticky[sc.doc.Path]["getDataParagraph"]   = getDataParagraph
sc.sticky[sc.doc.Path]["timing"]             = timing
sc.sticky[sc.doc.Path]["AIRNODE"]            = AIRNODE
sc.sticky[sc.doc.Path]["CONSTRUCTION"]       = CONSTRUCTION
sc.sticky[sc.doc.Path]["GEOMETRY"]           = GEOMETRY
sc.sticky[sc.doc.Path]["defaultconstr"]      = defaultconstr
#sc.sticky[sc.doc.Path]["REGIME"]             = REGIME
#sc.sticky[sc.doc.Path]["INFILTRATION"]       = INFILTRATION
#sc.sticky[sc.doc.Path]["VENTILATION"]        = VENTILATION
#sc.sticky[sc.doc.Path]["GAIN"]               = GAIN
#sc.sticky[sc.doc.Path]["HEATING"]            = HEATING
#sc.sticky[sc.doc.Path]["COOLING"]            = COOLING
sc.sticky[sc.doc.Path]["DAILYSCHEDULE"]      = DAILYSCHEDULE
sc.sticky[sc.doc.Path]["WEEKLYSCHEDULE"]     = WEEKLYSCHEDULE
sc.sticky[sc.doc.Path]["ZONECOLL"]           = ZONECOLL
sc.sticky[sc.doc.Path]["MULTIZONECOLL"]      = MULTIZONECOLL
sc.sticky[sc.doc.Path]["Template"]           = Template
sc.sticky[sc.doc.Path]["printdata"]          = printData
sc.sticky[sc.doc.Path]["printsingledata"]    = printSingleData
sc.sticky[sc.doc.Path]["Trnsys_folder"]      = TrnsysFolder.encode('utf-8')
sc.sticky[sc.doc.Path]["Project_folder"]     = ProjectFolder.encode('utf-8')
sc.sticky[sc.doc.Path]["Project_variants_folder"] = project_variants_folder.encode('utf-8')
sc.sticky[sc.doc.Path]["Variants_folder"]    = variants_folder.encode('utf-8')
sc.sticky[sc.doc.Path]["Results_folder"]     = results_folder.encode('utf-8')
sc.sticky[sc.doc.Path]["Project_name"]       = project_name.encode('utf-8')
sc.sticky[sc.doc.Path]["Short_name"]         = ShortVariantName.encode('utf-8')
sc.sticky[sc.doc.Path]["Long_name"]          = LongVariantName.encode('utf-8')
if os.path.dirname(WeatherFile):
    sc.sticky[sc.doc.Path]["Weather_file"]       = WeatherFile.encode('utf-8')
else:
    sc.sticky[sc.doc.Path]["Weather_file"]       = (ProjectFolder + WeatherFile).encode('utf-8')
sc.sticky[sc.doc.Path]["Hemisphere"]         = Hemisphere
sc.sticky[sc.doc.Path]["Altitude"]           = Altitude
sc.sticky[sc.doc.Path]["Tambmean"]           = AnnualMeanOutsideTemp
sc.sticky[sc.doc.Path]["Pressure"]           = AmbientPressure
sc.sticky[sc.doc.Path]["transformillfile"]   = transformillfile
sc.sticky[sc.doc.Path]["adaptBoundaryTemp"]  = adaptBoundaryTemp
sc.sticky[sc.doc.Path]["splitSurface"]       = splitSurface
sc.sticky[sc.doc.Path]["surfaceSplitting"]   = surfaceSplitting
#sc.sticky[sc.doc.Path]["Build_mode"]         = 'BID'                  #switch if TRNBUILD = 'BUI' or TRNBID = 'BID' is called
sc.sticky[sc.doc.Path]["TRNSYS"] = 18
sc.sticky[sc.doc.Path]["POLLUTANTS"]         = POLLUTANTS
sc.sticky[sc.doc.Path]["LARGEOPENINGS"]      = LARGEOPENINGS
sc.sticky[sc.doc.Path]["STRAIGHTDUCTS"]      = STRAIGHTDUCTS
sc.sticky[sc.doc.Path]["EXTERNALNODES"]      = EXTERNALNODES
sc.sticky[sc.doc.Path]["AUXILIARYNODES"]      = AUXILIARYNODES
sc.sticky[sc.doc.Path]["FANS"]      = FANS
sc.sticky[sc.doc.Path]["THERMALZONES"]       = THERMALZONES
sc.sticky[sc.doc.Path]["AIRLINKNETWORK"]     = AIRLINKNETWORK
sc.sticky[sc.doc.Path]["WINDVELOCITYPROFILE"]= WINDVELOCITYPROFILE
sc.sticky[sc.doc.Path]["SYSTEMUNITNO"] = range(800,1000)
sc.sticky[sc.doc.Path]["ADVANCEDMODELING"] = advanced_modeling
print "This Component ran at least once!\nPlease re-run if you change a library information! "
if Reload == True or ('library' not in sc.sticky[sc.doc.Path].keys()):
    sc.sticky[sc.doc.Path]['Const_coll'] = {}
    sc.sticky[sc.doc.Path]['Surface_Counter'] = 0
    sc.sticky[sc.doc.Path]["SYSTEM"] = {}
    #used information
    layerslib = []
    wallslib = []
    gainslib = []
    gainnames = []
    scheduleslib = []
    schedulenames = []
    windowslib = []
    datalines = WindowLibrary
    library = LIBRARY()
    #Window reading and class defition
    windID = []
    windowdict = {}
    paragraph  = getB17Paragraph('^*WinID','^_EXTENSION_WINPOOL_END_',datalines)
    for line in paragraph:
        line = re.sub('\n','',line)
        line = re.sub('\r','',line)
        search_data=re.search(r'{0}'.format('^\s*\d+'),line)
        if search_data is not None:
            data=line.split( )
            ID = re.sub(' ','',data[0])
            windowslib.append(WINDOW(ID))
            windowdict[ID] = {}
            windowdict[ID]['DESC'] = line + '\n'
            windowdict[ID]['DATA'] = []
    #library.Windows = windowslib
    del paragraph[-1]
    library.windowlib = paragraph
    # get all the window definition and store it for the output
    paragraph  = getB17Paragraph('^_EXTENSION_WINPOOL_START_','^\*\*\* END OF LIBRARY',datalines)
    paragraph.pop(0)
    del paragraph[-1]
    for para_item in range(len(paragraph)):
        paragraph[para_item] = paragraph[para_item].replace('\n', '\r\n')    # remove '\n' only
    windowcounter = -1
    winID = -1
    start = 0
    lastcounter = 0
    #subpara = []
    subpara = ''
    for ix,window_item in enumerate(paragraph):
        if (('WINDOW' in window_item or 'Window' in window_item) and ('Name' not in window_item and 'ID' not in window_item)):
            windowcounter += 1
        #subpara.append(window_item)
        search_id=re.match(r'Window\s+ID\s+:',window_item)
        if search_id is not None:
            dummy = window_item.split()
            winID = dummy[3]
        if windowcounter != lastcounter or ix == len(paragraph) - 1:
            windowdict[winID]['DATA'] = subpara
            #subpara = []
            subpara = ''
            lastcounter = windowcounter
        subpara += window_item
    for item in windowslib:
        item.Data = windowdict[item.Winid]['DATA']
        item.Desc = windowdict[item.Winid]['DESC']
        item.getShgc()
        item.getTvis()
        item.getUglas()
    library.windowdata = paragraph
    library.Windows = windowslib
    windowdict = {}
    paragraph = []
    windowslib = []
    # reset all used arrays that are no more necessary
    datalines = []
    layerslib = []
    wallslib = []
    gainslib = []
    gainnames = []
    scheduleslib = []
    schedulenames = []
    windowslib = []
    # Starting from here dependent components are reloaded
    #sys.exit()
    sc.sticky[sc.doc.Path]['library'] = library
    
    # Only expire dependent components once per reload cycle to prevent infinite loop
    if not sc.sticky[sc.doc.Path].get('lizard_reload_expired', False):
        for obj in ghenv.Component.OnPingDocument().Objects:
            if 'GhPython' in obj.ToString() and obj.Name != "Lizard_Component" and obj.Name != "WindowLibrary" and obj.Name != "Lizard_Construction" and obj.Name != "Lizard_Daily_Schedule"  and obj.Name != "Lizard_Weekly_Schedule" and obj.Name != "Lizard_Active_Slab_Layer" and obj.Name != "Lizard_Layer"  and obj.Name != "Lizard_Layer_Resistance" and obj.Name != "Lizard_Active_CC_Layer" and obj.Name != "Lizard_Annual_Schedule" and obj.Name != "Python Script" and obj.Name != "Lizard_Variant_Definition":
                obj.ExpireSolution(True)
        sc.sticky[sc.doc.Path]['lizard_reload_expired'] = True
else:
    library = sc.sticky[sc.doc.Path]['library']
    # Reset the reload flag when Reload is False, allowing next True to trigger expiration again
    if sc.sticky[sc.doc.Path].get('lizard_reload_expired', False):
        sc.sticky[sc.doc.Path]['lizard_reload_expired'] = False
#Check layer library and add new layer definition
if 'AddLayers' in locals() and AddLayers != None:
    delcoll = []
    for new_layer in AddLayers:
        for u in range(len(library.Layers)):
            if new_layer.Name == library.Layers[u].Name:
                delcoll.append(u)
    dummy = list(set(delcoll))
    dummy = sorted(dummy)
    for item in list(reversed(dummy)):
        library.Layers.pop(item)
    for new_layer in AddLayers:
        library.Layers.append(new_layer)
    sc.sticky[sc.doc.Path]['library'] = library
#Check wall library and add new wall definition
if 'AddWalls' in locals() and AddWalls != None:
    delcoll = []
    for new_item in AddWalls:
        for u in range(len(library.Walls)):
            if new_item.Name == library.Walls[u].Name:
                delcoll.append(u)
    dummy = list(set(delcoll))
    dummy = sorted(dummy)
    for item in list(reversed(dummy)):
        library.Walls.pop(item)
    for new_item in AddWalls:
        library.Walls.append(new_item)
    sc.sticky[sc.doc.Path]['library'] = library
#Check schedule library and add new schedule definition
if 'AddSchedules' in locals() and AddSchedules != None:
    for schedule in AddSchedules:
        schedulenames = []
        delcoll = []
        for j in schedule.Daysarray:
            for u in range(len(library.Schedules)):
                if j == library.Schedules[u].Name or schedule.Name == library.Schedules[u].Name:
                    delcoll.append(u)
        dummy = list(set(delcoll))
        dummy = sorted(dummy)
        for item in list(reversed(dummy)):
            library.Schedules.pop(item)
        for j in range (len(schedule.Daysarray)):
            if schedule.Daysarray[j] in schedulenames:
                pass
            else:
                schedulenames.append(schedule.Daysarray[j])
                library.Schedules.append(SCHEDULE(schedule.Daysarray[j]))
                library.Schedules[-1].Hours = schedule.Hoursarray[j]
                library.Schedules[-1].Values = schedule.Valuesarray[j]
        library.Schedules.append(SCHEDULE(schedule.Name))
        library.Schedules[-1].Days = schedule.Days
        library.Schedules[-1].Hourly = schedule.Hourly
        library.Schedules[-1].Userdef = 1
        sc.sticky[sc.doc.Path]['library'] = library
if 'AnnualSchedules' in locals() and AnnualSchedules != None:
    library.Annualschedules = AnnualSchedules
    sc.sticky[sc.doc.Path]["library"] = library
#automatically update multizone building component
#for obj in ghenv.Component.OnPingDocument().Objects:
    #print obj.Name
#    if obj.Name == "Lizard_Component" or obj.Name == "Number Slider" or obj.Name == "Panel"  or obj.Name == "Lizard_Variant_Definition" or obj.Name == "building_library":
#    if obj.Name == "Lizard_MultiZone":
#        obj.ExpireSolution(True)
#    if obj.Name == "Lizard_Active_Layer_ID":
#        obj.ExpireSolution(True)
#    if obj.Name == "Lizard_Surface_ID":
#        obj.ExpireSolution(True)


