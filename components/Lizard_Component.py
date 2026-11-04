"""
This is the key component to store model information
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
Modified by Junfeng Xiao, 2026.
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
        Required: False
        Options: NORTHERN, SOUTHERN
    Altitude (object): define the building altitude for thermal simulation
        Access: item
        Required: True
    GroundLevel (float): Z of the ground [m]. FallbackBoundary uses it, so the model has to stand at its real height.
        Access: item
        Required: False
        Default: 0
    FallbackBoundary (bool): for a surface without a category and without a partner. True = GROUND if all its vertices are at or below GroundLevel and it has no window and is no ADDWINDOW, otherwise EXTERNAL. False = an error. Not connected = True
        Access: item
        Required: False
    AnnualMeanOutsideTemp (object): Script variable Lizard
        Access: item
        Required: True
    AmbientPressure (object): Script variable Lizard
        Access: item
        Required: True
    AddSchedules (object): link the used schedules that are required for the regime components or the active layer
        Access: list
        Required: False
    AddLayers (object): link the layer definitions required for the wall assemblies
        Access: list
        Required: False
    AddConstructions (object): link the construction definitions containing the single layers
        Access: list
        Required: False
    AnnualSchedules (object): link the annual schedules definition in order to account e.g. for vacations, etc.
        Access: list
        Required: False
    Variants (object): Script variable Lizard
        Access: item
        Required: False
    Reload (object): define True if you added information to the library by walls, layers, etc. in order to update the library
        Access: item
        Required: False
    x (object): Script variable Lizard
        Access: item
        Required: False

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
ghenv.Component.Category = "TRNLizard"
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
        self.Boundarycond   = None                  #None = not set: filled in by compileModel
        self.Boundarytemp   = 0
        self.Geosurf        = 0
        self.Faces          = []
        self.Orientation    = []
        self.Construction   = None                  #None = not set: must be set before compileModel ends
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
        self.Frontback      = None                  #None = not set: filled in by compileModel
        self.Hygrothermal   = False                 #True = Lizard_Hygro: Type 395 model of the final EXTERNAL or BOUNDARY
        self.Sourcesurf     = None                  #Surfnum of the surface this one was split from
        self.Frontguessed   = False                 #True = neither the settings nor the surface type chose the FRONT side of the pair
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
        # Type 395 (HAMT) settings of the surface from Lizard_Hygro; None = input not connected, the System component then
        # writes the default of the deck
        self.Writereport = None     # parameter 6: True/None = 1 (write the Type395_*.out reports), False = -1
        self.Reportinterval = None  # parameter 7 [h], None = 1
        self.Addheatdepth = None    # parameter 5 [m] from the side-2 surface, None = t395_udepth of the System component or 0.02
        self.Addheat = None         # W per m2 of wall in QheatKJ (input 11): a number or '(TRNSYS expression)', None = active-layer load
        self.Layermindiv = None     # parameter 9 = minimum cells per material layer, None = t395_udivnum of the System component or 100
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
        self.Geosurffloor = 0
        self.Constructionset = None                 #defaults for the surfaces of this airnode, before the ones of the model
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
class CRACKS:
    """TRNFlow crack link: the type (CRACK CR_<name>: CS, EXPN) and the link between two nodes in one object."""
    def __init__(self):
        self.Cracks         = 1
        self.Name           = ''        # must start with CR_
        self.Cs             = 0.002     # air mass flow coefficient [kg/s at 1 Pa, per link]
        self.Expn           = 0.66      # flow exponent, 0.5 turbulent ... 1.0 laminar
        self.Frnode         = ''
        self.Tonode         = ''
        self.Frheight       = 0
        self.Toheight       = 0
        self.Fscale         = 1         # factor of the mass flow coefficient, 0 = closed (a number or 'INPUT 1*NAME')
        self.Output         = ''
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
# ---- Surface kernel (begin)
# Plain geometry on tuples: no Rhino, no sticky, the same code under IronPython 2 and CPython 3
# (tests/test_surface_kernel.py). Loops are lists of points without a repeated last point.
def vecAdd(a, b, scale=1.0):
    return (a[0]+scale*b[0], a[1]+scale*b[1], a[2]+scale*b[2])
def vecSub(a, b):
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def vecDot(a, b):
    return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def vecCross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def vecUnit(a):
    length = vecDot(a, a)**0.5
    return (a[0]/length, a[1]/length, a[2]/length)
def polyAreaVector(points):
    """Area vector of a planar 3D loop: its length is the area, its direction follows the right hand rule."""
    total = (0.0, 0.0, 0.0)
    for i in range(len(points)):
        total = vecAdd(total, vecCross(points[i], points[(i+1) % len(points)]))
    return (total[0]/2.0, total[1]/2.0, total[2]/2.0)
def polyArea2d(loop):
    """Signed area of a 2D loop, positive for counter-clockwise."""
    total = 0.0
    for i in range(len(loop)):
        a, b = loop[i], loop[(i+1) % len(loop)]
        total += a[0]*b[1]-b[0]*a[1]
    return total/2.0
def polyPerimeter2d(loop):
    total = 0.0
    for i in range(len(loop)):
        a, b = loop[i], loop[(i+1) % len(loop)]
        total += ((b[0]-a[0])**2+(b[1]-a[1])**2)**0.5
    return total
def pointInLoop2d(point, loop):
    """Even-odd test; a point exactly on the boundary may give either answer."""
    inside = False
    for i in range(len(loop)):
        a, b = loop[i], loop[(i+1) % len(loop)]
        if (a[1] > point[1]) != (b[1] > point[1]):
            if a[0]+(point[1]-a[1])*(b[0]-a[0])/(b[1]-a[1]) > point[0]:
                inside = not inside
    return inside
def pointSegmentDistance2d(p, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    length2 = dx*dx+dy*dy
    if length2 == 0:
        return ((p[0]-a[0])**2+(p[1]-a[1])**2)**0.5
    t = max(0.0, min(1.0, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length2))
    return ((p[0]-a[0]-t*dx)**2+(p[1]-a[1]-t*dy)**2)**0.5
def pointOnLoop2d(point, loop, tolerance):
    for i in range(len(loop)):
        if pointSegmentDistance2d(point, loop[i], loop[(i+1) % len(loop)]) < tolerance:
            return True
    return False
def cleanLoop2d(loop, tolerance):
    """The loop without repeated and collinear vertices."""
    result = list(loop)
    changed = True
    while changed and len(result) > 3:
        changed = False
        for i in range(len(result)):
            before, after = result[i-1], result[(i+1) % len(result)]
            if pointSegmentDistance2d(result[i], before, after) < tolerance:
                del result[i]
                changed = True
                break
    return result
def loopInterior2d(loops):
    """A point inside a region given by its outer loop and hole loops, in the widest span of the widest band."""
    heights = sorted(set([point[1] for loop in loops for point in loop]))
    bands = sorted([(heights[i+1]-heights[i], i) for i in range(len(heights)-1)], reverse=True)
    for gap, index in bands:
        y = heights[index]+gap/2.0
        crossings = []
        for loop in loops:
            for i in range(len(loop)):
                a, b = loop[i], loop[(i+1) % len(loop)]
                if (a[1] > y) != (b[1] > y):
                    crossings.append(a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]))
        crossings.sort()
        spans = [(crossings[i+1]-crossings[i], crossings[i]) for i in range(0, len(crossings)-1, 2)]
        if spans:
            width, start = max(spans)
            if width > 0:
                return (start+width/2.0, y)
    return None
class PointSnapper:
    """Maps every point closer than the tolerance to the first point seen there, through a grid of tolerance-sized cells."""
    def __init__(self, tolerance):
        self.tolerance = tolerance
        self.cells = {}
    def snap(self, point):
        cx, cy = int(point[0]//self.tolerance), int(point[1]//self.tolerance)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for other in self.cells.get((cx+dx, cy+dy), ()):
                    if ((other[0]-point[0])**2+(other[1]-point[1])**2)**0.5 < self.tolerance:
                        return other
        self.cells.setdefault((cx, cy), []).append(point)
        return point
def segmentCrossing2d(a, b, c, d):
    """Crossing point of the segments a-b and c-d, None for parallel segments or when they do not meet."""
    rx, ry = b[0]-a[0], b[1]-a[1]
    sx, sy = d[0]-c[0], d[1]-c[1]
    denominator = rx*sy-ry*sx
    if abs(denominator) < 1e-12:
        return None
    t = ((c[0]-a[0])*sy-(c[1]-a[1])*sx)/denominator
    u = ((c[0]-a[0])*ry-(c[1]-a[1])*rx)/denominator
    if t < 0 or t > 1 or u < 0 or u > 1:
        return None
    return (a[0]+t*rx, a[1]+t*ry)
def nodeSegments(segments, snapper):
    """Splits the undirected segments (pairs of snapped points) at every crossing and every point lying on them."""
    tolerance = snapper.tolerance
    segments = set([(min(a, b), max(a, b)) for a, b in segments if a != b])
    for attempt in range(8):
        ordered = sorted(segments)
        boxes = [(min(s[0][0], s[1][0])-tolerance, max(s[0][0], s[1][0])+tolerance,
                  min(s[0][1], s[1][1])-tolerance, max(s[0][1], s[1][1])+tolerance) for s in ordered]
        cuts = {}
        for i in range(len(ordered)):
            a, b = ordered[i]
            for j in range(i+1, len(ordered)):
                if boxes[i][1] < boxes[j][0] or boxes[j][1] < boxes[i][0] or boxes[i][3] < boxes[j][2] or boxes[j][3] < boxes[i][2]:
                    continue
                c, d = ordered[j]
                crossing = segmentCrossing2d(a, b, c, d)
                if crossing is not None:
                    point = snapper.snap(crossing)
                    if point not in (a, b):
                        cuts.setdefault(ordered[i], set()).add(point)
                    if point not in (c, d):
                        cuts.setdefault(ordered[j], set()).add(point)
                for point in (c, d):
                    if point not in (a, b) and pointSegmentDistance2d(point, a, b) < tolerance:
                        cuts.setdefault(ordered[i], set()).add(point)
                for point in (a, b):
                    if point not in (c, d) and pointSegmentDistance2d(point, c, d) < tolerance:
                        cuts.setdefault(ordered[j], set()).add(point)
        if not cuts:
            return segments
        for segment in cuts:
            segments.discard(segment)
            a, b = segment
            chain = sorted(cuts[segment], key=lambda p: (p[0]-a[0])**2+(p[1]-a[1])**2)
            chain = [a]+chain+[b]
            for k in range(len(chain)-1):
                if chain[k] != chain[k+1]:
                    segments.add((min(chain[k], chain[k+1]), max(chain[k], chain[k+1])))
    return segments
def edgeAngle2d(a, b):
    return math.atan2(b[1]-a[1], b[0]-a[0])
def traceLoops(edges):
    """Closed loops of directed edges, each with the region on its left: counter-clockwise shells, clockwise holes."""
    outgoing = {}
    for a, b in edges:
        outgoing.setdefault(a, []).append(b)
    loops = []
    unused = set(edges)
    for start in sorted(edges):
        if start not in unused:
            continue
        loop = []
        edge = start
        while edge in unused:
            unused.discard(edge)
            loop.append(edge[0])
            a, b = edge
            back = edgeAngle2d(b, a)
            best, bestturn = None, None
            for other in outgoing[b]:
                turn = (back-edgeAngle2d(b, other)) % (2*math.pi)
                if turn < 1e-12:
                    turn = 2*math.pi
                if bestturn is None or turn < bestturn:
                    best, bestturn = other, turn
            edge = (b, best)
        if len(loop) >= 3:
            loops.append(loop)
    return loops
def planarFaces(segments):
    """Faces of a noded set of segments: dicts with 'outer' (counter-clockwise) and 'holes' (clockwise); dangling edges are dropped."""
    neighbours = {}
    for a, b in segments:
        neighbours.setdefault(a, set()).add(b)
        neighbours.setdefault(b, set()).add(a)
    dangling = [p for p in neighbours if len(neighbours[p]) == 1]
    while dangling:
        point = dangling.pop()
        for other in list(neighbours.get(point, ())):
            neighbours[other].discard(point)
            if len(neighbours[other]) == 1:
                dangling.append(other)
        neighbours.pop(point, None)
    edges = []
    for point in neighbours:
        for other in neighbours[point]:
            edges.append((point, other))
    component = {}
    for point in sorted(neighbours):
        if point not in component:
            stack = [point]
            component[point] = point
            while stack:
                for other in neighbours[stack.pop()]:
                    if other not in component:
                        component[other] = point
                        stack.append(other)
    loops = traceLoops(edges)
    faces = [{'outer': loop, 'holes': []} for loop in loops if polyArea2d(loop) > 0]
    faces.sort(key=lambda face: polyArea2d(face['outer']))
    for loop in loops:
        if polyArea2d(loop) > 0:
            continue
        for face in faces:  # smallest first: the first one that holds the loop is its direct parent
            if component[face['outer'][0]] != component[loop[0]] and pointInLoop2d(loop[0], face['outer']):
                face['holes'].append(loop)
                break
    return faces
def faceEdges(face):
    edges = []
    for loop in [face['outer']]+face['holes']:
        for i in range(len(loop)):
            edges.append((loop[i], loop[(i+1) % len(loop)]))
    return edges
def splitHoles(face, snapper):
    """Simple loops that together make up a face with holes: b18 surfaces have one loop of vertices, so a hole is cut
    open with a horizontal line through it to the nearest boundary on both sides."""
    if not face['holes']:
        return [face['outer']]
    hole = sorted(face['holes'], key=lambda loop: min(loop))[0]
    heights = sorted(set([point[1] for point in hole]))
    gap, index = max([(heights[i+1]-heights[i], i) for i in range(len(heights)-1)])
    y = heights[index]+gap/2.0
    edges = faceEdges(face)
    own = []
    others = []
    for a, b in edges:
        if (a[1] > y) != (b[1] > y):
            x = a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1])
            if a in hole and b in hole:
                own.append(x)
            else:
                others.append(x)
    left = max([x for x in others if x < min(own)])
    right = min([x for x in others if x > max(own)])
    segments = [(a, b) for a, b in edges]
    for x0, x1 in ((left, min(own)), (max(own), right)):
        segments.append((snapper.snap((x0, y)), snapper.snap((x1, y))))
    pieces = []
    for part in planarFaces(nodeSegments(segments, snapper)):
        point = loopInterior2d([part['outer']]+part['holes'])
        if point is None or not pointInLoop2d(point, face['outer']):
            continue
        if True in [pointInLoop2d(point, other) for other in face['holes']]:
            continue
        pieces.extend(splitHoles(part, snapper))
    return pieces
def arrangePolygons(polygons, tolerance, slivertolerance=None):
    """Splits overlapping simple polygons of one plane into regions with one set of sources.

    polygons: list of (key, 2D loop). Returns a list of dicts sorted by cover and size: 'cover' = sorted tuple of the keys
    whose polygon holds the region (never empty), 'loop' = one simple counter-clockwise loop, 'area'. A region of one cover
    with holes comes as several loops. Regions narrower than slivertolerance (default: tolerance) go to the neighbour that
    shares the longest edge. The result does not depend on the order of the polygons.
    """
    if slivertolerance is None:
        slivertolerance = tolerance
    snapper = PointSnapper(tolerance)
    for point in sorted(set([point for key, loop in polygons for point in loop])):
        snapper.snap(point)
    sources = []
    segments = []
    for key, loop in sorted(polygons, key=lambda polygon: polygon[0]):
        snapped = []
        for point in loop:
            point = snapper.snap(point)
            if not snapped or snapped[-1] != point:
                snapped.append(point)
        if len(snapped) > 1 and snapped[0] == snapped[-1]:
            snapped.pop()
        if len(snapped) < 3:
            continue
        sources.append((key, snapped))
        for i in range(len(snapped)):
            segments.append((snapped[i], snapped[(i+1) % len(snapped)]))
    faces = planarFaces(nodeSegments(segments, snapper))
    faceofedge = {}
    for index, face in enumerate(faces):
        for edge in faceEdges(face):
            faceofedge[edge] = index
        point = loopInterior2d([face['outer']]+face['holes'])
        face['cover'] = ()
        if point is not None:
            face['cover'] = tuple(sorted([key for key, loop in sources if pointInLoop2d(point, loop)]))
    for index, face in enumerate(faces):
        area = polyArea2d(face['outer'])+sum([polyArea2d(hole) for hole in face['holes']])
        perimeter = polyPerimeter2d(face['outer'])+sum([polyPerimeter2d(hole) for hole in face['holes']])
        face['sliver'] = bool(face['cover']) and 2.0*area/perimeter < slivertolerance
    for index, face in enumerate(faces):
        if not face['sliver']:
            continue
        shared = {}
        for a, b in faceEdges(face):
            other = faceofedge.get((b, a))
            if other is not None and other != index and faces[other]['cover'] and not faces[other]['sliver']:
                length = ((b[0]-a[0])**2+(b[1]-a[1])**2)**0.5
                shared[faces[other]['cover']] = shared.get(faces[other]['cover'], 0.0)+length
        if shared:
            face['cover'] = max([(shared[cover], cover) for cover in shared])[1]
    grouped = {}
    for face in faces:
        if face['cover']:
            grouped.setdefault(face['cover'], []).extend(faceEdges(face))
    regions = []
    for cover in sorted(grouped):
        edges = set(grouped[cover])
        remaining = [edge for edge in sorted(edges) if (edge[1], edge[0]) not in edges]
        loops = traceLoops(remaining)
        shells = [{'outer': loop, 'holes': []} for loop in loops if polyArea2d(loop) > 0]
        shells.sort(key=lambda face: polyArea2d(face['outer']))
        for loop in loops:
            if polyArea2d(loop) > 0:
                continue
            middle = ((loop[0][0]+loop[1][0])/2.0, (loop[0][1]+loop[1][1])/2.0)
            for shell in shells:
                if pointInLoop2d(middle, shell['outer']):
                    shell['holes'].append(loop)
                    break
        for shell in shells:
            for loop in splitHoles(shell, snapper):
                loop = cleanLoop2d(loop, tolerance)
                regions.append({'cover': cover, 'loop': loop, 'area': polyArea2d(loop)})
    regions.sort(key=lambda region: (region['cover'], -region['area'], region['loop'][0]))
    return regions
def planeBasis(normal):
    """Unit vectors u, v of a plane with u x v = normal."""
    helper = (1.0, 0.0, 0.0)
    if abs(normal[0]) >= 0.9:
        helper = (0.0, 1.0, 0.0)
    u = vecUnit(vecCross(normal, helper))
    return u, vecCross(normal, u)
def canonicalDirection(normal):
    """The normal or its opposite, the same for both: the first clear component is positive."""
    for value in normal:
        if abs(value) > 1e-6:
            if value < 0:
                return (-normal[0], -normal[1], -normal[2])
            break
    return normal
def groupPlanes(faces, gaptolerance, angletolerance):
    """Groups of faces (dicts with 'key', 'points', 'normal') that lie in one plane, up to the gap: list of (direction, faces)."""
    cosine = math.cos(math.radians(angletolerance))
    directions = []
    for face in sorted(faces, key=lambda item: item['key']):
        direction = canonicalDirection(vecUnit(face['normal']))
        for known in directions:
            if abs(vecDot(known[0], direction)) >= cosine:
                known[1].append(face)
                break
        else:
            directions.append((direction, [face]))
    groups = []
    for direction, members in directions:
        offsets = sorted([(vecDot(direction, member['points'][0]), member['key'], member) for member in members], key=lambda entry: entry[:2])
        current = []
        for offset, key, member in offsets:
            if current and offset-current[0][0] > gaptolerance:
                groups.append((direction, [entry[1] for entry in current]))
                current = []
            current.append((offset, member))
        if current:
            groups.append((direction, [entry[1] for entry in current]))
    return groups
def convexStartIndex(points, normal):
    """Index of the first convex vertex (seen along the normal) of a loop, the start checkVerticesOrder looks for."""
    area = polyAreaVector(points)
    sign = 1.0
    if vecDot(area, normal) < 0:
        sign = -1.0
    for i in range(len(points)):
        turn = vecCross(vecSub(points[i], points[i-1]), vecSub(points[(i+1) % len(points)], points[i]))
        if sign*vecDot(turn, area) > 0:
            return i
    return 0
def rotateConvexStart(points, normal):
    start = convexStartIndex(points, normal)
    return points[start:]+points[:start]
def arrangeFaces(faces, tolerance, gaptolerance, angletolerance=1.0):
    """Regions of 3D faces (dicts with 'key', 'points', 'normal').

    Faces of one plane, up to gaptolerance between parallel planes, are arranged together. Returns a list of dicts: 'cover',
    'area', 'sides' {key: +1 or -1, side of the plane the normal of that face points to} and 'loops' {key: the region as a
    3D loop in the plane of that face and with the winding of that face}.
    """
    regions = []
    for direction, members in groupPlanes(faces, gaptolerance, angletolerance):
        u, v = planeBasis(direction)
        polygons = [(member['key'], [(vecDot(point, u), vecDot(point, v)) for point in member['points']]) for member in members]
        bykey = dict([(member['key'], member) for member in members])
        for region in arrangePolygons(polygons, tolerance, max(tolerance, gaptolerance)):
            loops = {}
            sides = {}
            for key in region['cover']:
                member = bykey[key]
                normal = vecUnit(member['normal'])
                sides[key] = 1
                if vecDot(normal, direction) < 0:
                    sides[key] = -1
                planeoffset = vecDot(normal, member['points'][0])
                points = []
                for x, y in region['loop']:
                    point = vecAdd(vecAdd((0.0, 0.0, 0.0), u, x), v, y)
                    points.append(vecAdd(point, direction, (planeoffset-vecDot(point, normal))/vecDot(direction, normal)))
                if vecDot(polyAreaVector(member['points']), direction) < 0:
                    points.reverse()
                loops[key] = rotateConvexStart(points, polyAreaVector(points))
            regions.append({'cover': region['cover'], 'area': region['area'], 'sides': sides, 'loops': loops})
    return regions
def triangulateLoop3d(points):
    """Triangles of a planar loop, by ear clipping; the loop may be concave."""
    area = polyAreaVector(points)
    remaining = list(points)
    triangles = []
    def holds(point, a, b, c):
        for p, q in ((a, b), (b, c), (c, a)):
            if vecDot(vecCross(vecSub(q, p), vecSub(point, p)), area) <= 0:
                return False
        return True
    while len(remaining) > 3:
        for k in range(len(remaining)):
            a, b, c = remaining[k-1], remaining[k], remaining[(k+1) % len(remaining)]
            if vecDot(vecCross(vecSub(b, a), vecSub(c, b)), area) <= 0:
                continue
            if True in [holds(point, a, b, c) for point in remaining if point not in (a, b, c)]:
                continue
            triangles.append((a, b, c))
            del remaining[k]
            break
        else:
            break
    if len(remaining) == 3:
        triangles.append(tuple(remaining))
    return triangles
def rayCrossesPolygon(origin, direction, points):
    """True/False: the ray crosses the polygon or not. None: it passes too close to the boundary to tell."""
    normal = vecUnit(polyAreaVector(points))
    denominator = vecDot(normal, direction)
    if abs(denominator) < 1e-9:
        return False
    distance = vecDot(normal, vecSub(points[0], origin))/denominator
    if distance <= 1e-7:
        return False
    hit = vecAdd(origin, direction, distance)
    u, v = planeBasis(normal)
    loop = [(vecDot(point, u), vecDot(point, v)) for point in points]
    point = (vecDot(hit, u), vecDot(hit, v))
    if pointOnLoop2d(point, loop, 1e-6):
        return None
    return pointInLoop2d(point, loop)
ORIENT_SAMPLES = ((0.34, 0.33, 0.33), (0.61, 0.26, 0.13), (0.17, 0.71, 0.12), (0.13, 0.19, 0.68), (0.47, 0.09, 0.44), (0.08, 0.41, 0.51))
def orientClosedPolygons(polygons, normals):
    """Which faces of one closed volume have a normal that points into the volume.

    A ray from the face along an outward normal starts outside, so it crosses the other faces an even number of times, and an
    inward one an odd number of times. The count ignores the normals of the others: any mix of wrong faces, concave rooms
    and T-junctions give the right answer. The answer is only used when the corrected faces close (areas times normals add up
    to zero, positive volume). Returns (indices to flip, closed).
    """
    flips = []
    votes = []
    for index in range(len(polygons)):
        direction = vecUnit(normals[index])
        triangles = triangulateLoop3d(polygons[index])
        triangles.sort(key=lambda t: -vecDot(polyAreaVector(t), polyAreaVector(t)))
        counts = []
        for triangle in triangles:
            for w0, w1, w2 in ORIENT_SAMPLES:
                origin = (w0*triangle[0][0]+w1*triangle[1][0]+w2*triangle[2][0],
                          w0*triangle[0][1]+w1*triangle[1][1]+w2*triangle[2][1],
                          w0*triangle[0][2]+w1*triangle[1][2]+w2*triangle[2][2])
                hits = [rayCrossesPolygon(origin, direction, polygons[other]) for other in range(len(polygons)) if other != index]
                if None not in hits:
                    counts.append(hits.count(True) % 2)
            if len(counts) >= len(ORIENT_SAMPLES):
                break
        votes.append(counts)
        if counts and sum(counts) == len(counts):
            flips.append(index)
    closure = (0.0, 0.0, 0.0)
    total = 0.0
    volume = 0.0
    for index in range(len(polygons)):
        sign = 1.0
        if index in flips:
            sign = -1.0
        area = vecDot(polyAreaVector(polygons[index]), polyAreaVector(polygons[index]))**0.5
        oriented = vecAdd((0.0, 0.0, 0.0), vecUnit(normals[index]), sign*area)
        closure = vecAdd(closure, oriented)
        total += area
        volume += vecDot(polygons[index][0], oriented)/3.0
    agreed = True not in [len(set(counts)) != 1 for counts in votes]
    closed = agreed and vecDot(closure, closure)**0.5 <= 1e-3*total and volume > 0
    if not closed:
        return [], False
    return flips, True
# ---- Surface kernel (end)
# ---- Surface model (begin)
# From the surfaces of the airnodes to what the b18 writer reads. No Rhino here either: makeSurfaceVertices, makeSurfaceBrep and
# flipSurfaceBreps below this block are the only contact (tests/test_surface_model.py replaces them).
ADJACENCY_TOLERANCE = 0.01      # m, points closer than this are one point
DEFAULT_GAP_TOLERANCE = 0.02    # m, parallel planes closer than this are one plane
NEAR_MISS_DISTANCE = 0.5        # m, faces this close get a hint when they are not adjacent
GROUND_LEVEL = 0.0              # m, input GroundLevel
FALLBACK_BOUNDARY = True        # input FallbackBoundary
GROUND_TEMPERATURE = 'INPUT 1*Tsoil'
CONSTRUCTION_SLOTS = ('ExteriorWall', 'InteriorWall', 'Roof', 'InteriorCeiling', 'InteriorFloor', 'GroundFloor', 'ExposedFloor')
EXTERIOR_CATEGORIES = ('EXTERNAL', 'EXTBOUNDARY', 'EXTCALC', 'EXTSKYBND', 'EXTVERTF', 'EXTBOUNDADJ', 'EXTCALEXT')
class ComponentFailure:
    """What a component outputs when it could not do its work. None would look like an input that is not connected, and the next
    component would go on with its defaults."""
    Failed = True
    def __init__(self, component, message):
        self.Component = component
        self.Message = message
    def __repr__(self):
        return "Failed:{0}:{1}".format(self.Component, self.Message)
def isFailure(value):
    """Asks the value and not its class: the class is defined again whenever Lizard_Component runs."""
    return getattr(value, 'Failed', False) is True
def isWindowSurface(item):
    return item.Type in ('WINDOW', 'BSDFWINDOW')
def isVirtualSurface(item):
    return item.Boundarycond == 'VIRTUAL' or 'Virtual' in (item.Construction or '')
def pointTuple(point):
    return (point.X, point.Y, point.Z)
def surfacePoints(item):
    return [pointTuple(point) for point in item.Vertices]
def surfaceFace(item):
    return {'key': item.Surfnum, 'points': surfacePoints(item), 'normal': pointTuple(item.Normalvector)}
def addIssue(issues, level, message, surfaces=()):
    issues.append({'level': level, 'message': message, 'surfaces': list(surfaces)})
def flipSurface(item):
    """The surface with the opposite normal; everything derived from the normal is computed after this."""
    item.Normalvector = item.Normalvector * -1.0
    vertices = list(reversed(item.Vertices))
    start = convexStartIndex([pointTuple(point) for point in vertices], pointTuple(item.Normalvector))
    item.Vertices = vertices[start:]+vertices[:start]
    flipSurfaceBreps(item)
def orientSurfaces(surfaces):
    """Corrects the normals of the surfaces of one airnode so that they point out of the room. Returns (flipped surfaces, closed);
    nothing is changed when the surfaces do not close a volume."""
    closing = [item for item in surfaces if not isWindowSurface(item)]
    if len(closing) < 4:
        return [], False
    flips, closed = orientClosedPolygons([surfacePoints(item) for item in closing], [pointTuple(item.Normalvector) for item in closing])
    if not closed:
        return [], False
    flipped = [closing[index] for index in flips]
    for item in flipped:
        flipSurface(item)
    cosine = math.cos(math.radians(1.0))
    for window in surfaces:
        if not isWindowSurface(window):
            continue
        points = surfacePoints(window)
        normal = pointTuple(window.Normalvector)
        for host in closing:
            hostnormal = pointTuple(host.Normalvector)
            hostpoints = surfacePoints(host)
            if abs(vecDot(normal, hostnormal)) < cosine or abs(vecDot(vecSub(points[0], hostpoints[0]), hostnormal)) > ADJACENCY_TOLERANCE:
                continue
            u, v = planeBasis(vecUnit(hostnormal))
            if pointInLoop2d(loopInterior2d([[(vecDot(point, u), vecDot(point, v)) for point in points]]), [(vecDot(point, u), vecDot(point, v)) for point in hostpoints]):
                if vecDot(normal, hostnormal) < 0:
                    flipSurface(window)
                    flipped.append(window)
                break
    return flipped, True
def isMirrorBoundary(item):
    """BOUNDARY with the room's own air temperature (or nothing) on the other side: the wall stands for a neighbour that is not modelled."""
    temperature = item.Boundarytemp
    if not temperature or temperature == 'Identical':
        return True
    return 'TAIR_@ANAME' in str(temperature) or str(temperature) == 'INPUT 1*TAIR_{0}'.format(item.Airnode)
