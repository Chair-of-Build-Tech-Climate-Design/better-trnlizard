"""
Thermal simulation project manager component. Use switches to re-write building and system files, and run the simulation.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.
-

Args:
    Reload (object): set this to true if information in the library is changing or the template of the dck
        Access: item
        Required: True
    ReportTemplate (object): Script variable Thermal System
        Access: item
        Required: True
    DckTemplate (object): this definition is used in order to replace the @variables with the information given in the variables dict
        Access: list
        Required: True
    Multizone (object): connect the output from the Multizone component
        Access: item
        Required: True
    WriteSimulationFiles (object): generating simulation files
        Access: item
        Required: True
    RunDaylightPreprocessing (object): this launches the daylight coefficient generation
        Access: item
        Required: True
    RunThermalPreprocessing (object): this launches the matrices generation
        Access: item
        Required: True
    RunThermalSimulation (object): this launches the matrices generation followed by the TRNEXE
        Access: item
        Required: True
    SimTimestep (object): define the simulation time step
        Access: item
        Required: True
    SimTolerance (object): Script variable Thermal System
        Access: item
        Required: True
    SimMaxIteration (object): Script variable Thermal System
        Access: item
        Required: True
    SimMaxWarning (object): Script variable Thermal System
        Access: item
        Required: True
    StartDay (object): first day of simulation time
        Access: item
        Required: True
    StartMonth (object): first month of simulation time
        Access: item
        Required: True
    StopDay (object): last day of simulation time
        Access: item
        Required: True
    StopMonth (object): last month of simulation time
        Access: item
        Required: True
    UserEquations (object): define Equations that will be directly written in the dck file
        Access: list
        Required: True
    UserOutputs (object): define Variables that will be directly plotted in the dck file
        Access: list
        Required: True
    ResFocusAirnode (object): link the Airnode name for that you want to show details in the Online Plotter. Only one name can be linked.
        Access: item
        Required: True
    SystemComponents (object): Script variable Thermal System
        Access: list
        Required: True
    t395_udepth (object): Script variable Thermal System
        Access: item
        Required: True
    t395_udivnum (object): Script variable Thermal System
        Access: item
        Required: True
    ShowPlotter (bool): True or not connected = draw the TRNSYS online plotters (Type65) while the simulation runs; False = keep them hidden (faster, for batch runs)
        Access: item
        Required: False

Returns:
    out (object): Log Information!!!
        Access: item
    Variant (object): simulation output files - connect to output component for visualization of results
        Access: item
    start_time (object): Script variable Thermal System
        Access: item
"""
#Changes:
"""
sherb
CSH_220427 |
compatibility with Trnsys 18_04 (internal W: drive):
-the values for the variables _distBaseSrf,_gridSize are specified by the user as input
into the Multizone Componentand passed as sticky variables so they can be printed into the BUI File
other changes:
-delete matrices that are to be generated in solar folde before starting trnRaytrace
to avoid copy of old matrices when trnRaytrace fails
-rad and pts file paths are written in Data Tree for component output (can be used for display of file)

CSH_220426 |
-only copy the generted ipm to b18 foldler not all files with .ipm extension
-check if ipm already existis in b18 folder and delete before renaming to avoid windows error|

CSH_220420 |
for trnRaytrace standalone compatibility:
-added zone ID to pts and inf file name
-added distance to base in srf inf file
other changes:
-added pts file name as funtion return value (ReadRadFile) to pass to trnraytrace as input arg
-only copy the generted shm to b18 foldler not all files with .shm extension
-Renamed OC Matrix genertaion from: runRtracexxxx to RuntrnRaytracexxxx|
[Test Updater]
"""
import rhinoscriptsyntax as rs
import re
import ghpythonlib.parallel
import scriptcontext as sc
import os
import math
import os.path
from subprocess import Popen
import time
import glob
import shutil
from collections import defaultdict
import Grasshopper.Kernel as gh
import sys
import copy
import System
import Rhino as rc
from operator import attrgetter
from itertools import chain
import System.Threading.Tasks as tasks
from Grasshopper import DataTree #CSH_220427
import operator
from datetime import datetime



start_time = datetime.now()
version = sc.sticky[sc.doc.Path]["version"]
date = sc.sticky[sc.doc.Path]["date"]
version = '2.4.0 (HAMT multi-surface)'
ghenv.Component.Name = "Lizard_System"
ghenv.Component.NickName = 'Thermal System'
ghenv.Component.Message = 'VER %s\n%s'%(version,date)
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "0 | Project"
w = gh.GH_RuntimeMessageLevel.Warning
err = gh.GH_RuntimeMessageLevel.Error
project_folder          = sc.sticky[sc.doc.Path]["Project_folder"].decode('utf-8')
project_variants_folder = sc.sticky[sc.doc.Path]["Project_variants_folder"].decode('utf-8')
variants_folder         = sc.sticky[sc.doc.Path]["Variants_folder"].decode('utf-8')
if 'Subfolder' in locals() and Subfolder:
    variants_folder += Subfolder + '\\'
#results_folder          = sc.sticky[sc.doc.Path]["Results_folder"].decode('utf-8')
project_name            = sc.sticky[sc.doc.Path]["Project_name"].decode('utf-8')
TRNSYS_path             = sc.sticky[sc.doc.Path]["Trnsys_folder"].decode('utf-8')
variant_name            = sc.sticky[sc.doc.Path]["Short_name"].decode('utf-8')
long_variant_name       = sc.sticky[sc.doc.Path]["Long_name"].decode('utf-8')
weather_file            = sc.sticky[sc.doc.Path]["Weather_file"].decode('utf-8')
timing                  = sc.sticky[sc.doc.Path]["timing"]
library                 = sc.sticky[sc.doc.Path]["library"]
build_mode              = sc.sticky[sc.doc.Path]["Build_mode"]
exe_mode                = sc.sticky[sc.doc.Path]["Exe_mode"]
#bui_file_base = sc.sticky[sc.doc.Path]["BUI_FILE"]
TRNSYS = sc.sticky[sc.doc.Path]["TRNSYS"]
getInputs           = sc.sticky[sc.doc.Path]["getInputs"]
checkAdjacent       = sc.sticky[sc.doc.Path]["checkAdjacent"]
findMaxSurfNum      = sc.sticky[sc.doc.Path]["findMaxSurfNum"]
library             = sc.sticky[sc.doc.Path]["library"]
hemisphere          = sc.sticky[sc.doc.Path]["Hemisphere"]

#buioutput, okey = sc.sticky[sc.doc.Path]["BUI_OUTPUT"]
#additional parameters
PrintJobList = False
ReUseMatrices = 0
UseMatricesFromGH = 0
reuse_shm_ism_ipm = ReUseMatrices
PrintReport = 1
TemplateReport = ReportTemplate
UdefPathDaylightRes = None
UseDaylightSim = 0
GridSize = 0.1
RunVFM = 0
if "PrintSingleSimFiles" in locals():
    RunSingleAirnodes = int(PrintSingleSimFiles)
else:
    RunSingleAirnodes = 0

Online = 0   #Type65 online plotters (deck constant showonline): 0 = shown, -1 = hidden. Input ShowPlotter: True or not connected = shown, False = hidden (faster batch runs)
if "ShowPlotter" in locals() and ShowPlotter is not None and str(ShowPlotter).strip().lower() in ("false", "0", "no", "off"):
    Online = -1
Turn = 0
#SystemComponents = [] #define as list input object
WriteDaylightGrid = 1
addoutstep = 1 #SimTimestep change this value if you want to have shorter plotting intervals for AddOutput results file
#additional parameters
#see if Results folder exists and if not generate it

if 'trnRaytraceShadingState' in locals() and trnRaytraceShadingState is not None:
    pass
else:
    trnRaytraceShadingState = 0
if 'StandardOutputs' in locals():
    pass
else:
    StandardOutputs = 1

rem = gh.GH_RuntimeMessageLevel.Remark
bla = gh.GH_RuntimeMessageLevel.Blank
warn = gh.GH_RuntimeMessageLevel.Warning
errorfound = 0
dummyMulti = copy.deepcopy(Multizone)


def checkTreeSurfaceOrientation(Airnodeinfo):
    for Airnode in Airnodeinfo:
        print '*'*20
        print Airnode
        surfaces = [x for x in Airnode.Surfaces if x.Construction=='WOOD']
        windows = [x for x in Airnode.Surfaces if 'TREE' in x.Construction]
        print 'Tree surfaces: %s' %len(surfaces)
        print 'Tree windows: %s' %len(windows)

        if len(surfaces) and len(windows) and len(surfaces)==len(windows):
            for i,s in enumerate(surfaces):
                print '-'*20
                print 'SURFACE %s' %i
                print s.Surfnum
                print s.Type
                print s.Construction
                print s.Orientation
                print s.Normalvector
                print 'WINDOW %s' %i
                print windows[i].Surfnum
                print windows[i].Construction
                print windows[i].Orientation
                print windows[i].Normalvector
#@Mark:add Radmaterial to constructions and windows
def addRadmaterial(subitems):
    global AddDaylightGeometry
    daylightgeometry_area = [ghcomp.Area(x)[0] for x in AddDaylightGeometry]
    daylightgeometry_centroid = [ghcomp.Area(x)[1] for x in AddDaylightGeometry]
    for a,c,s in zip(daylightgeometry_area,daylightgeometry_centroid,AddDaylightGeometry):
        if ghcomp.Area(subitems.Surface)[0]==a and ghcomp.Area(subitems.Surface)[1]==c:
            subitems.Radmaterial0 = s.UserDictionary['MAT']
            subitems.Radmaterial1 = s.UserDictionary['MAT']
    return subitems
# @OC END
def getparagraph(file,startpattern,stoppattern):
    output = []
    inparagraph = 'FALSE'
    lines=file
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
# this routine collects the available names that matched the searchpattern
def getdata(search_pattern,dataset,index,linecounter,column):
    data_get=dataset
    output = []
    for searchline in range(len(data_get)):
        search_data=re.search(r'{0}'.format(search_pattern),data_get[searchline])
        if search_data is not None:
            data=data_get[searchline+linecounter].replace('=',' ')
            data=data.split( )
            found_it = 0
            for data_dummy in range(len(data)):
                searchdata=re.search(r'^{0}'.format(index),data[data_dummy])
                if searchdata:
                    output.append(data[data_dummy + column])
                    found_it = 1
            if found_it == 0:
                output.append('')
    return output

def printtype9(Filename, dataarr):
    template = """
UNIT @self.Unitno TYPE 9	 @self.Name
*$UNIT_NAME 1 hour data
*$MODEL .\Utility\Data Readers\Generic Data Files\First Line is Simulation Start\Free Format\Type9a.tmf
*$POSITION 233 136
*$LAYER Weather - Data Files #
PARAMETERS 10
2		! 1 Mode
0		! 2 Header Lines to Skip
1		! 3 No. of values to read
1		! 4 Time interval of data
1		! 5 Interpolate or not?
1		! 6 Multiplication factor
0		! 7 Addition factor
1		! 8 Average or instantaneous value
@self.Lunitno 		! 9 Logical unit for input file
-1		! 10 Free format mode
*** External files
ASSIGN "@self.Filename" @self.Lunitno
*|? Input file name |1000

EQU @self.Loutarr
@self.Outarr
"""
    class TYPE:
        def __init__(self):
            """Class initialization"""
            self.Name = "DATAREADER"
            self.Unitno = 999
            self.Lunitno = 999
            self.Template = template
            self.Filename = Filename
            self.Uuid = ghenv.Component.InstanceGuid.ToString()
            self.Laxis = 0
            self.Label1 = 0
            self.Loutarr = 1
            self.Outarr = "%s = [999,%s]"%(dataarr[0],1)
        def fillTemplate(self):
            linedefinition=self.Template
            for attr, value in self.__dict__.iteritems():
                linedefinition=linedefinition.replace('@self.{0}'.format(attr), str(value))
            return linedefinition
        def __repr__(self):
            """Class representation."""
            return "{}:{}".format(self.__class__.__name__, self.Name)

    Type = TYPE()
    return Type.fillTemplate(), Type.Unitno

#print printtype9("TEST",["MFDHW"])[0]

def convertTry2017ETRS892WSG84(rval,uval):
    x_in = float(rval)
    y_in = float(uval)
    N_ITER = 15
    tol = 1.0E-10
    x_0 = 4000000
    y_0 = 2800000
    r_a = 1.56785594288739E-07
    rho_0 = 0.76847187042176
    e = 0.0818191910428157
    Q_c = 1.74933347569811
    Q_n = 0.775381599875433
    lambda_0 = 0.174532925199432
    Pi = 4*math.atan(1)
    # deoffset - descale
    x = (x_in-x_0)*r_a
    y = (y_in-y_0)*r_a
    # another deoffset
    y = rho_0 - y
    rho = (x**2 + y**2)**0.5
    # kind of factor
    ts = (rho/Q_c)**(1/Q_n)
    #first guess of phi
    phi = Pi/2-2*math.atan(ts)
    #iteration to correct phi
    eccnth = 0.5 * e
    i = 0
    dphi = 1 #inital value
    while ((i<N_ITER) and abs(dphi) > tol):
        con = e * math.sin(phi)
        dphi = Pi/2 - 2 * math.atan(ts * ((1 - con)/(1 + con))**eccnth) - phi
        phi = phi + dphi
        i = i + 1
    if(i>N_ITER):
        pass
        #error message iteration of lat not converged within N_ITER
    dlambda = math.atan2(x,y) / Q_n
    dlambda = dlambda + lambda_0
    long = dlambda * 180 / Pi
    lat = phi * 180 / Pi
    return str(-1*long),str(lat)

@timing
def printbui():
        buiout = open(variants_folder + variant_name + '.b%s'%TRNSYS, 'w')
        for lines in bui_file:
            lines = lines.replace('\r', '')    # remove '\n' only
            buiout.write(lines)
        buiout.close()
#this function runs through the generated bui file and replaces an argument
@timing
def printbuisingledata(data_collection, search_attr, replacing):
    datastorage = ''
    for item in data_collection:
        linedefinition=item
        linedefinition=linedefinition.replace('@{0}'.format(search_attr), str(replacing))
        datastorage = datastorage + linedefinition
    return datastorage
@timing
def printheader(text_string):
    sep_line = '*--------------------------------------------------------------------------------\n'
    return [sep_line,'*  ' + text_string + '\n',sep_line]
# ---- thermal mirror walls (begin)
# Thermal (Type 56 only) variants: a BOUNDARY wall whose boundary temperature is the own airnode's TAIR (mirror neighbour room)
# gets the back film that side 2 of the Type 395 walls (EXTCALBND, option A, implicit form) has: interior convective film plus the
# linearised longwave exchange with the room, in ONE coefficient (hconv2 of the e7 handler at T_ref).  HBACK of a BOUNDARY wall is
# ONE combined coefficient (TRNBuild manual 5.2.7.2, BOUNDARY TEMPERATURE: a combined coefficient when the boundary temperature is an
# air temperature) and Type 56 adds no longwave exchange on the back of a BOUNDARY wall (5.4.1.11), so both parts are added:
#   11 kJ/(h m2 K) + 4 * 2.041e-7 * 0.9 * 293.15^3 kJ/(h m2 K) = 29.51 kJ/(h m2 K)   (8.2 W/(m2 K); the library default 64 is 17.8)
# The library default HBACK 64 is the exterior convention and cannot be told from "never set"; any other explicit value, also a
# keyword such as VERTICAL, is kept.  HBACK belongs to the WALL type and is shared with the exterior wall (which needs 64), so the
# mirror walls get a derived wall type <name>_MIRROR that is written only when a mirror wall needs it.  EXTERNAL, ADJACENT,
# non-mirror BOUNDARY walls, the HAMT pseudo-walls (<construction>_HAMT, HIGH_COND, HIGH_RES) and all other categories are not touched.
MIRROR_HCONV_INTERIOR = 11.0      # kJ/(h m2 K), same value as t395_hconv_interior in the e7 handler
MIRROR_HBACK_DEFAULT = 64         # kJ/(h m2 K), library default HBACK, same as t395_hconv_back_default in the e7 handler
MIRROR_EPS = 0.9                  # same emissivity as t395_eps_side2 in the e7 handler
MIRROR_SIGMA = 2.041e-07          # kJ/(h m2 K4), same literal as SIGMA_S@surface in Lizard_DCK_Template.py
MIRROR_TREF_K = 293.15            # 20 C, reference temperature of the linearised longwave film (RTEMP of the b18), same value as t395_tref_k in the e7 handler
MIRROR_SUFFIX = '_MIRROR'
MIRROR_NAME_MAX = 32              # confirmed 2026-10-02: TRNBuild accepts it, and a Type 56 run with HHL_Wall_Gipskartonplatte_MIRROR (32) gave results identical to the 25-character name
def mirror_hback_value():
    """Combined back film of a mirror wall [kJ/(h m2 K)]: interior convective film plus the linearised longwave film."""
    return round(MIRROR_HCONV_INTERIOR + 4 * MIRROR_SIGMA * MIRROR_EPS * MIRROR_TREF_K ** 3, 2)
def is_default_hback(value):
    """True for the library default HBACK in any numeric spelling; an explicit value, a keyword such as VERTICAL or anything else is False."""
    try:
        return abs(float(value) - MIRROR_HBACK_DEFAULT) <= 1e-9
    except (TypeError, ValueError):
        return False
def is_mirror_boundary_surface(surface, airnode_name):
    """BOUNDARY surface whose boundary temperature is the own airnode's TAIR (the mirror test of EXTCALBND in the e7 handler)."""
    if surface.Boundarycond != 'BOUNDARY':
        return False
    tbound = str(surface.Boundarytemp).split('*')[-1].replace('@ANAME', str(airnode_name))
    return tbound.strip().upper() == 'TAIR_' + str(airnode_name).upper()
def mirror_type_name(original, taken, max_len=None):
    """<original>_MIRROR within the name limit, shortened and numbered where needed so that it is not in ``taken`` (lower case names)."""
    if max_len is None:
        max_len = MIRROR_NAME_MAX
    original = str(original)
    candidate = original[:max(1, max_len - len(MIRROR_SUFFIX))] + MIRROR_SUFFIX
    counter = 0
    while candidate.lower() in taken:
        counter += 1
        tail = str(counter)
        candidate = original[:max(1, max_len - len(MIRROR_SUFFIX) - len(tail))] + tail + MIRROR_SUFFIX
    return candidate
def plan_thermal_mirror_walls(dataset, wall_items):
    """({construction name: derived wall type name}, [(surface number, airnode name, construction name)]) of the thermal mirror walls.
    Pure function of the airnodes and the wall library, so the wall type definitions and the zone wall lines agree."""
    walls = {}
    taken = []
    for wall_item in wall_items:
        walls[wall_item.Name] = wall_item
        taken.append(str(wall_item.Name).lower())
    names = {}
    affected = []
    for airnode in dataset:
        for surface in airnode.Surfaces:
            if 'Virtual' in str(surface.Construction):
                continue
            if not is_mirror_boundary_surface(surface, airnode.Name):
                continue
            wall_item = walls.get(surface.Construction)
            if wall_item is None or not is_default_hback(wall_item.Hback):
                continue
            affected.append((surface.Surfnum, airnode.Name, surface.Construction))
            names[surface.Construction] = None
    for original in sorted(names):
        names[original] = mirror_type_name(original, taken)
        taken.append(names[original].lower())
    return names, affected
def derive_mirror_wall(wall_item, name):
    """Copy of a library wall type with the mirror back film; the shared library object itself is never modified."""
    derived = copy.copy(wall_item)
    derived.Name = name
    derived.Hback = mirror_hback_value()
    return derived
def mirror_wall_message(names, affected):
    """Runtime message that lists the walls which got a derived mirror wall type."""
    groups = []
    for original in sorted(names):
        numbers = ['%s (%s)' % (number, airnode) for (number, airnode, construction) in affected if construction == original]
        groups.append('%s (copy of %s): surface %s' % (names[original], original, ', '.join(numbers)))
    return ('Thermal mirror walls (BOUNDARY = own TAIR): the library default HBACK %g was replaced by %.2f kJ/(h m2 K) = %g convective + %.2f longwave, '
            'like side 2 of the Type 395 (EXTCALBND) walls. Wall types: %s. EXTERNAL, ADJACENT, non-mirror and HAMT walls are unchanged; '
            'an explicit H_Back other than %g in the construction is kept.'
            % (MIRROR_HBACK_DEFAULT, mirror_hback_value(), MIRROR_HCONV_INTERIOR, mirror_hback_value() - MIRROR_HCONV_INTERIOR,
               '; '.join(groups), MIRROR_HBACK_DEFAULT))
# ---- thermal mirror walls (end)
# ---- HAMT pseudo-walls (begin)
# A Type 395 (HAMT) surface (EXTCALEXT, EXTCALBND) is written as a pseudo-wall of high conductance whose boundary temperature is the
# Type 395 surface temperature (BOUNDARY = INPUT 1*TSI395_S<n>).  Its FRONT side is the room side of the real wall: Type 56 computes
# HCONVI (beta1 of Type 395) and REQV (hconv1 of Type 395) of the surface with HFRONT, ABS-FRONT and EPS-FRONT of the wall type the
# surface uses.  These films must therefore be the ones of the surface's own construction (Lizard_Construction, chosen in the Surface
# Settings).  The single library wall HIGH_COND used before was overwritten construction by construction, so every HAMT surface got
# the films of the construction handled last.  Now every construction used by a HAMT surface gets its own pseudo-wall type
# <construction>_HAMT: a copy of the library HIGH_COND (layer DIRECT) with HFRONT, ABS-FRONT/BACK and EPS-FRONT/BACK of the construction
# and HBACK 99999.  The library objects are never modified.  A construction missing in the library keeps the library HIGH_COND.
HAMT_WALL_BOUNDARIES = ('EXTCALEXT', 'EXTCALBND')
HAMT_WALL_BASE = 'HIGH_COND'      # library pseudo-wall the derived types are copied from; fallback for unknown constructions
HAMT_WALL_SUFFIX = '_HAMT'
HAMT_WALL_HBACK = 99999           # back side of the pseudo-wall: the boundary node is the Type 395 surface temperature
def hamt_wall_type_name(original, taken, max_len=None):
    """<original>_HAMT within the name limit of the derived wall types, shortened and numbered where needed so that it is not in ``taken`` (lower case names)."""
    if max_len is None:
        max_len = MIRROR_NAME_MAX
    original = str(original)
    candidate = original[:max(1, max_len - len(HAMT_WALL_SUFFIX))] + HAMT_WALL_SUFFIX
    counter = 0
    while candidate.lower() in taken:
        counter += 1
        tail = str(counter)
        candidate = original[:max(1, max_len - len(HAMT_WALL_SUFFIX) - len(tail))] + tail + HAMT_WALL_SUFFIX
    return candidate
def plan_hamt_pseudo_walls(dataset, wall_items):
    """{construction name: derived pseudo-wall type name} of the constructions used by HAMT surfaces.
    Constructions missing in the library are not planned.  Pure function of the airnodes and the wall library (like
    plan_thermal_mirror_walls), so the wall type definitions of printbuitoppart and the zone wall lines of printbuiZonepart agree."""
    known = []
    taken = []
    for wall_item in wall_items:
        known.append(wall_item.Name)
        taken.append(str(wall_item.Name).lower())
    names = {}
    for airnode in dataset:
        for surface in airnode.Surfaces:
            if surface.Boundarycond in HAMT_WALL_BOUNDARIES and surface.Construction in known:
                names[surface.Construction] = None
    for original in sorted(names):
        names[original] = hamt_wall_type_name(original, taken)
        taken.append(names[original].lower())
    return names
def derive_hamt_wall(base_item, construction_item, name):
    """Copy of the library pseudo-wall with the front and back films of the construction and HBACK 99999."""
    derived = copy.copy(base_item)
    derived.Name = name
    derived.Hfront = construction_item.Hfront
    derived.Hback = HAMT_WALL_HBACK
    derived.Abs_front = construction_item.Abs_front
    derived.Abs_back = construction_item.Abs_back
    derived.Eps_front = construction_item.Eps_front
    derived.Eps_back = construction_item.Eps_back
    return derived
def hamt_wall_message(names, wall_items):
    """Runtime message that lists the derived HAMT pseudo-wall types and their front films."""
    walls = {}
    for wall_item in wall_items:
        walls[wall_item.Name] = wall_item
    groups = []
    for original in sorted(names):
        wall_item = walls[original]
        groups.append('%s (from %s: HFRONT %s, ABS-FRONT %s, EPS-FRONT %s)' % (names[original], original, wall_item.Hfront,
                                                                               wall_item.Abs_front, wall_item.Eps_front))
    return 'HAMT walls (Type 395): one pseudo-wall type per construction, with the front films of the construction: %s.' % '; '.join(groups)
# ---- HAMT pseudo-walls (end)
# ---- HAMT gain of a zone
# GAIN HAMT_Gain_<zone> (printbuitoppart) and its regime line (printbuiZonepart) are written for the same zones: those with a
# Type 395 (HAMT) wall. Ecalsurfaces also lists the EXTCALC/BNDCALC surfaces of the external calculation, which are no HAMT walls.
HAMT_GAIN_BOUNDARIES = ('EXTCALEXT', 'EXTCALBND')
def has_hamt_surfaces(airnode):
    """True for a zone with an EXTCALEXT or EXTCALBND surface (plain loop: the callers contain exec, see IronPython 2)."""
    for surface in airnode.Surfaces:
        if surface.Boundarycond in HAMT_GAIN_BOUNDARIES:
            return True
    return False
# ---- HAMT gain of a zone (end)
# ---- TRNFlow helpers (begin)
# Parameters 4 to 14 of the TRNFlow version of Type 56 and the CRACK link type of the airflow network.
def trnflow_parameters(altitude):
    """Type 56 parameters 4 to 14 (text for @trnflowpar).

    The weather file is the weather of the building site, so the altitude of the building (project input Altitude) is also the
    altitude of the meteo station (parameter 10): the TRNFlow wind and pressure are not corrected for an altitude difference.
    """
    parameters = [
        ('-1', '4 Not used - Logical unit for monthly summary'),
        ('-1', '5 Not used - Logical unit for hourly temperatures'),
        ('-1', '6 Not used - Logical unit for hourly loads'),
        ('1', '7 Comis output / Tste'),
        (str(altitude), '8 Altitude of building'),
        ('10', '9 Height of meteo pylon'),
        (str(altitude), '10 Altitude of weather station'),
        ('0.14', '11 Velocity profile at weather station'),
        ('0.01', '12 Tolerance for internal iterations'),
        ('100', '13 Maximum number of internal iterations'),
        ('0.1', '14 Minimum relaxation factor'),
    ]
    return ''.join(['%s\t\t! %s\n' % (value, comment) for value, comment in parameters])
def trnflow_crack_type(crack):
    """BUI block of a crack link type (LINKTYPES); the manual's example: CRACK CR_001 / DESC / CS, EXPN / FILTER1..5."""
    return 'CRACK %s\n DESC= -\n CS= %s : EXPN= %s\n FILTER1= 0 : FILTER2= 0 : FILTER3= 0 : FILTER4= 0 : FILTER5= 0\n' % (
        crack.Name, crack.Cs, crack.Expn)
# ---- TRNFlow helpers (end)
@timing
def printbuitoppart(dataset):
    global collmessages
    foundextvertf = 0
    foundextboundadj = 0
    srfnum = 0
    lines = []
    Zones = ''
    orientations = ''
    templlines = templates.Header
    templlines=templlines.replace('@author', os.getenv("USERNAME"))
    templlines=templlines.replace('@calcmode', daylightmode)
    templlines=templlines.replace('@longitude', longitude)
    templlines=templlines.replace('@latitude', latitude)
    templlines=templlines.replace('@altitude', altitude)
    templlines=templlines.replace('@timezone', timezone)
    templlines=templlines.replace('@ab', str(dab))
    templlines=templlines.replace('@ad', str(dad))
    templlines=templlines.replace('@as', str(das))
    templlines=templlines.replace('@ar', str(dar))
    templlines=templlines.replace('@aa', str(daa))
    templlines=templlines.replace('@shader_reflectance', str(shader_reflectance))
    templlines=templlines.replace('@rotation', str(Rotation))
    comfortfound = 0
    if "GridSpacingSolarConcave" in locals() and GridSpacingSolarConcave is not None:
        sc.sticky[sc.doc.Path]["GridSpacingSolarConcave"]           = GridSpacingSolarConcave
    else:
        sc.sticky[sc.doc.Path]["GridSpacingSolarConcave"]           = 0.2 #CSH_220427 set Grid Spacing as default if no value is supplied
    templlines=templlines.replace('@solgrid_size', str(sc.sticky[sc.doc.Path]["GridSpacingSolarConcave"])) #CSH_220427

    if "GridDistanceSolarConcave" in locals() and GridDistanceSolarConcave is not None:
        sc.sticky[sc.doc.Path]["GridDistanceSolarConcave"]           = GridDistanceSolarConcave
    else:
        sc.sticky[sc.doc.Path]["GridDistanceSolarConcave"]           = 0.03 #CSH_220427 set Grid distance as default if no value is supplied
    templlines=templlines.replace('@solgrid_dist', str(sc.sticky[sc.doc.Path]["GridDistanceSolarConcave"])) #CSH_220427

    for item in dataset:
        for item2 in item.Comfort:
            templlines=templlines.replace('@elv_airspeed1', str(item2.Velocity2))
            templlines=templlines.replace('@elv_airspeed2', str(item2.Velocity3))
            templlines=templlines.replace('@elv_airspeed3', str(item2.Velocity4))
            comfortfound = 1
    if comfortfound == 0:
        templlines=templlines.replace('@elv_airspeed1', str(0))
        templlines=templlines.replace('@elv_airspeed2', str(0))
        templlines=templlines.replace('@elv_airspeed3', str(0))
    lines.append(templlines)
    lines.extend(printheader('L a y e r s'))
    cleaned_layer = []
    for wall_item in library.Walls:
        for subitems in surfaceinfo:
            if subitems.Construction == wall_item.Name:
                cleaned_layer.extend(wall_item.Layers.split())
            if subitems.Boundarycond == 'EXTCALC' or subitems.Boundarycond == 'BNDCALC':
                cleaned_layer.append('HIGH_RES')
            if subitems.Boundarycond == 'EXTCALEXT' or subitems.Boundarycond == 'EXTCALBND':
                cleaned_layer.append('DIRECT')
            if subitems.Boundarycond == 'EXTVERTF':
                foundextvertf = 1
            if subitems.Boundarycond == 'EXTBOUNDADJ':
                foundextboundadj = 1
    cleaned_layer = list(set(cleaned_layer))
    for layer_item in library.Layers:
        for cleaned_item in cleaned_layer:
            if layer_item.Name == cleaned_item:
                lines.append(printsingledata(layer_item,'Resistance','Pspacing','Conductivity','Cc_pidiameter'))
    # Intermediate part directly from the template
    lines.append(templates.Inputs)
    # Schedule definition from library plus addons
    collect_schedules = []
    for Airnodes in dataset:
        if Airnodes.Gain:
            for items in Airnodes.Gain:
                if items.Schedule != '':
                    collect_schedules.append(items.Schedule)
                if items.Annual != '' and items.Annual != None:
                    collect_schedules.append(items.Annual)
        if Airnodes.Heating:
            collect_schedules.append(Airnodes.Heating.Schedule)
        if Airnodes.Cooling:
            collect_schedules.append(Airnodes.Cooling.Schedule)
        if Airnodes.Dhw:
            collect_schedules.append(Airnodes.Dhw.Schedule)
        if Airnodes.Infiltration:
            collect_schedules.append(Airnodes.Infiltration.Schedule)
            if hasattr(Airnodes.Infiltration,'Annual') and Airnodes.Infiltration.Annual != '' and Airnodes.Infiltration.Annual != None:
                collect_schedules.append(Airnodes.Infiltration.Annual)
        if Airnodes.Ventilation:
            for items in Airnodes.Ventilation:
                if 'NOT' in items.Schedule:
                    pass
                else:
                    collect_schedules.append(items.Schedule)
        if Airnodes.Daylightctrl:
            for dcitem in Airnodes.Daylightctrl:
                collect_schedules.append(dcitem.Schedule)
        for subitem in item.Surfaces:
            if subitem.Scheduleheating:
                collect_schedules.append(subitem.Scheduleheating)
            if subitem.Schedulecooling:
                collect_schedules.append(subitem.Schedulecooling)
    collect_schedules = list(set(collect_schedules))
    lines.extend(printheader('S c h e d u l e s'))
    for subitems in collect_schedules:
        for schedule_items in library.Schedules:
            if subitems == schedule_items.Name:
                if schedule_items.Hourly != '':
                    collect_schedules.extend(list(set(schedule_items.Hourly.split())))
    for schedule_items in library.Schedules:
        for subitems in collect_schedules:
            if subitems == schedule_items.Name:
                lines.append(printsingledata(schedule_items,'Hours','Days'))
    for schedule_items in library.Annualschedules:
        for subitems in collect_schedules:
            if subitems == schedule_items.Name:
                lines.append(printsingledata(schedule_items,'Annual'))
    # Walls definition from the library
    if TRNSYS == 17:
        lines.extend(printheader('W a l l s'))
    else:
        lines.extend(printheader('C O N S T R U C T I O N (Wall, Floor, Ceiling,..)'))
    cleaned_walls = []
    for wall_item in library.Walls:
        for subitems in surfaceinfo:
            if subitems.Construction == wall_item.Name:
                cleaned_walls.append(subitems.Construction)
                if subitems.Boundarycond == 'EXTCALC' or subitems.Boundarycond == 'BNDCALC':
                    cleaned_walls.append('HIGH_RES')
                    for wall2_item in library.Walls:
                        if wall2_item.Name == 'HIGH_RES':
                            wall2_item.Hfront = wall_item.Hfront
                            wall2_item.Hback = wall_item.Hback
                            wall2_item.Abs_front = wall_item.Abs_front
                            wall2_item.Abs_back = wall_item.Abs_back
                            wall2_item.Eps_front = wall_item.Eps_front
                            wall2_item.Eps_back = wall_item.Eps_back
    # HAMT walls (EXTCALEXT, EXTCALBND): derived pseudo-wall type <construction>_HAMT per construction, the same plan as the zone wall lines
    hamt_wall_names = plan_hamt_pseudo_walls(dataset, library.Walls)
    hamt_wall_base = None
    for wall_item in library.Walls:
        if wall_item.Name == HAMT_WALL_BASE:
            hamt_wall_base = wall_item
    # the library HIGH_COND only for surfaces whose zone wall line falls back to it: printbuiZonepart skips Virtual surfaces, and writes a
    # WINDOW on an EXTCALEXT wall (Boundarycond copied from the wall, construction = window type) as a window, without a wall type
    for subitems in surfaceinfo:
        if (subitems.Boundarycond in HAMT_WALL_BOUNDARIES and subitems.Construction not in hamt_wall_names
                and "Virtual" not in subitems.Construction
                and not (subitems.Boundarycond == 'EXTCALEXT' and subitems.Type == 'WINDOW')):
            cleaned_walls.append(HAMT_WALL_BASE)
    if len(hamt_wall_names) > 0 and hamt_wall_base is None:
        ghenv.Component.AddRuntimeMessage(w, "The wall library has no %s, the pseudo-wall the HAMT (Type 395) wall types are copied from: the HAMT surfaces get no wall type." % HAMT_WALL_BASE)
    cleaned_walls = list(set(cleaned_walls))
    # thermal mirror walls: derived wall type <name>_MIRROR, only for constructions that a BOUNDARY = own TAIR wall needs
    mirror_wall_names, mirror_wall_surfaces = plan_thermal_mirror_walls(dataset, library.Walls)
    mirror_wall_written = []
    hamt_wall_written = []
    for wall_item in library.Walls:
        for cleaned_item in cleaned_walls:
            if wall_item.Name == cleaned_item:
                lines.append(printsingledata(wall_item,'Wall'))
                if wall_item.Name in mirror_wall_names and wall_item.Name not in mirror_wall_written:
                    mirror_wall_written.append(wall_item.Name)
                    lines.append(printsingledata(derive_mirror_wall(wall_item, mirror_wall_names[wall_item.Name]),'Wall'))
                if wall_item.Name in hamt_wall_names and wall_item.Name not in hamt_wall_written and hamt_wall_base is not None:
                    hamt_wall_written.append(wall_item.Name)
                    lines.append(printsingledata(derive_hamt_wall(hamt_wall_base, wall_item, hamt_wall_names[wall_item.Name]),'Wall'))
    if len(mirror_wall_surfaces) > 0:
        ghenv.Component.AddRuntimeMessage(rem, mirror_wall_message(mirror_wall_names, mirror_wall_surfaces))
    if len(hamt_wall_written) > 0:
        ghenv.Component.AddRuntimeMessage(rem, hamt_wall_message(hamt_wall_names, library.Walls))
    # Intermediate part directly from the template
    lines.extend(printheader('W i n d o w s'))
    window_names = []
    for item in dataset:
        for subitems in item.Surfaces:
            if (subitems.Type == 'WINDOW' or subitems.Type == 'ADDWINDOW') and subitems.BSDFWindows != 1:
                if subitems.Construction in window_names:
                    pass
                else:
                    window_names.append(subitems.Construction)
                    # @OC START
                    #@Mark:add Radmaterial to constructions and windows
                    if 'OC_command_lines_global_variables' in sc.sticky[sc.doc.Path]:
                        subitems = addRadmaterial(subitems)
                    # @OC END
                    lines.append(printsingledata(subitems,'Windows'))
            if (subitems.Type == 'WINDOW' or subitems.Type == 'ADDWINDOW') and subitems.BSDFWindows == 1:
                if subitems.Construction in window_names:
                    pass
                else:
                    window_names.append(subitems.Construction)
                    # @OC START
                    #@Mark:add Radmaterial to constructions and windows
                    if 'OC_command_lines_global_variables' in sc.sticky[sc.doc.Path]:
                        subitems = addRadmaterial(subitems)
                    # @OC END
                    if subitems.Gapventmode == 'STACK':
                        subitems.Gapmflow1 += str(subitems.Surfnum)
                    if subitems.Gapventmode == 'PERMANENT':
                        subitems.Gapmflow1 += str(subitems.Surfnum)
                        subitems.Gapintemp1 += str(subitems.Surfnum)
                    lines.append(printsingledata(subitems,'BSDFWindows'))
    # Print the library gains
    if TRNSYS == 17:
        lines.extend(printheader('D e f a u l t  G a i n s'))
        lines.extend(printheader('O t h e r  G a i n s'))
    else:
        lines.extend(printheader('G a i n s / L o s s e s'))
    for item in dataset:
        if item.Gain:
            for subitem in item.Gain:
                for gain_item in library.Gain:
                    if subitem.Name == gain_item.Name:
                        lines.append(printsingledata(gain_item,'Gain'))
    # Auto-define HAMT gains for zones with EXTCALEXT/EXTCALBND surfaces (multi-HAMT support)
    existing_gain_names = [str(gain_item.Name) for gain_item in library.Gain]
    for item in dataset:
        if has_hamt_surfaces(item) and ('HAMT_Gain_' + item.Name) not in existing_gain_names:
            lines.append('GAIN HAMT_Gain_{0}\r\n CONVECTIVE=0 : RADIATIVE=0 : HUMIDITY=INPUT 1*HamtHumidityGain_KgPerHr_{0} : ELPOWERFRAC=0 :  ABSOLUTE : CATEGORY=MISCELLANEOUS\r\n'.format(item.Name))
    for item in dataset:
        for item2 in item.Gain:
            if item2.Userdefined == 1:
                if 'THB' in item2.Name:
                    dummy = item2.Name
                    item2.Name = dummy + '_' + item.Name
                    lines.append(printsingledata(item2,'Gain'))
                    item2.Name = dummy.replace('_' + item.Name,'')
                else:
                    dummy = item2.Name
                    dummyrad = item2.Radiative
                    dummycon = item2.Convective
                    item2.Name = dummy + '_' + item.Name
                    item2.Radiative = dummyrad + '_' + item.Name
                    item2.Convective = dummycon + '_' + item.Name
                    item2.Humidity   = item2.Hum2
                    lines.append(printsingledata(item2,'Gain'))
                    item2.Name = dummy.replace('_' + item.Name,'')
                    item2.Radiative = dummyrad.replace('_' + item.Name,'')
                    item2.Convective = dummycon.replace('_' + item.Name,'')
            if item2.Userdefined == 2:
                dummy = item2.Name
                item2.Name = dummy + '_' + item.Name
                item2.Humidity   = item2.Hum2
                lines.append(printsingledata(item2,'Gain'))
                item2.Name = dummy.replace('_' + item.Name,'')
            if item2.Personsgain == 1:
                dummy = item2.Name
                dummyrad = item2.Radiative
                dummycon = item2.Convective
                item2.Name = dummy + '_' + item.Name
                item2.Radiative = dummyrad + '_' + item.Name
                item2.Convective = dummycon + '_' + item.Name
                # REGIME SCALE applies the people schedule to all gain channels, including humidity.
                item2.Humidity   = '{0}'.format(item2.Hum2/item.Areaperperson)
                lines.append(printsingledata(item2,'Gain'))
                item2.Name = dummy.replace('_' + item.Name,'')
                item2.Radiative = dummyrad.replace('_' + item.Name,'')
                item2.Convective = dummycon.replace('_' + item.Name,'')
            if item2.Computergain == 1:
                dummy = item2.Name
                dummyrad = item2.Radiative
                dummycon = item2.Convective
                item2.Name = dummy + '_' + item.Name
                item2.Radiative = dummyrad + '_' + item.Name
                item2.Convective = dummycon + '_' + item.Name
                lines.append(printsingledata(item2,'Gain'))
                item2.Name = dummy.replace('_' + item.Name,'')
                item2.Radiative = dummyrad.replace('_' + item.Name,'')
                item2.Convective = dummycon.replace('_' + item.Name,'')
            if item2.Lightinggain == 1:
                dummy = item2.Name
                dummyrad = item2.Radiative
                dummycon = item2.Convective
                item2.Name = dummy + '_' + item.Name
                item2.Radiative = dummyrad + '_' + item.Name
                item2.Convective = dummycon + '_' + item.Name
                lines.append(printsingledata(item2,'Gain'))
                item2.Name = dummy.replace('_' + item.Name,'')
                item2.Radiative = dummyrad.replace('_' + item.Name,'')
                item2.Convective = dummycon.replace('_' + item.Name,'')
    # Intermediate part directly from the template
    lines.extend(printheader('C o m f o r t'))
    for item in dataset:
        for item2 in item.Comfort:
            dummy = item2.Name
            item2.Name      = dummy + '_' + item.Name
            lines.append(printsingledata(item2,'Comfort'))
            item2.Name      = dummy.replace('_' + item.Name,'')
    lines.extend(printheader('I n f i l t r a t i o n'))
    for item in dataset:
        if item.Infiltration:
            dummy = item.Infiltration.Name
            dummyach = item.Infiltration.Airchange
            item.Infiltration.Name      = dummy + '_' + item.Name
            item.Infiltration.Airchange = dummyach + '_' + item.Name
            lines.append(printsingledata(item.Infiltration,'Infiltration'))
            item.Infiltration.Name      = dummy.replace('_' + item.Name,'')
            item.Infiltration.Airchange = dummyach.replace('_' + item.Name,'')
    lines.extend(printheader('V e n t i l a t i o n'))
    for item in dataset:
        if item.Ventilation:
            for ventilation_item in item.Ventilation:
                dummy = ventilation_item.Name
                dummyach = ventilation_item.Airchange
                dummyhum = ventilation_item.Humidity
                dummytemp= ventilation_item.Temperature
                dummyhummax = ventilation_item.Absmaxhum
                dummyhummin = ventilation_item.Absminhum
                dummysenshr = ventilation_item.Senshr
                dummycalcqahu = ventilation_item.Calcqahu
                dummyfanpower = ventilation_item.Specfanpower
                if ventilation_item.Type == 'STACKVENTILATION':
                    ventilation_item.Name = dummy + '_' + item.Name
                    ventilation_item.Airchange = dummyach + '_' + item.Name
                    dummylines=printsingledata(ventilation_item,'Ventilation')
                    dummylines = dummylines.replace('HUMIDITY','ABSHUMIDITY')
                    lines.append(dummylines)
                else:
                    ventilation_item.Name = dummy + '_MV_' + item.Name
                    ventilation_item.Airchange = dummyach + '_MV_' + item.Name
                    ventilation_item.Humidity = ventilation_item.Humidity + '_MV_' + item.Name
                    ventilation_item.Temperature = ventilation_item.Temperature + '_MV_' + item.Name
                    ventilation_item.Absminhum = ventilation_item.Absminhum + '_MV_' + item.Name
                    ventilation_item.Absmaxhum = ventilation_item.Absmaxhum + '_MV_' + item.Name
                    #ventilation_item.Senshr = ventilation_item.Senshr + '_MV_' + item.Name
                    dummylines=printsingledata(ventilation_item,'Ventilation')
                    dummylines = dummylines.replace('HUMIDITY','ABSHUMIDITY')
                    lines.append(dummylines)
                if ventilation_item.Type == 'STACKVENTILATION':
                    ventilation_item.Name = ventilation_item.Name.replace('_' + item.Name,'')
                    ventilation_item.Airchange = ventilation_item.Airchange.replace('_' + item.Name,'')
                else:
                    ventilation_item.Name = ventilation_item.Name.replace('_MV_' + item.Name,'')
                    ventilation_item.Airchange = ventilation_item.Airchange.replace('_MV_' + item.Name,'')
                    ventilation_item.Humidity = ventilation_item.Humidity.replace('_MV_' + item.Name,'')
                    ventilation_item.Temperature = ventilation_item.Temperature.replace('_MV_' + item.Name,'')
                    ventilation_item.Absminhum = ventilation_item.Absminhum.replace('_MV_' + item.Name,'')
                    ventilation_item.Absmaxhum = ventilation_item.Absmaxhum.replace('_MV_' + item.Name,'')
                    #ventilation_item.Senshr = ventilation_item.Senshr.replace('_MV_' + item.Name,'')
                if ventilation_item.Hybrid == 1:
                    ventilation_item.Name = dummy + '_HV_' + item.Name
                    ventilation_item.Airchange = dummyach + '_HV_' + item.Name
                    ventilation_item.Humidity = 'INPUT 1*{0}'.format(ventilation_item.Humoutside)
                    ventilation_item.Temperature = 'INPUT 1*{0}'.format(ventilation_item.Toutside)
                    ventilation_item.Absminhum = 'INPUT 1*{0}'.format(ventilation_item.Humoutside)
                    ventilation_item.Absmaxhum = 'INPUT 1*{0}'.format(ventilation_item.Humoutside)
                    ventilation_item.Calcqahu = 0
                    ventilation_item.Senshr = 0
                    ventilation_item.Specfanpower = 0
                    dummylines=printsingledata(ventilation_item,'Ventilation')
                    dummylines = dummylines.replace('HUMIDITY','ABSHUMIDITY')
                    lines.append(dummylines)
                    ventilation_item.Name           = ventilation_item.Name.replace('_HV_' + item.Name,'')
                    ventilation_item.Airchange      = ventilation_item.Airchange.replace('_HV_' + item.Name,'')
                    ventilation_item.Humidity       = dummyhum
                    ventilation_item.Temperature    = dummytemp
                    ventilation_item.Absminhum = dummyhummin
                    ventilation_item.Absmaxhum = dummyhummax
                    ventilation_item.Calcqahu = dummycalcqahu
                    ventilation_item.Senshr = dummysenshr
                    ventilation_item.Specfanpower = dummyfanpower
    #Coupling integration
    Couplingdef = []
    newcoupl = []
    if len(Coupling)>0:
        dummy = []
        for cpl_item in Coupling:
            if (cpl_item.Target in airnodenames) and cpl_item.Source in airnodenames:
                dummylines = printsingledata(cpl_item,'Ventilation')
                dummylines = dummylines.replace('HUMIDITY','ABSHUMIDITY')
                dummylines = dummylines.replace('AIRCHANGE','AIRFLOW')
                if cpl_item.Name in Couplingdef:
                    pass
                else:
                    Couplingdef.append(cpl_item.Name)
                    Coupling_coll.append(cpl_item)
                    lines.append(dummylines)
            else:
                mess = "Airnode for coupling definition %s is not existing. Coupling will be turned off!"%cpl_item.Name
                ghenv.Component.AddRuntimeMessage(w, mess)
                collmessages += mess + '\n'
    elements = ["Cooling","Heating"]
    for element in elements:
        headerout = ''
        for ei,eitem in enumerate(element):
            if ei == 0:
                headerout += eitem
            else:
                headerout += " %s"%eitem
        lines.extend(printheader(headerout))
        for item in dataset:
            #if item.Heating:
            if getattr(item, element):
                lines.append(printsingledata(getattr(item, element),element).replace("@aname",item.Name))
    # Heating Regime Definition
    lines.extend(printheader('D a y l i g h t   C o n t r o l'))
    for item in dataset:
        if item.Daylightctrl:
            for di, dcitem in enumerate(item.Daylightctrl):
                dummy = dcitem.Name
                dcitem.Name = dummy + str(di) + '_' + item.Name
                lines.append(printsingledata(dcitem,'Dctrl'))
                dcitem.Name = dummy.replace(str(di) + '_' + item.Name, '')
    # Collects the Zonenames and orientations
    cleaned_ori = []
    zonelist = []
    for item in dataset:
        zonelist.append(item.Zonename)
        for itemori in item.Orientations:
            cleaned_ori.append(itemori)
    zonelist = list(set(zonelist))
    neworder = []
    for key1 in sorted(zonedict):
        neworder.append(key1)

    for item in neworder:
        myZonestring = "%s " % item
        Zones = Zones + myZonestring
    cleaned_ori = list(set(cleaned_ori))
    orifilter = ['H','S','W','N','E']
    oridict = {}
    for item in orifilter:
        oridict[item] = []
    for item in cleaned_ori:
        for key in oridict:
            if key in item:
                oridict[key].append(item)
    sorted_ori = []
    for item in orifilter:
        sorted_ori.extend(oridict[item])
    for itemori in sorted_ori:
        myoristring = "%s " % itemori
        orientations = orientations + myoristring
    intcalcori = orientations
    if foundextvertf == 1:
        orientations+= "%s"%"VERTF"
    if foundextboundadj== 1:
        orientations+= "%s"%"ADJ_BUILD"
    templlines=templates.Zonesori
    templlines=templlines.replace('@Zones', Zones)
    templlines=templlines.replace('@Orientations', orientations)
    templlines=templlines.replace('@Intcalcori', intcalcori)
    templlines=templlines.replace('@Hemisphere', hemisphere)
    lines.append(templlines)

    return lines
@timing
def printbuiZonepart(dataset):
    lines = []
    # thermal mirror walls: derived wall type per construction, the same plan as the wall type definitions of printbuitoppart
    thermal_mirror_names = plan_thermal_mirror_walls(dataset, library.Walls)[0]
    # HAMT walls: derived pseudo-wall type per construction, the same plan as the wall type definitions of printbuitoppart
    hamt_wall_names = plan_hamt_pseudo_walls(dataset, library.Walls)
    # Here the individual Zone definition is starting
    # Defines the Zones
    Zone_name_coll = []
    comfid = 0
    zonedict = dict()
    for Airnodes in dataset:
        if Airnodes.Zonename in zonedict:
            zonedict[Airnodes.Zonename][Airnodes.Name] = Airnodes
        else:
            zonedict[Airnodes.Zonename] = dict()
            zonedict[Airnodes.Zonename][Airnodes.Name] = Airnodes
    neworder = []
    for key1 in sorted(zonedict):
        for key2 in sorted(zonedict[key1]):
            neworder.append(zonedict[key1][key2])
    for aix, Airnodes in enumerate(neworder):
        if aix == 0:
            lastzone = Airnodes.Zonename
        tbd_surfaces = []
        Airnodes.Al1surfaces = []
        Airnodes.Extal1surfaces = []
        Airnodes.Al2surfaces = []
        Airnodes.Extal2surfaces = []
        win_surfaces = []
        window_surfaces = []
        bsdf_surfaces = []
        wall_surfaces = []
        floor_surfaces = []
        ceiling_surfaces = []
        roof_surfaces = []
        extwall_surfaces_ori = []
        extwall_surfaces = []
        ecal_surfaces = []
        efical_surfaces = []
        constructionlines = ''
        zoneairnodeinfo = """*------------------------
*  Z o n e  {0}  /  A i r n o d e  {1}
*------------------------\n""".format(Airnodes.Zonename,Airnodes.Name)
        templlinesZone=templates.Zone
        templlinesZone=templlinesZone.replace('@zone', Airnodes.Zonename)
        templlinesZone=templlinesZone.replace('@beam', Airnodes.Beam)
        templlinesZone=templlinesZone.replace('@diffuse', Airnodes.Diffuse)
        templlinesZone=templlinesZone.replace('@longwave', Airnodes.Longwave)
        templlinesZone=templlinesZone.replace('@geomode', Airnodes.Geomode)
        templlinesZone=templlinesZone.replace('@fsolair', str(Airnodes.Fsolair))
        dlshadefound = 0
        if 'Complexshade' in dir(Airnodes) and getattr(Airnodes, 'Complexshade') is not None:
            dlshadefound = 1
            print 'Found complex shading definition'
            #if 'Shd' in sitem and 'tair' not in sitem and getattr(surface, sitem) is not None:
            #    dlshadefound = 1
        if dlshadefound == 0:
            templlinesZone=templlinesZone.replace('@dlshade', str(-1))
        else:
            templlinesZone=templlinesZone.replace('@dlshade', 'INPUT 1*DLSHADE_%s'%(Airnodes.Zonename))
        for attr, value in Airnodes.__dict__.iteritems():
            templlinesZone=templlinesZone.replace('@self.{0}'.format(attr), str(value))
        templlines=templates.Airnode
        templlines=templlines.replace('@zone', Airnodes.Zonename)
        for attr, value in Airnodes.__dict__.iteritems():
            templlines=templlines.replace('@self.{0}'.format(attr), str(value))
        for surfaces in Airnodes.Surfaces:
            appendstring = ''
            if "Virtual" in surfaces.Construction:
                continue
            if surfaces.Type == 'WALL':
                wall_surfaces.append(surfaces.Surfnum)
            if surfaces.Type == 'WINDOW' or surfaces.Type == 'ADDWINDOW':
                window_surfaces.append(surfaces.Surfnum)
            if surfaces.Type == 'FLOOR':
                floor_surfaces.append(surfaces.Surfnum)
            if surfaces.Type == 'CEILING':
                ceiling_surfaces.append(surfaces.Surfnum)
            if surfaces.Type == 'ROOF':
                roof_surfaces.append(surfaces.Surfnum)
            if surfaces.Activelayer == 1 and surfaces.Boundarycond != 'EXTCALC' and surfaces.Boundarycond != 'BNDCALC' and surfaces.Boundarycond != 'EXTCALEXT' and surfaces.Boundarycond != 'EXTCALBND':
                dummy = surfaces.Intemp
                if surfaces.Boundarycond == 'ADJACENT' and surfaces.Frontback == 'BACK':
                    if 'TSUP_AL' in dummy:
                        appendstring = " : INTEMP = @self.Intemp_{0} : MFLOW = INPUT 1*MFTAB_AL1_{0} : NLOOP = @self.Nloops : MFLOWMIN = @self.Mflowmin".format(surfaces.Adjairnode)
                    else:
                        appendstring = " : INTEMP = @self.Intemp : MFLOW = INPUT 1*MFTAB_AL1_{0} : NLOOP = @self.Nloops : MFLOWMIN = @self.Mflowmin".format(surfaces.Adjairnode)
                else:
                    if 'TSUP_AL' in dummy:
                        appendstring = " : INTEMP = @self.Intemp_{0} : MFLOW = INPUT 1*MFTAB_AL1_{0} : NLOOP = @self.Nloops : MFLOWMIN = @self.Mflowmin".format(Airnodes.Name)
                    else:
                        appendstring = " : INTEMP = @self.Intemp : MFLOW = INPUT 1*MFTAB_AL1_{0} : NLOOP = @self.Nloops : MFLOWMIN = @self.Mflowmin".format(Airnodes.Name)
                    Airnodes.Al1surfaces.append(surfaces.Surfnum)
            elif surfaces.Activelayer == 2 and surfaces.Boundarycond != 'EXTCALC' and surfaces.Boundarycond != 'BNDCALC' and surfaces.Boundarycond != 'EXTCALEXT' and surfaces.Boundarycond != 'EXTCALBND':
                dummy = surfaces.Intemp
                if surfaces.Boundarycond == 'ADJACENT' and surfaces.Frontback == 'BACK':
                    if 'TSUP_AL' in dummy:
                        appendstring = " : INTEMP = @self.Intemp_{0} : MFLOW = INPUT 1*MFTAB_AL2_{0} : NLOOP = @self.Nloops : MFLOWMIN = @self.Mflowmin".format(surfaces.Adjairnode)
                    else:
                        appendstring = " : INTEMP = @self.Intemp : MFLOW = INPUT 1*MFTAB_AL2_{0} : NLOOP = @self.Nloops : MFLOWMIN = @self.Mflowmin".format(surfaces.Adjairnode)
                else:
                    if 'TSUP_AL' in dummy:
                        appendstring = " : INTEMP = @self.Intemp_{0} : MFLOW = INPUT 1*MFTAB_AL2_{0} : NLOOP = @self.Nloops : MFLOWMIN = @self.Mflowmin".format(Airnodes.Name)
                    else:
                        appendstring = " : INTEMP = @self.Intemp : MFLOW = INPUT 1*MFTAB_AL2_{0} : NLOOP = @self.Nloops : MFLOWMIN = @self.Mflowmin".format(Airnodes.Name)
                    Airnodes.Al2surfaces.append(surfaces.Surfnum)
            else:
                appendstring = ''
            if surfaces.Activelayer == 1 and (surfaces.Boundarycond == 'EXTCALC' or surfaces.Boundarycond == 'BNDCALC' or surfaces.Boundarycond == 'EXTCALEXT' or surfaces.Boundarycond == 'EXTCALBND'):
                dummy = surfaces.Intemp
                if surfaces.Boundarycond == 'ADJACENT' and surfaces.Frontback == 'BACK':
                    pass
                else:
                    Airnodes.Extal1surfaces.append(surfaces.Surfnum)
            if surfaces.Activelayer == 2 and (surfaces.Boundarycond == 'EXTCALC' or surfaces.Boundarycond == 'BNDCALC' or surfaces.Boundarycond == 'EXTCALEXT' or surfaces.Boundarycond == 'EXTCALBND'):
                dummy = surfaces.Intemp
                if surfaces.Boundarycond == 'ADJACENT' and surfaces.Frontback == 'BACK':
                    pass
                else:
                    Airnodes.Extal2surfaces.append(surfaces.Surfnum)
                    pass
            #if (surfaces.Boundarycond == 'EXTERNAL' or surfaces.Boundarycond == 'EXTBOUNDARY' or surfaces.Boundarycond == 'EXTCALC' or surfaces.Boundarycond == 'EXTSKYBND') and surfaces.Type != 'WINDOW':
            if (surfaces.Boundarycond in ('EXTERNAL','EXTBOUNDARY','EXTCALC','EXTSKYBND','EXTVERTF','EXTBOUNDADJ','EXTCALEXT')) and surfaces.Type != 'WINDOW':
                srfnum = surfaces.Surfnum
                ori_construction = surfaces.Construction
                dummylines=templates.Constr
                if surfaces.Boundarycond == 'EXTERNAL':
                    dummylines=dummylines + ' : EXTERNAL : ORI=@self.Orientation : FSKY=@self.Fsky : GEOSURF=@self.Geosurf' + appendstring
                elif surfaces.Boundarycond == 'EXTSKYBND':
                    dummylines=dummylines + ' : EXTERNAL : ORI=@self.Orientation : TBOUNDARY=@self.Boundarytemp : WAGAIN=INPUT -1*QABSILW_S@self.Surfnum : GEOSURF=@self.Geosurf' + appendstring
                    tbd_surfaces.append(srfnum)
                elif surfaces.Boundarycond == 'EXTBOUNDARY':
                    dummylines=dummylines + ' : EXTERNAL : ORI=@self.Orientation : TBOUNDARY=@self.Boundarytemp : GEOSURF=@self.Geosurf' + appendstring
                # @OC START
                elif surfaces.Boundarycond == 'EXTBOUNDADJ':
                    dummylines=dummylines + ' : EXTERNAL : ORI=ADJ_BUILD : TBOUNDARY=@self.Boundarytemp : GEOSURF=@self.Geosurf' + appendstring
                    if "ADJ_BUILD" in manual_ori:
                        pass
                    else:
                        manual_ori.append("ADJ_BUILD")
                # @OC END
                elif surfaces.Boundarycond == 'EXTCALC':
                    dummylines=dummylines + ' : EXTERNAL : ORI=@self.Orientation : WAGAIN=INPUT 1*WGAIN_I_S@self.Surfnum : WAGAINO=INPUT 1*WGAIN_O_S@self.Surfnum : GEOSURF=@self.Geosurf' + appendstring
                    ecal_surfaces.append(srfnum)
                    surfaces.Construction = 'HIGH_RES'
                elif surfaces.Boundarycond == 'EXTCALEXT':
                    # jx changed
                    # Original
                    # jx debugging IDENTICAL
                    # dummylines=dummylines + ' : EXTERNAL : ORI=@self.Orientation : TBOUNDARY = INPUT 1*TSI395_S@self.Surfnum : GEOSURF=@self.Geosurf' + appendstring
                    # Changed
                    dummylines=dummylines + ' : ORI=@self.Orientation : BOUNDARY = INPUT 1*TSI395_S@self.Surfnum   : GEOSURF=@self.Geosurf' + appendstring
                    ecal_surfaces.append(srfnum)
                    # pseudo-wall type of the surface's own construction (front films), see plan_hamt_pseudo_walls
                    surfaces.Construction = hamt_wall_names.get(ori_construction, HAMT_WALL_BASE)
                elif surfaces.Boundarycond == 'EXTVERTF':
                    dummylines=dummylines + ' : EXTERNAL : ORI=VERTF : WAGAIN=0 : WAGAINO=INPUT 1*WGAIN_O_S@self.Surfnum : GEOSURF=@self.Geosurf' + appendstring
                    if "VERTF" in manual_ori:
                        pass
                    else:
                        manual_ori.append("VERTF")
                #OC_extra_categories_start apparently the extra categories will not be executed by TRNBuild
                if 'OC_command_lines_global_variables' in sc.sticky[sc.doc.Path]:
                    exec(sc.sticky['OC_command_lines_categories'])
                #OC_extra_categories_end
                if surfaces.Orientation in extwall_surfaces_ori:
                    pass
                else:
                    extwall_surfaces.append(srfnum)
                    extwall_surfaces_ori.append(surfaces.Orientation)
                dummytype = surfaces.Type
                if surfaces.Type == 'ADDWINDOW':
                    surfaces.Type = 'WINDOW'
                for attr, value in surfaces.__dict__.iteritems():
                    dummylines=dummylines.replace('@self.{0}'.format(attr), str(value))
                if dummytype == 'ADDWINDOW':
                    surfaces.Type = 'ADDWINDOW'
                dummylines=dummylines.replace('@ANAME', Airnodes.Name)
                dummylines=dummylines.replace('@ZNAME', Airnodes.Zonename)
                surfaces.Construction = ori_construction
                if surfaces.Type == 'ADDWINDOW':
                    if surfaces.BSDFWindows == 1:
                        bsdf_surfaces.append(srfnum)
                    win_surfaces.append(srfnum)
                    if surfaces.Mshade == 'OUT' and surfaces.Frontback == 'FRONT':
                        if 'Complexshade' in dir(Airnodes):
                            dummylines = dummylines + ' : ESHADE=INPUT 1*YSHDE_S{0} : SHADECNTRL=ESHADE_INTERNAL'.format(surfaces.Surfnum,Airnodes.Name)
                        else:
                            dummylines = dummylines + ' : ESHADE=INPUT {0}*YSHD_TEMP_{1} : SHADECNTRL=ESHADE_INTERNAL'.format(surfaces.Eshadeglazingcover,Airnodes.Name)
                    elif surfaces.Mshade == 'INT' and surfaces.Frontback == 'FRONT':
                        if 'Complexshade' in dir(Airnodes):
                            dummylines = dummylines + ' : ISHADE=INPUT 1*YSHDI_S{0} : SHADECNTRL=ISHADE_INTERNAL'.format(surfaces.Surfnum,Airnodes.Name)
                        else:
                            dummylines = dummylines + ' : ISHADE=INPUT {0}*YSHD_TEMP_{1} : SHADECNTRL=ISHADE_INTERNAL'.format(surfaces.Ishadeglazingcover,Airnodes.Name)
                    elif surfaces.Mshade == 'IOT' and surfaces.Frontback == 'FRONT':
                        if 'Complexshade' in dir(Airnodes):
                            dummylines = dummylines + ' : ESHADE=INPUT 1*YSHDE_S{0} : SHADECNTRL=INTERNAL : ISHADE=INPUT 1*YSHDI_S{0}'.format(surfaces.Surfnum,Airnodes.Name,surfaces.Ishadeglazingcover)
                        else:
                            dummylines = dummylines + ' : ESHADE=INPUT {0}*YSHD_TEMP_{2} : SHADECNTRL=INTERNAL : ISHADE=INPUT {1}*YSHD_TEMP_{2}'.format(surfaces.Eshadeglazingcover,surfaces.Ishadeglazingcover,Airnodes.Name)
                constructionlines = constructionlines + dummylines + "\r\n"
                if surfaces.Subsurface:
                    for window_item in Airnodes.Surfaces:
                        for subsurface_item in surfaces.Subsurface:
                            if subsurface_item == window_item.Surface:
                                srfnum = window_item.Surfnum
                                window_item.Surfnum = srfnum
                                if window_item.BSDFWindows == 1:
                                    bsdf_surfaces.append(srfnum)
                                win_surfaces.append(srfnum)
                                dummylines=templates.Constr
                                window_item.Boundarytemp = surfaces.Boundarytemp
                                if surfaces.Boundarycond == 'EXTERNAL':
                                    dummylines=dummylines + ' : EXTERNAL : ORI=@self.Orientation : FSKY=@self.Fsky : GEOSURF=@self.Geosurf'
                                elif surfaces.Boundarycond == 'EXTBOUNDARY':
                                    dummylines=dummylines + ' : EXTERNAL : ORI=@self.Orientation : TBOUNDARY=@self.Boundarytemp : GEOSURF=@self.Geosurf'
                                elif surfaces.Boundarycond == 'EXTBOUNDADJ':
                                    dummylines=dummylines + ' : EXTERNAL : ORI=ADJ_BUILD : TBOUNDARY=@self.Boundarytemp : GEOSURF=@self.Geosurf'
                                elif surfaces.Boundarycond == 'EXTSKYBND':
                                    dummylines=dummylines + ' : EXTERNAL : ORI=@self.Orientation : TBOUNDARY=@self.Boundarytemp : WAGAIN=INPUT -1*QABSILW_S@self.Surfnum : GEOSURF=@self.Geosurf'
                                    tbd_surfaces.append(srfnum)
                                elif surfaces.Boundarycond in ('EXTCALC', 'EXTCALEXT'):
                                    dummylines=dummylines + ' : EXTERNAL : ORI=@self.Orientation : FSKY=@self.Fsky : GEOSURF=@self.Geosurf'
                                elif surfaces.Boundarycond == 'EXTVERTF':
                                    dummylines=dummylines + ' : EXTERNAL : ORI=@self.Orientation : FSKY=@self.Fsky : GEOSURF=@self.Geosurf'
                                #OC_extra_categories_start
                                if 'OC_command_lines_global_variables' in sc.sticky[sc.doc.Path]:
                                    exec(sc.sticky['OC_command_lines_categories_windows'])
                                #OC_extra_categories_end
                                for winattr, winvalue in window_item.__dict__.iteritems():
                                    dummylines=dummylines.replace('@self.{0}'.format(winattr), str(winvalue))
                                dummylines=dummylines.replace('@ANAME', Airnodes.Name)
                                dummylines=dummylines.replace('@ZNAME', Airnodes.Zonename)
                                if window_item.Mshade == 'OUT':
                                    if 'Complexshade' in dir(Airnodes):
                                        dummylines = dummylines + ' : ESHADE=INPUT 1*YSHDE_S{0}+{2} : SHADECNTRL=ESHADE_INTERNAL'.format(window_item.Surfnum,Airnodes.Name,window_item.Fixshade)
                                    else:
                                        if window_item.Shdinput == None:
                                            dummylines = dummylines + ' : ESHADE=INPUT {0}*YSHD_TEMP_{1}+{2} : SHADECNTRL=ESHADE_INTERNAL'.format(window_item.Eshadeglazingcover,Airnodes.Name,window_item.Fixshade)
                                        else:
                                            dummylines = dummylines + ' : ESHADE=INPUT {0}*{3}+{2} : SHADECNTRL=ESHADE_INTERNAL'.format(window_item.Eshadeglazingcover,Airnodes.Name,window_item.Fixshade,window_item.Shdinput)
                                elif window_item.Mshade == 'INT':
                                    if 'Complexshade' in dir(Airnodes):
                                        dummylines = dummylines + ' : ISHADE=INPUT 1*YSHDI_S{0}+{2} : SHADECNTRL=ISHADE_INTERNAL'.format(window_item.Surfnum,Airnodes.Name,window_item.Fixshade)
                                    else:
                                        if window_item.Shdinput == None:
                                            dummylines = dummylines + ' : ISHADE=INPUT {0}*YSHD_TEMP_{1}+{2} : SHADECNTRL=ISHADE_INTERNAL'.format(window_item.Ishadeglazingcover,Airnodes.Name,window_item.Fixshade)
                                        else:
                                            dummylines = dummylines + ' : ISHADE=INPUT {0}*{3}+{2} : SHADECNTRL=ISHADE_INTERNAL'.format(window_item.Ishadeglazingcover,Airnodes.Name,window_item.Fixshade,window_item.Shdinput)
                                elif window_item.Mshade == 'IOT':
                                    if 'Complexshade' in dir(Airnodes):
                                        dummylines = dummylines + ' : ESHADE=INPUT 1*YSHDE_S{0}+{2} : SHADECNTRL=INTERNAL : ISHADE=INPUT 1*YSHDI_S{0}'.format(window_item.Surfnum,Airnodes.Name,window_item.Ishadeglazingcover,window_item.Fixshade)
                                    else:
                                        if window_item.Shdinput == None:
                                            dummylines = dummylines + ' : ESHADE=INPUT {0}*YSHD_TEMP_{2}+{3} : SHADECNTRL=INTERNAL : ISHADE=INPUT {1}*YSHD_TEMP_{2}'.format(window_item.Eshadeglazingcover,window_item.Ishadeglazingcover,Airnodes.Name,window_item.Fixshade)
                                        else:
                                            dummylines = dummylines + ' : ESHADE=INPUT {0}*{4}+{3} : SHADECNTRL=INTERNAL : ISHADE=INPUT {1}*YSHD_TEMP_{2}'.format(window_item.Eshadeglazingcover,window_item.Ishadeglazingcover,Airnodes.Name,window_item.Fixshade,window_item.Shdinput)
                                elif window_item.Mshade == 'BSDFCOMPLEX':
                                    dummylines = dummylines + ' : CSHADE=INPUT 1*YSHDB_S{0}'.format(window_item.Surfnum)
                                elif window_item.Mshade == 'BSDFSIMPLE':
                                    dummylines = dummylines + ' : CSHADE=INPUT {0}*YSHD_TEMP_{1} : SHADECNTRL=INTERNAL'.format(window_item.Cshade,Airnodes.Name)
                                constructionlines = constructionlines + dummylines + "\r\n"
            elif surfaces.Boundarycond == 'BOUNDARY' or surfaces.Boundarycond == 'EXTFICALC' or surfaces.Boundarycond == 'BNDCALC' or surfaces.Boundarycond == 'EXTCALBND':
                srfnum = surfaces.Surfnum
                ori_construction = surfaces.Construction
                dummylines=templates.Constr
                if surfaces.Boundarycond == 'EXTCALBND':
                    dummylines=dummylines + ' : BOUNDARY=INPUT 1*TSI395_S@self.Surfnum : GEOSURF=@self.Geosurf' + appendstring
                else:
                    dummylines=dummylines + ' : BOUNDARY=@self.Boundarytemp : GEOSURF=@self.Geosurf' + appendstring
                if surfaces.Boundarycond == 'BNDCALC':
                    dummylines=dummylines + ' : WAGAIN=INPUT 1*WGAIN_I_S@self.Surfnum : WAGAINO=INPUT 1*WGAIN_O_S@self.Surfnum'
                    ecal_surfaces.append(srfnum)
                    surfaces.Construction = 'HIGH_RES'
                if surfaces.Boundarycond == 'EXTCALBND':
                    #dummylines=dummylines + ' : WAGAIN=INPUT 1*WGAIN_I_S@self.Surfnum : WAGAINO=INPUT 1*WGAIN_O_S@self.Surfnum'
                    ecal_surfaces.append(srfnum)
                    # pseudo-wall type of the surface's own construction (front films), see plan_hamt_pseudo_walls
                    surfaces.Construction = hamt_wall_names.get(ori_construction, HAMT_WALL_BASE)
                    # Type 395 input 7 is QABSI-QWG, so a user WAGAIN never reaches the HAMT wall, and a Type 395 output wired here counts the wall feedback twice
                    if getattr(surfaces, "Wagain", None) or getattr(surfaces, "Wagaino", None):
                        ghenv.Component.AddRuntimeMessage(w, "Surface %s (EXTCALBND, Type 395 wall): WAGAIN/WAGAINO is lost, Type 395 receives QABSI-QWG which excludes it, and a Type 395 output wired here would count the wall feedback twice (TSI395 is already the boundary temperature). Put wall heat into Type 395 (QheatKJ) instead."%srfnum)
                # thermal mirror wall (BOUNDARY = own TAIR): the derived wall type with the combined back film
                if surfaces.Boundarycond == 'BOUNDARY' and ori_construction in thermal_mirror_names and is_mirror_boundary_surface(surfaces, Airnodes.Name):
                    surfaces.Construction = thermal_mirror_names[ori_construction]
                if hasattr(surfaces,"Wagain") and surfaces.Wagain:
                    dummylines=dummylines + ' : WAGAIN=%s'%(surfaces.Wagain)
                if hasattr(surfaces,"Wagaino") and surfaces.Wagaino:
                    dummylines=dummylines + ' : WAGAINO=%s'%(surfaces.Wagaino)
                for attr, value in surfaces.__dict__.iteritems():
                    dummylines=dummylines.replace('@self.{0}'.format(attr), str(value))
                dummylines=dummylines.replace('@ANAME', Airnodes.Name)
                dummylines=dummylines.replace('@ZNAME', Airnodes.Zonename)
                surfaces.Construction = ori_construction
                constructionlines = constructionlines + dummylines + "\r\n"
                if surfaces.Boundarycond == 'EXTFICALC':
                    efical_surfaces.append(srfnum)
            elif surfaces.Boundarycond == 'ADJACENT' and surfaces.Type != 'WINDOW':
                srfnum = surfaces.Surfnum
                dummylines=templates.Constr
                dummylines=dummylines + ' : ADJACENT=@self.Adjairnode : ADJ_SURF=@self.Adjsurf : @self.Frontback : COUPL=@self.Coupling : ORI=@self.Orientation : GEOSURF=@self.Geosurf' + appendstring
                dummytype = surfaces.Type
                if surfaces.Type == 'ADDWINDOW':
                    surfaces.Type = 'WINDOW'
                for attr, value in surfaces.__dict__.iteritems():
                    dummylines=dummylines.replace('@self.{0}'.format(attr), str(value))
                if dummytype == 'ADDWINDOW':
                    surfaces.Type = 'ADDWINDOW'
                dummylines=dummylines.replace('@ANAME', Airnodes.Name)
                dummylines=dummylines.replace('@ZNAME', Airnodes.Zonename)
                if surfaces.Type == 'ADDWINDOW':
                    if surfaces.BSDFWindows == 1:
                        bsdf_surfaces.append(srfnum)
                    win_surfaces.append(srfnum)
                    if surfaces.Mshade == 'OUT' and surfaces.Frontback == 'FRONT':
                        if 'Complexshade' in dir(Airnodes):
                            dummylines = dummylines + ' : ESHADE=INPUT 1*YSHDE_S{0} : SHADECNTRL=ESHADE_INTERNAL'.format(surfaces.Surfnum,Airnodes.Name)
                        else:
                            dummylines = dummylines + ' : ESHADE=INPUT {0}*YSHD_TEMP_{1} : SHADECNTRL=ESHADE_INTERNAL'.format(surfaces.Eshadeglazingcover,Airnodes.Name)
                    elif surfaces.Mshade == 'INT' and surfaces.Frontback == 'FRONT':
                        if 'Complexshade' in dir(Airnodes):
                            dummylines = dummylines + ' : ISHADE=INPUT 1*YSHDI_S{0} : SHADECNTRL=ISHADE_INTERNAL'.format(surfaces.Surfnum,Airnodes.Name)
                        else:
                            dummylines = dummylines + ' : ISHADE=INPUT {0}*YSHD_TEMP_{1} : SHADECNTRL=ISHADE_INTERNAL'.format(surfaces.Ishadeglazingcover,Airnodes.Name)
                    elif surfaces.Mshade == 'IOT' and surfaces.Frontback == 'FRONT':
                        if 'Complexshade' in dir(Airnodes):
                            dummylines = dummylines + ' : ESHADE=INPUT 1*YSHDE_S{0} : SHADECNTRL=INTERNAL : ISHADE=INPUT 1*YSHDI_S{0}'.format(surfaces.Surfnum,Airnodes.Name,surfaces.Ishadeglazingcover)
                        else:
                            dummylines = dummylines + ' : ESHADE=INPUT {0}*YSHD_TEMP_{2} : SHADECNTRL=INTERNAL : ISHADE=INPUT {1}*YSHD_TEMP_{2}'.format(surfaces.Eshadeglazingcover,surfaces.Ishadeglazingcover,Airnodes.Name)
                constructionlines = constructionlines + dummylines + "\r\n"
                if surfaces.Subsurface:
                    for window_item in Airnodes.Surfaces:
                        for subsurface_item in surfaces.Subsurface:
                            if subsurface_item == window_item.Surface:
                                window_item.Frontback = surfaces.Frontback
                                srfnum = window_item.Surfnum
                                if window_item.BSDFWindows == 1:
                                    bsdf_surfaces.append(srfnum)
                                win_surfaces.append(srfnum)
                                dummylines=templates.Constr
                                window_item.Boundarytemp = surfaces.Boundarytemp
                                dummylines=dummylines + ' : ADJACENT=@self.Adjairnode : ADJ_SURF=@self.Adjsurf : @self.Frontback : COUPL=@self.Coupling : ORI=@self.Orientation : GEOSURF=@self.Geosurf'
                                for winattr, winvalue in window_item.__dict__.iteritems():
                                    dummylines=dummylines.replace('@self.{0}'.format(winattr), str(winvalue))
                                dummylines=dummylines.replace('@ANAME', Airnodes.Name)
                                dummylines=dummylines.replace('@ZNAME', Airnodes.Zonename)
                                if window_item.Mshade == 'OUT' and window_item.Frontback == 'FRONT':
                                    if 'Complexshade' in dir(Airnodes):
                                        dummylines = dummylines + ' : ESHADE=INPUT 1*YSHDE_S{0} : SHADECNTRL=ESHADE_INTERNAL'.format(window_item.Surfnum,Airnodes.Name)
                                    else:
                                        dummylines = dummylines + ' : ESHADE=INPUT {0}*YSHD_TEMP_{1} : SHADECNTRL=ESHADE_INTERNAL'.format(window_item.Eshadeglazingcover,Airnodes.Name)
                                elif window_item.Mshade == 'INT' and window_item.Frontback == 'FRONT':
                                    if 'Complexshade' in dir(Airnodes):
                                        dummylines = dummylines + ' : ISHADE=INPUT 1*YSHDI_S{0} : SHADECNTRL=ISHADE_INTERNAL'.format(window_item.Surfnum,Airnodes.Name)
                                    else:
                                        dummylines = dummylines + ' : ISHADE=INPUT {0}*YSHD_TEMP_{1} : SHADECNTRL=ISHADE_INTERNAL'.format(window_item.Ishadeglazingcover,Airnodes.Name)
                                elif window_item.Mshade == 'IOT' and window_item.Frontback == 'FRONT':
                                    if 'Complexshade' in dir(Airnodes):
                                        dummylines = dummylines + ' : ESHADE=INPUT 1*YSHDE_S{0} : SHADECNTRL=INTERNAL : ISHADE=INPUT 1*YSHDI_S{0}'.format(window_item.Surfnum,Airnodes.Name,window_item.Ishadeglazingcover)
                                    else:
                                        dummylines = dummylines + ' : ESHADE=INPUT {0}*YSHD_TEMP_{2} : SHADECNTRL=INTERNAL : ISHADE=INPUT {1}*YSHD_TEMP_{2}'.format(window_item.Eshadeglazingcover,window_item.Ishadeglazingcover,Airnodes.Name)
                                constructionlines = constructionlines + dummylines + "\r\n"
        templlines=templlines.replace('@constructiondef', constructionlines)
        Airnodes.Winsurfaces = win_surfaces
        Airnodes.Bsdfsurfaces = bsdf_surfaces
        Airnodes.Wallsurfaces = wall_surfaces
        Airnodes.Floorsurfaces = floor_surfaces
        Airnodes.Ceilingsurfaces = ceiling_surfaces
        Airnodes.Roofsurfaces = roof_surfaces
        Airnodes.Extwallsurfaces = extwall_surfaces
        Airnodes.Extwallsurfacesori = extwall_surfaces_ori
        Airnodes.Tbdsurfaces = tbd_surfaces
        Airnodes.Ecalsurfaces = ecal_surfaces
        Airnodes.Eficalsurfaces = efical_surfaces
        Airnodes.Manualorientation = manual_ori
        # Zone Regime definition starting from here
        regimelines = ''
        for gain_item in Airnodes.Gain:
            if gain_item.Name:
                dummy = gain_item.Name
                scale1 = 1
                if gain_item.Schedule != '':
                    if "INPUT" in gain_item.Schedule:
                        scale1 = '%s'%gain_item.Schedule
                    else:
                        scale1 = 'SCHEDULE 1*%s'%gain_item.Schedule
                scale2 = 1
                if gain_item.Annual != '' and gain_item.Annual != None:
                    scale2 = 'SCHEDULE 1*%s'%gain_item.Annual
                if gain_item.Category == 'LIGHTS':
                    if gain_item.Dctrl is not None:
                        if Airnodes.Daylightctrl:
                            for di, dcitem in enumerate(Airnodes.Daylightctrl):
                                regimelines= regimelines + '{0} = {1} : SCALE= {2} : GEOPOS= 0 : SCALE2= {5} : FRAC_REFAREA= {3} : DLIGHT_CTRL={4}'.format(gain_item.Type, dummy + '_' + Airnodes.Name, scale1, dcitem.Frac_refarea, gain_item.Dctrl + str(di)  + '_' + Airnodes.Name, scale2)
                                if di == len(Airnodes.Daylightctrl) - 1:
                                    pass
                                else:
                                    regimelines += '\n'
                    else:
                        regimelines= regimelines + '{0} = {1} : SCALE= {2} : GEOPOS= 0 : SCALE2= {4} : FRAC_REFAREA= {3}'.format(gain_item.Type, dummy + '_' + Airnodes.Name, scale1, gain_item.Frac_refarea, scale2)
                else:
                    regimelines= regimelines + '{0} = {1} : SCALE= {2} : GEOPOS= 0 : SCALE2= {3} : FRAC_REFAREA= {4}'.format(gain_item.Type, dummy + '_' + Airnodes.Name, scale1, scale2, gain_item.Frac_refarea)
                regimelines = regimelines + '\r\n'
        hamt_gain_exists = False
        for g in Airnodes.Gain:
            if g.Name and 'HAMT_Gain' in str(g.Name):
                hamt_gain_exists = True
                break
        if has_hamt_surfaces(Airnodes) and not hamt_gain_exists:   # the zones that get GAIN HAMT_Gain_<zone> in printbuitoppart
            regimelines= regimelines + 'GAIN = HAMT_Gain_{0} : SCALE= 1 : GEOPOS= 0 : SCALE2= 1 : FRAC_REFAREA= -1'.format(Airnodes.Name)
            regimelines = regimelines + '\r\n'
        if Airnodes.Comfort:
            for subitem in Airnodes.Comfort:
                subitem.Setcoll = []
                Airnodes.ComfId = []
                for subitem2 in Airnodes.Comfortpts:
                    comfid = comfid + 1
                    Airnodes.ComfId.append(comfid)
                    if subitem.Type == 'SET':
                        subitem.Setcoll.append(comfid)
                    regimelines= regimelines + '{0} = {1} : COMFID= {2} : MRT= INTERNAL : GEOPOS= {3}'.format('COMFORT', subitem.Name + '_' + Airnodes.Name , comfid, comfid)
                    regimelines = regimelines + '\r\n'
        if Airnodes.Infiltration:
            dummy = Airnodes.Infiltration.Name
            regimelines= regimelines + '{0} = {1}'.format(Airnodes.Infiltration.Type.upper(), dummy + '_' + Airnodes.Name)
            regimelines = regimelines + '\r\n'
        for ventilation_item in Airnodes.Ventilation:
            dummy = ventilation_item.Name
            if ventilation_item.Type == 'STACKVENTILATION':
                regimelines= regimelines + 'VENTILATION = {0}'.format(dummy + '_' + Airnodes.Name)
                regimelines = regimelines + '\r\n'
            else:
                regimelines= regimelines + 'VENTILATION = {0}'.format(dummy + '_MV_' + Airnodes.Name)
                regimelines = regimelines + '\r\n'
                if ventilation_item.Hybrid == 1:
                    regimelines= regimelines + 'VENTILATION = {0}'.format(dummy + '_HV_' + Airnodes.Name)
                    regimelines = regimelines + '\r\n'
        for Coupling_item in Coupling_coll:
            if Coupling_item.Target == Airnodes.Name:
                dummy = Coupling_item.Name
                regimelines= regimelines + 'VENTILATION = {0}'.format(dummy)
                regimelines = regimelines + '\r\n'
        if Airnodes.Heating:
            dummy = Airnodes.Heating.Name
            dummy = dummy.replace("@aname",Airnodes.Name)
            regimelines= regimelines + '{0} = {1}'.format(Airnodes.Heating.Type.upper(), dummy)
            regimelines = regimelines + '\r\n'
        if Airnodes.Cooling:
            dummy = Airnodes.Cooling.Name
            dummy = dummy.replace("@aname",Airnodes.Name)
            regimelines= regimelines + '{0} = {1}'.format(Airnodes.Cooling.Type.upper(), dummy)
            regimelines = regimelines + '\r\n'
        if len(zonedict[Airnodes.Zonename]) > 1 and trnflowfound == 1:
                for subairnode in zonedict[Airnodes.Zonename]:
                    if subairnode == Airnodes.Name:
                        pass
                    else:
                        regimelines += 'ADJACENT_AIRNODE= %s : COUPL= 0\r\n'%subairnode
        templlines=templlines.replace('@regimedef', regimelines)
        templlines = templlines + '\r\n'
        lines.append(zoneairnodeinfo)
        if Airnodes.Zonename not in Zone_name_coll:
            lines.append(templlinesZone)
            Zone_name_coll.append(Airnodes.Zonename)
        lines.append(templlines)
    return lines
@timing
def printbuibotpart(dataset):
    lines = []
    # Intermediate part with Window library
    Airnodenames = ''
    for Airnodes in dataset:
        Airnodenames = Airnodes.Name + ' ' + Airnodenames
    templlines=templates.Output
    templlines=templlines.replace('@timebase', str(Timebase))
    templlines=templlines.replace('@airnodes', Airnodenames)
    templlines=templlines.replace('@singleairnode', dataset[-1].Name)
    add_schedules = ''
    collect_schedules = []
    for Airnodes in dataset:
        if Airnodes.Gain:
            for items in Airnodes.Gain:
                if items.Schedule != '':
                    collect_schedules.append(items.Schedule)
                if items.Annual != '' and items.Annual != None:
                    collect_schedules.append(items.Annual)
        if Airnodes.Heating:
            collect_schedules.append(Airnodes.Heating.Schedule)
        if Airnodes.Cooling:
            collect_schedules.append(Airnodes.Cooling.Schedule)
        if Airnodes.Dhw:
            collect_schedules.append(Airnodes.Dhw.Schedule)
        if Airnodes.Infiltration:
            collect_schedules.append(Airnodes.Infiltration.Schedule)
            if hasattr(Airnodes.Infiltration,'Annual') and Airnodes.Infiltration.Annual != '' and Airnodes.Infiltration.Annual != None:
                collect_schedules.append(Airnodes.Infiltration.Annual)
        if Airnodes.Ventilation:
            for items in Airnodes.Ventilation:
                if 'NOT' in items.Schedule:
                    pass
                else:
                    collect_schedules.append(items.Schedule)
        if Airnodes.Daylightctrl:
            for dcitem in Airnodes.Daylightctrl:
                collect_schedules.append(dcitem.Schedule)
    for item in dataset:
        for subitem in item.Surfaces:
            if subitem.Scheduleheating:
                collect_schedules.append(subitem.Scheduleheating)
            if subitem.Schedulecooling:
                collect_schedules.append(subitem.Schedulecooling)
    collect_schedules = list(set(collect_schedules))
    for items in collect_schedules:
        add_schedules = add_schedules + items + ', '
    templlines=templlines.replace('@addschedules', add_schedules)
    activelayeroutput = ''
    for Airnodes in dataset:
        if len(Airnodes.Al1surfaces) > 0 or len(Airnodes.Al2surfaces) > 0 :
            dummy_al = ''
            for al_items in Airnodes.Al1surfaces:
                dummy_al = dummy_al + str(al_items) + ', '
            for al_items in Airnodes.Al2surfaces:
                dummy_al = dummy_al + str(al_items) + ', '
            activelayeroutput =  activelayeroutput +  '\r\nAIRNODES = {0}\r\n'.format(Airnodes.Name)
            activelayeroutput =  activelayeroutput +  ' NTYPES =  58 : SURF = {0}  : TOFL - fluid outlet temperature of active layer\r\n'.format(dummy_al)
            activelayeroutput =  activelayeroutput +  '        =  57 : SURF = {0}  : TALM - node temperature of active layer\r\n'.format(dummy_al)
            activelayeroutput =  activelayeroutput +  '        =  17 : SURF = {0}  : TSI - inside surface temperature\r\n'.format(dummy_al)
            activelayeroutput =  activelayeroutput +  '        =  59 : SURF = {0}  : QALFL - energy input by fluid of active layer\r\n'.format(dummy_al)
            activelayeroutput =  activelayeroutput +  '        =  19 : SURF = {0}  : QCOMI - energy from  inside surface incl. conv. to the air and l-wave radiation to other surfaces\r\n'.format(dummy_al)
        elif activelayeroutput is not '':
            pass
        else:
            activelayeroutput = ''
    winouttempllines = ''
    for Airnodes in dataset:
        if len(window_coll) > 0:
            Airnodes.Winsurfaces = window_coll
        if (Airnodes.Winsurfaces and len(Airnodes.Winsurfaces) > 0):
            winouttempllines = winouttempllines + templates.Winoutput
            windowoutput = ''
            for win_item in Airnodes.Winsurfaces:
                windowoutput = windowoutput + str(win_item) + ', '
            winouttempllines=winouttempllines.replace('@airnodes', Airnodes.Name)
            winouttempllines=winouttempllines.replace('@winsurfaces', windowoutput)
    bsdfouttempllines = ''
    for Airnodes in dataset:
        if (Airnodes.Bsdfsurfaces and len(Airnodes.Bsdfsurfaces) > 0):
            bsdfouttempllines = bsdfouttempllines + templates.Bsdfoutput
            bsdfoutput = ''
            for win_item in Airnodes.Bsdfsurfaces:
                bsdfoutput = bsdfoutput + str(win_item) + ', '
            bsdfouttempllines=bsdfouttempllines.replace('@airnodes', Airnodes.Name)
            bsdfouttempllines=bsdfouttempllines.replace('@bsdfsurfaces', bsdfoutput)
    tbdouttempllines = ''
    for Airnodes in dataset:
        if (Airnodes.Tbdsurfaces and len(Airnodes.Tbdsurfaces) > 0):
            tbdouttempllines = tbdouttempllines + templates.Tbdoutput
            tbdoutput = ''
            for tbd_item in Airnodes.Tbdsurfaces:
                tbdoutput = tbdoutput + str(tbd_item) + ', '
            tbdouttempllines=tbdouttempllines.replace('@airnodes', Airnodes.Name)
            tbdouttempllines=tbdouttempllines.replace('@tbdsurfaces', tbdoutput)
    ecalouttempllines = ''
    for Airnodes in dataset:
        if (Airnodes.Ecalsurfaces and len(Airnodes.Ecalsurfaces) > 0):
            ecalouttempllines = ecalouttempllines + templates.Ecaloutput
            ecaloutput = ''
            for ecal_item in Airnodes.Ecalsurfaces:
                ecaloutput = ecaloutput + str(ecal_item) + ', '
            ecalouttempllines=ecalouttempllines.replace('@airnodes', Airnodes.Name)
            ecalouttempllines=ecalouttempllines.replace('@ecalsurfaces', ecaloutput)
    eficalouttempllines = ''
    for Airnodes in dataset:
        if (Airnodes.Eficalsurfaces and len(Airnodes.Eficalsurfaces) > 0):
            eficalouttempllines = eficalouttempllines + templates.Eficaloutput
            eficaloutput = ''
            for efical_item in Airnodes.Eficalsurfaces:
                eficaloutput = eficaloutput + str(efical_item) + ', '
            eficalouttempllines=eficalouttempllines.replace('@airnodes', Airnodes.Name)
            eficalouttempllines=eficalouttempllines.replace('@eficalsurfaces', eficaloutput)
    wallouttempllines = ''
    extwsurforicoll = []
    for Airnodes in dataset:
        if len(Airnodes.Extwallsurfaces) > 0:
            walloutput = ''
            for wall_item in range(len(Airnodes.Extwallsurfaces)):
                if (Airnodes.Extwallsurfacesori[wall_item] in extwsurforicoll):
                    pass
                else:
                    extwsurforicoll.append(Airnodes.Extwallsurfacesori[wall_item])
                    walloutput = walloutput + str(Airnodes.Extwallsurfaces[wall_item]) + ', '
            if walloutput is not '':
                wallouttempllines = wallouttempllines + templates.Walloutput
                wallouttempllines=wallouttempllines.replace('@airnodes', Airnodes.Name)
                wallouttempllines=wallouttempllines.replace('@wallsurfaces', walloutput)
    balouttempllines = ''
    for Airnodes in dataset:
        balsurfaces = []
        balsurfaces.extend(Airnodes.Winsurfaces)
        balsurfaces.extend(Airnodes.Wallsurfaces)
        balsurfaces.extend(Airnodes.Floorsurfaces)
        balsurfaces.extend(Airnodes.Ceilingsurfaces)
        balsurfaces.extend(Airnodes.Roofsurfaces)
        baloutput = ''
        baloutput = ', '.join(str(x) for x in balsurfaces)
        baloutput += ', '
        balouttempllines = balouttempllines + templates.Baloutput
        balouttempllines=balouttempllines.replace('@airnodes', Airnodes.Name)
        balouttempllines=balouttempllines.replace('@balsurfaces', baloutput)
    comfortouttempllines = ''
    counter = 0
    for Airnodes in dataset:
        if Airnodes.Comfort:
            comfortouttempllines = comfortouttempllines + templates.Comfortoutput
            comfortoutput = ''
            for subitem in Airnodes.Comfort:
                #print Airnodes.Name
                for cid in Airnodes.ComfId:
                    #counter = counter + 1
                    comfortoutput = comfortoutput + str(cid) + ', '
            comfortouttempllines=comfortouttempllines.replace('@airnodes', Airnodes.Name)
            comfortouttempllines=comfortouttempllines.replace('@comfort_points', comfortoutput)
    daylightouttempllines = ''
    for Airnodes in dataset:
        if Airnodes.Daylightctrl is not None:
            found = 0
            schedule = ''
            for dcitem in Airnodes.Daylightctrl:
                if dcitem.Print == True:
                    found = 1
                    schedule = dcitem.Schedule
            if found == 1:
                daylightouttempllines = daylightouttempllines + templates.Daylightoutput
                daylightouttempllines=daylightouttempllines.replace('@airnodes', Airnodes.Name)
                daylightouttempllines=daylightouttempllines.replace('@schedule', schedule)
    addouttempllines = ''
    linkdict = {}
    for Airnodes in dataset:
        if Airnodes.Output:
            onlyairlinks = 1
            for oi,output_item in enumerate(Airnodes.Output):
                if output_item and output_item.Type != 'AIRLINKS':
                    onlyairlinks = 0
            if onlyairlinks == 0:
                addouttempllines = addouttempllines + ' AIRNODES = {0}\r\n NTYPES '.format(Airnodes.Name)
            linkdict[Airnodes.Name] = {}
            for oi,output_item in enumerate(Airnodes.Output):
                if output_item:
                    pass
                else:
                    continue
                if oi == 0:
                    stri = ''
                else:
                    stri = '        '
                for ni,ntype in enumerate(output_item.NtypesNo):
                    #print ntype
                    if output_item.Type == 'SURFACE':
                        addouttempllines = addouttempllines + '{1}= {0} : SURF = '.format(ntype,stri)
                        for srf in output_item.SurfaceID:
                            addouttempllines = addouttempllines + '{0},'.format(srf)
                    elif output_item.Type == 'COMFORT':
                        addouttempllines = addouttempllines + '{1}= {0} : COMFID = '.format(ntype,stri)
                        for cmf in Airnodes.ComfId:
                            addouttempllines = addouttempllines + '{0},'.format(cmf)
                    elif output_item.Type == 'AIRLINKS':
                        for subname in output_item.Name:
                            if '%s%s'%(subname,Airnodes.Name) not in linkdict[Airnodes.Name]:
                                linkdict[Airnodes.Name]['%s%s'%(subname,Airnodes.Name)] = {}
                            if 'NTYPE' not in linkdict[Airnodes.Name]['%s%s'%(subname,Airnodes.Name)]:
                                linkdict[Airnodes.Name]['%s%s'%(subname,Airnodes.Name)]['NTYPE'] = []
                            if 'LABEL' not in linkdict[Airnodes.Name]['%s%s'%(subname,Airnodes.Name)]:
                                linkdict[Airnodes.Name]['%s%s'%(subname,Airnodes.Name)]['LABEL'] = []
                            linkdict[Airnodes.Name]['%s%s'%(subname,Airnodes.Name)]['NTYPE'].append( str(ntype) )
                            linkdict[Airnodes.Name]['%s%s'%(subname,Airnodes.Name)]['LABEL'].append( str(output_item.Ntype[ni]) )
                        continue
                    else:
                        addouttempllines = addouttempllines + '{1}= {0}'.format(ntype,stri)
                    addouttempllines = addouttempllines + ' : {}\r\n'.format(output_item.Ntype[ni])
            # Ensure HCONVI (NTYPE 108) output exists for HAMT surfaces (required by Type395 wiring)
            if len(Airnodes.Ecalsurfaces) > 0:
                hconvi_covered = []
                for output_item in Airnodes.Output:
                    if output_item and output_item.Type == 'SURFACE':
                        for ni, ntype in enumerate(output_item.NtypesNo):
                            if str(ntype) == '108':
                                hconvi_covered.extend([str(s) for s in output_item.SurfaceID])
                hconvi_missing = [str(s) for s in Airnodes.Ecalsurfaces if str(s) not in hconvi_covered]
                if hconvi_missing:
                    if onlyairlinks == 1:
                        addouttempllines = addouttempllines + ' AIRNODES = {0}\r\n NTYPES '.format(Airnodes.Name)
                        stri_h = ''
                    else:
                        stri_h = '        '
                    addouttempllines = addouttempllines + '{1}= {0} : SURF = '.format('108', stri_h)
                    for srf in hconvi_missing:
                        addouttempllines = addouttempllines + '{0},'.format(srf)
                    addouttempllines = addouttempllines + '   : HCONVI - pure convective HTC on FRONT (inside)\r\n'
    if trnflowfound == 1 or trnflowfound == -1:
        trnflowtempllines = templates.Trnflow
        pollutants = ''
        cracks     = ''
        crackdefined = []
        fans       = ''
        straightducts = ''
        flowcontrollers = ''
        largeopenings = ''
        testdata    = ''
        externalnodes = ''
        auxiliarynodes = ''
        thermalzones = ''
        windvelocityprofile = ''
        airlinknetwork = ''
        linkid = 0
        for Airnode in dataset:
            foundkey = []
            largeopendict = {}
            frheightdict = {}
            newlodict = {}
            if hasattr(Airnode, 'Trnflow'):
                linkoutput = {}
                if Airnode.Trnflow.__class__.__name__ == 'THERMALZONES':
                    if Airnode.Trnflow.Co2perperson > 0:
                        for gitem in Airnode.Gain:
                            if gitem.Personsgain == 1:
                                Airnode.Trnflow.Source = 'SCHEDULE %s*%s'%(Airnode.Floorarea / Airnode.Areaperperson * Airnode.Trnflow.Co2perperson, gitem.Schedule)
                    thermalzones = thermalzones + printsingledata(Airnode.Trnflow,'Thermalzones')
                    counter = 0
                    for surfaces in Airnode.Surfaces:
                        if hasattr(surfaces, 'Trnflow'):
                            if surfaces.Trnflow.__class__.__name__ == 'LARGEOPENINGS':
                                zarray = []
                                for vertices in surfaces.Vertices:
                                    zarray.append(vertices.Z)
                                minz = round(min(zarray),2)
                                iteminfo = rc.Geometry.AreaMassProperties.Compute(surfaces.Faces)
                                cpts = iteminfo.Centroid
                                node = rc.Geometry.Point3d(cpts.X, cpts.Y, minz)
                                if surfaces.Trnflow.Name in foundkey:
                                    frhcheck = True if newlodict['%s%s%s'%(surfaces.Trnflow.Name,counter,Airnode.Name)].Frheight == minz else False
                                    dictcheck = True if largeopendict[surfaces.Trnflow.Name].__dict__ == surfaces.Trnflow.__dict__ else False
                                    wheicheck = True if newlodict['%s%s%s'%(surfaces.Trnflow.Name,counter,Airnode.Name)].Loheight == surfaces.Wheig else False
                                    if frhcheck and dictcheck and wheicheck:
                                        if surfaces.Trnflow.Lowidth == None:
                                            newlodict['%s%s%s'%(surfaces.Trnflow.Name,counter,Airnode.Name)].Lowidth += surfaces.Wwid
                                        else:
                                            newlodict['%s%s%s'%(surfaces.Trnflow.Name,counter,Airnode.Name)].Lowidth += surfaces.Trnflow.Lowidth
                                    else:
                                        counter += 1
                                        newlodict['%s%s%s'%(surfaces.Trnflow.Name,counter,Airnode.Name)] = copy.deepcopy( surfaces.Trnflow )
                                        newlodict['%s%s%s'%(surfaces.Trnflow.Name,counter,Airnode.Name)].Name = '%s%s%s'%(surfaces.Trnflow.Name,counter,Airnode.Name)
                                        if surfaces.Trnflow.Frheight == None:
                                            newlodict['%s%s%s'%(surfaces.Trnflow.Name,counter,Airnode.Name)].Frheight = minz
                                            newlodict['%s%s%s'%(surfaces.Trnflow.Name,counter,Airnode.Name)].Refpoint = node
                                        if surfaces.Trnflow.Lowidth == None:
                                            newlodict['%s%s%s'%(surfaces.Trnflow.Name,counter,Airnode.Name)].Lowidth = surfaces.Wwid
                                        if surfaces.Trnflow.Loheight == None:
                                            newlodict['%s%s%s'%(surfaces.Trnflow.Name,counter,Airnode.Name)].Loheight = surfaces.Wheig
                                else:
                                    counter += 1
                                    largeopendict[surfaces.Trnflow.Name] = copy.deepcopy( surfaces.Trnflow )
                                    newlodict['%s%s%s'%(surfaces.Trnflow.Name,counter,Airnode.Name)] = copy.deepcopy( surfaces.Trnflow )
                                    newlodict['%s%s%s'%(surfaces.Trnflow.Name,counter,Airnode.Name)].Name = '%s%s%s'%(surfaces.Trnflow.Name,counter,Airnode.Name)
                                    if surfaces.Trnflow.Frheight == None:
                                        newlodict['%s%s%s'%(surfaces.Trnflow.Name,counter,Airnode.Name)].Frheight = minz
                                        newlodict['%s%s%s'%(surfaces.Trnflow.Name,counter,Airnode.Name)].Refpoint = node
                                    if surfaces.Trnflow.Lowidth == None:
                                        newlodict['%s%s%s'%(surfaces.Trnflow.Name,counter,Airnode.Name)].Lowidth = surfaces.Wwid
                                    if surfaces.Trnflow.Loheight == None:
                                        newlodict['%s%s%s'%(surfaces.Trnflow.Name,counter,Airnode.Name)].Loheight = surfaces.Wheig
                                    foundkey.append(surfaces.Trnflow.Name)
                    for surfaces in newlodict:
                        if 1 > 0:
                            if 1 > 0:
                                #if 'EXT' in surfaces.Boundarycond:
                                if 1 > 0:
                                    largeopenings += printsingledata(newlodict[surfaces],'Largeopenings')
                                    airlink = sc.sticky[sc.doc.Path]["AIRLINKNETWORK"]()
                                    airlink.Link = newlodict[surfaces].Name
                                    airlink.Frnode = newlodict[surfaces].Frnode
                                    airlink.Tonode = Airnode.Name
                                    #for subitem in TrnflowNetwork:
                                    #    if subitem.__class__.__name__ == 'EXTERNALNODES' and subitem.Name == surfaces.Trnflow.Frnode:
                                    #        airlink.Frheight = newlodict[surfaces].Frheight - subitem.Refheight
                                    #print Airnode.Name
                                    #print airlink.Tonode
                                    FrRefheight = 0
                                    for aitem in dataset:
                                        if aitem.Name == airlink.Frnode:
                                            FrRefheight = aitem.Trnflow.Refheight
                                    airlink.Frheight = newlodict[surfaces].Frheight - FrRefheight
                                    airlink.Toheight = newlodict[surfaces].Frheight - Airnode.Trnflow.Refheight
                                    airlink.Wiownhf = newlodict[surfaces].Wiownhf
                                    if 'INPUT' in newlodict[surfaces].Fscale:
                                        airlink.Fscale = newlodict[surfaces].Fscale + '_%s'%Airnode.Name
                                    else:
                                        airlink.Fscale = newlodict[surfaces].Fscale
                                    linkid += 1
                                    airlink.Id = linkid
                                    airlinknetwork = airlinknetwork + printsingledata(airlink,'Airlinknetwork')
                                    if Airnode.Name in linkdict:
                                        if airlink.Link in linkdict[Airnode.Name]:
                                            linkoutput[airlink.Id] = {}
                                            linkoutput[airlink.Id]['Name'] = airlink.Link
                                            linkoutput[airlink.Id]['Ntype'] = linkdict[Airnode.Name][airlink.Link]['NTYPE']
                                            linkoutput[airlink.Id]['Label'] = linkdict[Airnode.Name][airlink.Link]['LABEL']
                outlinknames = ''
                linkoutarray = []
                for outkey in linkoutput:
                    outlinknames += '%s[%s] '%(linkoutput[outkey]['Name'], outkey)
                    for oi, outkeysub in enumerate(linkoutput[airlink.Id]['Ntype']):
                        linkoutarray.append(' = {0} : {1}\r\n'.format(outkeysub,linkoutput[outkey]['Label'][oi]))
                if outlinknames != '':
                    addouttempllines = addouttempllines + ' AIRLINKS = {0}\r\n NTYPES '.format(outlinknames)
                if len(linkoutarray) > 0:
                    dummyarray = list(set(linkoutarray))
                    for ditem in dummyarray:
                        addouttempllines += ditem
        #print addouttempllines
        for subitem in TrnflowNetwork:
            if subitem.__class__.__name__ == 'POLLUTANTS':
                pollutants = pollutants + printsingledata(subitem,'Pollutants')
            if subitem.__class__.__name__ == 'LARGEOPENINGS':
                if subitem.Name not in foundkey:
                    largeopenings = largeopenings + printsingledata(subitem,'Largeopenings')
                airlink = sc.sticky[sc.doc.Path]["AIRLINKNETWORK"]()
                airlink.Link = subitem.Name
                airlink.Frnode = subitem.Frnode
                airlink.Tonode = subitem.Tonode
                airlink.Frheight = subitem.Frheight
                #changing Toheight based on horizontal or vertical
                if subitem.Wiownhf == 0:
                    airlink.Toheight = subitem.Toheight
                else:
                    if subitem.Toheight != None:
                        airlink.Toheight = subitem.Toheight
                    else:
                        airlink.Toheight = subitem.Frheigt
                #airlink.Toheight = subitem.Toheight
                airlink.Wiownhf = subitem.Wiownhf
                airlink.Fscale = subitem.Fscale
                linkid += 1
                airlink.Id = linkid
                airlinknetwork = airlinknetwork + printsingledata(airlink,'Airlinknetwork')
                if hasattr(subitem,'Output') and subitem.Output != '':
                    outlinknames = '%s[%s] '%(subitem.Name, airlink.Id)
                    if outlinknames != '':
                        addouttempllines = addouttempllines + ' AIRLINKS = {0}\r\n NTYPES '.format(outlinknames)
                    for outitem in subitem.Output:
                        for sui, suboutitem in enumerate(outitem.NtypesNo):
                            linkoutarray.append(' = {0} : {1}\r\n'.format(suboutitem,outitem.Ntype[sui]))
                        if len(linkoutarray) > 0:
                            dummyarray = list(set(linkoutarray))
                            for ditem in dummyarray:
                                addouttempllines += ditem
            if subitem.__class__.__name__ == 'CRACKS':
                if subitem.Name not in crackdefined:
                    crackdefined.append(subitem.Name)
                    cracks = cracks + trnflow_crack_type(subitem)
                airlink = sc.sticky[sc.doc.Path]["AIRLINKNETWORK"]()
                airlink.Link = subitem.Name
                airlink.Frnode = subitem.Frnode
                airlink.Tonode = subitem.Tonode
                airlink.Frheight = subitem.Frheight
                airlink.Toheight = subitem.Toheight
                airlink.Wiownhf = 0
                airlink.Fscale = subitem.Fscale
                linkid += 1
                airlink.Id = linkid
                airlinknetwork = airlinknetwork + printsingledata(airlink,'Airlinknetwork')
                if hasattr(subitem,'Output') and subitem.Output != '':
                    outlinknames = '%s[%s] '%(subitem.Name, airlink.Id)
                    addouttempllines = addouttempllines + ' AIRLINKS = {0}\r\n NTYPES '.format(outlinknames)
                    for outitem in subitem.Output:
                        for sui, suboutitem in enumerate(outitem.NtypesNo):
                            linkoutarray.append(' = {0} : {1}\r\n'.format(suboutitem,outitem.Ntype[sui]))
                        if len(linkoutarray) > 0:
                            dummyarray = list(set(linkoutarray))
                            for ditem in dummyarray:
                                addouttempllines += ditem
            if subitem.__class__.__name__ == 'STRAIGHTDUCTS':
                if subitem.Name not in foundkey:
                    straightducts = straightducts + printsingledata(subitem,'Straightducts')
                airlink = sc.sticky[sc.doc.Path]["AIRLINKNETWORK"]()
                airlink.Link = subitem.Name
                airlink.Frnode = subitem.Frnode
                airlink.Tonode = subitem.Tonode
                airlink.Frheight = subitem.Frheight
                airlink.Toheight = subitem.Toheight
                airlink.Wiownhf = 1
                airlink.Fscale = 1
                linkid += 1
                airlink.Id = linkid
                airlinknetwork = airlinknetwork + printsingledata(airlink,'Airlinknetwork')
                if hasattr(subitem,'Output') and subitem.Output != '':
                    outlinknames = '%s[%s] '%(subitem.Name, airlink.Id)
                    if outlinknames != '':
                        addouttempllines = addouttempllines + ' AIRLINKS = {0}\r\n NTYPES '.format(outlinknames)
                    for outitem in subitem.Output:
                        for sui, suboutitem in enumerate(outitem.NtypesNo):
                            linkoutarray.append(' = {0} : {1}\r\n'.format(suboutitem,outitem.Ntype[sui]))
                        if len(linkoutarray) > 0:
                            dummyarray = list(set(linkoutarray))
                            for ditem in dummyarray:
                                addouttempllines += ditem
            if subitem.__class__.__name__ == 'FANS':
                print "found"
                if subitem.Name not in foundkey:
                    fans = fans + printsingledata(subitem,'Fans')
                airlink = sc.sticky[sc.doc.Path]["AIRLINKNETWORK"]()
                airlink.Link = subitem.Name
                airlink.Frnode = subitem.Frnode
                airlink.Tonode = subitem.Tonode
                airlink.Frheight = subitem.Frheight
                airlink.Toheight = subitem.Toheight
                airlink.Wiownhf = 1
                airlink.Fscale = subitem.Fscale
                linkid += 1
                airlink.Id = linkid
                airlinknetwork = airlinknetwork + printsingledata(airlink,'Airlinknetwork')
                if hasattr(subitem,'Output') and subitem.Output != '':
                    outlinknames = '%s[%s] '%(subitem.Name, airlink.Id)
                    if outlinknames != '':
                        addouttempllines = addouttempllines + ' AIRLINKS = {0}\r\n NTYPES '.format(outlinknames)
                    for outitem in subitem.Output:
                        for sui, suboutitem in enumerate(outitem.NtypesNo):
                            linkoutarray.append(' = {0} : {1}\r\n'.format(suboutitem,outitem.Ntype[sui]))
                        if len(linkoutarray) > 0:
                            dummyarray = list(set(linkoutarray))
                            for ditem in dummyarray:
                                addouttempllines += ditem
            if subitem.__class__.__name__ == 'EXTERNALNODES':
                externalnodes = externalnodes + printsingledata(subitem,'Externalnodes')
            if subitem.__class__.__name__ == 'AUXILIARYNODES':
                auxiliarynodes = auxiliarynodes + printsingledata(subitem,'Auxiliarynodes')
            if subitem.__class__.__name__ == 'AIRLINKNETWORK':
                linkid += 1
                subitem.Id = linkid
                airlinknetwork = airlinknetwork + printsingledata(subitem,'Airlinknetwork')
            if subitem.__class__.__name__ == 'WINDVELOCITYPROFILE':
                windvelocityprofile = windvelocityprofile + printsingledata(subitem,'Windvelocityprofile')
        if trnflowfound == -1:
            calcflows = 0
        else:
            calcflows = 1
        trnflowtempllines = trnflowtempllines.replace('@Calcflows', str(calcflows))
        trnflowtempllines = trnflowtempllines.replace('@Pollutants', pollutants)
        trnflowtempllines = trnflowtempllines.replace('@Cracks', cracks)
        trnflowtempllines = trnflowtempllines.replace('@Fans', fans)
        trnflowtempllines = trnflowtempllines.replace('@Straightducts', straightducts)
        trnflowtempllines = trnflowtempllines.replace('@Flowcontrollers', flowcontrollers)
        trnflowtempllines = trnflowtempllines.replace('@Largeopenings', largeopenings)
        trnflowtempllines = trnflowtempllines.replace('@Testdata', testdata)
        trnflowtempllines = trnflowtempllines.replace('@Externalnodes', externalnodes)
        trnflowtempllines = trnflowtempllines.replace('@Auxiliarynodes', auxiliarynodes)
        trnflowtempllines = trnflowtempllines.replace('@Thermalzones', thermalzones)
        trnflowtempllines = trnflowtempllines.replace('@Windvelocityprofile', windvelocityprofile)
        trnflowtempllines = trnflowtempllines.replace('@Airlinknetwork', airlinknetwork)
        templlines=templlines.replace('@trnflowdef', trnflowtempllines)
    else:
        templlines=templlines.replace('@trnflowdef', '')
    templlines=templlines.replace('@addactivelayer', activelayeroutput)
    templlines=templlines.replace('@addcomfort', comfortouttempllines)
    templlines=templlines.replace('@adddaylight', daylightouttempllines)
    templlines=templlines.replace('@windowoutput', winouttempllines)
    templlines=templlines.replace('@bsdfoutput', bsdfouttempllines)
    templlines=templlines.replace('@walloutput', wallouttempllines)
    templlines=templlines.replace('@tbdoutput', tbdouttempllines)
    templlines=templlines.replace('@ecaloutput', ecalouttempllines)
    templlines=templlines.replace('@eficaloutput', eficalouttempllines)
    templlines=templlines.replace('@baloutput', balouttempllines)
    templlines=templlines.replace('@addoutput', addouttempllines)
    lines.append(templlines)
    # Window data definition from the library
    lines.append('_EXTENSION_WINPOOL_START_\r\n')
    cleaned_windows = []
    for item in dataset:
        for subitems in item.Surfaces:
            if subitems.Type == 'WINDOW' or subitems.Type == 'ADDWINDOW':
                cleaned_windows.append(subitems.Winid)
    if  AdditionalWinid is not None:
        if  len(AdditionalWinid)>0:
            print "add window found"
            cleaned_windows.extend(AdditionalWinid)
    #print cleaned_windows
    #print AdditionalWinid
    cleaned_windows = list(set(cleaned_windows))
    #print cleaned_windows
    for window_item in library.Windows:
        for cleaned_item in cleaned_windows:
            if str(window_item.Winid) == str(cleaned_item):
                lines.append(window_item.Data)
                break
    #OC_Add_Membrane to Window Library start
    if 'OC_command_lines_global_variables' in sc.sticky[sc.doc.Path]:
        lines.append((sc.sticky['OC_command_lines_window_membrane']+'*** END OF LIBRARY ***\r\n'
            '***************************************************************************************************\r\n'
            '*WinID   Description                              Design         U-Value g-value T-sol Rf-sol T-vis\r\n'
            '***************************************************************************************************\r\n'))
    #OC_Add_Membrane to Window Library END
    else:
        lines.append('*** END OF LIBRARY ***\r\n'
            '***************************************************************************************************\r\n'
            '*WinID   Description                              Design         U-Value g-value T-sol Rf-sol T-vis\r\n'
            '***************************************************************************************************\r\n')
    for window_item in library.Windows:
        for cleaned_item in cleaned_windows:
            if str(window_item.Name) == str(cleaned_item):
                lines.append(window_item.Desc)
    lines.append('_EXTENSION_WINPOOL_END_\r\n')
    #    lines.extend(library.windowdata)
    return lines
@timing
def printbuigeopart(dataset):
    lines = []
    # Starting from here the 3D BuildingGeometry part of the bui is written
    vertexlines = ''
    vertexcount = 0
    myvertexnostring = ''
    vertexarray = []
    Shadingvertexarray = []
    Dlshadingvertexarray = []
    Dlgeovertexarray = []
    wallvertexdefinition = ''
    dummyZonename = ''
    vertexnumber = 0
    virtualnumber = 20001
    virtualvertexdefinition = ''
    zonedict = dict()
    for Airnodes in dataset:
        if Airnodes.Zonename in zonedict:
            zonedict[Airnodes.Zonename][Airnodes.Name] = Airnodes
        else:
            zonedict[Airnodes.Zonename] = dict()
            zonedict[Airnodes.Zonename][Airnodes.Name] = Airnodes
    neworder = []
    for key1 in sorted(zonedict):
        for key2 in sorted(zonedict[key1]):
            neworder.append(zonedict[key1][key2])
    for Airnodes in neworder:
        if dummyZonename != Airnodes.Zonename:
            wallvertexdefinition = wallvertexdefinition + '\r\nzone {0}\r\n'.format(Airnodes.Zonename)
            dummyZonename = Airnodes.Zonename
        virtualvertexdefinition = virtualvertexdefinition + '\r\nairnode {0}\r\n'.format(Airnodes.Name)
        for surfaces in Airnodes.Surfaces:
            if "Virtual" in surfaces.Construction:
                for vertices in surfaces.Vertices:
                    if ([vertices[0],vertices[1],vertices[2]]) in vertexarray:
                        for i in range(len(vertexarray)):
                            if vertexarray[i] == ([vertices[0],vertices[1],vertices[2]]):
                                vertexnumber = i + 1
                                next
                    else:
                        vertexcount = vertexcount + 1
                        vertexarray.append([vertices[0],vertices[1],vertices[2]])
                        myvertexstring = 'vertex {0} {1:.12f} {2:.12f} {3:.12f}'.format(vertexcount,vertexarray[-1][0],vertexarray[-1][1],vertexarray[-1][2])
                        vertexlines = vertexlines + myvertexstring + "\r\n"
                        vertexnumber = vertexcount
                    myvertexnostring = myvertexnostring + ' {0}'.format(vertexnumber)
                virtualvertexdefinition =  virtualvertexdefinition + '{0} {1} {2}\r\n'.format(surfaces.Type.lower(),virtualnumber,myvertexnostring)
                virtualnumber += 1
                myvertexnostring = ''
                continue
            if surfaces.Type != 'WINDOW':
                for vertices in surfaces.Vertices:
                    if ([vertices[0],vertices[1],vertices[2]]) in vertexarray:
                        for i in range(len(vertexarray)):
                            if vertexarray[i] == ([vertices[0],vertices[1],vertices[2]]):
                                vertexnumber = i + 1
                                next
                    else:
                        vertexcount = vertexcount + 1
                        vertexarray.append([vertices[0],vertices[1],vertices[2]])
                        myvertexstring = 'vertex {0} {1:.12f} {2:.12f} {3:.12f}'.format(vertexcount,vertexarray[-1][0],vertexarray[-1][1],vertexarray[-1][2])
                        vertexlines = vertexlines + myvertexstring + "\r\n"
                        vertexnumber = vertexcount
                    myvertexnostring = myvertexnostring + ' {0}'.format(vertexnumber)

                dummytype = surfaces.Type

                if surfaces.Type == 'ADDWINDOW':

                    dummytype = 'WINDOW'
                wallvertexdefinition =  wallvertexdefinition + '{0} {1} {2}\r\n'.format(dummytype.lower(),surfaces.Surfnum,myvertexnostring)
                myvertexnostring = ''
            if surfaces.Subsurface and surfaces.Boundarycond != 'BOUNDARY':
                for subsurface_item in range(len(surfaces.Subsurface)):
                    for vertices in surfaces.Subsurfacedef[subsurface_item].Vertices:
                        if ([vertices[0],vertices[1],vertices[2]]) in vertexarray:
                            for i in range(len(vertexarray)):
                                if vertexarray[i] == ([vertices[0],vertices[1],vertices[2]]):
                                    vertexnumber = i + 1
                                    next
                        else:
                            vertexcount = vertexcount + 1
                            vertexarray.append([vertices[0],vertices[1],vertices[2]])
                            myvertexstring = 'vertex {0} {1:.12f} {2:.12f} {3:.12f}'.format(vertexcount,vertexarray[-1][0],vertexarray[-1][1],vertexarray[-1][2])
                            vertexlines = vertexlines + myvertexstring + "\r\n"
                            vertexnumber = vertexcount
                        myvertexnostring = myvertexnostring + ' {0}'.format(vertexnumber)
                    wallvertexdefinition =  wallvertexdefinition + '{0} {1} {2}\r\n'.format(surfaces.Subsurfacedef[subsurface_item].Type.lower(),surfaces.Subsurfacedef[subsurface_item].Surfnum,myvertexnostring)
                    myvertexnostring = ''
    templlines=templates.Geo3d
    templlines=templlines.replace('@BuildingGeometry', vertexlines + wallvertexdefinition)
    templlines=templlines.replace('@VirtualGeometry', virtualvertexdefinition)
    # Starting from here the 3D ShadingGeometry part of the bui is written
    if Shading:
        vertexnumberstart = vertexcount
        vertexlines = ''
        myvertexnostring = ''
        Shadingsurfaceno = 10000
        Shadingvertexdefinition = '\r\n'
        for Shading_items in Shading:
            ori_edges     = Shading_items.Edges
            dummyPolycurve = rc.Geometry.PolylineCurve.JoinCurves(ori_edges)
            polyline = dummyPolycurve[0].TryGetPolyline()
            if polyline[0] is True:
                pass
            else:
                continue
            sort_vertices = []
            for svitem in polyline[1]:
                sort_vertices.append(svitem)
            sort_vertices.pop()
            for vertices in sort_vertices:
                if ([vertices[0],vertices[1],vertices[2]]) in Shadingvertexarray:
                    for i in range(len(Shadingvertexarray)):
                        if Shadingvertexarray[i] == ([vertices[0],vertices[1],vertices[2]]):
                            vertexnumber = i + 1 + vertexnumberstart
                            next
                else:
                    vertexcount = vertexcount + 1
                    Shadingvertexarray.append([vertices[0],vertices[1],vertices[2]])
                    myvertexstring = 'vertex {0} {1:.12f} {2:.12f} {3:.12f}'.format(vertexcount,vertices[0],vertices[1],vertices[2])
                    vertexlines = vertexlines + myvertexstring + "\r\n"
                    vertexnumber = vertexcount
                myvertexnostring = myvertexnostring + ' {0}'.format(vertexnumber)
            Shadingsurfaceno = Shadingsurfaceno + 1
            Shadingvertexdefinition =  Shadingvertexdefinition + '{0} {1} {2}\r\n'.format('shader',Shadingsurfaceno,myvertexnostring)
            myvertexnostring = ''
        templlines=templlines.replace('@ShadingGeometry', vertexlines + Shadingvertexdefinition)
    else:
        templlines=templlines.replace('@ShadingGeometry', '')
    # Starting from here the 3D ComfortGeometry part of the bui is written
    mycomfortcount = 0
    comfortvertexdefinition = ''
    writeVAFfile = 0
    for Airnode_item in range(len(neworder)):
        if neworder[Airnode_item].Comfort:
            comfortvertexdefinition = comfortvertexdefinition + 'zone {0}\r\n'.format(neworder[Airnode_item].Zonename)
            for cmfitem in neworder[Airnode_item].Comfort:
                for vertices2 in neworder[Airnode_item].Comfortpts:
                    if type(vertices2) is rc.Geometry.Brep:
                        if vertices2.UserDictionary.TryGetValue('VAF')[0]:
                            writeVAFfile = 1
                        pmassprop = rc.Geometry.AreaMassProperties.Compute(vertices2)
                        vertices2 = pmassprop.Centroid
                    mycomfortcount = mycomfortcount + 1
                    comfortvertexdefinition = comfortvertexdefinition + 'cgeopos {0} {1} {2} {3}\r\n'.format(mycomfortcount,vertices2[0],vertices2[1],vertices2[2])
        if Airnode_item == len(neworder)-1 and mycomfortcount > 0:
            templlines=templlines.replace('@ComfortGeometry', comfortvertexdefinition)
        elif Airnode_item == len(neworder)-1 and mycomfortcount == 0:
            templlines=templlines.replace('@ComfortGeometry', '')
    # Starting from here the 3D DaylightSensors part of the bui is written
    mycomfortcount = 0
    vertexdefinition = ''
    for Airnode_item in range(len(neworder)):
        if neworder[Airnode_item].Daylightpts:
            vertexdefinition = vertexdefinition + 'zone {0}\r\n'.format(neworder[Airnode_item].Zonename)
            for vertices in neworder[Airnode_item].Daylightpts:
                if type(vertices) is rc.Geometry.Brep:
                    pmassprop = rc.Geometry.AreaMassProperties.Compute(vertices)
                    vertices = pmassprop.Centroid
                mycomfortcount = mycomfortcount + 1
                vertexdefinition = vertexdefinition + 'dgeopos {0} {1} {2} {3}\r\n'.format(mycomfortcount,vertices[0],vertices[1],vertices[2])
        if Airnode_item == len(neworder)-1 and mycomfortcount > 0:
            templlines=templlines.replace('@DaylightSensors', vertexdefinition)
        elif Airnode_item == len(neworder)-1 and mycomfortcount == 0:
            templlines=templlines.replace('@DaylightSensors', '')
    if writeVAFfile == 1:
        output_file = open(variants_folder + variant_name + '.vaf','w')
        # Step 4. Write to file
        header = """! air velocity adjustment factors (possitive value: windward; negative value: leeward)
! COMFORT: The air velocity defined for comfort type is multiplied by the air velocity adjustment factor.
!          wind direction North = 0, east = 90, ...
"""
        #initial loop to get principle infos about settings
        format_switch = 1
        roughness = 0.02
        zonennumiddict = {}
        for Airnode_item in range(len(neworder)):
            zid = "%03d"%airnodezoneid[neworder[Airnode_item].Name]
            zonennumiddict[zid] = {}
        for Airnode_item in range(len(neworder)):
            zid = "%03d"%airnodezoneid[neworder[Airnode_item].Name]
            zonennumiddict[zid]['PTS'] = 0
            if neworder[Airnode_item].Comfort:
                for cmfitem in neworder[Airnode_item].Comfort:
                    for vertices2 in neworder[Airnode_item].Comfortpts:
                        if type(vertices2) is rc.Geometry.Brep and vertices2.UserDictionary.TryGetValue('WINDDIR')[0]:
                            zonennumiddict[zid]['PTS'] += 1
                            wDirs_str = vertices2.UserDictionary.TryGetValue('WINDDIR')[1]
                            if vertices2.UserDictionary.TryGetValue('ROUGHNESS')[0]:
                                format_switch = 2
                                roughness = vertices2.UserDictionary.TryGetValue('ROUGHNESS')[1]
        output_file.write(header)
        output_file.write('%s   ! format switch\n\n'%format_switch)
        output_file.write('%s   ! number of wind directions' %len(wDirs_str.split()))
        if roughness != 0.02:
            output_file.write(' & surface roughnesses (at 10m) used to calculate UTCI\n')
        else:
            output_file.write('\n')
        for witem in wDirs_str.split():
            output_file.write('{:<4d} '.format(int(witem)))
        output_file.write('\n')
        if roughness != 0.02:
            for witem in wDirs_str.split():
                output_file.write('{:<3.2f} '.format(float(roughness)))
        output_file.write('\n')
        lastid = None
        for Airnode_item in range(len(neworder)):
            zid = "%03d"%airnodezoneid[neworder[Airnode_item].Name]
            if lastid is None or lastid != airnodezoneid[neworder[Airnode_item].Name]:
                output_file.write("\n%03d    ! zone ID\n"%airnodezoneid[neworder[Airnode_item].Name])
                output_file.write("%s    ! number of comfort pts\n"%zonennumiddict[zid]['PTS'])
                lastid = airnodezoneid[neworder[Airnode_item].Name]
                nocomfpts = 0
                counter = 0
            if neworder[Airnode_item].Comfort:
                for cmfitem in neworder[Airnode_item].Comfort:
                    for vertices2 in neworder[Airnode_item].Comfortpts:
                        if type(vertices2) is rc.Geometry.Brep and vertices2.UserDictionary.TryGetValue('VAF')[0]:
                            nocomfpts += 1
            if neworder[Airnode_item].Comfort:
                for cmfitem in neworder[Airnode_item].Comfort:
                    for vertices2 in neworder[Airnode_item].Comfortpts:
                        if type(vertices2) is rc.Geometry.Brep and vertices2.UserDictionary.TryGetValue('VAF')[0]:
                            counter += 1
                            vafval = vertices2.UserDictionary.TryGetValue('VAF')[1].split(',')
                            output_file.write('{0} '.format(counter) + ' '.join(vafval))
                            pmassprop = rc.Geometry.AreaMassProperties.Compute(vertices2)
                            vertices2 = pmassprop.Centroid
                            output_file.write(' {0} {1} {2}\n'.format(vertices2.X, vertices2.Y, vertices2.Z))
        output_file.close()
    else:
        filearr = os.listdir(variants_folder)
        for fileitem in filearr:
            if '.vaf' in fileitem:
                os.unlink(variants_folder + fileitem)
    #add complex shading configuration
    vertexnumberstart = vertexcount
    vertexlines = ''
    myvertexnostring = ''
    Shadingsurfaceno = 20000
    Shadingvertexdefinition = '\r\n'
    Shadingverdef = dict()
    for ai,Airnode_item in enumerate(neworder):
        if  'Complexshade' in dir(Airnode_item) and getattr(Airnode_item, 'Complexshade') is not None:
            for sitem in dir(Airnode_item.Complexshade):
                if 'Shd' in sitem and 'tair' not in sitem and getattr(Airnode_item.Complexshade, sitem) is not None:
                    key = sitem.lower()
                    if getattr(Airnode_item.Complexshade, sitem).Dlgeo != '':
                        #info = "shd0 {1} {0}\r\n".format(surface.Construction, surface.Shader.Dlmatshd0)
                        Shadingverdef[key] = ""
                        for Shading_items in getattr(Airnode_item.Complexshade, sitem).Dlgeo:
                            ori_edges     = Shading_items.Edges
                            dummyPolycurve = rc.Geometry.PolylineCurve.JoinCurves(ori_edges)
                            polyline = dummyPolycurve[0].TryGetPolyline()
                            sort_vertices = []
                            for svitem in polyline[1]:
                                sort_vertices.append(svitem)
                            sort_vertices.pop()
                            for vertices in sort_vertices:
                                if ([vertices[0],vertices[1],vertices[2]]) in Dlshadingvertexarray:
                                    for i in range(len(Dlshadingvertexarray)):
                                        if Dlshadingvertexarray[i] == ([vertices[0],vertices[1],vertices[2]]):
                                            vertexnumber = i + 1 + vertexnumberstart
                                            next
                                else:
                                    vertexcount = vertexcount + 1
                                    Dlshadingvertexarray.append([vertices[0],vertices[1],vertices[2]])
                                    myvertexstring = 'vertex {0} {1:.12f} {2:.12f} {3:.12f}'.format(vertexcount,vertices[0],vertices[1],vertices[2])
                                    vertexlines = vertexlines + myvertexstring + "\r\n"
                                    vertexnumber = vertexcount
                                myvertexnostring = myvertexnostring + ' {0}'.format(vertexnumber)
                            Shadingsurfaceno = Shadingsurfaceno + 1
                            #Shadingvertexdefinition =  Shadingvertexdefinition + '{0} {1} {2}\r\n'.format('dlshader',Shadingsurfaceno,myvertexnostring)
                            Shadingverdef[key] = Shadingverdef[key] + '{0} {3} {1} {2}\r\n'.format(key,Shadingsurfaceno,myvertexnostring, getattr(Airnode_item.Complexshade, sitem).Dlmat)
                            myvertexnostring = ''
    for item in sorted(Shadingverdef):
        Shadingvertexdefinition = Shadingvertexdefinition + Shadingverdef[item]
    if AddDaylightGeometry:
        vertexnumberstart = vertexcount
        Shadingsurfaceno = 30000
        for bitems in AddDaylightGeometry:
            ori_edges     = bitems.Edges
            dummyPolycurve = rc.Geometry.PolylineCurve.JoinCurves(ori_edges)
            polyline = dummyPolycurve[0].TryGetPolyline()
            if polyline[0] is True:
                pass
            else:
                continue
            sort_vertices = []
            for svitem in polyline[1]:
                sort_vertices.append(svitem)
            sort_vertices.pop()
            for vertices in sort_vertices:
                if ([vertices[0],vertices[1],vertices[2]]) in Dlgeovertexarray:
                    for i in range(len(Dlgeovertexarray)):
                        if Dlgeovertexarray[i] == ([vertices[0],vertices[1],vertices[2]]):
                            vertexnumber = i + 1 + vertexnumberstart
                            next
                else:
                    vertexcount = vertexcount + 1
                    Dlgeovertexarray.append([vertices[0],vertices[1],vertices[2]])
                    myvertexstring = 'vertex {0} {1:.12f} {2:.12f} {3:.12f}'.format(vertexcount,vertices[0],vertices[1],vertices[2])
                    vertexlines = vertexlines + myvertexstring + "\r\n"
                    vertexnumber = vertexcount
                myvertexnostring = myvertexnostring + ' {0}'.format(vertexnumber)
            Shadingsurfaceno = Shadingsurfaceno + 1
            Shadingvertexdefinition =  Shadingvertexdefinition + '{0} {1} {2} {3}\r\n'.format('surface',bitems.UserDictionary.TryGetValue("MAT")[1],Shadingsurfaceno,myvertexnostring)
            myvertexnostring = ''
    templlines=templlines.replace('@DaylightGeometry', vertexlines + Shadingvertexdefinition)
    lines.append(templlines)
    return lines

def getBuiOutputList(datafile):
    #print datafile.split('\r\n')
    datasplit = datafile.split('\n')
    data = getparagraph(datasplit,'^OUTPUTS','^END|MULTIZONE_AIRFLOW_NETWORK')
    cleaneddata = []
    for item in data:
        if re.match('^\s*OUTPUTS',item):
            continue
        if re.match('^\s*TRANSFER',item):
            continue
        if not item:
            continue
        if re.match('^\s*\*',item):
            continue
        if re.match('^\s*END',item):
            continue
        if re.search('901',item):
            continue
        if re.search('902',item):
            continue
        if re.search('903',item):
            continue
        if re.search('904',item):
            continue
        if re.search('905',item):
            continue
        if re.search('906',item):
            continue
        if re.search('907',item):
            continue
        cleaneddata.append(item)
    data = []
    airnodegroup = 0
    darray = []
    larray = []
    ntypearray = []
    outputinfo = []
    output = {}
    outputnumber = 0
    commonoutputs = [400,401,402]
    airlinkgroup = 0
    linkarray = []
    for ix,item in enumerate(cleaneddata):
        #loop through airnode groups
        if re.match('^\s*AIRNODES',item) or ix == len(cleaneddata)-1:
            if ix == len(cleaneddata)-1:
                dummy = item.replace('NTYPES','')
                dummy = dummy.replace('=','')
                dummy = re.sub('^\s*','',dummy)
                dummy = re.sub('\s*:\s*',':',dummy)
                dummy = dummy.split(':')
                ntypearray.append(dummy[0])
                del dummy[0]
                cldummy = []
                for di,ditem in enumerate(dummy):
                    if di == len(dummy) - 1:
                        cldummy.append(ditem.split(' ',1)[0])
                    else:
                        cldummy.append(ditem)
                darray.append(cldummy)
                larray.append(item)
            if airnodegroup > 0:
                for di,ditem in enumerate(darray):
                    if re.match('^\s*AIRLINKS',larray[di]):
                        airlinkgroup = 1
                    if re.match('^\s*AIRNODES',larray[di]):
                        airlinkgroup = 0
                    for aitem in airnode:
                        if len(ditem) == 1:
                            # JX Fix Deduplication
                            if airlinkgroup == 0:
                                outputnumber += 1
                                if int(ntypearray[di]) in commonoutputs:
                                    key = '{0}'.format(ditem[0],aitem)
                                else:
                                    key = '{0}_{1}'.format(ditem[0],aitem)
                                if key not in outputinfo:

                                    value = '[56,{0}]'.format(outputnumber)
                                    output[key] = value
                                    outputinfo.append(key)
                                #outputinfo.append('{0}_{1} = [56,{2}]'.format(ditem[0],aitem,outputnumber))
                        if len(ditem) == 2:
                            if re.match('SCHEDULE',ditem[0]):
                                dummy = ditem[0].replace('SCHEDULE','')
                                dummy = dummy.replace(',',' ')
                                for sitem in dummy.split():
                                    outputnumber += 1
                                    #outputinfo.append('SCHED_{0} = [56,{1}]'.format(sitem,outputnumber))
                                    key = 'SCHED_{0}'.format(sitem)
                                    value = '[56,{0}]'.format(outputnumber)
                                    output[key] = value
                                    if key in outputinfo:
                                        pass
                                    else:
                                        outputinfo.append(key)
                            if re.match('SURF',ditem[0]):
                                dummy = ditem[0].replace('SURF','')
                                dummy = dummy.replace(',',' ')
                                for sitem in dummy.split():
                                    outputnumber += 1
                                    #outputinfo.append('{0}_S{1} = [56,{2}]'.format(ditem[1],sitem,outputnumber))
                                    key = '{0}_S{1}'.format(ditem[1].replace('\r',''),sitem)
                                    value = '[56,{0}]'.format(outputnumber)
                                    output[key] = value
                                    if key in outputinfo:
                                        pass
                                    else:
                                        outputinfo.append(key)
                            if re.match('COMFID',ditem[0]):
                                dummy = ditem[0].replace('COMFID','')
                                dummy = dummy.replace(',',' ')
                                for sitem in dummy.split():
                                    outputnumber += 1
                                    #outputinfo.append('{0}_C{1} = [56,{2}]'.format(ditem[1],sitem,outputnumber))
                                    key = '{0}_C{1}'.format(ditem[1],sitem)
                                    value = '[56,{0}]'.format(outputnumber)
                                    output[key] = value
                                    if key in outputinfo:
                                        pass
                                    else:
                                        outputinfo.append(key)
                for li,litem in enumerate(larray):
                    if re.match('^\s*AIRLINKS',litem):
                        airlinkgroup = 1
                        linknames = litem.split('=')[-1]
                        linkarray = linknames.split()
                    if re.match('^\s*AIRNODES',litem):
                        airlinkgroup = 0
                        linkarray = []
                    if airlinkgroup == 1:
                        if len(darray[li]) == 1:
                            for l2item in linkarray:
                                p = re.compile('\[(\d+)\]')
                                m = p.search(l2item)
                                outputnumber += 1
                                key = '{0}_L{1}'.format(darray[li][0],m.group(1))
                                value = '[56,{0}]'.format(outputnumber)
                                output[key] = value
                                if key in outputinfo:
                                    pass
                                else:
                                    outputinfo.append(key)
                                #outputinfo.append('{0}_{1} = [56,{2}]'.format(ditem[0],aitem,outputnumber))
            dummy = item.replace('AIRNODES','')
            dummy = dummy.replace('=','')
            dummy = re.sub('^\s*','',dummy)
            airnode = dummy.split()
            airnodegroup += 1
            darray = []
            larray = []
        else:
            dummy = re.sub('NTYPES','',item)
            dummy = re.sub('=','',dummy)
            dummy = re.sub('^\s*','',dummy)
            dummy = re.sub('\s*:\s*',':',dummy)
            dummy = dummy.split(':')
            ntypearray.append(dummy[0])
            del dummy[0]
            cldummy = []
            for di,ditem in enumerate(dummy):
                if di == len(dummy) - 1:
                    cldummy.append(ditem.split(' ',1)[0])
                else:
                    cldummy.append(ditem)
            darray.append(cldummy)
            larray.append(item)
    return output,outputinfo

def getSimulationPeriod(startday = 1,startmonth = 'JAN',stopday = 31,stopmonth = 'DEC'):
    starthour = 1
    stophour = 24
    monthstarthour = {}
    monthstarthour['JAN'] = 0
    monthstarthour['FEB'] = 744
    monthstarthour['MAR'] = 1416
    monthstarthour['APR'] = 2160
    monthstarthour['MAY'] = 2880
    monthstarthour['JUN'] = 3624
    monthstarthour['JUL'] = 4344
    monthstarthour['AUG'] = 5088
    monthstarthour['SEP'] = 5832
    monthstarthour['OKT'] = 6552
    monthstarthour['NOV'] = 7296
    monthstarthour['DEC'] = 8016
    start = monthstarthour[startmonth] + (startday-1)*24 + (starthour-1)
    stop = monthstarthour[stopmonth] + (stopday-1)*24 + (stophour)
    return start,stop

def printDict(ddict,switch):
    if switch == 1:
        for ditem in sorted(ddict):
            print "%s => %s"%(ditem, ddict[ditem])
def printbui(bui_file):
    buiout = open(variants_folder + variant_name + '.b%s'%TRNSYS, 'w')
    for lines in bui_file:
        lines = lines.replace('\r', '')    # remove '\n' only
        buiout.write(lines)
    buiout.close()

def PrintOnline(name = 'Online', unit = 900, content = ['Tamb'], y1min = -5, y1max = 35, unit1 = '', y2min = -5, y2max = 35, unit2 = '', y1label = '', y2label = ''):
    dummyname = ''
    global lu_counter
    lu_counter = lu_counter + 1
    nrleft = 0
    nrright = 0
    if y1label == '':
        y1label = name
    if y2label == '':
        y2label = name
    for index_name in range(0,20):
        if index_name < len(content):
            dummyname = dummyname + "{0}\n".format(content[index_name])
            if index_name < 10:
                nrleft += 1
            else:
                nrright += 1
        #else:
        #    dummyname = dummyname + "Zero\n"
    plotdata = """*---------------
* Model "{0}" (Type 65)
*
UNIT {1} TYPE 65	 {0}
*$UNIT_NAME {0}
*$MODEL .\Output\Online Plotter\Online Plotter Without File\Type65d.tmf
*$POSITION 430 960
*$LAYER Main #
PARAMETERS 12
{7}		! 1 Nb. of left-axis variables
{8}		! 2 Nb. of right-axis variables
{2}		! 3 Left axis minimum
{3}		! 4 Left axis maximum
{4}		! 5 Right axis minimum
{5}		! 6 Right axis maximum
-1		! 7 Number of plots per simulation
14		! 8 X-axis gridpoints
showonline		! 9 Shut off Online w/o removing
-1		! 10 Logical unit for output file
0		! 11 Output file units
0		! 12 Output file delimiter
INPUTS {9}
{6}
*** INITIAL INPUT VALUES
{6}
LABELS  3
"{12}"
"{13}"
"{0}"
""".format(name, unit, y1min, y1max, y2min, y2max, dummyname, nrleft, nrright, nrleft+nrright, unit1, unit2, y1label, y2label)
    empty = ''
    if len(content) > 0:
        return plotdata
    else:
        return ''
def PrintPrintegrator(name = 'Printer', unit = 900, content = ['Tamb'], outpath = 'Results', labels = [], file = '', timestep = 1):
    dummyname = ''
    dummylabels = ''
    dummynini = ''
    if file == '':
        file = '{0}_1h.prn'.format(name)
    global lu_counter
    lu_counter = lu_counter + 2
    for index_name in range(len(content)):
        dummyname = dummynini + "{0}\n".format(content[index_name])
        if len(labels) == len(content):
            dummylabels = dummylabels + "{0}\n".format(labels[index_name])
        else:
            dummylabels = dummylabels + "{0}\n".format(content[index_name])
        dummynini = dummynini + "{0}\n".format(content[index_name])
    plotdata = """*---------------
* Model "{0} - 1h" (Type 46)
*
UNIT {1} TYPE 46	 {0} - 1h
*$UNIT_NAME {0} - 1h
*$MODEL .\Output\Printegrator\Formatted\User-Defined Period\Type46e.tmf
*$POSITION 530 960
*$LAYER Main #
*$# PRINTEGRATOR
PARAMETERS 5
{1}		! 1 Logical unit
-1		! 2 Logical unit for monthly summaries
0		! 3 Relative or absolute start time
{8}		! 4 Printing & integrating interval
0		! 5 Number of inputs to avoid integration
!2       ! 6 Predefined Formats, 0 means it uses either the manual format defined below or the standard format, 1 means outputs in F8.3, 2 means outputs in F9.2
!1       ! 7 Multiplication factor to monthly outputs only, The Factor will also be written to the units of the monthly Output
INPUTS {2}
{4}
*** INITIAL INPUT VALUES
{3}
LABELS {2}
{5}
FORMAT (1(F10.2,1X),{2}(F10.2,1X))
*** External files
ASSIGN "{6}\\{7}" {1}
*|? Output file for integrated results? |1000""".format(name, unit, len(content), dummynini, dummyname, dummylabels, outpath, file, timestep)
    return plotdata

@timing
def readbui():
        buiinp = open(variants_folder + variant_name + '.b%s'%TRNSYS, 'r')
        bui_file = buiinp.readlines()
        buiinp.close()
        return bui_file
@timing
def print_datasheet(template, zone_item, output_file ):
        reporttxt = open(output_file, 'a')
        p = re.compile('@(\w+)')
        m = p.search(template)
        if m is not None:
            multi = template.split('@')
            if len(multi) > 2:
                for i in range(len(multi)):
                    if i == 0:
                        dummy = multi[0]
                    if i > 0:
                        p = re.compile('^(\w+)')
                        m = p.search(multi[i])
                        replacestring = m.group(1)
                        dummy = dummy + re.sub('^(\w+)', str(variables[replacestring]).encode('string-escape'), multi[i])
                        template = dummy
            else:
                replacestring = m.group(1)
                template=re.sub('@'+replacestring, str(variables[replacestring]).encode('string-escape'), template)
        template = template + '\n'
        template = template.replace('\r', '')
        reporttxt.write(template)
        reporttxt.close()

@timing
def returnSurfaceOri(surface):
    return surface.Orientation
@timing
def writereport(zone_item, printtype):
        if printtype == 1:
            outputfile = variants_folder + 'report_' + str(zone_item.Airnode.Name) + '.txt'
            #reporttxt = open(outputfile, 'w')
            #reporttxt.close()
            #outputfileshort = variants_folder + 'summary_' + str(zone_item.Airnode.Name) + '.txt'
            #reporttxtshort = open(outputfileshort, 'w')
            #reporttxtshort.close()
        elif printtype == 2:
            outputfile = variants_folder + 'report.txt'
            #reporttxt = open(outputfile, 'w')
            #reporttxt.close()
            #outputfileshort = variants_folder + 'summary.txt'
            #reporttxtshort = open(outputfileshort, 'w')
            #reporttxtshort.close()
        print_datasheet(TemplateReport.Construction, zone_item, outputfile)
        print_datasheet(TemplateReport.Geometry, zone_item, outputfile)
        #schedulesdummy = list(set(schedulescoll))
        variables['vent']  = '     '
        variables['sve1']  = '     '
        variables['sve2']  = '     '
        variables['hybr']  = '     '
        variables['infi']  = '     '
        variables['pers']  = '     '
        variables['equi']  = '     '
        variables['ligh']  = '     '
        variables['othe']  = '     '
        variables['idht']  = '     '
        variables['idcl']  = '     '
        variables['alht']  = '     '
        variables['alcl']  = '     '
        variables['filename']  = ''
        #for items in schedulesdummy:
        #    variables['schedname'] = items
        #    variables['filename']  = '{0}_{1}_{2}'.format(variables['variantname'], variables['aname'], variables['schedname'])
        #    print_datasheet(TemplateReport.Schedules, zone_item, outputfile)
        if wallproperties:
            for item in wallproperties:
                pass
        if zone_item.Airnode.Gain:
            for gain_item in zone_item.Airnode.Gain:
                if gain_item.Lightinggain == 1:
                    print_datasheet(TemplateReport.Artificial_lighting, zone_item, outputfile)
                    variables['ligh']   = '|lig|'
                if gain_item.Personsgain == 1:
                    print_datasheet(TemplateReport.Internal_gains, zone_item, outputfile)
                    variables['pers']   = '|per|'
                if gain_item.Othergain == 1 and gain_item.Name != 'THB':
                    print_datasheet(TemplateReport.Other_gains, zone_item, outputfile)
                    variables['othe']   = '|aux|'
                if gain_item.Othergain == 1 and gain_item.Name == 'THB':
                    variables['thb_gain']   = gain_item.Specificpower
                    print_datasheet(TemplateReport.Thermal_bridge, zone_item, outputfile)
        if zone_item.Airnode.Heating:
            print_datasheet(TemplateReport.Heating, zone_item, outputfile)
            variables['idht']   = '|idh|'
        if zone_item.Airnode.Cooling:
            print_datasheet(TemplateReport.Cooling, zone_item, outputfile)
            variables['idcl']   = '|idc|'
        if zone_item.Airnode.Activelayer == 1:
            print_datasheet(TemplateReport.Active_layer, zone_item, outputfile)
            variables['alcl']   = '|alc|'
            variables['alht']   = '|alh|'
        if zone_item.Airnode.Infiltration:
            print_datasheet(TemplateReport.Infiltration, zone_item, outputfile)
            variables['infi']  = '|inf|'
        if zone_item.Airnode.Ventilation:
            for ventilation_item in zone_item.Airnode.Ventilation:
                if ventilation_item.Type == 'VENTILATION':
                    print_datasheet(TemplateReport.Ventilation, zone_item, outputfile)
                    variables['vent']  = '|ven|'
                    if ventilation_item.Hybrid == 1:
                        print_datasheet(TemplateReport.Hybrid_ventilation, zone_item, outputfile)
                        variables['hybr']  = '|hyb|'
                elif ventilation_item.Type == 'STACKVENTILATION' and ventilation_item.Name == 'STVENT1':
                    variables['sve1']  = '|sv1|'
                    print_datasheet(TemplateReport.Stack_ventilation1, zone_item, outputfile)
                elif ventilation_item.Type == 'STACKVENTILATION' and ventilation_item.Name == 'STVENT2':
                    variables['sve2']  = '|sv2|'
                    print_datasheet(TemplateReport.Stack_ventilation2, zone_item, outputfile)
        #variables['projvar_MAP']  = '{0}_{1}_MAP'.format(variables['variantname'], variables['aname'])
        #variables['projvar_SCATTER']  = '{0}_{1}_SCATTER'.format(variables['variantname'], variables['aname'])
        #variables['projvar_TL']  = '{0}_{1}_TL'.format(variables['variantname'], variables['aname'])
        #variables['projvar_WT_SEQU']  = '{0}_{1}_WT_SEQU'.format(variables['variantname'], variables['aname'])
        #variables['projvar_WP_SEQU']  = '{0}_{1}_WP_SEQU'.format(variables['variantname'], variables['aname'])
        #variables['projvar_ST_SEQU']  = '{0}_{1}_ST_SEQU'.format(variables['variantname'], variables['aname'])
        #variables['projvar_SP_SEQU']  = '{0}_{1}_SP_SEQU'.format(variables['variantname'], variables['aname'])
        #print_datasheet(TemplateReport.Results, zone_item, outputfile)
        #print_datasheet(TemplateReport.Summary, zone_item, outputfileshort)
        for items in sorted(zone_item.Airnode.Surfaces, key= returnSurfaceOri):
            if items.Type != 'WINDOW':
                variables['area_item'] = items.Area
                variables['assembly_item'] = items.Construction
                variables['type_item'] = items.Type
                variables['orientation_item'] = items.Orientation
                if hasattr(items, 'Uvalue'):
                    variables['uwall_item'] = round(items.Uvalue,2)
                else:
                    variables['uwall_item'] = 0
                print_datasheet(TemplateReport.Wall, zone_item, outputfile)
            if items.Type == 'WINDOW':
                variables['area_item'] = items.Area
                variables['assembly_item'] = items.Construction
                variables['type_item'] = items.Type
                variables['orientation_item'] = items.Orientation
                variables['name_item'] = items.Construction
                variables['fraction_item'] = 0
                if items.BSDFWindows == 1:
                    variables['uglas_item'] = "BSDF"
                    variables['shgc_item'] = "BSDF"
                    variables['tvis_item'] = "BSDF"
                else:
                    if hasattr(items, 'Uglas'):
                        variables['uglas_item'] = items.Uglas
                        variables['shgc_item'] = items.Shgc
                        variables['tvis_item'] = items.Tvis
                    else:
                        variables['uglas_item'] = 0
                        variables['shgc_item'] = 0
                        variables['tvis_item'] = 0
                variables['framefrac_item'] = items.Framefrac * 100
                variables['uframe_item'] = items.Uframe
                print_datasheet(TemplateReport.Window, zone_item, outputfile)
                if items.Mshade == 'OUT' or items.Mshade == 'INT':
                    variables['position_item'] = items.Mshade
                    variables['fraction_item'] = items.Mshadeglazingcover*100
                    variables['on_item'] = items.Shadeclose/3.6
                    variables['off_item'] = items.Shadeopen/3.6
                    variables['off2_item'] = items.Shdtairabove
                    print_datasheet(TemplateReport.Shading, zone_item, outputfile)


@timing
def writeScheduleReport(zone_item):
    outputfileshort = variants_folder + 'schedules' + '.txt'
    reporttxtshort = open(outputfileshort, 'w')
    reporttxtshort.close()
    schedulesdummy = list(set(schedulescoll))
    for items in schedulesdummy:
        variables['schedname'] = items
        variables['filename']  = '{0}_{1}_{2}'.format(variables['variantname'], variables['aname'], variables['schedname'])
        print_datasheet(TemplateReport.Schedules, zone_item, outputfileshort)

def getLinksInfo():
    dummystr = ''
    for i in range(1,60):
        dummystr += '%s,'%i
    dummystr += '%s'%60
    for aitem in links:
        if 'zunit' in aitem:
            continue
        funit,tunit = aitem.split(':')
        fx, fy = unitpos[funit].split()
        tx, ty = unitpos[tunit].split()
        frompos = '%s,%s'%(fx,fy)
        topos = '%s,%s'%(tx,ty)
        deltax = int(tx) - int(fx)
        deltay = int(ty) - int(fy)
        if deltax > 0:
            fxpos = 40
            txpos = 0
        if deltax == 0:
            fxpos = 20
            txpos = 20
        if deltax < 0:
            fxpos = 0
            txpos = 40
        if deltay > 0:
            fypos = 40
            typos = 0
        if deltay == 0:
            fypos = 20
            typos = 20
        if deltay < 0:
            fypos = 0
            typos = 40
        variables['linkdefinition'] += """*!LINK {0}\n*!CONNECTION_SET {1}:{2}:{3}:{4}:{5}:{6}:2:0:0:{7}:{8}\n""".format(aitem,fxpos,fypos,txpos,typos,dummystr,links[aitem]['style'],frompos,topos)
class VARIANTS:
    def __init__(self, name='', path=''):
        self.Name = name
        self.Path = path
@timing
def getDataParagraph(startpattern,stoppattern,datalines):
    output = []
    inparagraph = 'FALSE'
    lines=datalines
    data=lines[0].split( )
    for i in range(len(lines)):
        search_start=re.search(r'{0}'.format(startpattern),lines[i])
        if search_start is not None or inparagraph == 'TRUE':
            inparagraph = 'TRUE'
            output.append(lines[i])
            search_stop=re.search(r'{0}'.format(stoppattern),lines[i])
            if search_stop is not None or i == len(lines)-1:
                return output
                f.close()
                break
    print 'no match found!'
@timing
def scandirs(path):
    for currentFile in glob.glob( os.path.join(path, '*') ):
        #if os.path.isdir(currentFile):
        #    print 'got a directory: ' + currentFile
        #    scandirs(currentFile)
        #print "processing file: " + currentFile
        if reuse_shm_ism_ipm == 0:
            extensions = ('.ipm', '.ism', '.shm')
        else:
            extensions = ()
        if any(currentFile.endswith(ext) for ext in extensions):
            os.remove(currentFile)
        extensions = ('.lst')
def moveResultFiles(sourcefolder = '', targetfolder = '', extension = ['']):
    for currentFile in glob.glob( os.path.join(sourcefolder, '*') ):
        if os.path.isfile(currentFile):
            for ext in extension:
                if ext in currentFile:
                    # JX Fixed bugs path.join
                    target_fullpath = os.path.join(targetfolder, os.path.basename(currentFile))
                    if os.path.isfile(target_fullpath):
                        os.remove(target_fullpath)
                    os.rename(currentFile, target_fullpath)
def copyResultFiles(sourcefolder = '', targetfolder = '', extension = ['']):
    for currentFile in glob.glob( os.path.join(sourcefolder, '*') ):
        if os.path.isfile(currentFile):
            for ext in extension:
                if ext in currentFile:
                    if os.path.isfile(targetfolder + os.path.basename(currentFile)):
                        os.remove(targetfolder + os.path.basename(currentFile))
                    shutil.copyfile(currentFile, targetfolder + os.path.basename(currentFile))
def cleanSimulationFolder(sourcefolder = variants_folder, filecontent = ['']):
    for currentFile in glob.glob( os.path.join(sourcefolder, '*') ):
        if os.path.isfile(currentFile):
            for cont in filecontent:
                if cont in currentFile:
                    pass
                    try:
                        os.remove(currentFile)
                    except:
                        pass
@timing
def getbuiOutputs():
    #Open bui to generate the *.inf file
        mode = 'NEW'
        if mode == 'OLD':
            if build_mode == 'BUI':
                proc1 = Popen( TRNSYS_path + '\Building\TRNBUILD.exe ' + variants_folder + variant_name + '.b%s'%TRNSYS + ' /N', shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
                proc1.communicate() #now wait
            else:
                proc1 = Popen( TRNSYS_path + '\Building\TRNBID.exe ' + variants_folder + variant_name + '.b%s'%TRNSYS + ' /N' , shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
                proc1.communicate() #now wait
            check_trnsize = os.stat(variants_folder + variant_name + '.trn')
            if check_trnsize.st_size == 0:
                ghenv.Component.AddRuntimeMessage(err, "Construction definition is not working, please check the construction!")
                sys.exit()
            infin = open(variants_folder + variant_name + '.inf', 'r')
            infdata=getDataParagraph('OutNr','THERMAL CONDUCTANCE',infin.readlines())
            infdata.pop(0)
            infdata.pop(0)
            del infdata[-1]
            del infdata[-1]
            del infdata[-1]
            del infdata[-1]
            infin.close()
            infin = open(variants_folder + variant_name + '.inf', 'r')
            #wallproperties=getDataParagraph('THERMAL CONDUCTANCE OF USED WALL TYPES','end',infin.readlines())
            wallproperties=getDataParagraph('Used opaque construction types','end',infin.readlines())
            wallproperties.pop(0)
            wallproperties.pop(0)
            wallproperties.pop(0)
            infin.close()
            t56outputs = []
            outputs = ''
            counter_double = 0
            for infitem in infdata:
                pinf = re.compile('\*\s+\|\s+(\d+)\s+\|\s+(\w+_?#?\d?\d?)\s+\|')
                minf = pinf.search(infitem)
                if minf is not None:
                    if '#' in minf.group(2):
                        counter_double = counter_double + 1
                        print 'Note: Doubled output definition found, {0}'.format(minf.group(2))
                    t56outputs.append(minf.group(2).strip())
            outputs = 'EQUATIONS {0}\n'.format(len(t56outputs)-counter_double)
            for outputitem in range(len(t56outputs)):
                if '#' in t56outputs[outputitem]:
                    pass
                else:
                    outputs = outputs + '{0} = [56,{1}]\n'.format(t56outputs[outputitem].strip(),outputitem+1)
            variables['outputs'] = outputs
        else:
            outputs = 'EQUATIONS {0}\n'.format(len(okey))
            for outputitem in okey:
                outputs = outputs + '{0} = {1}\n'.format(re.sub('\r','',outputitem),buioutput[outputitem])
                #print outputitem
            variables['outputs'] = outputs
        #print variables['outputs']
# ----------------------------------------------------------------------------------------------------------------------
# Exterior solar gain of HAMT walls (EXTCALEXT)
# Type 56 handles an EXTCALEXT wall as a BOUNDARY surface (BOUNDARY = INPUT 1*TSI395_S<n>) and computes no incident
# radiation for it (IT_S<n> = 0), so the exterior side of the Type 395 wall needs another source. Type 15 and Type 56 call the
# same TRNSYS kernel routine (GetTiltedRadiation: same sky model, same ground reflectance), so the total radiation of a Type 15
# tilted surface with the slope/azimuth of an orientation is Type 56's IT of an EXTERNAL surface of that orientation (checked to
# 0.000 kJ/(h m2): a full year, Type 15 modes 1-5, eight building turns, orientations S, E, N and H_0_0). Type 15 therefore gets
# one extra tilted surface per distinct EXTCALEXT orientation; surface 1 stays the horizontal plane that every deck has.
TYPE15_FIRST_TILTED_OUTPUT = 24   # Type 15 output number of the total radiation on tilted surface 1 (outputs 24.. hold surfaces 1..n)
def getType15TiltedOutput(kind, surface_no, surface_count):
    """Type 15 output number of a per-surface result. kind: 0 total, 1 beam, 2 sky diffuse, 3 ground reflected, 4 total diffuse
    (sky + ground), 5 incidence angle, 6 slope, 7 azimuth; each kind holds one output per tilted surface (n = surface_count)."""
    return TYPE15_FIRST_TILTED_OUTPUT + kind * surface_count + surface_no - 1
def getType15TiltedSurface(orientation, turn = 0):
    """Slope and azimuth [deg] of a Type 15 tilted surface for an orientation name Y_azimuth_slope (for example S_0_90 or
    E_270_90; azimuth: 0 facing the equator, 90 west, 180 pole-ward, 270 east, as in TRNSYS, slope 0..180), or None for a name
    that does not follow this format. Type 56 receives the solar azimuth minus the building turn, so the surface is turned by +turn."""
    match = re.match(r'^[A-Za-z]_(-?\d+(?:\.\d+)?)_(\d+(?:\.\d+)?)$', str(orientation).strip())
    if match is None:
        return None
    slope = float(match.group(2))
    if slope > 180:
        return None
    azimuth = (float(match.group(1)) + float(turn)) % 360.0
    if azimuth > 180.0:
        azimuth = azimuth - 360.0
    return slope, azimuth
def getHamtSolarOrientations(zones):
    """Distinct orientations of the EXTCALEXT walls of all zones, in order of first appearance."""
    orientations = []
    for zone_item in zones:
        for surface in zone_item.Airnode.Surfaces:
            if surface.Boundarycond != 'EXTCALEXT' or surface.Type == 'WINDOW' or "Virtual" in surface.Construction:
                continue
            if str(surface.Orientation) not in orientations:
                orientations.append(str(surface.Orientation))
    return orientations
def getType15TiltedLines(tilted):
    """Parameter block of the extra Type 15 tilted surfaces. tilted: [(orientation, slope, azimuth)] (azimuth already turned).
    Returns (number of Type 15 parameters, number of tilted surfaces including the horizontal plane, parameter lines)."""
    lines = ''
    for ti, (orientation, slope, azimuth) in enumerate(tilted):
        first = 10 + 3 * ti
        lines = lines + '1\t\t! {0} Tracking mode (exterior solar of the HAMT walls of orientation {1})\n'.format(first, orientation)
        lines = lines + '{1:g}\t\t! {0} Slope of surface\n'.format(first + 1, slope)
        lines = lines + '{1:g}\t\t! {0} Azimuth of surface\n'.format(first + 2, azimuth)
    return 9 + 3 * len(tilted), 1 + len(tilted), lines
@timing
def printdck():
    #Convert the dck template into the final simulation file
        hamt_zone_surfaces = {}
        dckout = open(variants_folder + variant_name + '.d%s'%TRNSYS, 'w')
        ingroup = 0
        insubgroup = 0
        insubgroup2 = 0
        subdata = {}
        for il,lines in enumerate(dck_file):
            # @OC START
            #OC_Command_lines export / write text in dck file
            if 'OC_EVA_Parameter_Equations' in sc.sticky[sc.doc.Path]:
                if '@oc_tool' in lines:
                    oc_tool_lines = []
                    UTCI_Components_2 = "\n".join(UTCI_Components)
                    EVA_Components2 = "\n".join(EVA_Components)
                    Printegrator25_data_2 = "\n".join(Printegrator25_data)
                    UTCI_Components_EVA_2 = "\n".join(UTCI_Components_EVA)
                    oc_tool_lines.append(UTCI_Components_2)
                    oc_tool_lines.append(EVA_Components2)
                    oc_tool_lines.append(UTCI_Components_EVA_2)
                    oc_tool_lines.append(sc.sticky['OC_EVA_Parameter_Equations'])
                    oc_tool_lines.append(sc.sticky['OC_UTCI_parameter_equations'])
                    oc_tool_lines.append(UTCI_output_Equations_final)
                    oc_tool_lines.append(UTCI_control_Equations_EVA_final)
                    oc_tool_lines.append(EVA_Output_Equations_final)
                    oc_tool_lines.append(Printegrator25_data_2)
                    oc_tool_lines_2 = '\n'.join(oc_tool_lines)
                    variables['oc_tool'] = oc_tool_lines_2
                    #print oc_tool_lines_2
                    #lines.replace('@oc_tool', oc_tool_lines_2)
            # @OC END
            #first datablock that is the main groups
            match_search    = re.search('@(\w+)\#',lines)
            if match_search is not None and 's' in match_search.group(1)[0]:
                ingroup = 1
                blockdata = []
                lines=re.sub(match_search.group(0), '', lines)
                continue
            if ingroup == 1 and insubgroup == 0 and insubgroup2 == 0:
                blockdata.append(lines)
            #start subdatablock
            if match_search is not None and 'x' in match_search.group(1)[0]:
                insubgroup = 1
                category = re.sub('^\S', '', match_search.group(1))
                part = 'On'
                subdata[category] = {}
                subdata[category][part] = []
                lines=re.sub(match_search.group(0), '', lines)
                continue
            if match_search is not None and 'y' in match_search.group(1)[0]:
                part = 'Off'
                subdata[category][part] = []
                insubgroup2 = 1
                insubgroup = 0
                #subblockdata2 = []
                lines=re.sub(match_search.group(0), '', lines)
                continue
            if insubgroup == 1:
                subdata[category]['On'].append(lines)
            if insubgroup2 == 1:
                #subblockdata2.append(lines)
                subdata[category]['Off'].append(lines)
            if match_search is not None and 'z' in match_search.group(1)[0]:
                insubgroup = 0
                #del subdata[category]['On'][-1]
                insubgroup2 = 0
                del subdata[category]['Off'][-1]
                lines=re.sub(match_search.group(0), '', lines)
                continue
            #end subblockdata
            if match_search is not None and 'e' in match_search.group(1)[0]:
                ingroup = 0
                del blockdata[-1]
                lines=re.sub(match_search.group(0), '', lines)
                if 'e1' in  match_search.group(0) or 'e2' in  match_search.group(0):
                    if PrintReport == 2:
                        outputfile = variants_folder + 'report.txt'
                        reporttxt = open(outputfile, 'w')
                        reporttxt.close()
                        #outputfileshort = variants_folder + 'summary.txt'
                        #reporttxtshort = open(outputfileshort, 'w')
                        #reporttxtshort.close()
                    for zone_item in zone:
                        getzonevariables(zone_item)
                        if int(StandardOutputs) == 1:
                            newoutput = []
                            for stritem in printertempairnode:
                                newoutput.append(stritem.replace('@aname', variables['aname']))
                            variables['printertempairnode'] = PrintPrintegrator(name = 'Temperature', unit = variables['zunit16'], content = newoutput, labels = tempairnodelab, file = 'temp_1h_%s.prn'%variables['aname'])
                            newoutput = []
                            for stritem in printerpowairnode:
                                newoutput.append(stritem.replace('@aname', variables['aname']))
                            variables['printerpowairnode'] = PrintPrintegrator(name = 'Power', unit = variables['zunit17'], content = newoutput, labels = powairnodelab, file = 'p_spec_1h_%s.prn'%variables['aname'])
                        if (PrintReport == 1 or PrintReport == 2) and 'e2' in  match_search.group(0):
                            if PrintReport == 1:
                                outputfile = variants_folder + 'report_' + str(zone_item.Airnode.Name) + '.txt'
                                reporttxt = open(outputfile, 'w')
                                reporttxt.close()
                                #outputfileshort = variants_folder + 'summary_' + str(zone_item.Airnode.Name) + '.txt'
                                #reporttxtshort = open(outputfileshort, 'w')
                                #reporttxtshort.close()
                            writereport(zone_item, PrintReport)
                        #if 'MechVent' in dckdict[zone_item.Airnode.Name]:
                        #    print 'found'
                        for item in blockdata:
                            match_search3    = re.search('@(\w+)\#',item)
                            if match_search3 is not None and 'x' in match_search3.group(1)[0]:
                                category = re.sub('^\S', '', match_search3.group(1))
                                if category in dckdict[zone_item.Airnode.Name]:
                                    for subitem in subdata[category]['On']:
                                        for variablename in list(set(re.findall('@(\w+)',subitem))):
                                            subitem=re.sub('@'+variablename, str(variables[variablename]).encode('string-escape'), subitem)
                                        dckout.write(subitem)
                                else:
                                    for subitem in subdata[category]['Off']:
                                        for variablename in list(set(re.findall('@(\w+)',subitem))):
                                            subitem=re.sub('@'+variablename, str(variables[variablename]).encode('string-escape'), subitem)
                                        dckout.write(subitem)
                                continue
                            for variablename in list(set(re.findall('@(\w+)',item))):
                                item=re.sub('@'+variablename, str(variables[variablename]).encode('string-escape'), item)
                            dckout.write(item)
                    #if PrintReport > 0:
                    #    writeScheduleReport(zone[0])
                if 'e3' in  match_search.group(0):
                    for zone_item in zone:
                        variables['unitno']   = 800
                        if len(zone_item.Airnode.Ecalsurfaces) > 0:
                            for wall_item in zone_item.Airnode.Ecalsurfaces:
                                found = 0
                                for surface in zone_item.Airnode.Surfaces:
                                    if wall_item == surface.Surfnum:
                                        if hasattr(surface, 'Pcmlayer'):
                                            found = 1
                                        else:
                                            break
                                        variables['surface']  = surface.Surfnum
                                        variables['hconvo']   = walls_def[surface.Construction].Hback
                                        variables['abso']     = walls_def[surface.Construction].Abs_back
                                        variables['tbd']      = surface.Boundarytemp.split('*')[-1]
                                        variables['detailed'] = 0
                                        alposition = 0
                                        if len(zone_item.Airnode.Extal1surfaces) > 0:
                                            for sub3_item in range(len(zone_item.Airnode.Extal1surfaces)):
                                                if zone_item.Airnode.Extal1surfaces[sub3_item] == surface.Surfnum:
                                                    alposition = sub3_item
                                            if alposition == 0:
                                                variables['tsup399'] = 'Tinal1_' + zone_item.Airnode.Name
                                            else:
                                                variables['tsup399'] = 'TEOFL_S' + str(zone_item.Airnode.Extalsurfaces[alposition - 1])
                                            variables['mfsup399'] = 'mftab_' + zone_item.Airnode.Name
                                            variables['pdistance399'] = surface.Pspacing
                                            variables['pdiameter399'] = surface.Pdiameter
                                            variables['pwthickness399'] = surface.Pwallthickness
                                            variables['pconductivity399'] = surface.Pconductivity
                                            variables['cpfluid399'] = surface.Cpfluid
                                            variables['alloops399'] = surface.Nloops
                                        else:
                                            variables['tsup399'] = 18
                                            variables['mfsup399'] = 0
                                            variables['pdistance399'] = 0.15
                                            variables['pdiameter399'] = 0.02
                                            variables['pwthickness399'] = 0.002
                                            variables['pconductivity399'] = 1.46
                                            variables['cpfluid399'] = 4.19
                                            variables['alloops399'] = 1
                                        variables['pcmlayer'] = int(surface.Pcmlayer)
                                        variables['lu1'] = variables['unitno']
                                        variables['lu2'] = variables['unitno'] + 20
                                        dummy_layer_thickness = walls_def[surface.Construction].Thickness.split()
                                        #print dummy_layer_thickness
                                        dummy_layer_name = walls_def[surface.Construction].Layers.split()
                                        position = 0
                                        for subitem in range(len(dummy_layer_thickness)):
                                            if float(dummy_layer_thickness[subitem]) == 0:
                                                position = subitem
                                        variables['aldepth399'] = 0
                                        for subitem in range(0,position):
                                            variables['aldepth399'] = variables['aldepth399'] + float(dummy_layer_thickness[subitem])
                                        dummy_layer_thickness.pop(position)
                                        dummy_layer_name.pop(position)
                                        if zone_item.Airnode.Beam == 'DETAILED' or zone_item.Airnode.Diffuse == 'DETAILED' or zone_item.Airnode.Longwave == 'DETAILED':
                                            variables['detailed'] = 1
                                        variables['external'] = 0
                                        if surface.Boundarycond == 'EXTERNAL' or surface.Boundarycond == 'EXTCALC':
                                            variables['external'] = 1
                                        dummy_thickness = 0
                                        for subitem in dummy_layer_thickness:
                                            dummy_thickness = dummy_thickness + float(subitem)
                                        variables['nolayers'] = len(dummy_layer_name)
                                        variables['parameters']= 23 + (variables['nolayers'] - 1) * 5
                                        variables['layersdef']=''
                                        for subitem in range(len(dummy_layer_name)):
                                            dummy = dummy_layer_name[subitem]
                                            variables['layersdef']= variables['layersdef'] + """{0} ! 2 conductivity layer {4}
{1} ! 3 density of layer {4}
{2} ! 4 heat capacity of layer {4}
{3} ! 5 thickness of layer {4}
{5} ! 6 discretization of layer {4}""".format(layers_def[dummy].Conductivity,layers_def[dummy].Density,layers_def[dummy].Capacity, dummy_layer_thickness[subitem],subitem,1)
                                            if subitem < len(dummy_layer_name)-1:
                                                variables['layersdef']= variables['layersdef'] + '\n'
                                        variables['udeftemp']=''
                                        variables['udeftemp']= variables['udeftemp'] + """1 ! xx Number of userdefined wall temperatures
{0} ! 23 depth of Temperature n-1""".format(dummy_thickness/2)
                                        variables['wallarea'] = surface.Area
                                        variables['datafile1'] = surface.Fileheat
                                        variables['datafile2'] = surface.Filecool
                                        variables['unitno']   = variables['unitno'] + 1
                                        variables['aname']    = zone_item.Airnode.Name
                                        #variables['datafile1']= project_folder + 'Library\\Thermal\\cpPCMData_heat.dat'
                                        #variables['datafile2']= project_folder + 'Library\\Thermal\\cpPCMData_cool.dat'
                                if found == 1:
                                    for item in blockdata:
                                        for variablename in list(set(re.findall('@(\w+)',item))):
                                            item=re.sub('@'+variablename, str(variables[variablename]).encode('string-escape'), item)
                                        dckout.write(item)
                if 'e4' in  match_search.group(0):
                    for zone_item in zone:
                        variables['unitno']   = 900
                        if len(zone_item.Airnode.Eficalsurfaces) > 0:
                            for wall_item in zone_item.Airnode.Eficalsurfaces:
                                for surface in zone_item.Airnode.Surfaces:
                                    if wall_item == surface.Surfnum:
                                        variables['surface']  = surface.Surfnum
                                        variables['wallarea'] = surface.Area
                                        variables['unitno']   = variables['unitno'] + 1
                                        variables['aname']    = zone_item.Airnode.Name
                                        #variables['datafile1']= project_folder + 'Library\\Thermal\\cpPCMData_heat.dat'
                                        #variables['datafile2']= project_folder + 'Library\\Thermal\\cpPCMData_cool.dat'
                                        variables['datafile1']= TRNSYS_path + 'Building\\trnLIZARD\\Library\\Thermal\\cpPCMData_heat.dat'
                                        variables['datafile2']= TRNSYS_path + 'Building\\trnLIZARD\\Library\\Thermal\\cpPCMData_cool.dat'
                                for item in blockdata:
                                    for variablename in list(set(re.findall('@(\w+)',item))):
                                        item=re.sub('@'+variablename, str(variables[variablename]).encode('string-escape'), item)
                                    dckout.write(item)
                if 'e5' in  match_search.group(0):
                    for zone_item in zone:
                        if zone_item.Airnode.Ventilation:
                            for ventilation_item in zone_item.Airnode.Ventilation:
                                if ventilation_item.Calcmode == "AHU":
                                    getzonevariables(zone_item)
                                    for item in blockdata:
                                        for variablename in list(set(re.findall('@(\w+)',item))):
                                            item=re.sub('@'+variablename, str(variables[variablename]).encode('string-escape'), item)
                                        dckout.write(item)
                if 'e6' in  match_search.group(0):
                    for zone_item in zone:
                        if zone_item.Airnode.Activelayer == 1:
                            print 'found active layer'
                            getzonevariables(zone_item)
                            for item in blockdata:
                                for variablename in list(set(re.findall('@(\w+)',item))):
                                    item=re.sub('@'+variablename, str(variables[variablename]).encode('string-escape'), item)
                            dckout.write(item)
                if 'e7' in  match_search.group(0):
                    variables['unitno']   = 800
                    unit395_counter = 200
                    hamt_zone_surfaces = {}
                    # EXTCALBND side 2 (option A, IMPLICIT form): the far side of an internal wall faces a neighbour room, not the weather.
                    # Type 395 applies hconv2 ONCE and as a CONVECTIVE film only, with no separate longwave film on side 2, so the convective
                    # coefficient h_c and the longwave exchange with the neighbour room, linearised as h_r, go into that one film:
                    #   hconv2 = h_c + h_r                 h_c = interior convective coefficient, or an explicit non-default Hback of the wall
                    #                                      h_r = 4*SIGMA*eps*T_ref^3 = 18.51 kJ/(h m2 K) (eps 0.9, T_ref = 20 C)
                    #   TB2    = (h_c*TAIR + h_r*TMR)/hconv2   mirror neighbour (TB2 = own TAIR); any other boundary temperature is its own radiant
                    #                                      reference, so the weighted mean is that temperature itself (TB2 unchanged)
                    #   qWG2   = 0
                    #   beta2  = 7e-9*h_c/3.6              Lewis relation of the CONVECTIVE coefficient only (EXTCALEXT keeps its generic beta2)
                    # Why not the explicit form, qWG2 = AREA*SIGMA*eps*((273.15 + TMR)^4 - (273.15 + TSO395)^4) with hconv2 = h_c?  It is the same physics,
                    # but TSO395 is output 2 of the very Type 395 that takes qWG2 as input 8: an algebraic loop through TRNSYS (lagged iteration).
                    # TRNSYS test on the DIN GKP deck, QWG2_STABILITY_TEST_2026-09-30.md (260528_DIN16798-1 Comparison/trnlizard_side2_optionA): the explicit
                    # form costs 2.6x the run time and leaves 13 non-converged steps at STEP 0.1 h (185 at 0.25 h); the implicit form has the baseline run
                    # time, 0 non-converged steps and results within 0.05 K (p99) of the explicit form.  The thermal mirror walls get the same film as HBACK.
                    t395_hconv_interior     = 11      # TRNBuild interior convective default [kJ/(h m2 K)], about 3 W/(m2 K)
                    t395_hconv_back_default = 64      # library default HBACK = exterior convention, indistinguishable from "never set"
                    t395_tmr                = 'TMR_C1'  # same name as Type 395 input 14 of the DETAILED/SIMPLE side-1 coupling in Lizard_DCK_Template.py; global comfort-1 name, not per zone
                    t395_eps_side2          = 0.9     # same emissivity as the EXTCALEXT longwave terms and the Type 395 interior radiation film
                    t395_tref_k             = 293.15  # 20 C, reference temperature of the linearised longwave film = RTEMP of Type 56 (b18); same value as MIRROR_TREF_K
                    # Side 1 (room side) of a HAMT wall = the star-network link of Type 56, so that the zone and the wall exchange identical energy.
                    #   Type 56 (longwave STANDARD) exchanges heat with the wall surface as QCOMI = (Ts - TSTAR)/REQV [kJ/h] (manual Eq. 5.4.1-10: combined convection and
                    #   longwave to the other surfaces) and adds the absorbed gains QABSI at the surface node (Eq. 5.4.1-15). Type 395 with 11 inputs is ONE film, TB1 = TSTAR
                    #   with hconv1 = 1/(REQV*A) and no separate longwave film (has_separate_radiant_int = false), plus qWG1 = QABSI - QWG (QABSI excludes the longwave
                    #   exchange, which is inside the star link; QWG is a wall gain Type 56 has applied itself). Do NOT add QABSILW: with longwave STANDARD it is the radiative
                    #   share of the star link, -QCOMI = HCONVI*A*(TAIR - TSI) + QABSILW (exact in the DIN runs), i.e. it would count the longwave exchange twice.
                    #   In that mode Type 395 also takes the vapour pressure at the temperature of TB1 (hamt-core surface/boundary.rs: the interior Convection cell has one
                    #   temperature for heat and vapour), so RH1 is scaled to RH1*psat(TSTAR) = RH*psat(TAIR): the vapour pressure of the room air. beta1 stays the convective
                    #   Lewis coefficient of HCONVI. Longwave DETAILED / SIMPLE have no star node: the separated coupling (TAIR + HCONVI, TMR + linearised longwave film,
                    #   14 inputs) is kept and a warning is raised.
                    t395_magnus_a           = 17.62   # Magnus coefficients, saturation pressure over water; only their ratio is used (agrees with Hyland-Wexler to 2e-4 for |dT| <= 2 K between 10 and 30 C)
                    t395_magnus_b           = 243.12
                    # EXTCALEXT side 2: the longwave exchange with sky and ambient in qWG2 uses the outer surface temperature of the PREVIOUS time step,
                    # held by one Type 93 per wall (unit = Type 395 unit + t395_lag_unit_offset). With TSO395 of the current iteration the term is an
                    # algebraic loop through TRNSYS (TSO395 is output 2 of the Type 395 that takes qWG2 as input 8). TRNSYS test on the DIN GKP
                    # hygrothermal deck (2026-10-02, STEP 0.1 h, 260528_DIN16798-1 Comparison/trnlizard_fixes_20261002/extcalext_lag/REPORT.md):
                    # the loop left 22 non-converged steps per year (Message 441, all at sunrise or sunset, each running to the 4000-iteration limit
                    # while TSO swung by < 0.002 K) and took 1213 s; with the lag there are 0 non-converged steps and the run takes 681 s. Differences:
                    # zone air <= 0.02 K, annual heating +0.0008 %, outer wall surface <= 0.68 K (RMS 0.07 K, at sunrise/sunset), wall water content
                    # <= 0.05 %. A linearised implicit film as on EXTCALBND is not used here: it would put the cold sky into TB2, and the RH2 that
                    # keeps RH2*psat(TB2) at the vapour pressure of the outdoor air could exceed 100 %.
                    t395_lag_unit_offset    = 500     # 700, 701, ...: clear of the zone units (101 + 30 per zone), the plotters (65x) and the printers (95x)
                    if any(len(zone_item.Airnode.Ecalsurfaces) > 0 for zone_item in zone) and not any('@nin395' in template_line for template_line in blockdata):
                        ghenv.Component.AddRuntimeMessage(w, "The Type 395 block of the DCK template is out of date (no side-1 coupling placeholders): press Reload on the DCK template component, otherwise the old TAIR/HCONVI/TMR coupling is written.")
                    # Per-surface settings of Lizard_Hygro (surface attributes, None = input not connected): parameters 5 (depth),
                    # 6 (write report), 7 (report interval), 9 (minimum cells per layer) and the specific load in QheatKJ (input 11).
                    # Templates written before these settings have literal 1s for parameters 6 and 7 (reported once below).
                    t395_report_template = any('@writereport' in template_line for template_line in blockdata)
                    t395_report_warned = False
                    for zone_item in zone:
                        if len(zone_item.Airnode.Ecalsurfaces) > 0:
                            zname395 = zone_item.Airnode.Name
                            hamt_zone_surfaces[zname395] = []
                            # side-1 coupling of this zone's HAMT walls: the star link of Type 56 needs the star network (longwave STANDARD)
                            longwave395 = str(getattr(zone_item.Airnode, 'Longwave', 'STANDARD')).strip().upper()
                            star395 = (longwave395 == 'STANDARD')
                            if not star395:
                                simple_note395 = ' In SIMPLE mode the surface coefficients are combined (convection plus radiation) coefficients, so the longwave film is probably counted twice.' if longwave395 == 'SIMPLE' else ''
                                ghenv.Component.AddRuntimeMessage(w, "Zone %s: longwave mode %s has no star network (no TSTAR/REQV), so its HAMT walls (Type 395, surfaces %s) keep the separated coupling: convection HCONVI to TAIR plus a linearised longwave film to TMR. Type 56 evaluates the same wall-room longwave exchange with its own model, so the zone and the wall do not exchange identical energy. Use longwave STANDARD for an energy-consistent coupling.%s"%(zname395, longwave395, ', '.join(str(x) for x in zone_item.Airnode.Ecalsurfaces), simple_note395))
                            for wall_item in zone_item.Airnode.Ecalsurfaces:
                                for surface in zone_item.Airnode.Surfaces:
                                    if wall_item == surface.Surfnum:
                                        #print surface.Boundarycond
                                        variables['surface']  = surface.Surfnum
                                        variables['area'] = surface.Area
                                        variables['qwg2'] = 0
                                        # variables['mt1']  = '0.000000007*hconv1_S%s/3.6'%(surface.Surfnum) ! Adaptation to use HCONVI (only the convection part)
                                        variables['mt1'] = '0.000000007*HCONVI_S%s/3.6' % (surface.Surfnum)
                                        variables['mt2']  = '0.000000007*hconv2_S%s/3.6'%(surface.Surfnum)
                                        t395_report   = getattr(surface, 'Writereport', None)
                                        t395_interval = getattr(surface, 'Reportinterval', None)
                                        t395_depth    = getattr(surface, 'Addheatdepth', None)
                                        t395_heat     = getattr(surface, 'Addheat', None)
                                        t395_mindiv   = getattr(surface, 'Layermindiv', None)
                                        # QheatKJ (input 11) = specific load [W per m2 of wall] * AREA395 * 3.6: the total kJ/h of the wall, which Type 395
                                        # puts into the cell at the depth of parameter 5 (hamt-core multiplies it by the interpolation weights of that
                                        # cell only, not by the area). Default: the active-layer load of the zone; a Lizard_Hygro add_heat (a number, or a
                                        # TRNSYS expression in parentheses) replaces it for this surface and is not booked in qaddon (getzonevariables).
                                        if t395_heat is None:
                                            variables['specload'] = "-Q_al_{0}*AREA_{0}/Area_al1_{0}".format(zone_item.Airnode.Name)
                                        else:
                                            variables['specload'] = t395_heat
                                        variables['qaddon']         = '-QheatKJ_S%s'%(surface.Surfnum)
                                        variables['rh2']  = 'Rh_amb'
                                        lag93_unit = None   # Type 93 unit with TSO395 of the previous time step (EXTCALEXT walls only)
                                        if surface.Boundarycond == 'EXTCALEXT':
                                            variables['tbd']      = 'Tamb'
                                            variables['hconvo']   = '%s'%walls_def[surface.Construction].Hback
                                            #variables['hconvo']   = '1/ MAX(REQV_S%s,0.001)'%surface.Surfnum
                                            #variables['qwg2']  = 'IT_S%s * %s - QSKY_S%s'%(surface.Surfnum, walls_def[surface.Construction].Abs_back,surface.Surfnum)
                                            #print dir(surface)
                                            # Exterior solar: Type 56 gives a BOUNDARY-type wall no incident radiation (IT_S = 0), so the solar gain is the total radiation of the
                                            # Type 15 tilted surface with this wall's orientation (same kernel routine as Type 56, see getHamtSolarOrientations) times ABS-BACK.
                                            # The longwave emissivity is EPS-BACK, as in Type 56's outside heat balance (sigma * eps * (Tso^4 - Tfsky^4), Tfsky from Tsky, Tamb and Fsky).
                                            try:
                                                eps_exterior = float(walls_def[surface.Construction].Eps_back)
                                            except (AttributeError, TypeError, ValueError):
                                                eps_exterior = 0.9
                                            solar_surface_no = variables.get('hamt_solar_output', {}).get(str(getattr(surface, 'Orientation', '')))
                                            qwg2_solar = ''
                                            if solar_surface_no is not None:
                                                qwg2_solar = 'AREA395_S{0} * [15,{1}] * {2} + '.format(surface.Surfnum, getType15TiltedOutput(0, solar_surface_no, variables.get('hamt_solar_nsurf', 1)), walls_def[surface.Construction].Abs_back)
                                            # longwave terms with the outer surface temperature of the previous time step (see t395_lag_unit_offset)
                                            lag93_unit = unit395_counter + t395_lag_unit_offset
                                            tso_previous = '[{0},2]'.format(lag93_unit)
                                            variables['qwg2']  = qwg2_solar + 'AREA395_S{0} * {1} * SIGMA_S{0} * {2:g} * ((273.15 + Tsky)^4 - (273.15 + {3})^4) + AREA395_S{0} * (1-{1}) * SIGMA_S{0} * {2:g} * ((273.15 + Tamb)^4 - (273.15 + {3})^4)'.format(surface.Surfnum, surface.Fsky, eps_exterior, tso_previous)
                                            variables['rh2']  = 'Rh_amb'
                                        elif surface.Boundarycond == 'EXTCALBND':
                                            tbound = re.sub('@ANAME',zone_item.Airnode.Name,surface.Boundarytemp.split('*')[-1])

                                            variables['tbd']      = tbound
                                            # convective part h_c of the side-2 film: interior convective coefficient, unless the wall definition explicitly carries another back-side value
                                            hconv_bnd = t395_hconv_interior
                                            try:
                                                if abs(float(walls_def[surface.Construction].Hback) - t395_hconv_back_default) > 1e-9:
                                                    hconv_bnd = walls_def[surface.Construction].Hback
                                            except (TypeError, ValueError):
                                                pass
                                            # longwave part h_r of the side-2 film: the exchange with the neighbour room, linearised at T_ref (implicit, so no TSO395 term and no algebraic loop;
                                            # see the comment above the zone loop)
                                            hrad_bnd = '4*SIGMA_S{0}*{1}*{2}^3'.format(surface.Surfnum, t395_eps_side2, t395_tref_k)
                                            variables['hconvo']   = '{0} + {1}'.format(hconv_bnd, hrad_bnd)
                                            # TB2 = film-weighted mean of the two reference temperatures. A mirror neighbour (TB2 = this zone's TAIR) has this zone's mean radiant
                                            # temperature. For any other boundary temperature that temperature is also the best available radiant reference, so the weighted mean
                                            # is the temperature itself and TB2 stays as it is.
                                            variables['rh2']      = 'Rh_%s'%(zone_item.Airnode.Name)
                                            if tbound.strip().upper() == 'TAIR_' + zone_item.Airnode.Name.upper():
                                                variables['tbd']  = '({0}*TAIR_{1} + {2}*{3}) / hconv2_S{4}'.format(hconv_bnd, zone_item.Airnode.Name, hrad_bnd, t395_tmr, surface.Surfnum)
                                                # Type 395 takes the side-2 vapour pressure as RH2*psat(TB2) (one temperature for heat and vapour, as on side 1).
                                                # TB2 is now the weighted air/radiant temperature, so RH2 is scaled to keep the vapour pressure of the (mirror)
                                                # room air: RH2*psat(TB2) = RH*psat(TAIR), the same Magnus ratio as RH1 of the side-1 star link
                                                variables['rh2']  = 'Rh_{0}*EXP({1}*(TAIR_{0}/({2}+TAIR_{0})-TB2_S{3}/({2}+TB2_S{3})))'.format(zone_item.Airnode.Name, t395_magnus_a, t395_magnus_b, surface.Surfnum)
                                            variables['qwg2']     = 0
                                            # vapour: Lewis relation of the convective coefficient h_c only, not of the combined hconv2
                                            variables['mt2']      = '0.000000007*{0}/3.6'.format(hconv_bnd)
                                        variables['lu1'] = variables['unitno']
                                        # side-1 (room side) coupling, see the comment above the zone loop
                                        if star395:
                                            variables['tb1']     = 'TSTAR_%s'%zname395
                                            variables['hconv1']  = '(1/ MAX(REQV_S%s*AREA395_S%s,0.001))'%(surface.Surfnum,surface.Surfnum)
                                            variables['rh1']     = 'Rh_{0}*EXP({1}*(TAIR_{0}/({2}+TAIR_{0})-TSTAR_{0}/({2}+TSTAR_{0})))'.format(zname395,t395_magnus_a,t395_magnus_b)
                                            variables['nin395']  = 11
                                            variables['init395'] = '20 20 50 50 11 11 0 0 0 0 0'
                                        else:
                                            variables['tb1']     = 'TAIR_%s'%zname395
                                            variables['hconv1']  = 'HCONVI_S%s'%surface.Surfnum
                                            variables['rh1']     = 'Rh_%s'%zname395
                                            variables['nin395']  = 14
                                            variables['init395'] = '20 20 50 50 11 11 0 0 0 0 0 20 7.0 20.0'
                                            variables['d395']    = 'only with longwave DETAILED or SIMPLE'
                                        variables['unit395'] = unit395_counter
                                        unit395_counter = unit395_counter + 1
                                        hamt_zone_surfaces[zname395].append(surface.Surfnum)
                                        variables['udefdepth'] = t395_depth if t395_depth is not None else (t395_udepth if t395_udepth is not None else 0.02)
                                        variables['layer_min_div'] = t395_mindiv if t395_mindiv is not None else (t395_udivnum if t395_udivnum is not None else 100)
                                        variables['udivnum'] = variables['layer_min_div']   # parameter 9 placeholder of templates written before layer_min_div
                                        variables['writereport'] = -1 if t395_report is False else 1   # Type 395 writes its reports only for a value > 0
                                        variables['reportinterval'] = t395_interval if t395_interval is not None else 1
                                        if (t395_report is not None or t395_interval is not None) and not t395_report_template and not t395_report_warned:
                                            ghenv.Component.AddRuntimeMessage(w, "The Type 395 block of the DCK template is out of date (no @writereport/@reportinterval): press Reload on the DCK template component, otherwise write_report and report_interval of Lizard_Hygro are ignored (reports are written every 1 h).")
                                            t395_report_warned = True
                                        variables['datafile1'] = surface.Filemat
                                        variables['unitno']   = variables['unitno'] + 1
                                        variables['aname']    = zone_item.Airnode.Name
                                        # write the @s7# block per HAMT surface (multi-surface support)
                                        for item in blockdata:
                                            if star395 and '@d395' in item:
                                                continue  # inputs 12-14 (TAIR_MOIST1, HCONVI, TMR) exist only in the DETAILED/SIMPLE coupling
                                            for variablename in list(set(re.findall('@(\w+)',item))):
                                                item=re.sub('@'+variablename, str(variables[variablename]).encode('string-escape'), item)
                                            dckout.write(item)
                                        if lag93_unit is not None:
                                            # Type 93 (input value recall): output 2 = TSO395 of the previous time step, read by qWG2 of this wall.
                                            # The initial value is the initial wall temperature of the Type 395 block (20 C).
                                            dckout.write('\n'.join([
                                                '*' + '-' * 78,
                                                '* TSO395_S{0} of the previous time step for the longwave terms of qWG2_S{0} ([{1},2])'.format(surface.Surfnum, lag93_unit),
                                                'UNIT {0} TYPE 93\t TSO lag S{1}'.format(lag93_unit, surface.Surfnum),
                                                '*$UNIT_NAME TSO lag S{0}'.format(surface.Surfnum),
                                                '*$MODEL .\\Obsolete\\Input Value Recall\\Type93.tmf',
                                                'PARAMETERS 2',
                                                '1\t\t! 1 Number of inputs to be stored',
                                                '2\t\t! 2 Number of timesteps to be stored (including the current step)',
                                                'INPUTS 1',
                                                'TSO395_S{0}\t\t! outer surface temperature of the Type 395 wall (output 2)'.format(surface.Surfnum),
                                                '*** INITIAL INPUT VALUES',
                                                '20',
                                                '',
                                            ]))
                if 'e8' in  match_search.group(0):
                    for zname395, surfs395 in hamt_zone_surfaces.items():
                        variables['aname']       = zname395
                        variables['hamthumsum']  = ' + '.join(['HamtHumidityGain_KgPerHr_S%s'%s for s in surfs395])
                        for item in blockdata:
                            for variablename in list(set(re.findall('@(\w+)',item))):
                                item=re.sub('@'+variablename, str(variables[variablename]).encode('string-escape'), item)
                            dckout.write(item)
                if 'emulti1' in  match_search.group(0) and Multizone:
                    for item in blockdata:
                        for variablename in list(set(re.findall('@(\w+)',item))):
                            item=re.sub('@'+variablename, str(variables[variablename]).encode('string-escape'), item)
                        dckout.write(item)
                if 'emulti2' in  match_search.group(0) and Multizone:
                    for item in blockdata:
                        for variablename in list(set(re.findall('@(\w+)',item))):
                            item=re.sub('@'+variablename, str(variables[variablename]).encode('string-escape'), item)
                        dckout.write(item)
            if il == len(dck_file) - 20:
                getLinksInfo()
            if ingroup == 1 or insubgroup == 1:
                continue
            else:
                p = re.compile('@(\w+)')
                m = p.search(lines)
                if m is not None:
                    for variablename in list(set(re.findall('@(\w+)',lines))):
                        if isinstance(variables[variablename], basestring):
                            lines=lines.replace('@'+variablename, variables[variablename])
                        else:
                            lines=re.sub('@'+variablename, str(variables[variablename]).encode('string-escape'), lines)
                dckout.write(lines)
        dckout.close()
def runthermaldef():
    if build_mode == 'BUI' and reuse_shm_ism_ipm == 0:
        for zitem in zone:
            if len(zitem.Shader) > 0 or radmodedir == 'DETAILED':
                proc2 = Popen( TRNSYS_path + '\Building\TRNBUILD.exe ' + variants_folder + variant_name + '.b%s'%TRNSYS + ' /N /masks', shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
                proc2.communicate() #now wait
                break
        #cmh_200518 if radmodedif == 'STANDARD' and radmodelw == 'STANDARD':
        if radmodedif == 'STANDARD' and (radmodelw == 'STANDARD' or radmodelw == 'SIMPLE'):
            pass
        else:
            proc1 = Popen( TRNSYS_path + '\Building\TRNBUILD.exe ' + variants_folder + variant_name + '.b%s'%TRNSYS + ' /N /vfm', shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
            proc1.communicate() #now wait
    else:
        if reuse_shm_ism_ipm == 0:
            if radmodedif == 'DETAILED' or radmodelw == 'DETAILED':
                proc1 = Popen( TRNSYS_path + '\Building\TRNBID.exe ' + variants_folder + variant_name + '.b%s'%TRNSYS + ' /N /vfm', shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
                proc1.communicate() #now wait
            if radmodedir == 'DETAILED':
                proc2 = Popen( TRNSYS_path + '\Building\TRNBID.exe ' + variants_folder + variant_name + '.b%s'%TRNSYS + ' /N /masks', shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
                proc2.communicate() #now wait
        else:
            if radmodedif == 'DETAILED' or radmodelw == 'DETAILED':
                proc1 = Popen( TRNSYS_path + '\Building\TRNBUILD.exe ' + variants_folder + variant_name + '.b%s'%TRNSYS + ' /N /vfm', shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
                proc1.communicate() #now wait
#pablo
#new parameter ?RunVFM? . This is an Option for starting VFM calculation only.
#Therefore, create new function def runvfmdef()) in  ?Thermal simulation project manager component connect ?RunVFM? to ?data? (like RunRadianceSHM)
def runvfmdef():
    if build_mode == 'BUI' and reuse_shm_ism_ipm == 0:
        #cmh_200518 if radmodedif == 'STANDARD' and radmodelw == 'STANDARD':
        if radmodedif == 'STANDARD' and (radmodelw == 'STANDARD' or radmodelw == 'SIMPLE'):
            pass
        else:
            proc1 = Popen( TRNSYS_path + '\Building\TRNBUILD.exe ' + variants_folder + variant_name + '.b%s'%TRNSYS + ' /N /vfm', shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
            proc1.communicate() #now wait
    else:
        if reuse_shm_ism_ipm == 0:
            if radmodedif == 'DETAILED' or radmodelw == 'DETAILED':
                proc1 = Popen( TRNSYS_path + '\Building\TRNBID.exe ' + variants_folder + variant_name + '.b%s'%TRNSYS + ' /N /vfm', shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
                proc1.communicate() #now wait
        else:
            if radmodedif == 'DETAILED' or radmodelw == 'DETAILED':
                proc1 = Popen( TRNSYS_path + '\Building\TRNBUILD.exe ' + variants_folder + variant_name + '.b%s'%TRNSYS + ' /N /vfm', shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
                proc1.communicate() #now wait
def runsimulation():
    if exe_mode == 'exe64':
        proc1 = Popen( '"' + TRNSYS_path + '\\exe\\TRNexe64.exe" "' + variants_folder + variant_name + '.d%s" /N'%TRNSYS, shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
        proc1.communicate() #now wait
    elif exe_mode == 'exe32':
        proc1 = Popen( '"' + TRNSYS_path + '\\exe\\TRNexe.exe" "' + variants_folder + variant_name + '.d%s" /N'%TRNSYS, shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
        proc1.communicate() #now wait
    else:
        print("Please check your TRNSYS/TRNLizard path")

def radLine2Srf(ptCrd):
    def isCurveDup(crv, crvList):
        """This definition checks if a curve with the same start and end point
        is in the list """
        ptList = [crv.PointAtStart, crv.PointAtEnd]
        count = 0
        for c in crvList:
            # if len(crvList)>5: print c.PointAtStart,'           ', c.PointAtEnd, (c.PointAtStart in ptList) and (c.PointAtEnd in ptList)
            if (c.PointAtStart in ptList) and (c.PointAtEnd in ptList): count += 1
        # if len(crvList)>5: print count
        if count > 1: return True
        return False
    ptList = []
    for ptCount in range(0,len(ptCrd),3):
        ptList.append(rc.Geometry.Point3d(ptCrd[ptCount], ptCrd[ptCount+1], ptCrd[ptCount+2]))
    # make sure all the points are on the same plane
    #listLength = len(ptList)
    #tempPlane = rc.Geometry.Plane(ptList[0], ptList[int(1)], ptList[int(round(listLength/2))])
    ptOnPlane = ptList
    #[ptOnPlane.append(tempPlane.ClosestPoint(pt)) for pt in ptList]
    # it might look stupid but rc.Geometry.Polyline(ptOnPlane) doesn't work for self intersecting polylines
    if ptOnPlane[0]!= ptOnPlane[-1]: ptOnPlane.append(ptOnPlane[0])
    pl = rc.Geometry.Polyline(ptOnPlane).ToNurbsCurve()
    # print pl
    if showWireframe: return pl
    if len(ptOnPlane) == 5:
        srf = rc.Geometry.Brep.CreateFromCornerPoints(ptOnPlane[0], ptOnPlane[1], ptOnPlane[2],ptOnPlane[3], 0.0000001)
        return srf
    elif len(ptOnPlane) == 4:
        srf = rc.Geometry.Brep.CreateFromCornerPoints(ptOnPlane[0], ptOnPlane[1], ptOnPlane[2], 0.0000001)
        return srf
    plSeg = pl.DuplicateSegments()
    borderLines = []
    for seg in plSeg:
        if not isCurveDup(seg, plSeg): borderLines.append(seg)
    border = rc.Geometry.Curve.JoinCurves(borderLines)
    srf = rc.Geometry.Brep.CreatePlanarBreps(border)
    if srf: return srf[0]
    else: return pl
def createMesh(brep, gridSize):
    ## mesh breps
    def makeMeshFromSrf(i, inputBrep):
        try:
            mesh[i] = rc.Geometry.Mesh.CreateFromBrep(inputBrep, meshParam)[0]
            inputBrep.Dispose()
        except:
            print 'Error in converting Brep to Mesh...'
            pass
    # prepare bulk list for each surface
    mesh = [None] * len(brep)
    # set-up mesh parameters for each surface based on surface size
    meshParam = rc.Geometry.MeshingParameters.Default
    meshParam.MaximumEdgeLength = gridSize
    meshParam.MinimumEdgeLength = gridSize
    meshParam.GridAspectRatio = 1
    for i in range(len(mesh)): makeMeshFromSrf(i, brep[i])
    return mesh
def flattenList(l):return list(chain.from_iterable(l))
def getTestPts(inputMesh, movingDis, moveTestMesh= False, parallel = True):
        # preparing bulk lists
        testPoint = [[]] * len(inputMesh)
        srfNormals = [[]] * len(inputMesh)
        meshSrfCen = [[]] * len(inputMesh)
        meshSrfArea = [[]] * len(inputMesh)
        srfCount = 0
        for srf in inputMesh:
            testPoint[srfCount] = range(srf.Faces.Count)
            srfNormals[srfCount] = range(srf.Faces.Count)
            meshSrfCen[srfCount] = range(srf.Faces.Count)
            meshSrfArea[srfCount] = range(srf.Faces.Count)
            srfCount += 1
        try:
            def srfPtCalculator(i):
                # calculate face normals
                inputMesh[i].FaceNormals.ComputeFaceNormals()
                inputMesh[i].FaceNormals.UnitizeFaceNormals()
                for face in range(inputMesh[i].Faces.Count):
                    srfNormals[i][face] = (inputMesh[i].FaceNormals)[face] # store face normals
                    meshSrfCen[i][face] = inputMesh[i].Faces.GetFaceCenter(face) # store face centers
                    # calculate test points
                    if srfNormals[i][face]:
                        movingVec = rc.Geometry.Vector3f.Multiply(movingDis,srfNormals[i][face])
                        testPoint[i][face] = rc.Geometry.Point3d.Add(rc.Geometry.Point3d(meshSrfCen[i][face]), movingVec)
                    # make mesh surface, calculate the area, dispose the mesh and mass area calculation
                    tempMesh = rc.Geometry.Mesh()
                    tempMesh.Vertices.Add(inputMesh[i].Vertices[inputMesh[i].Faces[face].A]) #0
                    tempMesh.Vertices.Add(inputMesh[i].Vertices[inputMesh[i].Faces[face].B]) #1
                    tempMesh.Vertices.Add(inputMesh[i].Vertices[inputMesh[i].Faces[face].C]) #2
                    tempMesh.Vertices.Add(inputMesh[i].Vertices[inputMesh[i].Faces[face].D]) #3
                    tempMesh.Faces.AddFace(0, 1, 3, 2)
                    massData = rc.Geometry.AreaMassProperties.Compute(tempMesh)
                    meshSrfArea[i][face] = massData.Area
                    massData.Dispose()
                    tempMesh.Dispose()
        except:
            print 'Error in Extracting Test Points'
            pass
        # calling the function
        if parallel:
            tasks.Parallel.ForEach(range(len(inputMesh)),srfPtCalculator)
        else:
            for i in range(len(inputMesh)):
                srfPtCalculator(i)
        if moveTestMesh:
            # find surfaces based on first normal in srfNormals - It is a simplification we can write a better function for this later
            for meshCount, mesh in enumerate(inputMesh):
                vector = srfNormals[meshCount][0]
                vector.Unitize()
                vector = rc.Geometry.Vector3d.Multiply(movingDis, vector)
                mesh.Translate(vector.X, vector.Y, vector.Z)
        return flattenList(testPoint), flattenList(srfNormals), flattenList(meshSrfArea), inputMesh


def createFiles(mode, _subWorkingDir, _facesArea, _RADMaterials, _testPoints, _ptsVectors, shdstate, Properties, zone, filename, zoneid):
    # Flatten the _facesArea datatree
    flat_facesArea = _facesArea
    # Create and write data within 'area.pts' file
    PTSFileName = _subWorkingDir + str(zoneid) +"_"+ mode + "_area" + '.pts' #CSH_220420 added index
    with open(PTSFileName, 'w') as file_object:
        for value in flat_facesArea:
            for subvalue in value:
                file_object.write("%s\n" % subvalue)
    file_object.close()
    adjacentsurfaces = []
    duy = os.path.basename(filename).split('_')[2:]
    if len(duy) == 1:
        dzonename = duy[0].split('.')[0]
    for zone_item in zone:
        if zone_item.Name == dzonename:
            for sitem in zone_item.Airnode.Surfaces:
                #print sitem.Boundarycond
                #print sitem.Construction
                if re.match('ADJACENT',sitem.Boundarycond,True) and re.search('TREE', sitem.Construction):
                    adjacentsurfaces.append(sitem.Surfnum)
    externalwindows = []
    for zone_item in zone:
        if zone_item.Name == dzonename:
            for sitem in zone_item.Airnode.Surfaces:
                #print sitem.Boundarycond
                if re.match('^EXT',sitem.Boundarycond,True):
                    externalwindows.append(sitem.Surfnum)
    #print adjacentsurfaces
    # Create and write data within 'surfID_npoints.ptn' file
    if mode == 'shm':
        PTNFileName = _subWorkingDir + str(zoneid) +"_"+ mode  + "_surface" + '.inf' #CSH_220420 added index
    elif mode == 'geosurf' or mode == 'ipm':
        PTNFileName = _subWorkingDir + mode  + "_surface_%s"%shdstate + '.inf'
    with open(PTNFileName, 'w') as file_object:
        countSurface = len(_RADMaterials)
        file_object.write("%s %s !total number of surfaces dist_to_base\n" % (countSurface, _distBaseSrf)) #CSH_220420 added distance to base
        for i, raditem in enumerate(_RADMaterials):
            count = len(_facesArea[i])
            item = re.sub('S','',_RADMaterials[i])
            if (Properties[_RADMaterials[i]]['TYPE'] == 'trans' or Properties[_RADMaterials[i]]['TYPE'] == 'glass') and int(item) in adjacentsurfaces and mode=='geosurf':
                tau = float(Properties[_RADMaterials[i]]['DATA'])*float(Properties[_RADMaterials[i]]['FACTOR'])
            elif (Properties[_RADMaterials[i]]['TYPE'] == 'trans' or Properties[_RADMaterials[i]]['TYPE'] == 'glass') and int(item) in externalwindows and mode=='shm':
                #print Properties[_RADMaterials[i]]['DATA']
                #print Properties[_RADMaterials[i]]['FACTOR']
                #tau = float(Properties[_RADMaterials[i]]['DATA'])*float(Properties[_RADMaterials[i]]['FACTOR'])
                tau = float(Properties[_RADMaterials[i]]['DATA'])
            else:
                tau = 0
            if tau == 0 and mode == 'shm':
                pass
            else:
                if i == 0:
                    file_object.write("%s %s %s !SurfaceID ptn tau\n" % (item, count, tau))
                else:
                    file_object.write("%s %s %s\n" % (item, count, tau))
    file_object.close()
    # Flatten
    flat_testPoints =[]
    for i in range(len(_testPoints)):
        flat_testPoints.extend(_testPoints[i])
    flat_ptsVectors = []
    for i in range(len(_ptsVectors)):
        flat_ptsVectors.extend(_ptsVectors[i])
    # warning if not same length
    if len(flat_testPoints) != len(flat_ptsVectors):
        w = gh.GH_RuntimeMessageLevel.Warning
        ghenv.Component.AddRuntimeMessage(w, "Error, testPoints and ptsVectors do not have the same length")
    #Create and write data within 'testpoints_vectors.pts' file
    TestPTSFileName = _subWorkingDir + str(zoneid) +"_" + mode  + "_points_dirvectors" + '.pts' #CSH_220420 added index
    with open(TestPTSFileName, 'w') as file_object:
        for i in range(len(flat_testPoints)):
            ptsx = flat_testPoints[i][0]
            ptsy = flat_testPoints[i][1]
            ptsz = flat_testPoints[i][2]
            vectorx = flat_ptsVectors[i].X
            vectory = flat_ptsVectors[i].Y
            vectorz = flat_ptsVectors[i].Z
            file_object.write("%s %s %s %s %s %s\n" % (ptsx, ptsy, ptsz, vectorx, vectory, vectorz))
    file_object.close()
    return TestPTSFileName #CSH_220420 added pts file name as funtion return value to pass to trnraytrace as input arg

def readRadFile(filename, mode,zonesurfaces, zone):
    file = open(filename, 'r')
    fileAllJoined = ""
    for line in file:
        if line != []:
            line = line.replace("\n",",")
            line = line.replace("\t",",")
            line = line.replace(" ",",")
            if '#' in line: line = ""
            if line != "": fileAllJoined  = fileAllJoined + line.replace(" ", ",")
    file.close()

    fileSeparated = []
    nfile = fileAllJoined.split(",")
    for seg in nfile:
        if seg != "": fileSeparated.append(seg)
    surfaces = {}
    RADMaterials = []
    RADSurfaces = []
    Properties = {}
    #print fileSeparated
    zoneid, shaddummy, duy = os.path.basename(filename).split('_')
    duy = os.path.basename(filename).split('_')[2:]
    if len(duy) == 1:
        dzonename = duy[0].split('.')[0]
    #print zonesurfaces[zoneid]
    externalwindows = []
    for zone_item in zone:
        if zone_item.Name == dzonename:
            for sitem in zone_item.Airnode.Surfaces:
                #print sitem.Boundarycond
                if re.match('^EXT',sitem.Boundarycond,True):
                    externalwindows.append(sitem.Surfnum)
    #print externalwindows
    for segCount, seg in enumerate(fileSeparated):
        # I should fix this code later! This is really poor written.
        if re.search("void",seg):
            Properties[fileSeparated[segCount + 2]] = {}
            Properties[fileSeparated[segCount + 2]]['TYPE'] = fileSeparated[segCount + 1]

            #print fileSeparated[segCount + 6]

            #ccf changed 200722
            Properties[fileSeparated[segCount + 2]]['DATA'] = fileSeparated[segCount + 6]
            Properties[fileSeparated[segCount + 2]]['FACTOR'] = fileSeparated[segCount + 11]
        if seg.upper() == "polygon".upper():
            if re.search('WIN_',fileSeparated[segCount + 1]) and mode == 'shm':
                if int(re.sub('S','',fileSeparated[segCount - 1])) in externalwindows:
                    pass
                    print "found external window for shm calculation"
                else:
                    continue
            elif mode == 'geosurf':
                if int(re.sub('S','',fileSeparated[segCount - 1])) in zonesurfaces[zoneid]:
                    pass
                else:
                    continue
            elif mode == 'ipm':
                pass
            else:
                continue
            material = fileSeparated[segCount - 1]
            numPt = int(fileSeparated[segCount + 4])
            ptCrd = fileSeparated[segCount + 5: segCount + 5 + numPt]
            ptCrd = [float(pt) for pt in ptCrd]
            srf = radLine2Srf(ptCrd)
            if mode == 'geosurf':
                srf.Flip()
            RADMaterials.append(material)
            RADSurfaces.append(srf)
    #print RADMaterials


    _gridSize = sc.sticky[sc.doc.Path]["GridSpacingSolarConcave"] #CSH_220427 changed to take from b18 file input moved to multizone component

    moveTestMesh_ = True
    colltPts =[]
    collpVec = []
    collfArea = []
    collMesh = []
    for _testGeometry in RADSurfaces:
        inputMesh = []
        if type(_testGeometry) == rc.Geometry.Mesh and _distBaseSrf!=None:
            ghenv.Component.Params.Input[1].Name = '.'
            ghenv.Component.Params.Input[1].NickName = '.'
            inputMesh.append(_testGeometry)

        elif _gridSize!=None and _distBaseSrf!=None:
            initMesh = createMesh([_testGeometry], _gridSize)
            for m in initMesh: inputMesh.append(m)

        if _distBaseSrf<0:
            msg = "Distance from base should be greater than 0. Flip the input surface instead of using a negative number."
            ghenv.Component.AddRuntimeMessage(gh.GH_RuntimeMessageLevel.Warning, msg)
        else:
            testPoints, ptsVectors, facesArea, mesh = getTestPts(inputMesh, _distBaseSrf, moveTestMesh_)
            colltPts.append(testPoints)
            collpVec.append(ptsVectors)
            collfArea.append(facesArea)
        collMesh.append(mesh)
    return collMesh, colltPts, collpVec, collfArea, RADMaterials, Properties

# Start zone depending Variable declaration for the deck file
@timing
def getzonevariables(zone_item):
    variables['resdir']          = subfolderres
    #print zone_item.Airnode.Name
    variables['aname']          = zone_item.Airnode.Name
    variables['zname']          = zone_item.Airnode.Zonename
    variables['ablaname']       = zone_item.Airnode.Name
    dckdict[zone_item.Airnode.Name] = {}
    variables['stadiacrossarea']    = 4000
    #ideal heating and cooling
    variables['buihtmaxpower']      = 1000
    variables['buiclmaxpower']      = 1000
    variables['T_set_ht']           = 20
    variables['Deltatht']           = 0
    variables['schedule_ht']        = 0
    variables['T_set_cl']           = 20
    variables['Deltatcl']           = 0
    variables['schedule_cl']        = 0
    variables['tamb24h_htbui']      = 12
    variables['yx_top_ht']          = 0
    variables['yx_top_cl']          = 0
    variables['tamb24h_clbui']      = 12
    variables['ctrl_htbui']      = zone_item.Airnode.Name
    variables['ctrl_clbui']      = zone_item.Airnode.Name
    variables['tctrl_htbui']      = 'TOP_%s'%zone_item.Airnode.Name
    variables['tctrl_clbui']      = 'TOP_%s'%zone_item.Airnode.Name
    #standard gains
    variables['luxlevel']         = 'not defined'
    variables['efflight']         = 120
    variables['power_light']      = 10
    variables['dimming']          = 0
    variables['sched_light']      = 0
    variables['powercomp']        = 0
    variables['poweraddon']       = 0
    variables['appers']           = zone_item.Airnode.Areaperperson
    variables['power_pers']       = 0
    variables['co2ppers']         = 0
    variables['A1ratio']          = 1
    variables['A2ratio']          = 0
    variables['A3ratio']          = 0
    variables['winterred_comp']   = 0
    variables['winterred_pers']   = 0
    variables['gainredon']        = 12
    variables['compheat']         = 0
    variables['lightheat']        = 0
    variables['mischeat']        = 0
    variables['perm_light']       = 0
    variables['power_comp']       = 0
    variables['power_comp_tot']   = 0
    variables['compheat']         = 0
    variables['sched_comp']       = 0
    variables['sched_og']         = 0
    variables['power_og']         = 0
    variables['oc_tool'] = ''
    variables['UTCIcomfortonline'] = ''
    variables['UTCIcomfortprint'] = ''
    variables['TMRcomfortonline'] = ''
    variables['TMRcomfortprint'] = ''
    #coldbridge
    variables['thb_val']        = 0.05
    variables['thb_area']       = 0
    #infiltration
    variables['ach_inf']        = 0
    variables['schedule_inf']   = 0
    variables['min_inf']        = 0
    variables['yx_inf']         = 0
    # @OC START
    #OC_zone_variables
    if 'OC_command_lines_zone_variables' in sc.sticky[sc.doc.Path]:
        exec(sc.sticky['OC_command_lines_zone_variables'])
    # @OC END
    #earth duct
    variables['Tmean_amb']      = sc.sticky[sc.doc.Path]["Tambmean"]
    variables['eta_ed']         = 0
    #ventilation
    variables['aeff1top']        = 1
    variables['aeff1bot']        = 1
    variables['hdiff_sv1']       = 1
    variables['schedule_sv1']    = 0
    variables['taircomp_sv1']    = 26
    variables['tairon_sv1']      = 25
    variables['tairoff_sv1']     = 23
    variables['tambon_sv1']      = 12
    variables['tamb24on_sv1']    = 12
    variables['maxach_sv1']      = 5
    variables['aeff2top']        = 1
    variables['aeff2bot']        = 1
    variables['hdiff_sv2']       = 1
    variables['schedule_sv2']    = 0
    variables['taircomp_sv2']    = 26
    variables['tairon_sv2']      = 25
    variables['tairoff_sv2']     = 23
    variables['tambon_sv2']      = 1000
    variables['tamb24on_sv2']    = 1000
    variables['maxach_sv2']      = 5
    variables['humctrl_sv1']      = 0
    variables['humctrl_sv2']      = 0
    variables['humctrl_mv']      = 0
    variables['tsummer_mv']     = 18
    variables['twinter_mv']     = 22
    variables['tsummer2_mv']     = 18
    variables['twinter2_mv']     = 22
    variables['hummax_mv']      = -1
    variables['hummin_mv']      = -1
    variables['hrcsens']        = 0
    variables['hrclat']         = 0
    variables['schedule_annual']    = 1
    variables['schedule_mv']    = 0
    variables['schedule2_mv']   = 1
    variables['acr_mv']         = 0
    variables['acr_min_mv']      = 0
    variables['acr_max_mv']      = 0
    variables['tamb24h_mvcl']   = 12
    variables['reftemp_mv']     = 'Tamb_m24'
    variables['sfp_mv']         = 1
    variables['THYB_up_hi']     = 26
    variables['THYB_lo_hi']     = 12
    variables['TSUP_up_hi']     = 26
    variables['TSUP_lo_hi']     = 12
    variables['yx_hyb']         = 0
    variables['yx_mv']          = 0
    variables['mvreduction']    = 0
    variables['mvfraction']    = 1
    variables['toutsideahu']    = 'Tamb'
    variables['woutsideahu']    = 'Abshum_amb'
    variables['toutside_sv1']   = 'Tamb'
    variables['toutside_sv2']   = 'Tamb'
    variables['thrcmv']    = 0
    variables['abshumsupmv']    = 0
    variables['relhumsupmv']    = 0
    variables['ahusenht']    = 0
    variables['ahusencl']    = 0
    variables['ahulathu']    = 0
    variables['ahulatdh']    = 0
    variables['ahusendhcl']  = 0
    variables['ahusendhht']  = 0
    variables['hrcsencl']    = 0
    variables['hrcsenht']    = 0
    #comfort
    variables['setdef']         = ''
    variables['setcomf1']       = 0
    variables['setcomf2']       = 0
    variables['setcomf3']       = 0
    variables['setcomf4']       = 0
    #shading control
    variables['tshdactive']     = -20
    variables['shadingctrl']    = 0
    variables['shadingcta']    = 0
    variables['shadingctb']    = 0
    #domestic hot water
    variables['tcw']            = 14
    variables['thw']            = 45
    variables['wwpperspd']      = 0
    variables['npers']          = 0
    variables['schedule_dhw']   = 0
    variables['fhours']         = 1
    #active layer
    variables['tsurfal1']      = 0
    variables['toutal1']         = 0
    variables['tnodeal1']          = 0
    variables['qtabsfl1']        = 0
    variables['qtabsfl2']        = 0
    variables['qtabs1']         = 0
    variables['qtabs2']         = 0
    variables['mflowal1']          = 0
    variables['tinal2']         = 0
    variables['tinal3']         = 0
    variables['schedule_al1ht']  = 0
    variables['schedule_al1cl']  = 0
    variables['tsummeral1']        = 0
    variables['twinteral1']        = 0
    variables['tsummer2al1']        = 0
    variables['twinter2al1']        = 0
    variables['tamb24h_al1cl']   = 0
    variables['tamb24h_al1ht']   = 0
    variables['allyear_al1cl']   = 0
    variables['permsched_al1cl']   = 0
    variables['thton_al1']       = 20 + 0.5
    variables['thtoff_al1']      = 20 + 1.5
    variables['tclon_al1']       = 26 - 0.5
    variables['tcloff_al1']      = 26 - 1.5
    variables['actl1_tdpctrl']   = 1
    variables['actl1_suplmode']  = 0
    variables['shpal1']         = 40
    variables['scpal1']         = 50
    variables['areaal1']         = 0
    variables['actl1ctrl_']      = 'TOP_'
    variables['smflowal1']         = 0
    variables['yal1cl']     = 0
    variables['yal1ht']    = 0
    variables['ctrlal1'] = variables['aname']
    variables['tsurfal2']      = 0
    variables['toutal2']         = 0
    variables['tnodeal2']          = 0
    variables['mflowal2']          = 0
    variables['schedule_al2ht']  = 0
    variables['schedule_al2cl']  = 0
    variables['tsummeral2']        = 0
    variables['twinteral2']        = 0
    variables['tsummer2al2']        = 0
    variables['twinter2al2']        = 0
    variables['tamb24h_al2cl']   = 0
    variables['tamb24h_al2ht']   = 0
    variables['allyear_al2cl']   = 0
    variables['permsched_al2cl']   = 0
    variables['thton_al2']       = 20 + 0.5
    variables['thtoff_al2']      = 20 + 1.5
    variables['tclon_al2']       = 26 - 0.5
    variables['tcloff_al2']      = 26 - 1.5
    variables['actl2_tdpctrl']   = 1
    variables['actl2_suplmode']  = 0
    variables['shpal2']         = 40
    variables['scpal2']         = 50
    variables['areaal2']         = 0
    variables['actl2ctrl_']      = 'TOP_'
    variables['smflowal2']         = 0
    variables['yal2cl']     = 0
    variables['yal2ht']    = 0
    variables['ctrlal2'] = variables['aname']
    variables['setback_al1']    = 0
    variables['setback_al2']    = 0
    #balance outputs
    #variables['qcomiwall']         = 0
    #variables['qcomiwin']          = 0
    #variables['qcomifloor']        = 0
    #variables['qcomiceiling']      = 0
    #variables['qcomiroof']         = 0
    variables['qsiwall']         = 0
    variables['qsiwin']          = 0
    variables['qsiext']          = '0'
    variables['qsifloor']        = 0
    variables['qsiceiling']      = 0
    variables['qsiroof']         = 0
    variables['qsiabwall']         = 0
    variables['qsiabwin']          = 0
    variables['qsiabfloor']        = 0
    variables['qsiabceiling']      = 0
    variables['qsiabroof']         = 0
    variables['qaddon']         = '0'
    # add-on demand of THIS zone: the QheatKJ of its own HAMT walls (it used to collect the walls of every zone, so each zone of a
    # multi-zone model reported the wall heat of all zones). QheatKJ of the active-layer load is add-on demand; a Lizard_Hygro
    # add_heat is a source the user prescribes (heater, calibration source, ...) and is not booked as demand of the zone
    for wall_item in zone_item.Airnode.Ecalsurfaces:
        for surface in zone_item.Airnode.Surfaces:
            if wall_item == surface.Surfnum:
                if getattr(surface, 'Addheat', None) is None:
                    variables['qaddon']  += '-QheatKJ_S%s'%(surface.Surfnum)
    #airnode definition
    variables['anr']            = "%02d" % (zone_item.Anr,)
    unitsperzone = 30
    for counter in range(1,unitsperzone):
        variables["zunit%02d" % counter] = "%02d" % (counter + (zone_item.Anr - 1) * unitsperzone + zoneunitstart)
    variables['column1'] = (zone_item.Anr - 1) * 200 + 230
    variables['column2'] = (zone_item.Anr - 1) * 200 + 330
    convdict  = {}
    for item in unitpos:
        if 'zunit' in item:
            newkey = variables[item]
            convdict[item] = newkey
        else:
            pass
    for item in convdict:
        unitpos[convdict[item]] = copy.deepcopy(unitpos[item])
        unitpos[convdict[item]] = re.sub('@column1',str(variables['column1']),unitpos[convdict[item]] )
        unitpos[convdict[item]] = re.sub('@column2',str(variables['column2']),unitpos[convdict[item]] )
        variables['upos%s' % item] = unitpos[convdict[item]]
    for item in unitpos:
        if 'zunit' in item:
            continue
        else:
            unitpos[item] = re.sub('@column1',str(variables['column1']),unitpos[item] )
            unitpos[item] = re.sub('@column2',str(variables['column2']),unitpos[item] )
            variables["upos%03d" % int(item)] = unitpos[item]
    newlink = {}
    for item in links:
        if 'zunit' in item:
            fname, tname = item.split(':')
            if 'zunit' in fname:
                newfname = variables[fname]
            else:
                newfname = fname
            if 'zunit' in tname:
                newtname = variables[tname]
            else:
                newtname = tname
            newlink['%s:%s'%(newfname,newtname)] = links[item]
    for item in newlink:
        links[item] = newlink[item]
    variables['volume']         = round(zone_item.Airnode.Volume,1)
    variables['refarea']        = round(zone_item.Airnode.Floorarea,1)
    variables['totairnodearea']        = round(zone_item.Airnode.Totfloorarea,1)
    variables['sched_occ']      = 1
    variables['dssen1']         = 'SHD_active_{0} * [{1},2] + not(SHD_active_{0}) * [{1},1]'.format(variables['aname'],variables['zunit04'])
    variables['dssen2']         = 'SHD_active_{0} * [{1},4] + not(SHD_active_{0}) * [{1},3]'.format(variables['aname'],variables['zunit04'])
    variables['dssen3']         = 'SHD_active_{0} * [{1},6] + not(SHD_active_{0}) * [{1},5]'.format(variables['aname'],variables['zunit04'])
    #annual schedule
    variables['jan']       = 1
    variables['feb']       = 1
    variables['mar']       = 1
    variables['apr']       = 1
    variables['may']       = 1
    variables['jun']       = 1
    variables['jul']       = 1
    variables['aug']       = 1
    variables['sep']       = 1
    variables['oct']       = 1
    variables['nov']       = 1
    variables['dec']       = 1
    variables['useannual_mv']       = 1
    variables['useannual_light']    = 0
    variables['useannual_comp']     = 1
    #ideal heating and cooling
    if zone_item.Airnode.Heating:
        variables['buihtmaxpower']      = zone_item.Airnode.Heating.Maxpower
        variables['T_set_ht']           = zone_item.Airnode.Heating.Settemperature
        variables['Deltatht']           = zone_item.Airnode.Heating.Setback
        variables['schedule_ht']        = 'SCHED_' + zone_item.Airnode.Heating.Schedule
        schedulescoll.append(variables['schedule_ht'])
        variables['tamb24h_htbui']      = zone_item.Airnode.Heating.Tamb24hon
        if zone_item.Airnode.Heating.Ctrl == 'OPERATIVE':
            variables['yx_top_ht']             = 1
        #if zone_item.Airnode.Heating.Space == 'ZONE':
        #    variables['ctrl_htbui'] = variables['zname']
        #elif zone_item.Airnode.Heating.Space == 'AIRNODE':
        #    variables['ctrl_htbui'] = variables['aname']
        #else:
        #    variables['ctrl_htbui'] = zone_item.Airnode.Heating.Space
        #variables['tctrl_htbui'] = 'TOP_%s'%variables['ctrl_htbui']
        if zone_item.Airnode.Heating.Space is None:
            variables['ctrl_htbui'] = variables['aname']
        else:
            variables['ctrl_htbui'] = zone_item.Airnode.Heating.Space
        if zone_item.Airnode.Heating.Ctrl is None:
            variables['tctrl_htbui'] = zone_item.Airnode.Heating.Space
            variables['yx_top_ht']             = 1
            variables['ctrl_htbui'] = variables['aname']
    if zone_item.Airnode.Cooling:
        variables['buiclmaxpower']      = zone_item.Airnode.Cooling.Maxpower
        variables['T_set_cl']           = zone_item.Airnode.Cooling.Settemperature
        variables['Deltatcl']           = zone_item.Airnode.Cooling.Setback
        variables['schedule_cl']        = 'SCHED_' + zone_item.Airnode.Cooling.Schedule
        schedulescoll.append(variables['schedule_cl'])
        variables['tamb24h_clbui']      = zone_item.Airnode.Cooling.Tamb24hon
        if zone_item.Airnode.Cooling.Ctrl == 'OPERATIVE':
            variables['yx_top_cl']             = 1
        #if zone_item.Airnode.Cooling.Space == 'ZONE':
        #    variables['ctrl_clbui'] = variables['zname']
        #elif zone_item.Airnode.Cooling.Space == 'AIRNODE':
        #    variables['ctrl_clbui'] = variables['aname']
        #else:
        #    variables['ctrl_clbui'] = zone_item.Airnode.Cooling.Space
        #variables['tctrl_clbui'] = 'TOP_%s'%variables['ctrl_clbui']
        if zone_item.Airnode.Cooling.Space is None:
            variables['ctrl_clbui'] = variables['aname']
        else:
            variables['ctrl_clbui'] = zone_item.Airnode.Cooling.Space
        if zone_item.Airnode.Cooling.Ctrl is None:
            variables['tctrl_clbui'] = zone_item.Airnode.Cooling.Space
            variables['yx_top_cl']             = 1
            variables['ctrl_clbui'] = variables['aname']
    #illuminance
    if UseDaylightSim == 0:
        pass
    else:
        if UdefPathDaylightRes:
            variables['illfilename'] = UdefPathDaylightRes + variant_name + '_' + zone_item.Airnode.Name + '.ill'
            if os.path.isfile(variables['illfilename']):
                pass
            else:
                ghenv.Component.AddRuntimeMessage(err, "Illuminance file missing for variant %s, Airnode %s"%(variant_name, zone_item.Airnode.Name))
                sys.exit()
        else:
            variables['illfilename'] = variant_name + '_' + zone_item.Airnode.Name + '.ill'
    """
    for items in zone_item.Airnode.Winsurfaces:
        for items2 in zone_item.Airnode.Surfaces:
            if items2.Surfnum == items and items2.Mshade == 'BSDFCOMPLEX':
                dummy_config = items2.Configids.rstrip()
                dummy_config = dummy_config.split(',')
                dummy_config.append(items2.Baseconfigid)
                dummy_config = list(set(dummy_config))
                dummy_config.pop(0)
                config_list = []
                for i in reversed(dummy_config):
                    config_list.append(i)
                variables['type9inp'] = len(config_list)*3 * int(items2.BSDFFacades)
                variables['type9par'] = variables['type9inp']*4+6
                variables['type9data'] = ''
                for item in range(0,variables['type9inp']):
                    variables['type9data'] = variables['type9data'] + '1 1 0 1 ! Interpolmode, Mult, Add, Sample\n'
                variables['dssen1'] = variables['dssen1'] + ' + LUX_level1_S{0}_{1}'.format(items2.Surfnum,zone_item.Airnode.Name)
                variables['dssen2'] = variables['dssen2'] + ' + LUX_level2_S{0}_{1}'.format(items2.Surfnum,zone_item.Airnode.Name)
                variables['dssen3'] = variables['dssen3'] + ' + LUX_level3_S{0}_{1}'.format(items2.Surfnum,zone_item.Airnode.Name)
                variables['BSDF_window_file'] = items2.Datafile
                variables['BSDF_gas_file'] = 'gasdata.csv'
    """
    #shading control
    if len(zone_item.Airnode.Winsurfaces)>0:
        output_storage = '0'
        output_storagea = '0'
        output_storageb = '0'
        for items in zone_item.Airnode.Winsurfaces:
            output_storage = output_storage + '+ SHADCNTRL_S{0}'.format(items)
            for items2 in zone_item.Airnode.Surfaces:
                if items2.Surfnum == items and items2.Sgroup == 'B':
                    output_storageb = output_storageb + '+ SHADCNTRL_S{0}'.format(items)
                elif items2.Surfnum == items:
                    output_storagea = output_storagea + '+ SHADCNTRL_S{0}'.format(items)
            for items2 in zone_item.Airnode.Surfaces:
                if items2.Surfnum == items:
                    variables['tshdactive']  = items2.Shdtairabove
        variables['shadingctrl'] = 'gt({0},0)'.format(output_storage)
        variables['shadingcta'] = 'gt({0},0)'.format(output_storagea)
        variables['shadingctb'] = 'gt({0},0)'.format(output_storageb)
        for items in zone_item.Airnode.Winsurfaces:
            for items2 in zone_item.Airnode.Surfaces:
                if items2.Surfnum == items and items2.Mshade == 'BSDFCOMPLEX':
                    variables['shadingctrl'] = 0
        states = []
        cshdfound = 0
        if 'Complexshade' in dir(zone_item.Airnode):
            for citem in dir(zone_item.Airnode.Complexshade.Ctrl):
                if 'Crit' in citem and getattr(zone_item.Airnode.Complexshade.Ctrl,citem):
                    cshdfound = 1
                    variables['shadeno'] += 1
                    dummy = getattr(zone_item.Airnode.Complexshade.Ctrl,citem)
                    dummy = re.sub('aname','%s'%zone_item.Airnode.Name,dummy)
                    dummy = re.sub('zname','%s'%zone_item.Airnode.Zonename,dummy)
                    variables['shadedef'] += '{0}_{2} = {1}\n'.format(citem,dummy,zone_item.Airnode.Name)
                if 'State' in citem and getattr(zone_item.Airnode.Complexshade.Ctrl,citem):
                    variables['shadeno'] += 1
                    states.append(citem)
                    dummy = getattr(zone_item.Airnode.Complexshade.Ctrl,citem)
                    dummy = re.sub('aname','%s'%zone_item.Airnode.Name,dummy)
                    dummy = re.sub('zname','%s'%zone_item.Airnode.Zonename,dummy)
                    variables['shadedef'] += '{0}_{2} = {1}\n'.format(citem,dummy,zone_item.Airnode.Name)
            dummyea = '0'
            dummyia = '0'
            dummyeb = '0'
            dummyib = '0'
            for sitem in dir(zone_item.Airnode.Complexshade):
                if 'Shd' in sitem and getattr(zone_item.Airnode.Complexshade, sitem) != None :
                    if '2' in sitem:
                        state = 'State2_{0}'.format(zone_item.Airnode.Name)
                    if '3' in sitem:
                        state = 'State3_{0}'.format(zone_item.Airnode.Name)
                    if '4' in sitem:
                        state = 'State4_{0}'.format(zone_item.Airnode.Name)
                    if '5' in sitem:
                        state = 'State5_{0}'.format(zone_item.Airnode.Name)
                    if '6' in sitem:
                        state = 'State6_{0}'.format(zone_item.Airnode.Name)
                    if '7' in sitem:
                        state = 'State7_{0}'.format(zone_item.Airnode.Name)
                    if '8' in sitem:
                        state = 'State8_{0}'.format(zone_item.Airnode.Name)
                    if '9' in sitem:
                        state = 'State9_{0}'.format(zone_item.Airnode.Name)
                    dummyea += '+ {0} * {1}'.format(getattr(zone_item.Airnode.Complexshade, sitem).Eshadeglazingcovera, state )
                    dummyia += '+ {0} * {1}'.format(getattr(zone_item.Airnode.Complexshade, sitem).Ishadeglazingcovera, state )
                    dummyeb += '+ {0} * {1}'.format(getattr(zone_item.Airnode.Complexshade, sitem).Eshadeglazingcoverb, state )
                    dummyib += '+ {0} * {1}'.format(getattr(zone_item.Airnode.Complexshade, sitem).Ishadeglazingcoverb, state )
            for items in zone_item.Airnode.Winsurfaces:
                for items2 in zone_item.Airnode.Surfaces:
                    if items2.Surfnum == items:
                        if items2.Mshade == 'OUT' or items2.Mshade == 'IOT':
                            variables['shadeno'] += 1
                            if items2.Sgroup == 'B':
                                variables['shadedef'] += 'YSHDE_S{0} = {1}\n'.format(items,dummyeb, zone_item.Airnode.Name)
                            else:
                                variables['shadedef'] += 'YSHDE_S{0} = {1}\n'.format(items,dummyea, zone_item.Airnode.Name)
                        if items2.Mshade == 'INT' or items2.Mshade == 'IOT':
                            variables['shadeno'] += 1
                            if items2.Sgroup == 'B':
                                variables['shadedef'] += 'YSHDI_S{0} = {1}\n'.format(items,dummyib, zone_item.Airnode.Name)
                            else:
                                variables['shadedef'] += 'YSHDI_S{0} = {1}\n'.format(items,dummyia, zone_item.Airnode.Name)
            variables['shadeno'] += 1
            states = list(set(states))
            dummy = '0'
            for stitem in states:
                if '2' in stitem:
                    multiply = 2
                if '3' in stitem:
                    multiply = 3
                if '4' in stitem:
                    multiply = 4
                if '5' in stitem:
                    multiply = 5
                if '6' in stitem:
                    multiply = 6
                if '7' in stitem:
                    multiply = 7
                if '8' in stitem:
                    multiply = 8
                if '9' in stitem:
                    multiply = 9
                dummy += '+ {0}_{1}*{2}'.format(stitem,zone_item.Airnode.Name,multiply)
            variables['shadedef'] += 'DLSHADE_{0} = {1}\n'.format(zone_item.Airnode.Name,dummy)
    #print variables['shadedef']
    #gains
    if zone_item.Airnode.Gain:
        for gain_item in zone_item.Airnode.Gain:
            if gain_item.Personsgain == 1:
                variables['sched_occ']        = 'SCHED_' + str(gain_item.Schedule)
                schedulescoll.append(variables['sched_occ'])
                if gain_item.Annual == None or gain_item.Annual == '':
                    pass
                else:
                    variables['sched_occ']        += '*SCHED_' + str(gain_item.Annual)
                schedulescoll.append('SCHED_' + str(gain_item.Annual))
                #variables['power_pers']       = gain_item.Specificpower
                variables['power_pers']       = round((gain_item.Conv2 + gain_item.Rad2)/zone_item.Airnode.Areaperperson,2)
                variables['gainredon']        = str(gain_item.Tamb24hon)
                variables['winterred_pers']   = str(float(gain_item.Winterred) / 100)
                variables['co2ppers'] = gain_item.CO2
                if len(zone) > 1:
                    variables['co2ppers'] = 0  #in multizone case no CO2 calculation is possible
                if gain_item.Annual != None:
                    foundannual = 0
                    for annual_item in library.Annualschedules:
                        if annual_item.Name == gain_item.Annual:
                            variables['annual_schedule']       = 'SCHED_%s'%annual_item.Name
                            foundannual = 1
                    if foundannual == 0:
                        print 'NOTE: Annual schedule %s not found'%gain_item.Annual
            if gain_item.Lightinggain == 1:
                variables['efflight']         = gain_item.Efflight
                variables['dimming']          = gain_item.Dimming
                variables['sched_light']      = 'SCHED_' + str(gain_item.Schedule)
                schedulescoll.append(variables['sched_light'])
                variables['power_light']      = gain_item.Specificpower
                variables['lightheat']        = gain_item.Heatbylight
                variables['perm_light']       = gain_item.Permlight
                variables['daylightfact']     = gain_item.Daylightfactor
                if zone_item.Airnode.Daylightctrl and gain_item.Dctrl == 'DLC':
                    for dlcitem in zone_item.Airnode.Daylightctrl:
                        variables['luxlevel']         = dlcitem.Illsetpoint1
                        if dlcitem.Cntrlmode == 1:
                            variables['ctrl_light']       = 'ALWAYS ON'
                        if dlcitem.Cntrlmode == 2:
                            variables['ctrl_light']       = 'ON/OFF'
                        if dlcitem.Cntrlmode == 3:
                            variables['ctrl_light']       = 'CONTINUOS'
                        if dlcitem.Cntrlmode == 4:
                            variables['ctrl_light']       = 'CONTINUOS ON/OFF'
                else:
                    variables['ctrl_light']       = 'ALWAYS ON'
            if gain_item.Computergain == 1:
                variables['sched_comp']       = 'SCHED_' + str(gain_item.Schedule)
                schedulescoll.append(variables['sched_comp'])
                variables['power_comp']       = float(gain_item.Specificpower) / float(variables['appers'])
                variables['power_comp_tot']   = gain_item.Specificpower
                variables['compheat']         = gain_item.Heatbycomp
                variables['winterred_comp']   = str(float(gain_item.Winterred) / 100)
            if gain_item.Othergain == 1:
                if 'THB' in gain_item.Name:
                    area_dummy = 0
                    for items in zone_item.Airnode.Surfaces:
                        if items.Boundarycond == 'EXTERNAL':
                            area_dummy = area_dummy + items.Area
                    variables['thb_val']   = gain_item.Specificpower
                    variables['thb_area']  = area_dummy
                else:
                    #variables['poweraddon']       = str(variables['poweraddon']) + '+' + str(gain_item.Specificpower) + '* SCHED_' + str(gain_item.Schedule) + '* max(not({0}),[{1},1]) * (1 - lt(Tamb_m24,{2} ) * {3})'.format(variables['useannual_comp'], variables['zunit17'], variables['gainredon'], variables['winterred_comp'])
                    variables['poweraddon']       = str(variables['poweraddon']) + '+' + str(gain_item.Specificpower)
                    variables['sched_og']         = 'SCHED_' + str(gain_item.Schedule)
                    variables['mischeat']         = gain_item.Heatbymisc
                    schedulescoll.append(variables['sched_og'])
                    variables['power_og']         = gain_item.Specificpower
    #co2 coupling
    variables['couplco2']       = 0
    if zone[-1].Coupling:
        for coupl_items in zone[-1].Coupling:
            if coupl_items.Target == zone_item.Airnode.Name:
                variables['couplco2']       = 'CO2coupl_{0} / (Vol_{0}+0.000001)'.format(zone_item.Airnode.Name)
                #variables['couplco2']       = 'CO2coupl_{0} / (Vol_{0}+0.000001) - max(CO2l_{0},CO2_amb)'.format(zone_item.Airnode.Name)
                break
    #infiltration
    if zone_item.Airnode.Infiltration:
        variables['yx_inf']       = 1
        variables['ach_inf']      = zone_item.Airnode.Infiltration.Ach
        variables['min_inf']      = zone_item.Airnode.Infiltration.Minach
        variables['schedule_inf'] = 'SCHED_' + zone_item.Airnode.Infiltration.Schedule
        # @OC START
        #OC_infiltration variables
        if 'OC_command_lines_infiltration_variables' in sc.sticky[sc.doc.Path]:
            if zone_item.Airnode.Infiltration.Windredfac:
                exec(sc.sticky['OC_command_lines_infiltration_variables'])
        # @OC_END
        schedulescoll.append(variables['schedule_inf'])
        if hasattr(zone_item.Airnode.Infiltration,'Annual') and zone_item.Airnode.Infiltration.Annual != None:
            variables['schedule_inf']        += '*SCHED_' + str(zone_item.Airnode.Infiltration.Annual)
            schedulescoll.append('SCHED_' + str(zone_item.Airnode.Infiltration.Annual))
    #earth duct
    if zone_item.Airnode.Earthduct:
        variables['Tmean_amb']      = zone_item.Airnode.Earthduct.Tmean
        variables['eta_ed']         = zone_item.Airnode.Earthduct.Eff
    #mechanical ventilation
    if zone_item.Airnode.Ventilation:
        for ventilation_item in zone_item.Airnode.Ventilation:
            if ventilation_item.Type == 'STACKVENTILATION' and ventilation_item.Name == 'STVENT1':
                variables['taircomp_sv1']    = 'Tlair_{0}'.format(zone_item.Airnode.Name)
                for coupl_item2 in zone_item.Coupling:
                    if coupl_item2.FirstZone == zone_item.Airnode.Name and coupl_item2.Info == 'STVENT1' and coupl_item2.TempCtrl == 'LAST':
                        variables['taircomp_sv1']    = 'Tlair_{0}'.format(coupl_item2.LastZone)
                    elif coupl_item2.FirstZone == zone_item.Airnode.Name and coupl_item2.Info == 'STVENT1' and coupl_item2.TempCtrl == 'FIRST':
                        variables['taircomp_sv1']    = 'Tlair_{0}'.format(coupl_item2.FirstZone)
                    elif coupl_item2.FirstZone == zone_item.Airnode.Name and coupl_item2.Info == 'STVENT1' and coupl_item2.TempCtrl == 'MEAN':
                        Tmeancoll = '( 0 '
                        VolColl = ' / ( 0 '
                        for dummy_zones in range(len(coupl_item2.AllZones)):
                            Tmeancoll = Tmeancoll + '+ TLAIR_{0} * VOL_{0}'.format(coupl_item2.AllZones[dummy_zones])
                            VolColl   = VolColl   + '+ VOL_{0}'.format(coupl_item2.AllZones[dummy_zones])
                            if dummy_zones == len(coupl_item2.AllZones)-1:
                                Tmeancoll = Tmeancoll + ')'
                                VolColl   = VolColl + ')'
                                variables['taircomp_sv1']    = Tmeancoll + VolColl
                    else:
                        variables['taircomp_sv1']    = 'Tlair_{0}'.format(zone_item.Airnode.Name)
                variables['aeff1top']    = max( ventilation_item.Aefftop, ventilation_item.Aefftopfl * zone_item.Airnode.Floorarea)
                variables['aeff1bot']    = max( ventilation_item.Aeffbot, ventilation_item.Aeffbotfl * zone_item.Airnode.Floorarea)
                variables['hdiff_sv1']   = ventilation_item.Hdiff
                variables['schedule_sv1']= 'SCHED_' + ventilation_item.Schedule
                schedulescoll.append(variables['schedule_sv1'])
                variables['tairon_sv1']  = ventilation_item.Tairon
                variables['tairoff_sv1'] = ventilation_item.Tairoff
                variables['tambon_sv1']  = ventilation_item.Tambon
                variables['tamb24on_sv1']= ventilation_item.Tamb24on
                variables['maxach_sv1']  = ventilation_item.Maxach
                variables['toutside_sv1']= ventilation_item.Toutside
                variables['woutside_sv1']= ventilation_item.Humoutside
                variables['humctrl_sv1'] = ventilation_item.Humctrl
                if ventilation_item.Tempctrl == "OPERATIVE":
                    variables['tempctrl_sv1'] = "TOP_"
                else:
                    variables['tempctrl_sv1'] = "TAIR_"
            elif ventilation_item.Type == 'STACKVENTILATION' and ventilation_item.Name == 'STVENT2':
                variables['taircomp_sv2']    = 'Tlair_{0}'.format(zone_item.Airnode.Name)
                for coupl_item2 in zone_item.Coupling:
                    if coupl_item2.FirstZone == zone_item.Airnode.Name and coupl_item2.Info == 'STVENT2' and coupl_item2.TempCtrl == 'LAST'  and coupl_item2.LastZone in airnodelist:
                        variables['taircomp_sv2']    = 'Tlair_{0}'.format(coupl_item2.LastZone)
                    elif coupl_item2.FirstZone == zone_item.Airnode.Name and coupl_item2.Info == 'STVENT2' and coupl_item2.TempCtrl == 'FIRST':
                        variables['taircomp_sv2']    = 'Tlair_{0}'.format(coupl_item2.FirstZone)
                    elif coupl_item2.FirstZone == zone_item.Airnode.Name and coupl_item2.Info == 'STVENT2' and coupl_item2.TempCtrl == 'MEAN':
                        Tmeancoll = '( 0 '
                        VolColl = ' / ( 0 '
                        for dummy_zones in range(len(coupl_item2.AllZones)):
                            Tmeancoll = Tmeancoll + '+ TlAIR_{0} * VOL_{0}'.format(coupl_item2.AllZones[dummy_zones])
                            VolColl   = VolColl   + '+ VOL_{0}'.format(coupl_item2.AllZones[dummy_zones])
                            if dummy_zones == len(coupl_item2.AllZones)-1:
                                Tmeancoll = Tmeancoll + ')'
                                VolColl   = VolColl + ')'
                                variables['taircomp_sv2']    = Tmeancoll + VolColl
                    else:
                        variables['taircomp_sv2']    = 'Tlair_{0}'.format(zone_item.Airnode.Name)
                variables['aeff2top']    = max( ventilation_item.Aefftop, ventilation_item.Aefftopfl * zone_item.Airnode.Floorarea)
                variables['aeff2bot']    = max( ventilation_item.Aeffbot, ventilation_item.Aeffbotfl * zone_item.Airnode.Floorarea)
                variables['hdiff_sv2']   = ventilation_item.Hdiff
                if 'NOT(GT(SCHED' in ventilation_item.Schedule:
                    variables['schedule_sv2']= ventilation_item.Schedule
                else:
                    variables['schedule_sv2']= 'SCHED_' + ventilation_item.Schedule
                    schedulescoll.append(variables['schedule_sv2'])
                variables['tairon_sv2']  = ventilation_item.Tairon
                variables['tairoff_sv2'] = ventilation_item.Tairoff
                variables['tambon_sv2']  = ventilation_item.Tambon
                variables['tamb24on_sv2']= ventilation_item.Tamb24on
                variables['maxach_sv2']  = ventilation_item.Maxach
                variables['toutside_sv2']= ventilation_item.Toutside
                variables['woutside_sv2']= ventilation_item.Humoutside
                variables['humctrl_sv2'] = ventilation_item.Humctrl
                if ventilation_item.Tempctrl == "OPERATIVE":
                    variables['tempctrl_sv2'] = "TOP_"
                else:
                    variables['tempctrl_sv2'] = "TAIR_"
            elif ventilation_item.Type == 'VENTILATION':
                dckdict[zone_item.Airnode.Name]['MechVent'] = {}
                for coupl_item2 in zone_item.Coupling:
                    if coupl_item2.FirstZone == zone_item.Airnode.Name and coupl_item2.Info == 'MECHANICAL' and coupl_item2.LastZone in airnodelist:
                        variables['ablaname'] = coupl_item2.LastZone
                    else:
                        variables['ablaname'] = zone_item.Airnode.Name
                variables['tsummer_mv']     = ventilation_item.Tsummer
                variables['twinter_mv']     = ventilation_item.Twinter
                variables['tsummer2_mv']     = ventilation_item.Tsummer2
                variables['twinter2_mv']     = ventilation_item.Twinter2
                variables['hummax_mv']      = ventilation_item.Humsummer
                variables['hummin_mv']      = ventilation_item.Humwinter
                variables['hrcsens']        = ventilation_item.Hrcsens
                variables['hrclat']         = ventilation_item.Hrclat
                variables['hrcsenspc']      = round(float(ventilation_item.Hrcsens)*100,2)
                variables['hrclatpc']       = round(float(ventilation_item.Hrclat)*100,2)
                variables['schedule_mv']    = 'SCHED_' + ventilation_item.Schedule
                variables['schedule2_mv']   = 'SCHED_' + ventilation_item.Schedule2
                schedulescoll.append(variables['schedule_mv'])
                schedulescoll.append(variables['schedule2_mv'])
                if type(ventilation_item.Vflow) == str:
                    variables['acr_mv'] = ventilation_item.Vflow
                else:
                    variables['acr_mv']         = round(max(ventilation_item.Ach,ventilation_item.Vflow / zone_item.Airnode.Volume,ventilation_item.Vflowppers * zone_item.Airnode.Floorarea / variables['appers'] / zone_item.Airnode.Volume),2)
                variables['acr_min_mv']     = round(ventilation_item.Achmin,2)
                variables['tamb24h_mvcl']   = ventilation_item.Tamb24hcl
                if hasattr(ventilation_item,'Reftemp') and ventilation_item.Reftemp is not None:
                    variables['reftemp_mv']  = ventilation_item.Reftemp
                variables['sfp_mv']         = ventilation_item.Sfp
                if type(ventilation_item.Vflow) == str:
                    variables['svf_mv']         = 0
                    variables['vf_ppers']       = 0
                else:
                    variables['svf_mv']         = round(zone_item.Airnode.Volume*variables['acr_mv']/zone_item.Airnode.Floorarea,2)
                    variables['vf_ppers']       = round(zone_item.Airnode.Volume*variables['acr_mv']/(zone_item.Airnode.Floorarea/variables['appers']),2)
                variables['yx_mv']          = 1
                variables['mvreduction']    = ventilation_item.Winterred
                variables['mvfraction']    = ventilation_item.Winterfract
                variables['toutsideahu']    = ventilation_item.Toutsidemv
                variables['woutsideahu']    = ventilation_item.Humoutsidemv
                variables['humctrl_mv']     = ventilation_item.Humctrl
                variables['TSUP_up_hi'] = ventilation_item.Tsuphigh
                variables['TSUP_lo_hi'] = ventilation_item.Tsuplow
                variables['acr_max_mv'] = ventilation_item.Maxach
                if ventilation_item.Hybrid == 1:
                    variables['yx_hyb']     = ventilation_item.Hybrid
                    variables['THYB_up_hi'] = ventilation_item.Thybhigh
                    variables['THYB_lo_hi'] = ventilation_item.Thyblow
                #added part for Calcmode Standard
                if ventilation_item.Calcmode == "STANDARD":
                    variables['woutsideahu']    = "Abshum_amb"
                    #variables['thrcmv']         = "gt(ACR_ahu_mv_{0},0) * min((eta_wrg_sen_{0}*(Text_{0}-Tamb)),Tair_{0} - 4) + Tamb".format(variables['aname'])
                    variables['abshumsupmv']    = "gt(ACR_ahu_mv_%s,0) * min(max(Abshum_hu_mv_%s,Abshum_amb),Abshum_dh_mv_%s) + not(gt(ACR_ahu_mv_%s,0))*Abshum_amb"%(variables['aname'],variables['aname'],variables['aname'],variables['aname'])
                    #variables['relhumsupmv']    = "Rh_sup_mv33_{0}".format(variables['aname'])
                    variables['thrcmv']         = "TAHU_HR_%s"%(variables['aname'])
                    #variables['abshumsupmv']    = "SHAHU_HR_%s"%(variables['aname'])
                    #variables['relhumsupmv']    = "RHAHU_HR_%s"%(variables['aname'])
                    variables['relhumsupmv']    = 0
                    variables['ahusenht']    = "QAHU_SENSH_{0} / 3.6 / Area_{0}".format(variables['aname'])
                    variables['ahusencl']    = "QAHU_SENSC_{0} / 3.6 / Area_{0}".format(variables['aname'])
                    variables['ahulathu']    = "QAHU_HUMH_{0} / 3.6 / Area_{0}".format(variables['aname'])
                    variables['ahulatdh']    = "QAHU_DEHUMC_{0} / 3.6 / Area_{0}".format(variables['aname'])
                    variables['ahusendhcl']    = 0
                    variables['ahusendhht']    = "QAHU_REHEATH_{0} / 3.6 / Area_{0}".format(variables['aname'])
                    variables['hrcsencl']    = "QAHU_HRSENSC_{0} / 3.6 / Area_{0}".format(variables['aname'])
                    variables['hrcsenht']    = "QAHU_HRSENSH_{0} / 3.6 / Area_{0}".format(variables['aname'])
                else:
                    variables['thrcmv']    = "Thrc336_%s"%(variables['aname'])
                    variables['abshumsupmv']    = "Abshumsup336_%s"%(variables['aname'])
                    variables['relhumsupmv']    = "Rhsup336_%s"%(variables['aname'])
                    variables['ahusenht']    = "Q_ahu_sen_ht336_%s"%(variables['aname'])
                    variables['ahusencl']    = "Q_ahu_sen_cl336_%s"%(variables['aname'])
                    variables['ahulathu']    = "Q_ahu_lat_hu336_%s"%(variables['aname'])
                    variables['ahulatdh']    = "Q_ahu_lat_dh336_%s"%(variables['aname'])
                    variables['ahusendhcl']  = "Q_ahu_sen_dh_cl336_%s"%(variables['aname'])
                    variables['ahusendhht']  = "Q_ahu_sen_dh_ht336_%s"%(variables['aname'])
                    variables['hrcsencl']    = "Q_hrc_sen_cl336_%s"%(variables['aname'])
                    variables['hrcsenht']    = "Q_hrc_sen_ht336_%s"%(variables['aname'])
    #domestic hot water
    if zone_item.Airnode.Dhw:
        variables['tcw'] = zone_item.Airnode.Dhw.Tcw
        variables['thw'] = zone_item.Airnode.Dhw.Thw
        variables['wwpperspd'] = zone_item.Airnode.Dhw.Wwpperspday
        variables['npers'] = zone_item.Airnode.Floorarea/variables['appers']
        variables['fhours'] = zone_item.Airnode.Dhw.Fhours
        variables['schedule_dhw'] = 'SCHED_' + str(zone_item.Airnode.Dhw.Schedule)
        schedulescoll.append(variables['schedule_dhw'])
        if hasattr(zone_item.Airnode.Dhw, "Filename"):
            if zone_item.Airnode.Dhw.Filename is not None:
                variables['DHW'] = printtype9(zone_item.Airnode.Dhw.Filename, ["MFDHW"])[0]
                variables['wwpperspd'] = "MFDHW"
                variables['npers'] = 1
                variables['fhours'] = 1
                variables['schedule_dhw'] = 1
    #active layer definition
    if '1' in zone_item.Airnode.Activelayer:
        dckdict[zone_item.Airnode.Name]['ActiveLayer1'] = {}
        tsi_coll = '0'
        talm_coll = '0'
        qalfl_coll = '0'
        qcomi_coll = '0'
        for al_item in range(len(zone_item.Airnode.Al1surfaces)):
            tsi_coll = tsi_coll + ' + TSI_S{0}'.format(zone_item.Airnode.Al1surfaces[al_item])
            talm_coll = talm_coll + ' + TALM_S{0}'.format(zone_item.Airnode.Al1surfaces[al_item])
            qalfl_coll = qalfl_coll + ' + QALFL_S{0}'.format(zone_item.Airnode.Al1surfaces[al_item])
            qcomi_coll = qcomi_coll + ' + QCOMI_S{0}'.format(zone_item.Airnode.Al1surfaces[al_item])
            if al_item == len(zone_item.Airnode.Al1surfaces) - 1:
                variables['toutal1']    = '(TOFL_S{0})'.format(zone_item.Airnode.Al1surfaces[al_item])
        for al_item in range(len(zone_item.Airnode.Extal1surfaces)):
            tsi_coll = tsi_coll + ' + TESI_S{0}'.format(zone_item.Airnode.Extal1surfaces[al_item])
            qalfl_coll = qalfl_coll + ' + QEALFL_S{0}'.format(zone_item.Airnode.Extal1surfaces[al_item])
            if al_item == len(zone_item.Airnode.Extal1surfaces) - 1:
                variables['toutal1']    = '(TEOFL_S{0})'.format(zone_item.Airnode.Extal1surfaces[al_item])
        if len(zone_item.Airnode.Al1surfaces)>0:
            variables['tsurfal1'] = '({0})/({1}+0.00000001)'.format(tsi_coll,len(zone_item.Airnode.Al1surfaces))
            variables['tnodeal1']     = '({0})/({1}+0.00000001)'.format(talm_coll,len(zone_item.Airnode.Al1surfaces))
            variables['qtabsfl1']    = '({0})'.format(qalfl_coll)
            variables['qtabs1']    = '({0})'.format(qcomi_coll)
        if len(zone_item.Airnode.Extal1surfaces)>0:
            variables['tsurfal11'] = '({0})/({1}+0.00000001)'.format(tsi_coll,len(zone_item.Airnode.Extal1surfaces))
            variables['tnodeal1']     = '({0})/({1}+0.00000001)'.format(talm_coll,len(zone_item.Airnode.Extal1surfaces))
            variables['qtabsfl1']    = '({0})'.format(qalfl_coll)
        variables['areaal1']     = 0
        for items in zone_item.Airnode.Surfaces:
            if items.Activelayer == 1 and items.Frontback != 'BACK':
                    variables['areaal1']        = variables['areaal1'] + items.Area
                    variables['mflowal1']         = int(items.Massflow*variables['areaal1'])
                    variables['smflowal1']        = int(items.Massflow)
                    variables['schedule_al1ht'] = 'SCHED_' + items.Scheduleheating
                    variables['schedule_al1cl'] = 'SCHED_' + items.Schedulecooling
                    schedulescoll.append(variables['schedule_al1ht'])
                    schedulescoll.append(variables['schedule_al1cl'])
                    variables['tsummeral1']       = items.Tempcooling
                    variables['twinteral1']       = items.Tempheating
                    variables['tamb24h_al1cl']  = items.Tamb24hcooling
                    variables['tamb24h_al1ht']  = items.Tamb24hcooling - 3
                    variables['allyear_al1cl']   = items.Allyearcl
                    variables['permsched_al1cl']   = items.Schedcl
                    variables['shpal1']        = items.Shp
                    variables['scpal1']        = items.Scp
                    variables['thton_al1']     = items.Theat
                    variables['thtoff_al1']    = '+ 2K'
                    variables['tclon_al1']     = items.Tcool
                    variables['tcloff_al1']    = '- 2K'
                    variables['yal1cl']     = items.Ycool
                    variables['yal1ht']    = items.Yheat
                    variables['setback_al1'] = items.Setback
                    if not zone_item.Airnode.Cooling:
                        pass
                        variables['T_set_cl']           = items.Tcool
                    if not zone_item.Airnode.Heating:
                        pass
                        variables['T_set_ht']           = items.Theat
                    variables['actl1ctrl_']       = items.Tempctrl
                    variables['actl1_tdpctrl']    = items.Tdpctrl
                    variables['actl1_suplmode']    = items.Supplymode
                    if items.Space is None:
                        variables['ctrlal1'] = variables['aname']
                    else:
                        variables['ctrlal1'] = items.Space
    if '2' in zone_item.Airnode.Activelayer:
        dckdict[zone_item.Airnode.Name]['ActiveLayer2'] = {}
        tsi_coll = '0'
        talm_coll = '0'
        qalfl_coll = '0'
        qcomi_coll = '0'
        for al_item in range(len(zone_item.Airnode.Al2surfaces)):
            tsi_coll = tsi_coll + ' + TSI_S{0}'.format(zone_item.Airnode.Al2surfaces[al_item])
            talm_coll = talm_coll + ' + TALM_S{0}'.format(zone_item.Airnode.Al2surfaces[al_item])
            qalfl_coll = qalfl_coll + ' + QALFL_S{0}'.format(zone_item.Airnode.Al2surfaces[al_item])
            qcomi_coll = qcomi_coll + ' + QCOMI_S{0}'.format(zone_item.Airnode.Al2surfaces[al_item])
            if al_item == len(zone_item.Airnode.Al2surfaces) - 1:
                variables['toutal2']    = '(TOFL_S{0})'.format(zone_item.Airnode.Al2surfaces[al_item])
        for al_item in range(len(zone_item.Airnode.Extal2surfaces)):
            tsi_coll = tsi_coll + ' + TESI_S{0}'.format(zone_item.Airnode.Extal2surfaces[al_item])
            qalfl_coll = qalfl_coll + ' + QEALFL_S{0}'.format(zone_item.Airnode.Extal2surfaces[al_item])
            if al_item == len(zone_item.Airnode.Extal2surfaces) - 1:
                variables['toutal2']    = '(TEOFL_S{0})'.format(zone_item.Airnode.Extal2surfaces[al_item])
        if len(zone_item.Airnode.Al2surfaces)>0:
            variables['tsurfal2'] = '({0})/({1}+0.00000001)'.format(tsi_coll,len(zone_item.Airnode.Al2surfaces))
            variables['tnodeal2']     = '({0})/({1}+0.00000001)'.format(talm_coll,len(zone_item.Airnode.Al2surfaces))
            variables['qtabsfl2']    = '({0})'.format(qalfl_coll)
            variables['qtabs2']    = '({0})'.format(qcomi_coll)
        if len(zone_item.Airnode.Extal2surfaces)>0:
            variables['tsurfal2'] = '({0})/({1}+0.00000001)'.format(tsi_coll,len(zone_item.Airnode.Extal2surfaces))
            variables['tnodeal2']     = '({0})/({1}+0.00000001)'.format(talm_coll,len(zone_item.Airnode.Extal2surfaces))
            variables['qtabsfl2']    = '({0})'.format(qalfl_coll)
        variables['areaal2']     = 0
        for items in zone_item.Airnode.Surfaces:
            if items.Activelayer == 2 and items.Frontback != 'BACK':
                    variables['areaal2']        = variables['areaal2'] + items.Area
                    variables['mflowal2']         = int(items.Massflow*variables['areaal2'])
                    variables['smflowal2']        = int(items.Massflow)
                    variables['schedule_al2ht'] = 'SCHED_' + items.Scheduleheating
                    variables['schedule_al2cl'] = 'SCHED_' + items.Schedulecooling
                    schedulescoll.append(variables['schedule_al2ht'])
                    schedulescoll.append(variables['schedule_al2cl'])
                    variables['tsummeral2']       = items.Tempcooling
                    variables['twinteral2']       = items.Tempheating
                    variables['tamb24h_al2cl']  = items.Tamb24hcooling
                    variables['tamb24h_al2ht']  = items.Tamb24hcooling - 3
                    variables['allyear_al2cl']   = items.Allyearcl
                    variables['permsched_al2cl']   = items.Schedcl
                    variables['shpal2']        = items.Shp
                    variables['scpal2']        = items.Scp
                    variables['thton_al2']     = items.Theat
                    variables['thtoff_al2']    = '+ 2K'
                    variables['tclon_al2']     = items.Tcool
                    variables['tcloff_al2']    = '- 2K'
                    variables['yal2cl']     = items.Ycool
                    variables['yal2ht']    = items.Yheat
                    variables['setback_al2'] = items.Setback
                    if not zone_item.Airnode.Cooling:
                        pass
                        variables['T_set_cl']           = items.Tcool
                    if not zone_item.Airnode.Heating:
                        pass
                        variables['T_set_ht']           = items.Theat
                    variables['actl2ctrl_']       = items.Tempctrl
                    variables['actl2_tdpctrl']    = items.Tdpctrl
                    variables['actl2_suplmode']    = items.Supplymode
                    if items.Space is None:
                        variables['ctrlal2'] = variables['aname']
                    else:
                        variables['ctrlal2'] = items.Space
    # Define solar outputs for Window Surfaces
    if len(zone_item.Airnode.Winsurfaces)>0:
        for items in zone_item.Airnode.Winsurfaces:
            variables['solarnr'] = variables['solarnr'] + 3
            variables['solaroutputs'] = variables['solaroutputs'] + 'IBSHAD_S{0}\nIDSHAD_S{0}\nAREA_S{0}\n'.format(items)
    # Define balance outputs
    if zone_item.Airnode.Winsurfaces:
        variables['qcomiwin'] = '+'.join('QCOMI_S%s'%x for x in zone_item.Airnode.Winsurfaces)
        variables['qsiwin']   = '+'.join('QABSI_S%s - QCOMI_S%s'%(x,x) for x in zone_item.Airnode.Winsurfaces)
        variables['qsiabwin'] = '+'.join('QSIAB_S%s'%x for x in zone_item.Airnode.Winsurfaces)
    if zone_item.Airnode.Wallsurfaces:
        variables['qcomiwall'] = '+'.join('QCOMI_S%s'%x for x in zone_item.Airnode.Wallsurfaces)
        variables['qsiwall']   = '+'.join('QABSI_S%s - QCOMI_S%s'%(x,x) for x in zone_item.Airnode.Wallsurfaces)
        variables['qsiabwall'] = '+'.join('QSIAB_S%s'%x for x in zone_item.Airnode.Wallsurfaces)
    if zone_item.Airnode.Floorsurfaces:
        variables['qcomifloor'] = '+'.join('QCOMI_S%s'%x for x in zone_item.Airnode.Floorsurfaces)
        variables['qsifloor']   = '+'.join('QABSI_S%s - QCOMI_S%s'%(x,x) for x in zone_item.Airnode.Floorsurfaces)
        variables['qsiabfloor'] = '+'.join('QSIAB_S%s'%x for x in zone_item.Airnode.Floorsurfaces)
    if zone_item.Airnode.Ceilingsurfaces:
        variables['qcomiceiling'] = '+'.join('QCOMI_S%s'%x for x in zone_item.Airnode.Ceilingsurfaces)
        variables['qsiceiling']   = '+'.join('QABSI_S%s - QCOMI_S%s'%(x,x) for x in zone_item.Airnode.Ceilingsurfaces)
        variables['qsiabceiling'] = '+'.join('QSIAB_S%s'%x for x in zone_item.Airnode.Ceilingsurfaces)
    if zone_item.Airnode.Roofsurfaces:
        variables['qcomiroof'] = '+'.join('QCOMI_S%s'%x for x in zone_item.Airnode.Roofsurfaces)
        variables['qsiroof']   = '+'.join('QABSI_S%s - QCOMI_S%s'%(x,x) for x in zone_item.Airnode.Roofsurfaces)
        variables['qsiabroof'] = '+'.join('QSIAB_S%s'%x for x in zone_item.Airnode.Roofsurfaces)
    variables['utci_unit'] = 300
    variables['tmrlw']     = 20
    #Summarize the geometrical information
    variables['area_outside']   = 0
    variables['area_outwall']   = 0
    variables['area_out_s']     = 0
    variables['area_out_w']     = 0
    variables['area_out_n']     = 0
    variables['area_out_e']     = 0
    variables['area_window']    = 0
    variables['area_win_s']     = 0
    variables['area_win_w']     = 0
    variables['area_win_n']     = 0
    variables['area_win_e']     = 0
    variables['area_floor']     = 0
    variables['area_fl_act']  = 0
    variables['areafrac_fl_act']  = 0
    variables['area_ceiling']   = 0
    variables['area_cl_act']  = 0
    variables['areafrac_cl_act']  = 0
    variables['area_wall']      = 0
    variables['out_ori']     = ''
    variables['win_ori']     = ''
    for items in zone_item.Airnode.Surfaces:
        if items.Boundarycond == 'EXTERNAL':
            variables['area_outside']   = variables['area_outside'] + round(items.Area,1)
            variables['qsiext']   += ' + QABSI_S%s - QCOMI_S%s'%(str(items.Surfnum),str(items.Surfnum))
        if items.Boundarycond == 'EXTERNAL' and items.Type != 'WINDOW':
            variables['area_outwall']   = variables['area_outwall'] + round(items.Area,1)
            if 'S' in items.Orientation:
                variables['area_out_s']   = variables['area_out_s'] + round(items.Area,1)
            elif 'W' in items.Orientation:
                variables['area_out_w']   = variables['area_out_w'] + round(items.Area,1)
            elif 'N' in items.Orientation:
                variables['area_out_n']   = variables['area_out_n'] + round(items.Area,1)
            elif 'E' in items.Orientation:
                variables['area_out_e']   = variables['area_out_e'] + round(items.Area,1)
        if items.Type == 'WINDOW':
            variables['area_window']   = variables['area_window'] + round(items.Area,1)
            if 'S' in items.Orientation:
                variables['area_win_s']   = variables['area_win_s'] + round(items.Area,1)
            elif 'W' in items.Orientation:
                variables['area_win_w']   = variables['area_win_w'] + round(items.Area,1)
            elif 'N' in items.Orientation:
                variables['area_win_n']   = variables['area_win_n'] + round(items.Area,1)
            elif 'E' in items.Orientation:
                variables['area_win_e']   = variables['area_win_e'] + round(items.Area,1)
        if items.Orientation == 'H_0_180':
            variables['area_floor']   = variables['area_floor'] + round(items.Area,1)
            if items.Activelayer == 1:
                variables['area_fl_act']   = variables['area_fl_act'] + round(items.Area,1)
            variables['areafrac_fl_act']   = int(variables['area_fl_act'] / variables['area_floor'] * 100)
        if items.Orientation == 'H_0_0':
            variables['area_ceiling']   = variables['area_ceiling'] + round(items.Area,1)
            if items.Activelayer == 1:
                variables['area_cl_act']   = variables['area_cl_act'] + round(items.Area,1)
            variables['areafrac_cl_act']   = int(variables['area_cl_act'] / variables['area_ceiling'] * 100)
        if items.Orientation != 'H_0_0' and items.Orientation != 'H_0_180' and items.Type != 'WINDOW':
            variables['area_wall']   = variables['area_wall'] + round(items.Area,1)
    #printDict(variables,1)
    #print variables.keys()
    for key in variables:
        if re.search( '@aname', str(variables[key])):
            variables[key] = re.sub('@aname', zone_item.Airnode.Name,variables[key])


class ZONE:
    def __init__(self, item='', number = 0):
        self.Airnode = item
        self.Name = ''
        self.Anr     = number
        self.Coupling = Coupling
        self.comfortptsno = item.comfortptsno
        self.Shader = Shading
        self.MatricesPath = variants_folder + variant_name

class runForm(System.Windows.Forms.Form):
    def __init__(self,name):
        self.__disable_events = False
        self.__value_changed_callback = None
        self.SuspendLayout()
        self.Name = name
        self.Text = '%s Is Running...'%self.Name
        self.ClientSize = System.Drawing.Size(290, 30)
        self.BackColor = System.Drawing.SystemColors.Window
        self.TransparencyKey = System.Drawing.Color.FromArgb(224, 224, 224)
        self.ShowIcon = False
        self.ControlBox = False
        self.Load += self.Form1Load
        self.StartPosition = System.Windows.Forms.FormStartPosition.CenterScreen
        self.ResumeLayout()
        self.PerformLayout()
    #def Label1Click(self, sender, e):
    #    pass
    def Form1Load(self, sender, e):
        pass

#The following conversion can be used in order to convert all class content to a dictionary for further processing
def todict(obj, classkey=None):
    if isinstance(obj, dict):
        for k in obj.keys():
            obj[k] = todict(obj[k], classkey)
        return obj
    elif hasattr(obj, "__iter__"):
        return [todict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = dict([(key, todict(value, classkey))
            for key, value in obj.__dict__.iteritems()
            if not callable(value) and not key.startswith('_')])
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    else:
        return obj


#CCF new for loop to define multizone and system simulation
if WriteSimulationFiles:
    for rui,runitem in enumerate(dummyMulti.airnode):
        variants_folder         = sc.sticky[sc.doc.Path]["Variants_folder"].decode('utf-8')
        if RunSingleAirnodes == 1:
            Airnode = [runitem]
        elif rui < len(dummyMulti.airnode) - 1:
            continue
        else:
            Airnode = dummyMulti.airnode
        Shading = dummyMulti.shading
        AddDaylightGeometry = dummyMulti.adddaylightgeo
        Coupling = dummyMulti.coupling
        Timebase = dummyMulti.timebase
        DaylightMode = dummyMulti.daylightmode

        #---- initial definition end
        WriteBuilding = 0
        simplify = 0
        dlmode = 1
        Rotation = 0
        ShaderReflectance = 0.2
        collmessages = ""

        if 'AdditionalWinid' in locals() and AdditionalWinid is not None:
            pass
        else:
            AdditionalWinid = None

        if 'Timebase' in locals():
            if Timebase is not None:
                pass
            else:
                Timebase = 1
        else:
            Timebase = 1


        if 'GeneralSettings' in locals():
            if GeneralSettings is not None:
                pass
            else:
                GeneralSettings = None
        else:
            GeneralSettings = None

        if 'DaylightMode' in locals():
            if DaylightMode is not None:
                daylightmode = DaylightMode
                if DaylightMode == "RAY":
                    daylightmode = "RAD"
            else:
                daylightmode = "CLASSIC"
        else:
            daylightmode = "CLASSIC"

        if dlmode == 0:
            dab = 3
            dad = 128
            das = 64
            dar = 32
            daa = 0.1
        elif dlmode == 1:
            dab = 6
            dad = 768
            das = 384
            dar = 192
            daa = 0.1
        else:
            dab = 8
            dad = 768*2
            das = 384*2
            dar = 192*2
            daa = 0.1
        shader_reflectance = ShaderReflectance
        showWallThickness = False
        rs.EnableRedraw(False)

        foundtfinp = 0
        for item in ghenv.Component.Params.Input:
            if item.NickName == "TrnflowNetwork":
                foundtfinp = 1

        if 'TrnflowNetwork' in locals() and foundtfinp == 1:
            trnflowfound = -1
            sc.sticky[sc.doc.Path]["trnflow"] = -1
        else:
            TrnflowNetwork = [] #define as list
            trnflowfound = 0
            sc.sticky[sc.doc.Path]["trnflow"] = 0
        if 'TrnflowNetwork' in locals() and len(TrnflowNetwork) > 0:
            trnflowfound = 1
            sc.sticky[sc.doc.Path]["trnflow"] = 1
        # @OC START
        # Mark: check if the window type and orientation has been changed
        lizard_Zones = sc.sticky[sc.doc.Path]["ZONECOLL"]()
        ObjectsFromLz = lizard_Zones.callFromZones(Airnode)
        Airnode = []
        for LO in ObjectsFromLz:
            Airnode.append(LO)
        Airnode.sort(key=operator.attrgetter("Name"), reverse=False)
        ### START make general changes to definitions here
        if GeneralSettings:
            for Airnode_item in Airnode:
                for setitem in GeneralSettings:
                    if setitem.Type == "GEOMETRY":
                        for sitem in Airnode_item.Surfaces:
                            if re.search(setitem.Search1,getattr(sitem,"%s"%setitem.Filter1)):
                                #print getattr(sitem,setitem.ChangeAttr)
                                setattr(sitem, setitem.ChangeAttr, setitem.ChangeTo)
        """
        for Airnode_item in Airnode:
            for setitem in GeneralSettings:
        if setitem.Type == "GEOMETRY":
        for sitem in Airnode_item.Surfaces:
        #print getattr(sitem,"%s"%setitem.Filter1)
        if re.search(setitem.Search1,getattr(sitem,"%s"%setitem.Filter1)):
        print getattr(sitem, setitem.ChangeAttr)
        """
        if RunSingleAirnodes == 1:
            for Airnode_item in Airnode:
                variants_folder += "%s"%Airnode_item.Name + '\\'
        #---- initial definition start
        subfolderres = "Results"
        results_dir = variants_folder + '/%s/'%subfolderres
        if os.path.isdir(results_dir) is False:
            os.mkdir(results_dir)

        ### STOP make general changes to definitions here
        surfaceinfo = []
        surfacenumbers = []
        for Airnode_item in Airnode:
            for sitem in Airnode_item.Surfaces:
                surfacenumbers.append(sitem.Surfnum)
        surfacenumbers = list(set(surfacenumbers))
        foundsurfacenum = []
        for Airnode_item in Airnode:
            for sitem in Airnode_item.Surfaces:
                if sitem.Surfnum in foundsurfacenum:
                    mess = "multiple times the same surface number is used %s"%sitem.Surfnum
                    print mess
                    ghenv.Component.AddRuntimeMessage(w, mess)
                    newnumber = surfacenumbers[-1] + 1
                    surfacenumbers.append(newnumber)
                    sitem.Surfnum = surfacenumbers[-1]
                    mess = "new surface number is used %s"%sitem.Surfnum
                    print mess
                    ghenv.Component.AddRuntimeMessage(w, mess)
                else:
                    foundsurfacenum.append(sitem.Surfnum)
            surfaceinfo.extend(Airnode_item.Surfaces)
        templates = sc.sticky[sc.doc.Path]["Template"]
        printdata = sc.sticky[sc.doc.Path]["printdata"]
        printsingledata = sc.sticky[sc.doc.Path]["printsingledata"]
        Airnodeinfo     = []
        Airnodeinfo.extend(Airnode)
        bui_file        = []
        Zone            = []
        Coupling_coll   = []
        #Preset Daylight Geopos ID's
        zonedict = dict()
        for Airnodes in Airnodeinfo:
            if Airnodes.Zonename in zonedict:
                zonedict[Airnodes.Zonename][Airnodes.Name] = Airnodes
            else:
                zonedict[Airnodes.Zonename] = dict()
                zonedict[Airnodes.Zonename][Airnodes.Name] = Airnodes
        neworder = []
        airnodenames = []
        airnodezoneid = {}
        noid = 0
        for key1 in sorted(zonedict):
            noid += 1
            for key2 in sorted(zonedict[key1]):
                neworder.append(zonedict[key1][key2])
                airnodenames.append(key2)
                airnodezoneid[key2] = noid
        daylightID = 0
        for item in neworder:
            if item.Daylightctrl:
                for dc, dcitem in enumerate(item.Daylightctrl):
                    for si, subitem in enumerate(dcitem.Grid):
                        if si == 0:
                            if dcitem.Sel1 > 0:
                                dcitem.Geopos1 = dcitem.Sel1 + daylightID
                            if dcitem.Sel2 > 0:
                                dcitem.Geopos2 = dcitem.Sel2 + daylightID
                            if dcitem.Sel3 > 0:
                                dcitem.Geopos3 = dcitem.Sel3 + daylightID
                            if dcitem.Sel4 > 0:
                                dcitem.Geopos4 = dcitem.Sel4 + daylightID
                        daylightID += 1
        #convertTry2017ETRS892WSG84(3720500,2705500)
        #convertTry2017ETRS892WSG84(4339500,2730500)
        #convertTry2017ETRS892WSG84(3931500,3110500)
        #Get location information
        if '.epw' in weather_file:
            f = open(weather_file, 'r')
            datalines=f.readlines()
            dummy = datalines[0].strip()
            dummy = dummy.split(',')
            f.close()
            altitude =dummy[-1]
            longitude=str(-float(dummy[len(dummy)-3]))
            latitude =dummy[len(dummy)-4]
            gmt      =dummy[len(dummy)-2]
            if gmt == 'solar':
                gmt = 1
                print 'gmt of one is used because of solar definition in the dataset'
            timezone = str(float(gmt)*(-15))
        elif '.tmy3' in weather_file or '.tm3' in weather_file:
            f = open(weather_file, 'r')
            datalines=f.readlines()
            dummy = datalines[0].strip()
            dummy = dummy.split(',')
            f.close()
            altitude =dummy[-1]
            longitude=dummy[len(dummy)-3]
            latitude =dummy[len(dummy)-2]
            gmt      =dummy[len(dummy)-4]
            timezone = str(float(gmt)*(-15))
        elif '.tmy2' in weather_file or '.tm2' in weather_file:
            f = open(weather_file, 'r')
            datalines=f.readlines()
            dummy = datalines[0].strip()
            dummy = dummy.split()
            f.close()
            altitude =dummy[-1]
            longitude=dummy[len(dummy)-3] + '.' + dummy[len(dummy)-2]
            latitude =dummy[len(dummy)-6] + '.' + dummy[len(dummy)-5]
            gmt      =dummy[len(dummy)-8]
            timezone = str(float(gmt)*(-15))
        elif '.dat' in weather_file and ('TRY2015' in weather_file or 'TRY2045' in weather_file):
            f = open(weather_file, 'r')
            datalines=f.readlines()
            xval = datalines[1].strip()
            xval = (xval.split()[2])
            yval = datalines[2].strip()
            yval = (yval.split()[2])
            altdummy = datalines[3].strip()
            altitude = (altdummy.split()[2])
            f.close()
            longitude, latitude = convertTry2017ETRS892WSG84(xval,yval)
            gmt = 1
            timezone = str(float(gmt)*(-15))
        else:
            f = open(weather_file, 'r')
            datalines=f.readlines()
            paragraph=getparagraph(datalines,'^<userdefined>','^<data>')
            f.close()
            dummy = paragraph[0].split( )
            dummyindex = len(dummy)-2
            altitude= dummy[dummyindex]
            longitude=getdata('^<longitude>',paragraph,'<longitude>',0,1)[-1]
            latitude=getdata('^<latitude>',paragraph,'<latitude>',0,1)[-1]
            gmt=getdata('^<gmt>',paragraph,'<gmt>',0,1)[-1]
            if gmt == 'solar':
                gmt = 1
                print 'gmt of one is used because of solar definition in the dataset'
            timezone = str(float(gmt)*(-15))
        #Library should be disconnected from class Zone to reduce memory size
        if library not in locals():
            library = sc.sticky[sc.doc.Path]["library"]
        """
        #Search shading geometry for non planar surfaces
        NonPlanarShading = []
        for shditem in Shading:
            for sitem in shditem.Surfaces:
                if sitem.IsPlanar():
                    pass
                else:
                    NonPlanarShading.append(sitem)
                    ghenv.Component.AddRuntimeMessage(err, "Non planar shading geometry was found!")
        """
        """
        for sitem in Shading:
            if sitem.IsSurface is False:
                errorfound = 1
                ghenv.Component.AddRuntimeMessage(err, "Shading definition contains geometry which is not a type of surface. Please check!!!")
        """
        #tbd_surfaces = []
        #ecal_surfaces = []
        #efical_surfaces = []
        manual_ori = []
        mismatched_adjacent = []
        new_surfaces = []
        if len(new_surfaces) > 0:
            for item in new_surfaces:
                surfaceinfo.append(item)
                for Airnode_item in Airnode:
                     if Airnode_item.Name == item.Airnode:
                         Airnode_item.surfaces.append(item)
        if 'OC_command_lines_global_variables' in sc.sticky[sc.doc.Path]:
            checkTreeSurfaceOrientation(Airnodeinfo)
        adjacent,mismatched_adjacent,message  = checkAdjacent(surfaceinfo,mismatched_adjacent)
        if 'OC_command_lines_global_variables' in sc.sticky[sc.doc.Path]:
            checkTreeSurfaceOrientation(Airnodeinfo)
        for mitem in message:
            ghenv.Component.AddRuntimeMessage(w, mitem)
            collmessages += mitem + '\n'
        MismatchedAdjacent = mismatched_adjacent
        #if len(message) > 0:
        #    sys.exit()
        SurfaceVolumes = []
        if showWallThickness == True:
            for surface in surfaceinfo:
                if surface.Type != 'WINDOW':
                    extrvector = surface.Normalvector * surface.Wallthickness
                    newbrep = surface.Surface.Duplicate()
                    newbrep.Translate(extrvector)
                    SurfaceVolumes.append(surface.Surface)
                    SurfaceVolumes.append(newbrep)
                    for citem in surface.Surface.Curves3D:
                        SurfaceVolumes.append(rc.Geometry.Extrusion.CreateExtrusion(citem, extrvector).ToBrep())
        rebuild = 1
        if (rebuild==1 or ('Buifile' not in sc.sticky[sc.doc.Path].keys())) and len(Airnodeinfo) > 0:
            zonenames = []
            znr = 0
            for item in range(len(Airnodeinfo)):
                Zone.append(ZONE(Airnodeinfo[item],item + 1))
                Zone[-1].Name = Airnodeinfo[item].Zonename
                if Zone[-1].Name in zonenames:
                    pass
                else:
                    zonenames.append(Zone[-1].Name)
                    znr += 1
                Zone[-1].Znr = znr
                Zone[-1].Coupling = Coupling
            bui_file.extend(printbuitoppart(Airnodeinfo))
            window_coll = []
            if simplify == 0:
                bui_file.extend(printbuiZonepart(Airnodeinfo))
            else:
                bui_file.append(printbuiZonepart(Airnodeinfo)[0])
                dummy_array = printbuiZonepart(Airnodeinfo)[1]
                collection = dummy_array.split('\r\n')
                walldict = {}
                surfaceno = []
                surfacecheck = []
                for subitem in collection:
                    pass
                    #if 'WALL' in subitem:
                    if 'WALL' in subitem or 'WINDOW' in subitem:
                        dummy = re.sub(' ','',subitem)
                        splitted = re.split('=|:',dummy)
                        surfaceno.append(splitted[3])
                        surfacecheck.append(splitted[3])
                        walldict[surfaceno[-1]] = splitted
                for item in surfaceno:
                    if item in walldict:
                        for subitem in surfaceno:
                            if subitem in walldict and item != subitem:
                                if walldict[item][1] == walldict[subitem][1]:
                                    matching = 1
                                    for array_items in range(6,len(walldict[item])):
                                        if walldict[item][array_items] != walldict[subitem][array_items] and walldict[item][array_items-1]  != 'GEOSURF':
                                            matching = 0
                                    if matching == 1:
                                        for array_items in range(len(walldict[item])):
                                            if array_items > 0 and walldict[item][array_items-1] == 'AREA':
                                                walldict[item][array_items] = float(walldict[item][array_items]) + float(walldict[subitem][array_items])
                                            if array_items > 0 and walldict[item][array_items-1] == 'GEOSURF':
                                                walldict[item][array_items] = float(walldict[item][array_items]) + float(walldict[subitem][array_items])
                                        walldict.pop(subitem, None)
                                        #print 'match_found'
                newcoll = ''
                for item in collection:
                    pass
                    if 'WALL' in item or 'WINDOW' in item:
                        two_parts = re.split('AREA=',item)
                        two_parts[0] = two_parts[0] + 'AREA='
                        dummy = re.sub(' ','',item)
                        splitted = re.split('=|:',dummy)
                        if splitted[3] in walldict:
                            if 'WINDOW' in item:
                                window_coll.append(splitted[3])
                            for array_items in range(5,len(walldict[splitted[3]])):
                                two_parts[1] = re.sub(splitted[array_items] + ' ',str(walldict[splitted[3]][array_items]),two_parts[1])
                                if array_items == len(walldict[splitted[3]]) - 1:
                                    two_parts[1] = re.sub(splitted[array_items] + '$',str(walldict[splitted[3]][array_items]),two_parts[1])
                            newcoll = newcoll + '\r\n' + two_parts[0] + two_parts[1]
                    else:
                        newcoll = newcoll + '\r\n' + item
                newcoll = newcoll + '\r\n'
                bui_file.append(newcoll)
            bui_file.extend(printbuibotpart(Airnodeinfo))
            if simplify == 0:
                bui_file.extend(printbuigeopart(Airnodeinfo))
            # Get all required bui inputs
            searchedinputs = getInputs(bui_file)
            buiinput = ''
            for items in searchedinputs:
                buiinput = buiinput + '{0} '.format(items)
            if trnflowfound == 1:
                buiinput = 'WINDVEL WINDDIR PAMB_ABS CONAMB_1 CONAMB_2 CONAMB_3 CONAMB_4 CONAMB_5 TRNFLOW ' + buiinput
            if trnflowfound == -1:
                buiinput = 'WINDVEL WINDDIR PAMB_ABS CONAMB_1 CONAMB_2 CONAMB_3 CONAMB_4 CONAMB_5 0,0 ' + buiinput
            addinpdesc = ''
            inpdummy = buiinput.split()
            for item in inpdummy:
                addinpdesc += ' %s : any : Input\n'%item
            buiinput += '\nINPUTS_DESCRIPTION\n' + addinpdesc
            bui_file_tmp = printbuisingledata( bui_file, 'addinputs', buiinput)
            sc.sticky[sc.doc.Path]["Zone"] = Zone
            Multizone = Zone
            Zone = []
        #starting from here information in translated into dictionary
        #Multizone = sc.sticky[sc.doc.Path]["MULTIZONECOLL"]().addToZones(sc.sticky[sc.doc.Path]["Zone"]) !CCF changed
        #for sitem in Shading:   !CF change back
        #    Multizone.Append(sitem)
        rs.EnableRedraw(True)
        if WriteBuilding == 1:
            printbui()
        #sc.sticky[sc.doc.Path]["BUI_FILE"] = bui_file
        #this funtion returns the outputlist depending on the bui file
        if len(Airnodeinfo) > 0:
            sc.sticky[sc.doc.Path]["BUI_OUTPUT"] = getBuiOutputList(bui_file_tmp)
        surfaceinfo = []
        Airnodeinfo = []
        Coupling_coll = []
        tbd_surfaces = []
        ecal_surfaces = []
        efical_surfaces = []
        template = []
        manual_ori = []
        if collmessages != '':
            ghenv.Component.Message = '%s'%(collmessages)
        else:
            ghenv.Component.Message = 'VER %s\n%s'%(version,date)
        if errorfound == 1:
            Multizone = None
        Zone = []


        SimStartTime,SimStopTime = getSimulationPeriod(startday = StartDay,startmonth = StartMonth,stopday = StopDay,stopmonth = StopMonth)
        if Reload or ('Template_dck' not in sc.sticky[sc.doc.Path].keys()):
            datalines = DckTemplate
            sc.sticky[sc.doc.Path]["Template_dck"] = datalines
        dck_file = sc.sticky[sc.doc.Path]["Template_dck"]
        if Multizone:
            #lizard_zones = sc.sticky[sc.doc.Path]["MULTIZONECOLL"]()
            #ObjectsFromLz = lizard_zones.callFromZones(Multizone)
            #zone = ObjectsFromLz[0]
            zone = Multizone
            #print zone
        else:
            zone = []
        zoneunitstart = 100
        if 'Job6' in sc.sticky[sc.doc.Path].keys():
            job6 = sc.sticky[sc.doc.Path]['Job6']
        else:
            sc.sticky[sc.doc.Path]['Job6'] = []
            job6 = sc.sticky[sc.doc.Path]['Job6']
        if 'Job7' in sc.sticky[sc.doc.Path].keys():
            job7 = sc.sticky[sc.doc.Path]['Job7']
        else:
            sc.sticky[sc.doc.Path]['Job7'] = []
            job7 = sc.sticky[sc.doc.Path]['Job7']
        if 'Job8' in sc.sticky[sc.doc.Path].keys():
            job8 = sc.sticky[sc.doc.Path]['Job8']
        else:
            sc.sticky[sc.doc.Path]['Job8'] = []
            job8 = sc.sticky[sc.doc.Path]['Job8']
        radmodedir = 'STANDARD'
        radmodedif = 'STANDARD'
        radmodelw = 'STANDARD'
        airnodelist = []
        detailedism = 0
        detailedvfm = 0
        detailedlight = 0
        for zone_item in zone:
            if len(zone_item.Shader) > 0:
                detailedism = 1
            if zone_item.Airnode.Beam == 'DETAILED':
                radmodedir = 'DETAILED'
                detailedism = 1
            if zone_item.Airnode.Diffuse == 'DETAILED':
                radmodedif = 'DETAILED'
                detailedvfm = 1
            if zone_item.Airnode.Longwave == 'DETAILED':
                radmodelw = 'DETAILED'
                detailedvfm = 1
            if zone_item.Airnode.Daylightctrl:
                for dcitem in zone_item.Airnode.Daylightctrl:
                    if dcitem.Illmode == 3:
                        detailedlight = 1
            airnodelist.append(zone_item.Airnode.Name)
        detailedlightctrl = 0
        for zone_item in zone:
            for gitem in zone_item.Airnode.Gain:
                if gitem.Dctrl:
                    detailedlightctrl = 1
        if detailedism == 1:
            ghenv.Component.AddRuntimeMessage(w, "Thermal preprocessing required!")
        if detailedlight == 1 and detailedlightctrl == 1:
            ghenv.Component.AddRuntimeMessage(w, "Daylight preprocessing required!")
        bui_file = []
        lu_counter = 950
        # @OC START
        #OC_pritnegrator_25
        if 'OC_command_lines_printegrator_25' in sc.sticky[sc.doc.Path]:
            lu_counter,plotdata = sc.sticky['OC_command_lines_printegrator_25'](name = 'Printer25', unit = 250, content = ['Tamb'], counter = lu_counter)
        else:
            pass
        # @OC END
        variables       = {}
        variables_dict  = {}
        #Manipulate that WriteSimulationFiles always happens before Preprocessing
        if RunDaylightPreprocessing == True or RunThermalPreprocessing == True:
            WriteSimulationFiles = 1
        if WriteSimulationFiles == 1:
            # Start global Variable declaration for the deck file
            variables['variantname'] = variant_name
            variables['longvarname'] = long_variant_name
            variables['projectname'] = project_name
            variables['refarea'] = 0
            variables['turn'] = Turn
            variables['totairnodearea'] = 0
            variables['creator'] = os.getenv("USERNAME")
            variables['timestamp'] = time.asctime()
            variables['version'] = TRNSYS
            variables['timestep']       = SimTimestep
            if SimTolerance is not None:
                variables['tolerance'] = SimTolerance
            else:
                if SimTimestep < 0.25:
                    variables['tolerance']      = 0.0001
                else:
                    variables['tolerance']      = 0.001
            if SimMaxIteration is not None:
                variables['maxiter'] = SimMaxIteration
            else:
                variables['maxiter'] = 50
            if SimMaxWarning is not None:
                variables['maxwarning'] = SimMaxWarning
            else:
                variables['maxwarning'] = 300
            variables['starttime']      = SimStartTime
            variables['stoptime']       = SimStopTime
            variables['altitude']        = sc.sticky[sc.doc.Path]["Altitude"]
            variables['ambpres']        = sc.sticky[sc.doc.Path]["Pressure"]
            variables['online']         = Online
            variables['ydaysim']        = UseDaylightSim
            variables['daylightfact']   = 0.02
            if sc.sticky[sc.doc.Path].has_key("trnflow") and sc.sticky[sc.doc.Path]["trnflow"] > 0:
                variables['trnflow']        = sc.sticky[sc.doc.Path]["trnflow"]
            else:
                variables['trnflow']        = 0
            variables['couplco2']       = 0
            variables['endsingle']      = 'END'
            variables['userdefout']     = ''
            variables['multionline']    = ''
            variables['couplonline']    = ''
            variables['BSDFonline']     = ''
            variables['comfortonline']  = ''
            variables['comfortprint']   = ''
            variables['focairnodeonline']  = ''
            variables['printertempairnode']  = ''
            variables['printerpowairnode']  = ''
            variables['summaryprinter']  = ''
            variables['setcomfortprint']= ''
            variables['addoutputprint'] = ''
            variables['addoutputonline']= ''
            variables['shadeno']       = 6
            variables['shadedef']      = ''
            variables['linkdefinition']      = ''
            variables['BSDFLU']         = ''
            # @OC START
            #OC_global variables
            variables['oc_tool'] = ''
            variables['UTCIcomfortonline'] = ''
            variables['UTCIcomfortprint'] = ''
            variables['TMRcomfortonline'] = ''
            variables['TMRcomfortprint'] = ''
            if 'OC_command_lines_global_variables' in sc.sticky[sc.doc.Path]:
                exec(sc.sticky['OC_command_lines_global_variables'])
            # @OC END
            variables['DHW']     = ''
            variables['BSDF_block']     = ''
            variables['BSDF']     = ''
            variables['illfilename']    = 'dataFile.txt'
            variables['type9inp']       = 6
            variables['type9par']       = 6*4+6
            variables['type9data']      = ''
            for item in range(0,variables['type9inp']):
                variables['type9data']  = variables['type9data'] + '1 1 0 1 ! Interpolmode, Mult, Add, Sample\n'
            variables['dssen1']         = '0'
            variables['dssen2']         = '0'
            variables['dssen3']         = '0'
            weather_file_name = weather_file.split('\\')[-1]
            weather_found = 0
            for currentFile in glob.glob( os.path.join(variants_folder, '*') ):
                if currentFile.split('\\')[-1] == weather_file_name:
                    weather_found = 1
                    break
            if weather_found == 0:
                shutil.copy(weather_file, variants_folder)
                print 'Note: Weather copied to Variant folder'
            variables['weatherfile']    = weather_file_name
            # Exterior solar of the EXTCALEXT walls: one extra Type 15 tilted surface per orientation (Type 15-3 layout: EPW, TMY2 and TMY3
            # weather files; DWD TRY 2015 and TRY 2045, file type 10 "German TRY 2017", have the same parameter and output layout)
            variables['hamt_solar_output'] = {}   # orientation -> Type 15 tilted surface number (1 = horizontal plane), read by the e7 handler
            variables['hamt_solar_nsurf']  = 1
            hamt_solar_oris = getHamtSolarOrientations(zone)
            is_dwd_try = (".dat" in weather_file) and (("TRY2015" in weather_file) or ("TRY2045" in weather_file))
            if is_dwd_try or (".epw" in weather_file) or ("tm2" in weather_file) or ("tm3" in weather_file) or ("tmy3" in weather_file):
                t15_name = 'Type15-3'
                t15_tmf = 'Energy+ Weather Files (EPW)\\Type15-3.tmf'
                if is_dwd_try:
                    mode = 10
                    t15_name = 'Type15-10'
                    t15_tmf = 'German TRY 2017\\Type15-10.tmf'
                elif ".epw" in weather_file:
                    mode = 3
                elif ".tm2" in weather_file:
                    mode = 2
                elif ".tm3" or "tmy3" in weather_file:
                    mode = 7
                hamt_solar_tilted = []
                for ori_name in hamt_solar_oris:
                    tilted_surface = getType15TiltedSurface(ori_name, Turn)
                    if tilted_surface is None:
                        ghenv.Component.AddRuntimeMessage(w, "Orientation %s of an EXTCALEXT wall does not follow the Y_azimuth_slope format: its exterior solar gain is zero." % ori_name)
                    else:
                        hamt_solar_tilted.append((ori_name,) + tilted_surface)
                        variables['hamt_solar_output'][ori_name] = len(hamt_solar_tilted) + 1
                t15_npar, t15_nsurf, t15_extra = getType15TiltedLines(hamt_solar_tilted)
                variables['hamt_solar_nsurf'] = t15_nsurf
                variables['weather_data_reader'] = """
*------------------------------------------------------------------------------
* Model "{4}" (Type 15)
*
UNIT 15 TYPE 15	 {4}
*$UNIT_NAME {4}
*$MODEL .\Weather Data Reading and Processing\Standard Format\{5}
*$POSITION 330 31
*$LAYER Weather - Data Files #
PARAMETERS {1}
{0}		! 1 File Type
36		! 2 Logical unit
5		! 3 Tilted Surface Radiation Mode
GRDREF		! 4 Ground reflectance - no snow
0.2		! 5 Ground reflectance - snow cover
{2}		! 6 Number of surfaces
1		! 7 Tracking mode
0.0		! 8 Slope of surface
0		! 9 Azimuth of surface
{3}""".format(mode, t15_npar, t15_nsurf, t15_extra, t15_name, t15_tmf)
                variables['azen_link'] = '15,16'
                variables['aazm_link'] = '15,17'
                variables['rh_link']   = '15,7'
                variables['ith_link']  = '15,18'
                variables['ibh_link']  = '15,19'
                variables['idh_link']  = '15,20'
                variables['ta_link']   = '15,1'
                variables['wv_link']   = '15,8'
                variables['wd_link']   = '15,9'
            else:
                if len(hamt_solar_oris) > 0:
                    ghenv.Component.AddRuntimeMessage(w, "EXTCALEXT walls get their exterior solar gain from extra Type 15 tilted surfaces, which needs an EPW, TMY2, TMY3 or DWD TRY 2015/2045 weather file: the exterior solar gain of the HAMT walls is zero.")
                variables['weather_data_reader'] = """
*------------------------------------------------------------------------------
* Model "Type99-2" (Type 99)
*
UNIT 99 TYPE 99	 Type99-2
*$UNIT_NAME Type99-2
*$MODEL .\Weather Data Reading and Processing\User Format\Type99.tmf
*$POSITION 330 31
*$LAYER Main #
PARAMETERS 3
36		! 1 Logical unit
5		! 2 Sky model for diffuse radiation
1		! 3 Tracking mode
INPUTS 3
GRDREF		! [unconnected] Ground reflectance
0,0		! [unconnected] Slope of surface
0,0		! [unconnected] Azimuth of surface
*** INITIAL INPUT VALUES
0.2 0.0 0.0
"""
                variables['azen_link'] = '99,10'
                variables['aazm_link'] = '99,11'
                variables['rh_link']   = '99,2'
                variables['ith_link']  = '99,12'
                variables['ibh_link']  = '99,13'
                variables['idh_link']  = '99,14'
                variables['ta_link']   = '99,1'
                variables['wv_link']   = '99,3'
                variables['wd_link']   = '99,4'
            variables['stadiacrossarea'] = 4000
            variables['sysdef'] = ''
            links = {}
            unitpos = {}
            newunitpos = {}
            unitpos['1']   = '230 31'
            unitpos['2']   = '730 31'
            unitpos['3']   = '830 31'
            unitpos['4']   = '930 31'
            unitpos['5']   = '1030 31'
            unitpos['6']   = '@column2 180'
            unitpos['7']   = '530 630'
            unitpos['8']   = '830 630'
            unitpos['9']   = '830 630'
            unitpos['15']  = '330 31'
            unitpos['27']  = '430 31'
            unitpos['33']  = '530 31'
            unitpos['46']  = '@column2 830'
            unitpos['56']  = '630 630'
            unitpos['69']  = '630 31'
            unitpos['651']  = '@column1 730'
            unitpos['652']  = '@column1 780'
            unitpos['653']  = '@column1 830'
            unitpos['655']  = '@column1 930'
            unitpos['zunit01'] = '@column2 230'
            unitpos['zunit03'] = '@column2 530'
            unitpos['zunit04'] = '@column2 280'
            unitpos['zunit05'] = '@column2 330'
            unitpos['zunit06'] = '@column2 380'
            unitpos['zunit07'] = '830 630'
            unitpos['zunit08'] = '830 630'
            unitpos['zunit09'] = '@column2 430'
            unitpos['zunit10'] = '@column2 480'
            unitpos['zunit11'] = '@column2 530'
            unitpos['zunit12'] = '@column2 480'
            unitpos['zunit13'] = '@column2 530'
            unitpos['zunit14'] = '@column2 730'
            unitpos['zunit15'] = '@column2 780'
            unitpos['zunit20'] = '@column1 130'
            unitpos['zunit21'] = '@column1 180'
            unitpos['zunit22'] = '@column1 230'
            unitpos['zunit23'] = '@column1 280'
            unitpos['zunit24'] = '@column1 330'
            unitpos['zunit25'] = '@column1 380'
            unitpos['zunit26'] = '@column1 430'
            unitpos['zunit27'] = '@column1 480'
            unitpos['zunit28'] = '@column1 530'
            unitpos['zunit29'] = '@column2 130'
            dummyarray = ['15:1','15:2','15:5','15:33','15:69']
            color = 32768
            for item in dummyarray:
                links[item] = {}
                links[item]['style'] = color
            dummyarray = ['2:3','2:27','2:33','7:5','27:2','33:2','69:2','zunit20:2']
            color = 0
            for item in dummyarray:
                links[item] = {}
                links[item]['style'] = color
            for item in unitpos:
                if 'zunit' in item:
                    continue
                else:
                    variables["upos%03d" % int(item)] = unitpos[item]
            #earth duct
            variables['Tmean_amb']      = sc.sticky[sc.doc.Path]["Tambmean"]
            variables['eta_ed']         = 0
            # Define solar outputs for Window Surfaces
            variables['solarnr']        = 2
            variables['solaroutputs']   = ''
            # Define solar outputs for Window Surfaces
            variables['radnr']          = 2
            #variables['radonline']      = 'AAZM\nAZEN\n'
            variables['radonline']      = ''
            variables['radoutputs']     = 'IT_H = [{0}]/3.6\n'.format(variables['ith_link'])
            coll_ext_walls  = []
            BSDFcounter     = 70
            BSDFused        = 0
            BSDFdata        = ''
            variables['totarea'] = 0
            variables['focaname'] = ''
            variables['outputs'] = ''
            variables['nr_ofT56par']    = 3
            variables['trnflowpar']      = ''
            variables['nr_of_T56inputs'] = 7
            collmanori = []
            variables['opt_T56inputs']   = ''
            variables['opt_T56initial']  = ''
            for zone_item in zone:
                collmanori.extend(zone_item.Airnode.Manualorientation)
            collmanori = list(set(collmanori))
            if len(collmanori) > 0:
                variables['nr_of_T56inputs'] += 3*len(collmanori)
            for citem in collmanori:
                variables['opt_T56inputs']   += '0,0\n0,0\n0,0\n'
                variables['opt_T56initial']  += '0 0 0 '
            variables['opt_T56inputs']   += 'GRDREF\n'
            variables['opt_T56initial']  += '0.2 '
            variables['coupling'] = ''
            variables['aname'] = ''
            variables['zname'] = ''
            variables['resdir'] = ''
        if WriteSimulationFiles == 1 and Multizone:
            layers_def  = defaultdict(dict)
            walls_def   = defaultdict(dict)
            PERT        = 0
            PENRT       = 0
            for layer_item in library.Layers:
                layers_def[layer_item.Name] = layer_item
            for wall_item in library.Walls:
                walls_def[wall_item.Name]  = wall_item
            dckdict  = {}
            extwsurforicoll = []
            schedulescoll = []
            if ResFocusAirnode:
                variables['focaname']   = ResFocusAirnode
            else:
                variables['focaname']   = zone[-1].Airnode.Name
            sc.sticky[sc.doc.Path]['focusairnode']   = variables['focaname']
            # Define solar outputs for Window Surfaces
            variables['radnr']          = 2
            #variables['radonline']      = 'AAZM\nAZEN\n'
            variables['radonline']      = ['AAZM','AZEN']
            variables['radoutputs']     = 'IT_H = [{0}]/3.6\n'.format(variables['ith_link'])
            for zone_item in zone:
                coll_ext_walls.extend(zone_item.Airnode.Extwallsurfacesori)
                zone_item.Airnode.Extwallsurfaces.reverse()
                zone_item.Airnode.Extwallsurfacesori.reverse()
                for items in range(len(zone_item.Airnode.Extwallsurfaces)):
                    if (zone_item.Airnode.Extwallsurfacesori[items] in extwsurforicoll):
                        pass
                    else:
                        variables['radnr']      = variables['radnr'] + 3
                        # An EXTCALEXT wall is a BOUNDARY surface for Type 56 (IT_S = 0): show the Type 15 radiation of its orientation instead
                        rep_is_hamt = False
                        for rep_item in zone_item.Airnode.Surfaces:
                            if rep_item.Surfnum == zone_item.Airnode.Extwallsurfaces[items] and rep_item.Boundarycond == 'EXTCALEXT':
                                rep_is_hamt = True
                        if rep_is_hamt and zone_item.Airnode.Extwallsurfacesori[items] in variables['hamt_solar_output']:
                            for rad_prefix, rad_kind in (('IT', 0), ('IB', 1), ('ID', 4)):
                                variables['radoutputs'] = variables['radoutputs'] + '{0}_{1} = [15,{2}]/3.6\n'.format(rad_prefix, zone_item.Airnode.Extwallsurfacesori[items], getType15TiltedOutput(rad_kind, variables['hamt_solar_output'][zone_item.Airnode.Extwallsurfacesori[items]], variables['hamt_solar_nsurf']))
                        else:
                            variables['radoutputs'] = variables['radoutputs'] + 'IT_{0} = IT_S{1}/(3.6*AREA_S{1}+0.00000001)\n'.format(zone_item.Airnode.Extwallsurfacesori[items],zone_item.Airnode.Extwallsurfaces[items])
                            variables['radoutputs'] = variables['radoutputs'] + 'IB_{0} = IB_S{1}/(3.6*AREA_S{1}+0.00000001)\n'.format(zone_item.Airnode.Extwallsurfacesori[items],zone_item.Airnode.Extwallsurfaces[items])
                            variables['radoutputs'] = variables['radoutputs'] + 'ID_{0} = ID_S{1}/(3.6*AREA_S{1}+0.00000001)\n'.format(zone_item.Airnode.Extwallsurfacesori[items],zone_item.Airnode.Extwallsurfaces[items])
                        extwsurforicoll.append(zone_item.Airnode.Extwallsurfacesori[items])
                for items in zone_item.Airnode.Winsurfaces:
                    for items2 in zone_item.Airnode.Surfaces:
                        if items2.Surfnum == items and items2.BSDFWindows == 1:
                            BSDFused = 1
                if BSDFused == 1:
                    for items in zone_item.Airnode.Winsurfaces:
                        for items2 in zone_item.Airnode.Surfaces:
                            if items2.Surfnum == items:
                                BSDFcounter = BSDFcounter + 1
                                if hasattr(items2, 'Datafile'):
                                    BSDFdata = items2.Datafile
                                else:
                                    pass
                                    #BSDFdata = variables['BSDF_gas_file']
                                #variables['BSDFLU']         = variables['BSDFLU'] + 'CONSTANTS 1\nwindowFileLU{0} = {0}\nASSIGN {1} windowFileLU{0}\n\n'.format(BSDFcounter,BSDFdata)
            for i in range(0,18):
                if i <= len(extwsurforicoll)-1:
                    #variables['radonline'] = variables['radonline'] + 'IT_{0}\n'.format(extwsurforicoll[i])
                    variables['radonline'].append('IT_{0}'.format(extwsurforicoll[i]))
                    variables['radonline'].append('IB_{0}'.format(extwsurforicoll[i]))
                    variables['radonline'].append('ID_{0}'.format(extwsurforicoll[i]))
                #else:
                #    variables['radonline'] = variables['radonline'] + 'Zero\n'
            variables['radonline'] = PrintOnline(name = 'Irradiation',  unit = lu_counter, content = variables['radonline'], y1min = 0, y1max = 1500, y2min = 0, y2max = 1500, unit1 = '[W/m2]', unit2 = '[W/m2]')
            onlinetempoutput = ['Tamb',
                'Tamb_m24',
                'Tsoil',
                'Tsky',
                'Thrc_%s'%variables['focaname'],
                'Tsup_mv_%s'%variables['focaname'],
                'Tair_%s'%variables['focaname'],
                'Top_%s'%variables['focaname'],
                'Tdp_%s'%variables['focaname'],
                'dK_%s'%variables['focaname'],
                'Tsup_al1_%s'%variables['focaname'],
                'Tout_al1_%s'%variables['focaname'],
                'Tnode_al1_%s'%variables['focaname'],
                'Tsurf_al1_%s'%variables['focaname'],
                'Twb_amb',
                'Tset_cl_%s'%variables['focaname'],
                'Tset_ht_%s'%variables['focaname'],
                'Tdp_amb',
                'Occupation_%s'%variables['focaname'],
                'Daytime']
            onlineheatoutput = [
                'Q_tot_ht_%s'%variables['focaname'],
                'Q_heat_%s'%variables['focaname'],
                'Q_lat_hu_%s'%variables['focaname'],
                'Q_ahu_sen_ht_%s'%variables['focaname'],
                'Q_ahu_lat_hu_%s'%variables['focaname'],
                'Q_al_ht_%s'%variables['focaname'],
                'Q_earthd_ht_%s'%variables['focaname'],
                'Q_hrc_sen_ht_%s'%variables['focaname'],
                'Q_ahu_sen_dh_ht_%s'%variables['focaname'],
                'Q_dhw_%s'%variables['focaname'],
                'Q_tot_cl_%s'%variables['focaname'],
                'Q_cool_%s'%variables['focaname'],
                'Q_lat_dh_%s'%variables['focaname'],
                'Q_ahu_sen_cl_%s'%variables['focaname'],
                'Q_ahu_dh_cl_%s'%variables['focaname'],
                'Q_al_cl_%s'%variables['focaname'],
                'Q_earthd_cl_%s'%variables['focaname'],
                'Q_hrc_sen_cl_%s'%variables['focaname'],
                'Q_addon_ht_%s'%variables['focaname'],
                'Q_addon_cl_%s'%variables['focaname']]
            onlineelecoutput = [
                'Q_tot_el_%s'%variables['focaname'],
                'Q_light_el_%s'%variables['focaname'],
                'Q_equip_el_%s'%variables['focaname'],
                'Q_misc_el_%s'%variables['focaname'],
                'Q_al_el_%s'%variables['focaname'],
                'Q_ahu_el_%s'%variables['focaname'],
                'Zero',
                'Zero',
                'Zero',
                'Occupation_%s'%variables['focaname'],
                'Q_soltr_%s'%variables['focaname'],
                'Q_intgain_%s'%variables['focaname'],
                'Q_people_%s'%variables['focaname'],
                'Q_inf_%s'%variables['focaname'],
                'Q_vent_%s'%variables['focaname'],
                'Q_alsrf_%s'%variables['focaname'],
                'Q_thb_%s'%variables['focaname'],
                'Q_surf_%s'%variables['focaname'],
                'Q_solabs_%s'%variables['focaname'],
                'Zero']
            onlineairoutput = [
                'Rh_amb',
                'Rh_%s'%variables['focaname'],
                'X_amb',
                'X_mv_%s'%variables['focaname'],
                'X_%s'%variables['focaname'],
                'CO2_%s'%variables['focaname'],
                'deltaCO2_%s'%variables['focaname'],
                'Zero',
                'Zero',
                'Zero',
                'ACR_inf_%s'%variables['focaname'],
                'ACR_ahu_mv_%s'%variables['focaname'],
                'ACR_ahu_hv_%s'%variables['focaname'],
                'ACR_sv1_%s'%variables['focaname'],
                'ACR_sv2_%s'%variables['focaname'],
                'ACR_tot_%s'%variables['focaname'],
                'ACR_CO2_%s'%variables['focaname'],
                'Vol_%s'%variables['focaname'],
                'Area_%s'%variables['focaname'],
                'Zero']
            printertempairnode = """
Occupation_@aname
Tamb
X_amb
Tamb_m24
Tamb_g24
Tset_cl_@aname
Tset_ht_@aname
Tair_@aname
Top_@aname
ATop_@aname
ATair_@aname
Tdp_@aname
X_@aname
Arh_@aname
Tsup_al1_@aname
Tout_al1_@aname
Tsurf_al1_@aname
Tsup_mv_@aname
X_mv_@aname
Tearthd_@aname
Thrc_@aname
ACR_tot_@aname
Vol_@aname
SHD_active_@aname
Area_@aname
dK_@aname
ACR_sv1_@aname
ACR_sv2_@aname
ACR_ahu_mv_@aname
ACR_ahu_hv_@aname
ACR_inf_@aname
""".split()
            tempairnodelab = '0-1 C g/kg C C C C C C C C C g/kg % C C C C g/kg C C 1/h m3 0/1 m2 K 1/h 1/h 1/h 1/h 1/h'.split()
            printerpowairnode = """
Occupation_@aname
Q_heat_@aname
Q_lat_hu_@aname
Q_al_ht_@aname
Q_ahu_sen_ht_@aname
Q_ahu_sen_dh_ht_@aname
Q_ahu_lat_hu_@aname
Q_dhw_@aname
Q_addon_ht_@aname
Q_tot_ht_@aname
Q_cool_@aname
Q_lat_dh_@aname
Q_al_cl_@aname
Q_ahu_sen_cl_@aname
Q_ahu_dh_cl_@aname
Q_addon_cl_@aname
Q_tot_cl_@aname
Q_light_el_@aname
Q_equip_el_@aname
Q_misc_el_@aname
Q_al_el_@aname
Q_ahu_el_@aname
Q_tot_el_@aname
Q_solabs_@aname
Q_intgain_@aname
Q_surf_@aname
Q_inf_@aname
Q_vent_@aname
Q_coup_@aname
Q_solair_@aname
Q_surf_ext_@aname
""".split()
            powairnodelab = '0-1 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2'.split()
            summaryprinter = """
Totarea
Q_heat
Q_lat_hu
Q_al_ht
Q_ahu_sen_ht
Q_ahu_sen_dh_ht
Q_ahu_lat_hu
Q_dhw
Q_tot_ht
Q_cool
Q_lat_dh
Q_al_cl
Q_ahu_sen_cl
Q_ahu_dh_cl
Q_tot_cl
Q_light_el
Q_equip_el
Q_misc_el
Q_al_el
Q_ahu_el
Q_tot_el
Zero
""".split()
            sumlabels = 'm2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 W/m2 Zero'.split()
        # Get all required bui inputs
        if WriteSimulationFiles == 1 and Multizone:
            #bui_file_base = sc.sticky[sc.doc.Path]["BUI_FILE"]
            bui_file_base = bui_file_tmp
            buioutput, okey = sc.sticky[sc.doc.Path]["BUI_OUTPUT"]
            printbui(bui_file_base)
            bui_file_base = []
            bui_file = readbui()
            dummy = []
            for items in bui_file:
                search_inputs=re.search(r'INPUTS ',items)
                if search_inputs is not None:
                    dummy = items.split()
            dummy.pop(0)
            searchedinputs = dummy
            for i,item in enumerate(searchedinputs):
                if 'CONAMB' in item:
                    searchedinputs[i] = re.sub('CONAMB', 'CCONAMB',searchedinputs[i])
            if variables['trnflow'] == 1 or sc.sticky[sc.doc.Path]["trnflow"] == -1:
                variables['nr_ofT56par']    = 14
                variables['trnflowpar']      = trnflow_parameters(sc.sticky[sc.doc.Path]["Altitude"])
            initialval = {}
            if "InitialValues" in locals():
                for items in InitialValues:
                    key,value = items.split('=')
                    key = re.sub(' ','',key)
                    initialval[key] = value
            for items in searchedinputs:
                variables['nr_of_T56inputs'] = variables['nr_of_T56inputs'] + 1
                variables['opt_T56inputs']   = variables['opt_T56inputs'] + '{0}\n'.format(items)
                # @OC START
                #OC_Comand lines: Input Value for wind dependent hcon cannot be 0
                if initialval.has_key(items):
                    variables['opt_T56initial']  = variables['opt_T56initial'] + '%s '%initialval[items]
                elif items == 'hcon_wind_dep' or items == 'CNV_MEM_IN' or items == 'CNV_MEM_OUT':
                    variables['opt_T56initial']  = variables['opt_T56initial'] + '1 '
                else:
                    variables['opt_T56initial']  = variables['opt_T56initial'] + '0 '
                # @OC END
            #Summarize the geometrical information
            variables['area_outside'] = 0
            variables['area_window'] = 0
            variables['area_floor'] = 0
            variables['area_ceiling'] = 0
            variables['area_wall'] = 0
            #Collect all the summed energy demands
            for zone_item in zone:
                variables['totarea']    = variables['totarea'] + zone_item.Airnode.Totfloorarea
            variables['coll_Q_heat']        = '0'
            variables['coll_Q_inf']         = '0'
            variables['coll_Q_vent']        = '0'
            variables['coll_Q_intgain']     = '0'
            variables['coll_Q_conv']        = '0'
            variables['coll_Q_rad']         = '0'
            variables['coll_Q_soltr']       = '0'
            variables['coll_Q_cool']        = '0'
            variables['coll_Q_lat_dh']      = '0'
            variables['coll_Q_lat_hu']      = '0'
            variables['coll_Q_people']        = '0'
            variables['coll_Q_light']       = '0'
            variables['coll_Q_equip']        = '0'
            variables['coll_Q_misc']       = '0'
            variables['coll_Q_ahu_sen_ht']  = '0'
            variables['coll_Q_ahu_sen_cl']  = '0'
            variables['coll_Q_ahu_lat_hu']  = '0'
            variables['coll_Q_ahu_lat_dh']  = '0'
            variables['coll_Q_ahu_el']      = '0'
            variables['coll_Q_alfl_cl']     = '0'
            variables['coll_Q_alfl_ht']     = '0'
            variables['coll_Q_tabs1']       = '0'
            variables['coll_Q_dhw']         = '0'
            variables['coll_Q_ht_tot']      = '0'
            variables['coll_Q_cl_tot']      = '0'
            variables['coll_Q_el_tot']      = '0'
            variables['coll_Q_al_el']       = '0'
            variables['coll_Q_ahu_sen_dh_ht'] = '0'
            variables['coll_Q_ahu_sen_dh_cl'] = '0'
            variables['coll_Q_thb'] = '0'
        if WriteSimulationFiles == 1:
            #collect all the summarized outputs
            variables['coll_Q_heat'] = '(' + ' + '.join(str('Q_heat_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_inf'] = '(' + ' + '.join(str('Q_inf_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_vent'] = '(' + ' + '.join(str('Q_vent_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_intgain'] = '(' + ' + '.join(str('Q_intgain_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_conv'] = '(' + ' + '.join(str('Q_conv_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_rad'] = '(' + ' + '.join(str('Q_rad_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_soltr'] = '(' + ' + '.join(str('Q_soltr_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_cool'] = '(' + ' + '.join(str('Q_cool_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_lat_dh'] = '(' + ' + '.join(str('Q_lat_dh_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_lat_hu'] = '(' + ' + '.join(str('Q_lat_hu_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_people'] = '(' + ' + '.join(str('Q_people_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_light'] = '(' + ' + '.join(str('Q_light_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_equip'] = '(' + ' + '.join(str('Q_equip_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_misc'] = '(' + ' + '.join(str('Q_misc_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_ahu_sen_ht'] = '(' + ' + '.join(str('Q_ahu_sen_ht_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_ahu_sen_cl'] = '(' + ' + '.join(str('Q_ahu_sen_cl_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_ahu_lat_hu'] = '(' + ' + '.join(str('Q_ahu_lat_hu_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_ahu_lat_dh'] = '(' + ' + '.join(str('Q_ahu_lat_dh_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_ahu_el'] = '(' + ' + '.join(str('Q_ahu_el_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_alfl_ht'] = '(' + ' + '.join(str('Q_al_ht_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_alfl_cl'] = '(' + ' + '.join(str('Q_al_cl_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_tabs1'] = '(' + ' + '.join(str('Q_alsrf_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_dhw'] = '(' + ' + '.join(str('Q_dhw_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_ht_tot'] = '( Q_ht_addon + ' + ' + '.join(str('Q_tot_ht_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_cl_tot'] = '( Q_cl_addon + ' + ' + '.join(str('Q_tot_cl_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_el_tot'] = '( Q_el_addon + ' + ' + '.join(str('Q_tot_el_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_al_el'] = '(' + ' + '.join(str('Q_al_el_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_ahu_sen_dh_ht'] = '(' + ' + '.join(str('Q_ahu_sen_dh_ht_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_ahu_sen_dh_cl'] = '(' + ' + '.join(str('Q_ahu_sen_dh_cl_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
            variables['coll_Q_thb'] = '(' + ' + '.join(str('Q_thb_%s * Totarea_%s')%(x,x) for x in airnodelist) + ')/(Totarea+0.000001)'
        outputlist = 0
        outputnames = []
        userdefoutnames = defaultdict()
        if WriteSimulationFiles == 1 and Multizone:
            if int(StandardOutputs) == 1:
                variables['focairnodeonline'] +=  PrintOnline(name = 'Temperature', unit = 651, content = onlinetempoutput, y1min = -5, y1max = 35, y2min = -5, y2max = 35, y1label = 'Temperature [C]', y2label = 'Temperature [C]')
                variables['focairnodeonline'] +=  PrintOnline(name = 'HeatCool', unit = 652, content = onlineheatoutput, y1min = -100, y1max = 100, y2min = -100, y2max = 100, y1label = 'Spec Power  [W/m2]', y2label = 'Spec Power  [W/m2]')
                variables['focairnodeonline'] +=  PrintOnline(name = 'ElecBala', unit = 653, content = onlineelecoutput, y1min = -100, y1max = 100, y2min = -100, y2max = 100, y1label = 'Spec Power  [W/m2]', y2label = 'Spec Power  [W/m2]')
                variables['focairnodeonline'] +=  PrintOnline(name = 'AirQuality', unit = 655, content = onlineairoutput, y1min = 0, y1max = 100, y2min = 0, y2max = 10, y1label = 'Humidity [%][g/kg]CO2 [VOLppm]', y2label = 'ACH [1/h]')
                variables['summaryprinter'] +=  PrintPrintegrator(name = 'Power', unit = 46, content = summaryprinter, labels = sumlabels, file = 'p_tot_1h.prn')
            # Coupling definition based on ventilation
            variables['coupling'] = ''
            if zone[-1].Coupling:
                couplcount = 0
                type2count = 0
                equcoll = ''
                type2coll = ''
                datanames = []
                datacoll  = []
                co2coupl  = {}
                for coupl_items in zone[-1].Coupling:
                    if coupl_items.Source in airnodelist and coupl_items.Target in airnodelist:
                        pass
                    else:
                        continue
                    if coupl_items.Target in co2coupl:
                        pass
                    else:
                        co2coupl[coupl_items.Target] = '0'
                    if coupl_items.Info == 'INVERSION':
                        if coupl_items.ACR_Vol == coupl_items.Target:
                            pass
                        else:
                            type2count = type2count + 1
                        linkname1 = "{1}TO{0}".format(coupl_items.Target, coupl_items.Source)
                        if linkname1 in datanames:
                            pass
                        else:
                            datanames.append(linkname1)
                            datacoll.append("MF_{0} = 0".format(linkname1))
                            couplcount = couplcount + 1
                            co2coupl[coupl_items.Target] += ' + MF_{0} / rhoAir * (CO2l_{1} - CO2l_{2} )'.format(linkname1, coupl_items.Source, coupl_items.Target)
                        if linkname1 in datanames:
                            for item3 in range(len(datanames)):
                                if linkname1 in datanames[item3]:
                                    datacoll[item3] = datacoll[item3] + " + {4} * rhoAir * {3}*VOL_{1}*[2{2},1]".format(coupl_items.Source, coupl_items.ACR_Vol, type2count, coupl_items.ACR,coupl_items.ScaleFactor)
                        else:
                            datacoll[-1] = datacoll[-1] + " + {4} * rhoAir * {3}*VOL_{1}*[2{2},1]".format(coupl_items.Source, coupl_items.ACR_Vol, type2count, coupl_items.ACR,coupl_items.ScaleFactor)
                        if coupl_items.ACR_Vol == coupl_items.Target:
                            pass
                        else:
                            type2coll = type2coll + """\nUNIT 2{2} TYPE 2	 Type2d
*$POSITION 830 630
*$LAYER Main # #
PARAMETERS 2
5 ! 1 No. of oscillations
95		! 2 High limit cut-out
INPUTS 6
Tair_{1}		! [equation] Upper input value
Tlair_{0}		! [unconnected] Lower input value
0,0		! [unconnected] Monitoring value
2{2},1 		! Type2d:Output control function ->Input control function
0,0		! [unconnected] Upper dead band
0,0		! [unconnected] Lower dead band
*** INITIAL INPUT VALUES
25 24 90 0 0.5 0.1\n""".format(coupl_items.Source, coupl_items.Target ,type2count)
                    elif coupl_items.Info == 'PERMANENT':
                        linkname1 = "{1}TO{0}".format(coupl_items.Target, coupl_items.Source)
                        if linkname1 in datanames:
                            pass
                        else:
                            datanames.append(linkname1)
                            datacoll.append("MF_{0} = 0".format(linkname1))
                            couplcount = couplcount + 1
                            co2coupl[coupl_items.Target] += ' + MF_{0} / rhoAir * (CO2l_{1} - CO2l_{2})'.format(linkname1, coupl_items.Source, coupl_items.Target)
                        if linkname1 in datanames:
                            for item3 in range(len(datanames)):
                                if linkname1 in datanames[item3]:
                                    datacoll[item3] = datacoll[item3] + " + {4} * rhoAir * {3}*VOL_{1}".format(coupl_items.Source, coupl_items.ACR_Vol, type2count, coupl_items.ACR,coupl_items.ScaleFactor)
                        else:
                            datacoll[-1] = datacoll[-1] + " + {4} * rhoAir * {3}*VOL_{1}".format(coupl_items.Source, coupl_items.ACR_Vol, type2count, coupl_items.ACR,coupl_items.ScaleFactor)
                    elif coupl_items.Info == 'STVENT1' or coupl_items.Info == 'STVENT2' or coupl_items.Info == 'MECHANICAL':
                        linkname1 = "{1}TO{0}".format(coupl_items.Target, coupl_items.Source)
                        if linkname1 in datanames:
                            pass
                        else:
                            datanames.append(linkname1)
                            datacoll.append("MF_{0} = 0".format(linkname1))
                            couplcount = couplcount + 1
                            co2coupl[coupl_items.Target] += ' + MF_{0} / rhoAir * (CO2l_{1} - CO2l_{2})'.format(linkname1, coupl_items.Source, coupl_items.Target)
                        if linkname1 in datanames:
                            for item3 in range(len(datanames)):
                                if linkname1 in datanames[item3]:
                                    if coupl_items.Info == 'STVENT1':
                                        datacoll[item3] = datacoll[item3] + " + {1} * MF_sv1_{0}".format(coupl_items.FirstZone,coupl_items.ScaleFactor)
                                    elif coupl_items.Info == 'STVENT2':
                                        datacoll[item3] = datacoll[item3] + " + {1} * MF_sv2_{0}".format(coupl_items.FirstZone,coupl_items.ScaleFactor)
                                    elif coupl_items.Info == 'MECHANICAL':
                                        datacoll[item3] = datacoll[item3] + " + {1} * MF_sup_{0}".format(coupl_items.FirstZone,coupl_items.ScaleFactor)
                        else:
                            if coupl_items.Info == 'STVENT1':
                                datacoll[-1] = datacoll[-1] + " + {1} * MF_sv1_{0}".format(coupl_items.FirstZone,coupl_items.ScaleFactor)
                            elif coupl_items.Info == 'STVENT2':
                                datacoll[-1] = datacoll[-1] + " + {1} * MF_sv2_{0}".format(coupl_items.FirstZone,coupl_items.ScaleFactor)
                            elif coupl_items.Info == 'MECHANICAL':
                                datacoll[-1] = datacoll[-1] + " + {1} * MF_sup_{0}".format(coupl_items.FirstZone,coupl_items.ScaleFactor)
                for item in datacoll:
                    equcoll = equcoll + item + '\n'
                if equcoll != '':
                    equposition = """*$POSITION 830 630
*$LAYER Main # # \n"""
                    dummyco2 = ''
                    for coitem in co2coupl:
                        dummyco2 += ' CO2coupl_%s = %s\n'%(coitem,co2coupl[coitem])
                        couplcount += 1
                        #for subitem in co2coupl[coitem]:
                        #    dummyco2 += '+' + subitem
                    equcoll = "EQU {0}\n".format(couplcount) + equcoll
                    equcoll = equcoll + dummyco2 + type2coll + equposition
                    variables['coupling'] = variables['coupling'] + equcoll
            # BSDF shading definition
            variables['BSDF'] = ''
            BSDFcount = 0
            type2count = 0
            equcoll = ''
            type2coll = ''
            datanames = []
            datacoll  = []
            for zone_item in zone:
                if len(zone_item.Airnode.Winsurfaces)>0:
                    for items in zone_item.Airnode.Winsurfaces:
                        for items2 in zone_item.Airnode.Surfaces:
                            if items2.Mshade == 'BSDFCOMPLEX' and items2.Surfnum == items:
                                zone_item.Airnode.BSDFWinsurfaces.append(items)
                                variables['anr']         = "%02d" % (zone_item.Anr,)
                                dummy_config = items2.Configids.rstrip()
                                dummy_config = dummy_config.split(',')
                                dummy_config.append(items2.Baseconfigid)
                                dummy_config = list(set(dummy_config))
                                dummy_config.pop(0)
                                config_list = []
                                for i in reversed(dummy_config):
                                    config_list.append(i)
                                type2count = type2count + 1
                                BSDFcount = BSDFcount + 5
                                dummyazimuth = items2.BSDFazimuth
                                if dummyazimuth > 180:
                                    dummyazimuth = (-360 + dummyazimuth)
                                shadingdef = "YSHD_BSDF_S{0}_{1}".format(items2.Surfnum, zone_item.Airnode.Name)
                                """
                                datacoll.append("{0} = 0 + [3{2},1] * Yshd_temp_{5} * (gt(Tamb_m24,{1}) * {3} + not(gt(Tamb_m24,{1})) * {4})\n".format(shadingdef,items2.Summertair24above,type2count,items2.Configfss,items2.Configfsw,zone_item.Airnode.Name,items2.Surfnum))
                                datacoll.append("SHDPOS_S{6}_{5} = eql({0},0)*{0} + not(eql({0},0))*{0}\n".format(shadingdef,items2.Summertair24above,type2count,items2.Configfss,items2.Configfsw,zone_item.Airnode.Name,items2.Surfnum))
                                datacoll.append('\n')
                                dummysen1 = '0'
                                dummysen2 = '0'
                                dummysen3 = '0'
                                if 'W' in items2.Orientation or 'E' in items2.Orientation or items2.BSDFFacades == 1:
                                    dummy_counter1 = 1
                                    dummy_counter2 = 2
                                    dummy_counter3 = 3
                                else:
                                    dummy_counter1 = 1 + 3 * len(config_list)
                                    dummy_counter2 = 2 + 3 * len(config_list)
                                    dummy_counter3 = 3 + 3 * len(config_list)
                                for item in range(len(config_list)):
                                    dummysen1 = dummysen1 + ' + [{0},{1}]*eql(SHDPOS_S{4}_{2},{3})'.format(variables['zunit04'],dummy_counter1,zone_item.Airnode.Name,config_list[item],items2.Surfnum)
                                    dummy_counter1 = dummy_counter1 + 3
                                datacoll.append("LUX_level1_S{0}_{1} = {2}\n".format(items2.Surfnum,zone_item.Airnode.Name,dummysen1))
                                for item in range(len(config_list)):
                                    dummysen2 = dummysen2 + ' + [{0},{1}]*eql(SHDPOS_S{4}_{2},{3})'.format(variables['zunit04'],dummy_counter2,zone_item.Airnode.Name,config_list[item],items2.Surfnum)
                                    dummy_counter2 = dummy_counter2 + 3
                                datacoll.append("LUX_level2_S{0}_{1} = {2}\n".format(items2.Surfnum,zone_item.Airnode.Name,dummysen2))
                                for item in range(len(config_list)):
                                    dummysen3 = dummysen3 + ' + [{0},{1}]*eql(SHDPOS_S{4}_{2},{3})'.format(variables['zunit04'],dummy_counter3,zone_item.Airnode.Name,config_list[item],items2.Surfnum)
                                    dummy_counter3 = dummy_counter3 + 3
                                datacoll.append("LUX_level3_S{0}_{1} = {2}\n".format(items2.Surfnum,zone_item.Airnode.Name,dummysen3))
                                datacoll.append('\n')
                                """
                                type2coll = type2coll + """\nUNIT 3{1} TYPE 2	 Type2d
PARAMETERS 2
5 ! 1 No. of oscillations
95		! 2 High limit cut-out
INPUTS 6
IT_{0}		! [equation] Upper input value
0,0		! [unconnected] Lower input value
0,0		! [unconnected] Monitoring value
3{1},1 		! Type2d:Output control function ->Input control function
0,0		! [unconnected] Upper dead band
0,0		! [unconnected] Lower dead band
*** INITIAL INPUT VALUES
25 0 90 0 {2} {3}\n""".format(items2.Orientation,type2count,items2.Shadeclose / 3.6,items2.Shadeopen / 3.6)
            for item in datacoll:
                equcoll = equcoll + item
            if equcoll != '':
                equcoll = "EQU {0}\n".format(BSDFcount) + equcoll
                equcoll = equcoll + '\n' + type2coll
                variables['BSDF'] = variables['BSDF'] + equcoll
            # BSDF shading definition
            variables['BSDF'] = ''
            BSDFcount = 0
            type2count = 0
            equcoll = ''
            type2coll = ''
            datanames = []
            datacoll  = []
            for zone_item in zone:
                if len(zone_item.Airnode.Bsdfsurfaces)>0:
                    for items in zone_item.Airnode.Winsurfaces:
                        for items2 in zone_item.Airnode.Surfaces:
                            if (items2.Mshade == 'BSDFSIMPLE' or items2.Mshade == 'BSDFCOMPLEX') and items2.Surfnum == items:
                                if items2.Gapventmode == 'STACK':
                                    BSDFcount += 9
                                    datacoll.append("""VOL{0}_{1}     = {2}
TDIF{0}_{1}     = MAX(ABS(TGGAP1_S{1}-Tamb),0.1)
ATOP{0}_{1}  = {3}
ABOT{0}_{1}  = {4}
HDIF{0}_{1}   = {5}
VER1{0}_{1}   = ATOP{0}_{1}/VOL{0}_{1}
VER2{0}_{1}   = ATOP{0}_{1}**2/ABOT{0}_{1}**2
ACH{0}_{1}    = VER1{0}_{1}*3600*(9.81*HDIF{0}_{1}*TDIF{0}_{1}/((Tamb+273.15)*(1+VER2{0}_{1})))**0.5
MFLOW{0}_{1}  = rhoAir * VOL{0}_{1} * ACH{0}_{1}""".format(items2.Gapvent1,
                items,items2.Gapvolume,items2.Gapeffopeningtop,items2.Gapeffopeningbot,items2.Gapheightdiffopen))
                                    datacoll.append('\n')
                                elif items2.Gapventmode == 'PERMANENT':
                                    BSDFcount += 2
                                    datacoll.append("""TSUP{0}_{1}     = {2}
MFLOW{0}_{1}  = {3}""".format(items2.Gapvent1, items, items2.Tsupgap, items2.Mflowperm))
                                    datacoll.append('\n')
            for item in datacoll:
                equcoll = equcoll + item
            if equcoll != '':
                equcoll = "EQU {0}\n".format(BSDFcount) + equcoll
                equcoll = equcoll + '\n' + type2coll
                variables['BSDF'] = variables['BSDF'] + equcoll
            #print BSDF online plotter
            BSDF_found = 0
            dummyname = ''
            stopindex = 17
            for zone_item in zone:
                if len(zone_item.Airnode.Winsurfaces)>0:
                    for items in zone_item.Airnode.Winsurfaces:
                        for items2 in zone_item.Airnode.Surfaces:
                            if items2.BSDFWindows == 1 and items2.Surfnum == items:
                                variables['endsingle']  = ''
                                BSDF_found = 1
                                datacounter = 1
                                if stopindex > 0: dummyname = dummyname + "TGGAP1_S{0}\n".format(items2.Surfnum)
                                stopindex = stopindex - datacounter
                                #if stopindex > 0: dummyname = dummyname + "YSHD_TEMP_{1}\n".format(items2.Surfnum,zone_item.Airnode.Name)
                                #stopindex = stopindex - datacounter
                                #if stopindex > 0: dummyname = dummyname + "SHDPOS_S{0}_{1}\n".format(items2.Surfnum,zone_item.Airnode.Name)
                                #stopindex = stopindex - datacounter
                                #if stopindex > 0: dummyname = dummyname + "B3_GTOT_S{0}\n".format(items2.Surfnum,zone_item.Airnode.Name)
                                #stopindex = stopindex - datacounter
                                #if stopindex > 0: dummyname = dummyname + "B3_FCISHD_S{0}\n".format(items2.Surfnum,zone_item.Airnode.Name)
                                #stopindex = stopindex - datacounter
                                #dummyname = dummyname + "B3_AI_S{0}\n".format(items2.Surfnum,zone_item.Airnode.Name)
            if stopindex > 0:
                for index_name in range(0,stopindex):
                    dummyname = dummyname + "Zero\n"
            if BSDF_found == 1:
                variables['BSDFonline']="""*---------------
* Model "Comfort" (Type 65)
*
UNIT 659 TYPE 65	 BSDF
*$UNIT_NAME Multi
*$MODEL .\Output\Online Plotter\Online Plotter Without File\Type65d.tmf
*$POSITION 1052 95
*$LAYER Main #
PARAMETERS 12
10		! 1 Nb. of left-axis variables
10		! 2 Nb. of right-axis variables
-5		! 3 Left axis minimum
35		! 4 Left axis maximum
-5		! 5 Right axis minimum
35		! 6 Right axis maximum
-1		! 7 Number of plots per simulation
14		! 8 X-axis gridpoints
showonline		! 9 Shut off Online w/o removing
-1		! 10 Logical unit for output file
0		! 11 Output file units
0		! 12 Output file delimiter
INPUTS 20
Tamb
AAZM
AZEN
{0}
*** INITIAL INPUT VALUES
Tamb
AAZM
AZEN
{0}
LABELS  3
"BSDF"
"BSDF"
"BSDF" """.format(dummyname)
            #print Multizone online plotter
            if len(airnodelist) > 1:
                variables['endsingle']  = ''
                online_content = ['TAMB']
                for item in airnodelist:
                    online_content.append("TOP_{0}".format(item))
                    online_content.append("TAIR_{0}".format(item))
                variables['multionline']= PrintOnline(name = 'Multi', unit = lu_counter, content = online_content, y1min = -5, y1max = 35, y2min = -5, y2max = 35)
            #print coupling online plotter
            if zone[-1].Coupling:
                online_content = []
                for index_name in zone[-1].Coupling:
                    if index_name.Source in airnodelist and index_name.Target in airnodelist:
                        pass
                    else:
                        continue
                    online_content.append("MF_{0}".format(index_name.Name))
                variables['couplonline']= PrintOnline(name = 'Coupl', unit = lu_counter, content = online_content, y1min = 0, y1max = 10000, y2min = 0, y2max = 10000)
            #print comfort online plotter and printer file
            comfortlist = 0
            #cmh_200513 comfortoutput = 'TMR'
            comfortoutput = ['TMR','PMV']
            for zone_item in zone:
                comfortlist = comfortlist + zone_item.comfortptsno
            if comfortlist > 0:
                online_content = []
                for citem in comfortoutput:
                    for item in range(1,comfortlist+1):
                        online_content.append("{0}_C{1}".format(citem,item))
                variables['comfortonline']= PrintOnline(name = 'Comfort', unit = lu_counter, content = online_content, y1min = -5, y1max = 35, y2min = -5, y2max = 35)
                variables['comfortprint'] = PrintPrintegrator(name = 'Comfort', unit = lu_counter, content = online_content)
            # @OC START
            #OC_TMR and UTCI variables
            if 'OC_command_lines_TMR_UTCI_1' in sc.sticky[sc.doc.Path]:
                exec(sc.sticky['OC_command_lines_TMR_UTCI_1'])
                exec(sc.sticky['OC_command_lines_TMR_UTCI_2'])
                UTCI_output_Equations_final = sc.sticky['UTCI_output_Equations'].format(len(UTCI_output_equations),UTCI_output_equations_2,'UTCI_output_Equations')
                UTCI_control_Equations_EVA_final =sc.sticky['UTCI_output_Equations'].format(len(UTCI_EVA_control_list),UTCI_EVA_control_list2,'UTCI_control_Equations_EVA')
                EVA_Output_Equations_final =sc.sticky['UTCI_output_Equations'].format(len(EVA_Output_list),EVA_Output_list2,'EVA_Output_Equations')
                lu_counter = 975
            # @OC_END

            comfortlist = 0
            comfidcoll = []
            for zone_item in zone:
                if zone_item.Airnode.Comfort:
                    for comfort_item in range(len(zone_item.Airnode.Comfort)):
                        if zone_item.Airnode.Comfort[comfort_item].Type == 'SET':
                            comfortlist = 1
                            comfidcoll = zone_item.Airnode.Comfort[comfort_item].Setcoll
                            #for comfortid in range(len(zone_item.Airnode.Comfort[comfort_item].Setcoll)):
                            #    pass
                            break
            if comfortlist > 0:
                content = []
                for index_name in range(1,len(comfidcoll) + 1):
                    content.append("pmvlw_set_C{0}_{1}".format(comfidcoll[index_name-1],zone[0].Airnode.Name))
                variables['setcomfortprint'] = PrintPrintegrator(name = 'SetComfort', unit = lu_counter, content = content)
            # Stop Variable declaration for the deck file
            #userdefined online plotter and printer file
            for zone_item in zone:
                if zone_item.Airnode.Output:
                    for output_item in zone_item.Airnode.Output:
                        udefoutput = []
                        if output_item:
                            pass
                        else:
                            continue
                        if output_item.Type == 'SURFACE':
                            outputlist = outputlist + len(output_item.NtypesNo) * len(output_item.SurfaceID)
                            outputnames.extend(output_item.NtypesShort)
                            udefoutput.extend(output_item.NtypesShort)
                        elif output_item.Type == 'COMFORT':
                            outputlist = outputlist + 1
                            dummy = []
                            #addouttempllines = addouttempllines + '= {0} : COMFID = '.format(ntype)
                            for cmf in zone_item.Airnode.ComfId:
                                dummy.append('{0}_C{1}'.format(output_item.NtypesShort[0],cmf))
                            outputnames.extend(dummy)
                            udefoutput.extend(dummy)
                        elif output_item.Type == 'AIRLINKS':
                            for doitem in output_item.Ntype:
                                for dsubitem in okey:
                                    if doitem in dsubitem:
                                        outputlist = outputlist + 1
                                        outputnames.append(dsubitem)
                                        udefoutput.append(dsubitem)
                        else:
                            outputlist = outputlist + len(output_item.NtypesNo)
                            for item2 in output_item.NtypesShort:
                                outputnames.append('{0}_{1}'.format(item2,zone_item.Airnode.Name))
                                udefoutput.append('{0}_{1}'.format(item2,zone_item.Airnode.Name))
                        if output_item.UserName and output_item.UserName != '':
                            userdefoutnames[output_item.UserName] = udefoutput
                            outputnames.append(output_item.UserName)
        if WriteSimulationFiles == 1:
            dummyequ = 0
            dummystr = ''
            useroutputnames = []
            for item in UserEquations:
                for subitem in item.split('\r\n'):
                    dummy = subitem.split('=')
                    userdefoutnames[dummy[0]] = [dummy[1]]
                    outputnames.append(dummy[0])
                    useroutputnames.append(dummy[0])
            for item in UserOutputs:
                outputnames.append(item)
            for ix, key in enumerate(useroutputnames):
                dummyequ += 1
                dummystr += key + '='
                dummystr += '+'.join(str(x) for x in userdefoutnames[key])
                dummystr += '\n'
            if dummystr != '':
                variables['userdefout'] = """EQU {0}\n{1}""".format(dummyequ, dummystr)
            if outputlist > 0 or len(outputnames) > 0:
                if len(outputnames) <= 20:
                    variables['addoutputonline'] = variables['addoutputonline'] + PrintOnline(name = 'AddOutput', unit = lu_counter, content = outputnames[0:20], y1min = 0, y1max = 100, y2min = 0, y2max = 100)
                if len(outputnames) > 20:
                    variables['addoutputonline'] = variables['addoutputonline'] + PrintOnline(name = 'AddOutput', unit = lu_counter, content = outputnames[0:20], y1min = 0, y1max = 100, y2min = 0, y2max = 100)
                    variables['addoutputonline'] = variables['addoutputonline'] + PrintOnline(name = 'AddOutput2', unit = lu_counter, content = outputnames[20:40], y1min = 0, y1max = 100, y2min = 0, y2max = 100)
                variables['addoutputprint']  = PrintPrintegrator(name = 'AddOutput', unit = lu_counter, content = outputnames, timestep = addoutstep)
        if WriteSimulationFiles == 1:
            for sysitem in SystemComponents:
                variables['sysdef'] += sysitem.fillTemplate()
        # Stop Variable declaration for the deck file
        infofile = []
        Variants = []
        wallproperties = []
        if WriteSimulationFiles == True:
            scandirs(variants_folder)
            if Multizone:
                getbuiOutputs()
            printdck()
        if PrintJobList == True:
            joblist = []
            joblist.append('*!6')
            timesleep = str(3)
            if build_mode == 'BUI':
                joblist.append( variants_folder + ' ' + timesleep + ' ' + TRNSYS_path + '\Building\TRNBUILD.exe ' + variants_folder + str(variant_name) + '.b%s'%TRNSYS + ' /N /vfm' )
            else:
                joblist.append( variants_folder + ' ' + timesleep + ' ' + TRNSYS_path + '\Building\TRNBID.exe ' + variants_folder + str(variant_name) + '.b%s'%TRNSYS + ' /N /vfm' )
            job6.extend(joblist)
            sc.sticky[sc.doc.Path]['Job6'] = job6
            joblist = []
            joblist.append('*!7')
            if build_mode == 'BUI':
                joblist.append( variants_folder + ' ' + timesleep + ' ' + TRNSYS_path + '\Building\TRNBUILD.exe ' + variants_folder + str(variant_name) + '.b%s'%TRNSYS + ' /N /masks' )
            else:
                joblist.append( variants_folder + ' ' + timesleep + ' ' + TRNSYS_path + '\Building\TRNBID.exe ' + variants_folder + str(variant_name) + '.b%s'%TRNSYS + ' /N /masks' )
            job7.extend(joblist)
            sc.sticky[sc.doc.Path]['Job7'] = job7
            joblist = []
            joblist.append('*!8')
            timesleep = str(1)
            joblist.append( variants_folder + ' ' + timesleep + ' ' + TRNSYS_path + '\exe\TRNExe.exe' + ' ' + variants_folder + str(variant_name) + '.d%s /N'%TRNSYS )
            job8.extend(joblist)
            sc.sticky[sc.doc.Path]['Job8'] = job8
        for zone_item in zone:
            variables['refarea']        = round(zone_item.Airnode.Floorarea,1)
        #print zone

        _distBaseSrf = sc.sticky[sc.doc.Path]["GridDistanceSolarConcave"] #CSH_220427 moved up in code; this variable is set in Multizone component

        #Starting from here the Variant list is written in append or reset mode
        infofile = VARIANTS(variant_name,variants_folder)
        darea = variables['refarea'] if Multizone else 0
        dummy = '{0}\t{1}\t{2}\t{3}'.format(darea,infofile.Name,long_variant_name,infofile.Path)
        Variantlist = []
        Variantlist.append(dummy)
        sc.sticky[sc.doc.Path]['Variant'] = Variantlist
        Variant = dummy

        if RunDaylightPreprocessing == True:
            proc1 = Popen( TRNSYS_path + '\\Building\\trnRAD\\trnRAD.exe ' + variants_folder + variant_name + '.b%s'%TRNSYS, shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
            form = runForm('trnRAD')
            form.Show()
            proc1.communicate() #now wait
            form.Close()


        if RunThermalPreprocessing == True:
            pass
            #check_trnsize = os.stat(variants_folder + variant_name + '.trn')
            #if check_trnsize.st_size == 0:
            #    ghenv.Component.AddRuntimeMessage(err, "Construction definition is not working, please check the construction!")
            #    sys.exit()
            runthermaldef()

        #pablo
        if RunVFM == True:
            pass
            #check_trnsize = os.stat(variants_folder + variant_name + '.trn')
            #if check_trnsize.st_size == 0:
            #    ghenv.Component.AddRuntimeMessage(err, "Construction definition is not working, please check the construction!")
            #    sys.exit()
            runvfmdef()
        if RunThermalSimulation == True:
            runsimulation()

            #copyResultFiles(sourcefolder = variants_folder, targetfolder = results_folder, extension = ['.ill'])
            # moveResultFiles(sourcefolder = variants_folder, targetfolder = results_folder, extension = ['.prn','.ill_grid','.grid','.df'])
            # JX Changed
            results_folder = os.path.join(variants_folder, "Results")
            moveResultFiles(sourcefolder = variants_folder, targetfolder = results_folder, extension = ['.prn','.out'])
            # cleanSimulationFolder(sourcefolder = variants_folder, filecontent = ['Qspec.sum','.rad','.BAL','.log','.bld','trn','xyz','.hea','.out','.dc','.oct','.bat'])
        #variables_dict = todict(zone.Airnode[-1].surfaces)
        #starting from here a daylight grid with surfaces can be printed
        if RunDaylightPreprocessing == 1 or WriteDaylightGrid == 1:
            zonedict = dict()
            for zone_item in zone:
                if zone_item.Airnode.Zonename in zonedict:
                    zonedict[zone_item.Airnode.Zonename][zone_item.Airnode.Name] = zone_item.Airnode
                else:
                    zonedict[zone_item.Airnode.Zonename] = dict()
                    zonedict[zone_item.Airnode.Zonename][zone_item.Airnode.Name] = zone_item.Airnode
            neworder = []
            for key1 in zonedict:
                for key2 in zonedict[key1]:
                    neworder.append(zonedict[key1][key2])
            print_dlgrid = 0
            for airnode_item in neworder:
                if airnode_item.Daylight:
                    print_dlgrid = 1
            if print_dlgrid == 1:
                zone_grid = []
                for airnode_item in neworder:
                    daylight_grid = []
                    for dlitem in airnode_item.Daylight:
                        zone_grid.append("%s %s"%(airnode_item.Zonename,airnode_item.Name))
                        daylight_grid.extend(dlitem.Mesh1)
                        daylight_grid.extend(dlitem.Mesh2)
                        daylight_grid.extend(dlitem.Mesh3)
                        for ix,item in enumerate(daylight_grid):
                            points_string = ''
                            points = []
                            for vitem in item.Vertices:
                                points.append(vitem.Location)
                            for point_item in points:
                                points_string = points_string + ('{0:10f} {1:10f} {2:10f} '.format(point_item[0],point_item[1],point_item[2]))
                            points_string = points_string + '|'
                            zone_grid.append(points_string)
                gridoutput = variants_folder + 'model' + '.grid'
                f = open(gridoutput, 'w')
                for item in zone_grid:
                    f.write(str(item)+'\n')
                f.close()
                #writeillgridfile(res_illuminance,res_illuminance2)
        OpenBuildingFile = False
        if OpenBuildingFile == True and build_mode == 'BUI':
            proc1 = Popen( TRNSYS_path + '\Building\TRNBUILD.exe ' + variants_folder + variant_name + '.b%s'%TRNSYS, shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)

#Starting from here the Variant list is written in append or reset mode
infofile = VARIANTS(variant_name,variants_folder)
darea = 0
dummy = '{0}\t{1}\t{2}\t{3}'.format(darea,infofile.Name,long_variant_name,infofile.Path)
Variantlist = []
Variantlist.append(dummy)
sc.sticky[sc.doc.Path]['Variant'] = Variantlist
Variant = dummy