def surfaceParticipates(item, autoadjacency):
    """Whether a surface looks for a partner: an unset or ADJACENT category always, the plain categories on request."""
    category = item.Boundarycond
    if not category or category in ('ADJACENT', 'AUTOBOUND'):
        return True
    if not autoadjacency or item.Hygrothermal:
        return False
    return category == 'EXTERNAL' or (category == 'BOUNDARY' and isMirrorBoundary(item))
def makeSurfacePiece(parent, points):
    """A copy of the parent surface with the geometry of one region; windows are hosted afterwards."""
    piece = copy.copy(parent)
    piece.Vertices = makeSurfaceVertices(points)
    piece.Surface = piece.Faces = makeSurfaceBrep(points, parent.Normalvector)
    piece.Area = vecDot(polyAreaVector(points), polyAreaVector(points))**0.5
    piece.Subsurface = []
    piece.Subsurfacedef = []
    piece.Sourcesurf = parent.Surfnum
    return piece
def loopHolds(points, inner, normal):
    """Whether the 3D loop inner lies within the 3D loop points of the same plane."""
    u, v = planeBasis(vecUnit(normal))
    outer2d = [(vecDot(point, u), vecDot(point, v)) for point in points]
    inner2d = [(vecDot(point, u), vecDot(point, v)) for point in inner]
    for i in range(len(inner2d)):
        a, b = inner2d[i], inner2d[(i+1) % len(inner2d)]
        for point in (a, ((a[0]+b[0])/2.0, (a[1]+b[1])/2.0)):
            if not pointInLoop2d(point, outer2d) and not pointOnLoop2d(point, outer2d, ADJACENCY_TOLERANCE):
                return False
    return True
def hostWindows(parent, pieces, issues):
    """Hands the windows of a split surface to the piece that holds them; the first piece is the biggest one."""
    for window in parent.Subsurfacedef:
        points = surfacePoints(window)
        host = None
        for piece in pieces:
            if loopHolds(surfacePoints(piece), points, pointTuple(parent.Normalvector)):
                host = piece
                break
        if host is None:
            addIssue(issues, 'error', "Window {0} crosses the line where surface {1} is split: move the window or split the wall yourself".format(window.Surfnum, parent.Surfnum), [parent, window])
            host = pieces[0]
        host.Subsurface.append(window.Surface)
        host.Subsurfacedef.append(window)
        host.Area = host.Area-window.Area
def wallLayers(name, walls):
    wall = walls.get(name)
    if wall is None:
        return None
    return list(zip(wall.Layers.split(), wall.Thickness.split()))
def frontOfPair(a, b):
    """(front surface, back surface, guessed). An explicit FRONT/BACK on either side decides, then the only side with an active layer (the
    deck defines a circuit for the airnode of its FRONT), then the only side with a construction (it lists its layers from its own side),
    then the floor (floor constructions list their layers from the walking surface down). Between walls the airnode that sorts first is
    the front: guessed."""
    if a.Frontback != b.Frontback and (a.Frontback or b.Frontback):
        if a.Frontback == 'FRONT' or b.Frontback == 'BACK':
            return a, b, False
        return b, a, False
    if (a.Activelayer != 0) != (b.Activelayer != 0):
        if a.Activelayer != 0:
            return a, b, False
        return b, a, False
    if bool(a.Construction) != bool(b.Construction):
        if a.Construction:
            return a, b, False
        return b, a, False
    if a.Type == 'FLOOR' or b.Type == 'FLOOR':
        if a.Type == 'FLOOR':
            return a, b, False
        return b, a, False
    front, back = sorted([a, b], key=lambda item: (item.Airnode, item.Surfnum))
    return front, back, True
def isSymmetric(layers):
    return layers == list(reversed(layers))
def matchConstructions(front, back, walls, issues):
    """Both sides of a pair end up with a construction: an empty side follows the other one; two constructions must be the same or mirrored."""
    if front.Type == 'ADDWINDOW':
        back.Construction = front.Construction
        return
    if back.Type == 'ADDWINDOW':
        front.Construction = back.Construction
        return
    if not front.Construction and not back.Construction:
        return
    if not front.Construction:
        layers = wallLayers(back.Construction, walls)
        if layers and not isSymmetric(layers):
            addIssue(issues, 'error', "Surface {0} is the FRONT of the pair but has no construction, and the construction {1} of surface {2} lists its layers from the other side: fill {3}".format(front.Surfnum, back.Construction, back.Surfnum, constructionSlot(front)), [front, back])
        front.Construction = back.Construction
        return
    if not back.Construction:
        back.Construction = front.Construction
    if front.Construction == back.Construction:
        layers = wallLayers(front.Construction, walls)
        if front.Frontguessed and layers and not isSymmetric(layers):
            addIssue(issues, 'warning', "Surfaces {0} & {1} have no FRONT/BACK of their own and the non-symmetric construction {2}: {0} is used as FRONT".format(front.Surfnum, back.Surfnum, front.Construction), [front, back])
        return
    frontlayers, backlayers = wallLayers(front.Construction, walls), wallLayers(back.Construction, walls)
    if frontlayers is None or backlayers is None or frontlayers != list(reversed(backlayers)):
        addIssue(issues, 'error', "Surfaces {0} & {1} are adjacent but have the different constructions {2} and {3}".format(front.Surfnum, back.Surfnum, front.Construction, back.Construction), [front, back])
def sumPoints(points):
    total = (0.0, 0.0, 0.0)
    for point in points:
        total = vecAdd(total, point)
    return total
def pairWindows(front, back, issues):
    """Windows in adjacent walls need a window on the other side at the same place."""
    remaining = list(back.Subsurfacedef)
    for window in front.Subsurfacedef:
        points = surfacePoints(window)
        centre = vecAdd((0.0, 0.0, 0.0), sumPoints(points), 1.0/len(points))
        partner = None
        for other in remaining:
            others = surfacePoints(other)
            othercentre = vecAdd((0.0, 0.0, 0.0), sumPoints(others), 1.0/len(others))
            offset = vecSub(centre, othercentre)
            parallel = vecDot(offset, vecUnit(pointTuple(front.Normalvector)))
            if vecDot(offset, offset)-parallel*parallel < ADJACENCY_TOLERANCE**2 and abs(window.Area-other.Area) < ADJACENCY_TOLERANCE*(window.Area**0.5):
                partner = other
                break
        if partner is None:
            addIssue(issues, 'error', "Window {0} is in the adjacent surface {1} but surface {2} has no window at the same place".format(window.Surfnum, front.Surfnum, back.Surfnum), [window])
            continue
        remaining.remove(partner)
        window.Adjsurf, partner.Adjsurf = partner.Surfnum, window.Surfnum
        window.Adjairnode, partner.Adjairnode = partner.Airnode, window.Airnode
        partner.Orientation = window.Orientation
        partner.Construction = window.Construction
    for window in remaining:
        addIssue(issues, 'error', "Window {0} is in the adjacent surface {1} but surface {2} has no window at the same place".format(window.Surfnum, back.Surfnum, front.Surfnum), [window])
def pairSurfaces(a, b, issues):
    """Makes two surfaces of one region adjacent. Returns (front, back) for the orientation that is shared at the end."""
    if a.Hygrothermal or b.Hygrothermal:
        addIssue(issues, 'error', "Surfaces {0} & {1} are adjacent but a HAMT surface can only be EXTERNAL or BOUNDARY".format(a.Surfnum, b.Surfnum), [a, b])
    front, back, guessed = frontOfPair(a, b)
    front.Frontguessed = guessed
    front.Frontback, back.Frontback = 'FRONT', 'BACK'
    front.Boundarycond = back.Boundarycond = 'ADJACENT'
    front.Adjsurf, back.Adjsurf = back.Surfnum, front.Surfnum
    front.Adjairnode, back.Adjairnode = back.Airnode, front.Airnode
    if back.Activelayer != 0 and front.Activelayer == 0:
        addIssue(issues, 'error', "Surface {0} has an active layer but is the BACK of the pair with surface {1}: make it the FRONT or leave FRONT/BACK empty".format(back.Surfnum, front.Surfnum), [front, back])
    if front.Activelayer != 0:
        back.Activelayer = front.Activelayer
        back.Intemp = front.Intemp
    if front.Coupling != 0 or back.Coupling != 0:
        front.Coupling = "INPUT 1*MF_{0}_{1}".format(back.Airnode, front.Airnode)
        back.Coupling = "INPUT 1*MF_{0}_{1}".format(front.Airnode, back.Airnode)
    for host in (front, back):
        for window in host.Subsurfacedef:
            window.Frontback = host.Frontback
            window.Boundarycond = 'ADJACENT'
    pairWindows(front, back, issues)
    if abs(front.Area-back.Area) > 0.01*max(front.Area, back.Area):
        addIssue(issues, 'warning', "Adjacent surfaces {0} & {1} differ in area: {2:.2f} and {3:.2f} m2".format(front.Surfnum, back.Surfnum, front.Area, back.Area), [front, back])
    return front, back
def fallbackBoundary(item, issues):
    """The boundary condition of a surface without a category and without a partner. Like the walls, a floor only has its height to go by."""
    if not FALLBACK_BOUNDARY:
        addIssue(issues, 'error', "Surface {0} of {1} has no boundary condition and no partner, and FallbackBoundary is off: set its Category".format(item.Surfnum, item.Airnode), [item])
        return
    below = max([point[2] for point in surfacePoints(item)]) <= GROUND_LEVEL + ADJACENCY_TOLERANCE
    if below and not item.Subsurfacedef and item.Type != 'ADDWINDOW':
        item.Boundarycond = 'BOUNDARY'
        item.Boundarytemp = GROUND_TEMPERATURE
        addIssue(issues, 'warning', "Surface {0} of {1} has no boundary condition and no partner, and lies at or below GroundLevel {2}: GROUND is used".format(item.Surfnum, item.Airnode, GROUND_LEVEL), [item])
    else:
        item.Boundarycond = 'EXTERNAL'
        if below and item.Subsurfacedef:
            addIssue(issues, 'warning', "Surface {0} of {1} lies at or below GroundLevel {2} but has a window: EXTERNAL is used".format(item.Surfnum, item.Airnode, GROUND_LEVEL), [item])
        elif item.Type == 'FLOOR':
            addIssue(issues, 'warning', "Floor surface {0} of {1} has no boundary condition and no surface below, and lies above GroundLevel {2}: EXTERNAL is used".format(item.Surfnum, item.Airnode, GROUND_LEVEL), [item])
def finishUnmatched(item, standalone, issues):
    """The boundary condition of a surface (or a part of one) that has no partner."""
    category = item.Boundarycond
    if category == 'ADJACENT' and standalone:
        item.Boundarycond = 'BOUNDARY'
        item.Boundarytemp = 'INPUT 1*TAIR_{0}'.format(item.Airnode)
    elif category == 'ADJACENT':
        addIssue(issues, 'error', "No adjacent surface found for surface {0} of {1}".format(item.Surfnum, item.Airnode), [item])
    elif category == 'AUTOBOUND':
        addIssue(issues, 'warning', "No opposite AUTOBOUND surface for surface {0}: BOUNDARY with the air temperature of {1} is used".format(item.Surfnum, item.Airnode), [item])
        item.Boundarycond = 'BOUNDARY'
        item.Boundarytemp = 'INPUT 1*TAIR_{0}'.format(item.Airnode)
    elif not category:
        fallbackBoundary(item, issues)
    for window in item.Subsurfacedef:
        window.Boundarycond = item.Boundarycond
def addFacingHints(unmatched, walls, gaptolerance, issues):
    """Hints for faces without a partner that do face a surface of another room within NEAR_MISS_DISTANCE."""
    cosine = math.cos(math.radians(1.0))
    for item in unmatched:
        points = surfacePoints(item)
        normal = vecUnit(pointTuple(item.Normalvector))
        u, v = planeBasis(normal)
        loop = [(vecDot(point, u), vecDot(point, v)) for point in points]
        for other in walls:
            if other.Airnode == item.Airnode or other is item:
                continue
            othernormal = vecUnit(pointTuple(other.Normalvector))
            otherpoints = surfacePoints(other)
            distance = abs(vecDot(vecSub(otherpoints[0], points[0]), normal))
            if vecDot(normal, othernormal) > -cosine or distance > NEAR_MISS_DISTANCE:
                continue
            otherloop = [(vecDot(point, u), vecDot(point, v)) for point in otherpoints]
            shared = [region for region in arrangePolygons([(0, loop), (1, otherloop)], ADJACENCY_TOLERANCE) if len(region['cover']) == 2]
            if not shared or sum([region['area'] for region in shared]) < 0.01:
                continue
            if distance > gaptolerance:
                addIssue(issues, 'warning', "Surface {0} of {1} has no partner but surface {2} of {3} is {4:.2f} m away: raise GapTolerance if they are one wall".format(item.Surfnum, item.Airnode, other.Surfnum, other.Airnode, distance), [item, other])
            else:
                addIssue(issues, 'warning', "Surface {0} of {1} faces surface {2} of {3}, which keeps its own {4}".format(item.Surfnum, item.Airnode, other.Surfnum, other.Airnode, other.Boundarycond), [item, other])
            break
def expandSurfaceOutputs(airnodes, splits):
    """Surface outputs of a split surface cover all of its pieces."""
    for airnode in airnodes:
        for output in airnode.Output or []:
            if output and output.Type == 'SURFACE':
                for number in list(output.SurfaceID):
                    for new in splits.get(number, ()):
                        if new not in output.SurfaceID:
                            output.SurfaceID.append(new)
                            for short in output.Ntype:
                                output.NtypesShort.append('{0}_S{1}'.format(short, new))
def resolveAdjacency(airnodes, autoadjacency, gaptolerance, standalone, issues):
    """Splits the surfaces that look for a partner along what faces them and sets their boundary conditions.

    A pair needs two surfaces of different airnodes with opposite normals in one plane. Returns the (front, back) pairs."""
    allnumbers = []
    participants = []
    others = []
    for airnode in airnodes:
        for item in airnode.Surfaces:
            allnumbers.append(item.Surfnum)
            if isWindowSurface(item) or isVirtualSurface(item):
                continue
            if surfaceParticipates(item, autoadjacency):
                participants.append(item)
            else:
                others.append(item)
    bynumber = dict([(item.Surfnum, item) for item in participants])
    regions = arrangeFaces([surfaceFace(item) for item in participants], ADJACENCY_TOLERANCE, gaptolerance)
    regionsof = {}
    regionpairs = {}
    for index, region in enumerate(regions):
        cover = region['cover']
        for key in cover:
            regionsof.setdefault(key, []).append(index)
        if len(cover) == 1:
            continue
        if len(cover) > 2 or region['sides'][cover[0]] == region['sides'][cover[1]]:
            addIssue(issues, 'error', "Surfaces {0} overlap on the same side of a wall: {1:.2f} m2".format(', '.join([str(key) for key in cover]), region['area']), [bynumber[key] for key in cover])
        elif bynumber[cover[0]].Airnode == bynumber[cover[1]].Airnode:
            addIssue(issues, 'warning', "Surfaces {0} & {1} of {2} face each other and are not coupled".format(cover[0], cover[1], bynumber[cover[0]].Airnode), [bynumber[key] for key in cover])
        else:
            regionpairs[index] = cover
    nextnumber = max(allnumbers or [0])+1
    pieces = {}
    splits = {}
    replaced = {}
    for key in sorted(regionsof):
        parent = bynumber[key]
        own = sorted(regionsof[key], key=lambda index: (-regions[index]['area'], index))
        if len(own) == 1:
            pieces[(key, own[0])] = parent
            continue
        chained = 'TOFL_S' in str(parent.Intemp) and parent.Activelayer != 0
        for airnode in airnodes:
            for item in airnode.Surfaces:
                chained = chained or 'TOFL_S{0}'.format(key) == str(item.Intemp).replace('INPUT 1*', '')
        if chained:
            addIssue(issues, 'error', "Surface {0} would be split but belongs to a serial active layer circuit: split it yourself".format(key), [parent])
        created = []
        for rank, index in enumerate(own):
            piece = makeSurfacePiece(parent, regions[index]['loops'][key])
            if rank > 0:
                piece.Surfnum = nextnumber
                splits.setdefault(key, []).append(nextnumber)
                nextnumber += 1
            pieces[(key, index)] = piece
            created.append(piece)
        if parent.Activelayer != 0 and not chained:
            for previous, piece in zip(created, created[1:]):
                piece.Intemp = 'INPUT 1*TOFL_S{0}'.format(previous.Surfnum)
            addIssue(issues, 'warning', "Active layer surface {0} was split: its pieces {1} are a serial circuit".format(key, ', '.join([str(piece.Surfnum) for piece in created])), created)
        hostWindows(parent, created, issues)
        replaced[key] = created
    for airnode in airnodes:
        surfaces = []
        for item in airnode.Surfaces:
            if item.Surfnum in replaced and item is bynumber.get(item.Surfnum):
                surfaces.extend(replaced[item.Surfnum])
            else:
                surfaces.append(item)
        airnode.Surfaces = surfaces
    expandSurfaceOutputs(airnodes, splits)
    pairs = []
    changed = []
    unmatched = []
    converted = {}
    for index in sorted(regionpairs):
        first, second = regionpairs[index]
        a, b = pieces[(first, index)], pieces[(second, index)]
        changed.extend([a, b])
        if a.Boundarycond == 'AUTOBOUND' and b.Boundarycond == 'AUTOBOUND':
            for item, other in ((a, b), (b, a)):
                item.Boundarycond = 'BOUNDARY'
                item.Bndairnode = other.Airnode
                item.Boundarytemp = 'INPUT 1*TAIR_{0}'.format(other.Airnode)
                for window in item.Subsurfacedef:
                    window.Boundarycond = 'BOUNDARY'
        elif a.Boundarycond == 'AUTOBOUND' or b.Boundarycond == 'AUTOBOUND':
            addIssue(issues, 'warning', "Surfaces {0} & {1} face each other but only one of them is AUTOBOUND".format(a.Surfnum, b.Surfnum), [a, b])
            finishUnmatched(a, standalone, issues)
            finishUnmatched(b, standalone, issues)
        else:
            for item in (a, b):
                if item.Boundarycond in ('EXTERNAL', 'BOUNDARY') and item.Construction:
                    converted.setdefault(item.Construction, []).append(item)
            pairs.append(pairSurfaces(a, b, issues))
    for construction in sorted(converted, key=str):
        items = converted[construction]
        addIssue(issues, 'warning', "Surfaces {0} were not declared adjacent but face another room: they keep the construction {1}, check that it suits an inner wall".format(', '.join(sorted(set([str(item.Surfnum) for item in items]))), construction), items)
    paired = [index for index in regionpairs]
    for key, index in sorted(pieces):
        if index not in paired:
            item = pieces[(key, index)]
            unmatched.append(item)
            changed.append(item)
            finishUnmatched(item, standalone, issues)
    for item in participants:
        if item.Surfnum not in regionsof:  # too small for any region
            unmatched.append(item)
            changed.append(item)
            finishUnmatched(item, standalone, issues)
    getSurfaceType(changed)
    allwalls = []
    for airnode in airnodes:
        allwalls.extend([item for item in airnode.Surfaces if not isWindowSurface(item) and not isVirtualSurface(item)])
    if not standalone:
        addFacingHints(unmatched, allwalls, gaptolerance, issues)
    return pairs
def constructionSlot(item):
    """The slot of a construction set for a surface with its final type and boundary condition."""
    exterior = item.Boundarycond in EXTERIOR_CATEGORIES
    ground = item.Boundarycond in ('BOUNDARY', 'EXTCALBND') and re.search(r'\bTsoil\b', str(item.Boundarytemp)) is not None
    if item.Type == 'FLOOR':
        if exterior:
            return 'ExposedFloor'
        if item.Boundarycond in ('ADJACENT', 'INTERNAL') or isMirrorBoundary(item):
            return 'InteriorFloor'
        return 'GroundFloor'
    if item.Type in ('ROOF', 'CEILING'):
        if exterior or ground:
            return 'Roof'
        return 'InteriorCeiling'
    if exterior or ground:
        return 'ExteriorWall'
    return 'InteriorWall'
def fillConstructions(airnodes, pairs, modelset, library, issues):
    """Gives the surfaces without a construction the one of their slot, from the set of the airnode and then from the set of the model. A
    surface whose partner has a construction follows that one. Matches the two sides of every pair afterwards."""
    walls = dict([(wall.Name, wall) for wall in library.Walls])
    following = []
    for front, back in pairs:
        if front.Construction:
            following.append(id(back))
        if back.Construction:
            following.append(id(front))
    filled = {}
    for airnode in airnodes:
        sets = [item for item in (airnode.Constructionset, modelset) if item is not None and not isFailure(item)]
        for item in airnode.Surfaces:
            if item.Construction or isWindowSurface(item) or isVirtualSurface(item) or item.Type == 'ADDWINDOW' or id(item) in following:
                continue
            slot = constructionSlot(item)
            for constructions in sets:
                name = getattr(constructions, slot, None)
                if name:
                    item.Construction = name
                    filled.setdefault((slot, name), []).append(item)
                    break
    for front, back in pairs:
        matchConstructions(front, back, walls, issues)
    for slot, name in sorted(filled):
        items = filled[(slot, name)]
        addIssue(issues, 'info', "Construction set: {0} = {1} on surfaces {2}".format(slot, name, ', '.join([str(item.Surfnum) for item in items])), items)
def subtractSurfaces(faces, explicit):
    """What remains of the faces of a solid when other surfaces lie on them. Returns ({number of a face with a surface on it: the 3D loops
    that remain}, [surfaces, or parts of them, beside the faces])."""
    if not explicit:
        return {}, []
    numbers = [item.Surfnum for item in faces]
    bynumber = dict([(item.Surfnum, item) for item in explicit])
    touched = []
    remaining = {}
    outside = []
    for region in arrangeFaces([surfaceFace(item) for item in list(faces)+list(explicit)], ADJACENCY_TOLERANCE, DEFAULT_GAP_TOLERANCE):
        own = [key for key in region['cover'] if key in numbers]
        others = [key for key in region['cover'] if key not in numbers]
        if not others:
            for key in own:
                remaining.setdefault(key, []).append(region['loops'][key])
        elif own:
            touched.extend(own)
        else:
            outside.extend([bynumber[key] for key in others if bynumber[key] not in outside])
    return dict([(key, remaining.get(key, [])) for key in touched]), outside
def setFailures(airnodes, modelset):
    """The messages of the construction sets that failed. Such a set stops the model: its surfaces must not go on without their defaults."""
    messages = []
    for airnode in airnodes:
        if isFailure(airnode.Constructionset):
            messages.append("Airnode {0}: {1}".format(airnode.Name, airnode.Constructionset.Message))
    if isFailure(modelset):
        messages.append("Multizone: {0}".format(modelset.Message))
    return messages
def hasActiveLayer(wall, library):
    """Whether a layer of the wall has pipes, the same test as in Lizard_Active_Layer_Surface."""
    active = [layer.Name for layer in library.Layers if layer.Pdiameter != '' or getattr(layer, 'Cc_pidiameter', '') != '']
    return True in [name in active for name in wall.Layers.split()]
def finalizeSurfaces(airnodes, library, pairs, issues, setfailed=False):
    """Fills what is still empty, checks that every surface can be written, and fills what is derived from the final values. A surface
    without a construction is not reported when a set has failed: that error says it already."""
    walls = dict([(wall.Name, wall) for wall in library.Walls])
    for airnode in airnodes:
        for item in airnode.Surfaces:
            if not item.Frontback:
                item.Frontback = 'FRONT'
            if isWindowSurface(item) or isVirtualSurface(item):
                continue
            if item.Hygrothermal:
                if item.Boundarycond == 'EXTERNAL':
                    item.Boundarycond = 'EXTCALEXT'
                elif item.Boundarycond == 'BOUNDARY':
                    item.Boundarycond = 'EXTCALBND'
            if not item.Boundarytemp:
                item.Boundarytemp = 'Identical'
            if item.Type == 'ADDWINDOW':
                continue
            if not item.Construction:
                if setfailed:
                    continue
                addIssue(issues, 'error', "Surface {0} of {1} ({2}, {3}) has no construction: set one on the surface or fill {4} in a construction set".format(item.Surfnum, item.Airnode, item.Type, item.Boundarycond, constructionSlot(item)), [item])
            elif item.Construction not in walls:
                addIssue(issues, 'error', "Surface {0} of {1}: construction {2} is not in the library".format(item.Surfnum, item.Airnode, item.Construction), [item])
            else:
                wall = walls[item.Construction]
                if item.Activelayer != 0 and not hasActiveLayer(wall, library):
                    addIssue(issues, 'error', "Surface {0} of {1} has an active layer but its construction {2} has none: set the construction before Lizard_Active_Layer_Surface".format(item.Surfnum, item.Airnode, item.Construction), [item])
                item.Uvalue = wall.Uvalue
                item.Abs_front = wall.Abs_front
                item.Abs_back = wall.Abs_back
                item.Wallthickness = sum([float(value) for value in wall.Thickness.split()])
    if True in [issue['level'] == 'error' for issue in issues]:
        return
    for airnode in airnodes:
        if airnode.Geosurffloor > 0:
            defineGeosurf(airnode.Geosurffloor, airnode.Surfaces)
    for front, back in pairs:
        back.Orientation = front.Orientation
def compileModel(airnodes, library, autoadjacency=False, gaptolerance=None, standalone=False, constructionset=None):
    """The one path from the airnodes to the surfaces the b18 writer reads, for System and for inspection.

    Works on the given airnodes (deep copies from callFromZones). Returns the issues: dicts with 'level' ('error', 'warning' or 'info'),
    'message' and 'surfaces'. With an error the surfaces are not complete and must not be written. AUTOMATIC is the same as an empty
    category: it only exists because an empty setting keeps the value of the surface.
    """
    issues = []
    if gaptolerance is None:
        gaptolerance = DEFAULT_GAP_TOLERANCE
    gaptolerance = max(float(gaptolerance), ADJACENCY_TOLERANCE)
    for airnode in airnodes:
        for item in airnode.Surfaces:
            item.Airnode = airnode.Name
            if item.Boundarycond == 'AUTOMATIC':
                item.Boundarycond = None
    failures = setFailures(airnodes, constructionset)
    for message in failures:
        addIssue(issues, 'error', message)
    pairs = resolveAdjacency(airnodes, autoadjacency, gaptolerance, standalone, issues)
    fillConstructions(airnodes, pairs, constructionset, library, issues)
    finalizeSurfaces(airnodes, library, pairs, issues, len(failures) > 0)
    return issues
INSPECT_GROUPS = ('External', 'Adjacent', 'Boundary', 'Mirror', 'Window', 'Other', 'Unresolved')
INSPECT_COLOURS = {'External': (66, 133, 200), 'Adjacent': (92, 170, 100), 'Boundary': (226, 142, 50), 'Mirror': (150, 105, 190),
                   'Window': (150, 215, 230), 'Other': (160, 160, 160), 'Unresolved': (214, 50, 50)}
INSPECT_COLUMNS = ('airnode', 'surface', 'source', 'type', 'group', 'category', 'temperature', 'construction', 'fromset', 'slot', 'frontback', 'partner', 'area')
def inspectGroup(item):
    """The group of a surface in the inspection, from its final boundary condition."""
    if isWindowSurface(item) or item.Type == 'ADDWINDOW':
        return 'Window'
    if isVirtualSurface(item):
        return 'Other'
    category = item.Boundarycond
    if not category or (category == 'ADJACENT' and not item.Adjsurf):
        return 'Unresolved'
    if category == 'ADJACENT':
        return 'Adjacent'
    if category in EXTERIOR_CATEGORIES:
        return 'External'
    if category in ('BOUNDARY', 'EXTCALBND') and isMirrorBoundary(item):
        return 'Mirror'
    if category in ('BOUNDARY', 'EXTCALBND', 'EXTFICALC', 'BNDCALC', 'AUTOBOUND'):
        return 'Boundary'
    return 'Other'
def inspectRow(airnode, item, group, filled):
    slot = ''
    if group != 'Window' and not isVirtualSurface(item):
        slot = constructionSlot(item)
    partner = ''
    if item.Adjsurf:
        partner = '{0}:{1}'.format(item.Adjairnode, item.Adjsurf)
    return {'airnode': airnode.Name, 'surface': item.Surfnum, 'source': item.Sourcesurf if item.Sourcesurf is not None else item.Surfnum, 'type': item.Type,
            'group': group, 'category': item.Boundarycond, 'temperature': item.Boundarytemp, 'construction': item.Construction, 'fromset': id(item) in filled,
            'slot': slot, 'frontback': item.Frontback, 'partner': partner, 'area': float(item.Area or 0.0)}
def inspectModel(airnodes, library, autoadjacency=False, gaptolerance=None, standalone=False, constructionset=None):
    """compileModel for looking at the result, also when it has errors. Works on the given airnodes (deep copies from callFromZones).

    Returns a dict: 'airnodes' (names), 'groups' {group: one list of surfaces per airnode}, 'rows' (one dict per surface), 'summary' and 'issues'."""
    issues = []
    if standalone:
        for airnode in airnodes:
            issues.extend(compileModel([airnode], library, autoadjacency, gaptolerance, True, constructionset))
    else:
        issues = compileModel(airnodes, library, autoadjacency, gaptolerance, False, constructionset)
    filled = []
    for issue in issues:
        if issue['level'] == 'info':
            filled.extend([id(item) for item in issue['surfaces']])
    groups = dict([(group, [[] for airnode in airnodes]) for group in INSPECT_GROUPS])
    rows = []
    for index, airnode in enumerate(airnodes):
        for item in airnode.Surfaces:
            group = inspectGroup(item)
            groups[group][index].append(item)
            rows.append(inspectRow(airnode, item, group, filled))
    summary = []
    for group in INSPECT_GROUPS:
        own = [row for row in rows if row['group'] == group]
        if own:
            summary.append('{0}: {1} surfaces, {2:.2f} m2'.format(group, len(own), sum([row['area'] for row in own])))
    return {'airnodes': [airnode.Name for airnode in airnodes], 'groups': groups, 'rows': rows, 'summary': summary, 'issues': issues}
def inspectTable(rows):
    """Tab-separated lines with a header, for a panel or a spreadsheet."""
    lines = ['\t'.join([column.capitalize() for column in INSPECT_COLUMNS])]
    for row in rows:
        values = []
        for column in INSPECT_COLUMNS:
            if column == 'area':
                values.append('{0:.2f}'.format(row[column]))
            elif row[column] is None:
                values.append('')
            else:
                values.append(str(row[column]))
        lines.append('\t'.join(values))
    return lines
# ---- Surface model (end)
def surfaceNormal(brep):
    """Normal of the single face of a surface as Rhino shows it: a face can be flipped against its underlying surface. It is read from that
    surface, because the docs do not say whether BrepFace.NormalAt already includes the flag, and in the middle of it: (0,0) can lie outside."""
    face = brep.Faces[0]
    surface = face.UnderlyingSurface()
    normal = surface.NormalAt(surface.Domain(0).Mid, surface.Domain(1).Mid)
    if face.OrientationIsReversed:
        normal.Reverse()
    return normal
def makeSurfaceVertices(points):
    return [rc.Geometry.Point3d(point[0],point[1],point[2]) for point in points]
def makeSurfaceBrep(points, normal):
    curve = rc.Geometry.Polyline(makeSurfaceVertices(list(points)+[points[0]])).ToNurbsCurve()
    brep = rc.Geometry.Brep.CreatePlanarBreps(curve,ADJACENCY_TOLERANCE)[0]
    if rc.Geometry.Vector3d.Multiply(surfaceNormal(brep),normal) < 0:
        brep.Flip()
    return brep
def upstreamErrors(component, level):
    """The errors of everything upstream of a component, as 'name: message'. A component in error leaves its output empty, which looks
    like nothing connected, also behind a merge. level = GH_RuntimeMessageLevel.Error."""
    found = []
    seen = set([component.InstanceGuid])
    stack = [component]
    while stack:
        current = stack.pop()
        if current is not component:
            for message in current.RuntimeMessages(level):
                found.append("{0}: {1}".format(current.NickName, message))
        inputs = [current]
        if hasattr(current, 'Params'):
            inputs = current.Params.Input
        for param in inputs:
            for source in param.Sources:
                owner = source.Attributes.GetTopLevel.DocObject
                if owner.InstanceGuid not in seen:
                    seen.add(owner.InstanceGuid)
                    stack.append(owner)
    return found
def requireInputs(component, names):
    """Stop a script with an error when one of its required inputs has no data. Lizard_Updater writes the call into the script, with
    the names of the Required: True inputs of its docstring."""
    missing = [str(param.Name) for param in component.Params.Input if str(param.Name) in names and param.VolatileDataCount == 0]
    if missing:
        component.AddRuntimeMessage(gh.GH_RuntimeMessageLevel.Error, "Required input without data: " + ", ".join(missing))
        sys.exit()
def solidFaces(solid):
    """The faces of a room solid as single-face Breps with outward normals. Returns (faces, problem)."""
    brep = solid.DuplicateBrep()
    brep.MergeCoplanarFaces(abs_tolerance)
    if not brep.IsSolid:
        return [], "The Brep with {0} faces given to the airnode is not a closed solid".format(brep.Faces.Count)
    if brep.SolidOrientation == rc.Geometry.BrepSolidOrientation.Inward:
        brep.Flip()
    faces = []
    for face in brep.Faces:
        if not face.IsPlanar(abs_tolerance):
            return [], "The solid has a curved face: rebuild it from planar faces"
        if face.Loops.Count > 1:
            return [], "The solid has a face with a hole: split that face first, a surface of the b18 has one loop of vertices"
        faces.append(face.DuplicateFace(False))
    return faces, None
def flipSurfaceBreps(item):
    item.Faces.Flip()
    if item.Surface is not item.Faces:
        item.Surface.Flip()
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
        collection = sc.sticky[sc.doc.Path]['Const_coll']
        for obj_items in range(len(Brep)):
            # the copy takes the new LID: the output of the upstream component keeps its own
            geometry = Brep[obj_items].DuplicateBrep()
            parent = None
            if geometry.UserDictionary.ContainsKey('LID'):
                parent = collection.get(geometry.UserDictionary['LID'])
            if parent is not None:
                # later settings go on top of the ones this surface already has
                record = copy.copy(parent)
                record.Surface = geometry
            else:
                record = sc.sticky[sc.doc.Path]["GEOMETRY"](geometry)
            record.Faces           = geometry
            record.Area            = geometry.GetArea()
            ori_normal             = surfaceNormal(geometry)
            record.Vertices        = getSurfaceVertices(ori_normal,geometry)
            record.Normalvector    = ori_normal
            if len(record.Vertices) > 4:
                record.Vertices = cleanVertices(record.Vertices)
            record.Vertices = checkVerticesOrder(record.Vertices, ori_normal)
            box = geometry.GetBoundingBox(False)
            lizkey = '{0}:{1}:{2}:{3}'.format(GHComponentID, obj_items, box.Min, box.Max)
            if parent is not None:
                record.Surfnum = parent.Surfnum
            elif lizkey in collection:
                record.Surfnum = collection[lizkey].Surfnum
            else:
                sc.sticky[sc.doc.Path]['Surface_Counter'] = sc.sticky[sc.doc.Path]['Surface_Counter'] + 1
                record.Surfnum = sc.sticky[sc.doc.Path]['Surface_Counter']
            collection[lizkey] = record
            geometry.UserDictionary.Set('LID', lizkey)
            geometry.UserDictionary.Set('ID', record.Surfnum)
            geometries.append(geometry)
        return geometries
    def expandSolids(self, breps, GHComponentID):
        """The input of an airnode as surfaces. What comes from a surface component stays, a bare face is registered, and a solid becomes
        its faces (no boundary condition, no construction) without the parts covered by the other surfaces. Returns (breps, problem)."""
        surfaces = []
        bare = []
        solids = []
        for brep in breps:
            if brep.UserDictionary.ContainsKey('LID'):
                surfaces.append(brep)
            elif brep.Faces.Count > 1:
                solids.append(brep)
            else:
                bare.append(brep)
        if len(solids) > 1:
            return [], "An airnode takes one solid, {0} were connected".format(len(solids))
        surfaces.extend(self.addToConstruction(bare, GHComponentID + ':face'))
        if not solids:
            return surfaces, None
        faces, problem = solidFaces(solids[0])
        if problem:
            return [], problem
        facebreps = self.addToConstruction(faces, GHComponentID + ':solid')
        records = self.callFromConstruction(facebreps)
        explicit = [item for item in self.callFromConstruction(surfaces) if not isWindowSurface(item) and not isVirtualSurface(item) and item.Type != 'ADDWINDOW']
        pieces, outside = subtractSurfaces(records, explicit)
        if outside:
            return [], "Surfaces {0} do not lie on a face of the solid".format(', '.join([str(item.Surfnum) for item in outside]))
        for brep, record in zip(facebreps, records):
            if record.Surfnum in pieces:
                loops = pieces[record.Surfnum]
                surfaces.extend(self.addToConstruction([makeSurfaceBrep(loop, record.Normalvector) for loop in loops], '{0}:piece:{1}'.format(GHComponentID, record.Surfnum)))
            else:
                surfaces.append(brep)
        return surfaces, None
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
                    if not sc.sticky[sc.doc.Path]['Const_coll'][key].Construction:
                        continue
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
        """Writes the settings on the surfaces. An empty setting keeps the value the surface already has."""
        if dataclass is None:
            return
        for gitem in geometry:
            key = gitem.UserDictionary['LID']
            if not sc.sticky[sc.doc.Path]['Const_coll'].has_key(key):
                continue
            record = sc.sticky[sc.doc.Path]['Const_coll'][key]
            datadict = vars(dataclass)
            for name, value in datadict.items():
                if name == 'Boundarytemp':
                    continue
                if value is None or value == '':
                    if not hasattr(record, name):
                        setattr(record, name, value)
                elif name == 'Construction' and 'WIN_' in value:
                    record.Construction = value + '_' + getWinOrientation(gitem)
                else:
                    setattr(record, name, value)
            temperature = datadict.get('Boundarytemp')
            if temperature:
                if not re.search('^-?\\d', str(temperature)):
                    appendtxt = ''
                    if record.Boundarycond == 'EXTFICALC':
                        appendtxt = record.Surfnum
                    temperature = 'INPUT 1*{0}'.format(temperature + str(appendtxt))
                record.Boundarytemp = temperature
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
    new_normal = surfaceNormal(new_srf)
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
        facenormal = item.Normalvector
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
        facenormal = surfaceNormal(item)
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
    facenormal = surfaceNormal(items)
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
if 'GroundLevel' in locals() and GroundLevel != None:
    GROUND_LEVEL = float(GroundLevel)
if 'FallbackBoundary' in locals() and FallbackBoundary != None:
    FALLBACK_BOUNDARY = bool(FallbackBoundary)
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
sc.sticky[sc.doc.Path]["compileModel"]       = compileModel
sc.sticky[sc.doc.Path]["orientSurfaces"]     = orientSurfaces
sc.sticky[sc.doc.Path]["ComponentFailure"]   = ComponentFailure
sc.sticky[sc.doc.Path]["isFailure"]          = isFailure
sc.sticky[sc.doc.Path]["setFailures"]        = setFailures
sc.sticky[sc.doc.Path]["upstreamErrors"]     = upstreamErrors
sc.sticky[sc.doc.Path]["requireInputs"]      = requireInputs
sc.sticky[sc.doc.Path]["inspectModel"]       = inspectModel
sc.sticky[sc.doc.Path]["inspectTable"]       = inspectTable
sc.sticky[sc.doc.Path]["INSPECT_GROUPS"]     = INSPECT_GROUPS
sc.sticky[sc.doc.Path]["INSPECT_COLOURS"]    = INSPECT_COLOURS
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
sc.sticky[sc.doc.Path]["CRACKS"]             = CRACKS
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


