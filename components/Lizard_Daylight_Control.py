"""
Define the daylight grid and control points.
-
TRNLizard
Copyright (c) 2020 Transsolar Energietechnik GmbH
All Rights Reserved.
See the file "License.txt" for additional terms and conditions.

Args:
    DaylightIll (object): Define the basis for conversion of the exterior lighting level to the inside according to weather data information.
        Access: item
        Required: False
    CtrlMode (object): Operation mode, user interaction or automatic control methods.
        Access: item
        Required: False
    GridPts (Point3d): Connect the points3d that are used for daylight simulation
        Access: list
        Required: False
    GridInfo (object): Script variable Daylight_Control
        Access: item
        Required: False
    BakePts (object): Set this to True in order to see the grid specific Id's of the points in order to select numbers.
        Access: item
        Required: False
    SelectedPts (int): Define the selected grid points that are used to control the lighting mode. Up to 4 locations are possible and the lighting results averaged.
        Access: list
        Required: False
    DaylightFactor (float): Define daylight factor value, if DaylightIll mode is Daylight Factor
        Access: item
        Required: False
    UpperIlluminance (object): Indoor illuminance set point
        Access: item
        Required: False
    LowerIlluminance (object): Script variable Daylight_Control
        Access: item
        Required: False
    AnalysisSchedule (str): Schedule used to post-process *.ill file
        Access: item
        Required: False
    AirnodeAreaFraction (object): Script variable Daylight_Control
        Access: item
        Required: False
    PrintIlluminanceFile (bool): Printing out *.ill file if on True
        Access: item
        Required: False

Returns:
    DaylightCtrl (object): connect to the airnode component - HINT: Press shift key in order to connect multiple outputs to one input node
        Access: item
"""
version='2.2.1'
ghenv.Component.Name = "Lizard_Daylight_Control"
ghenv.Component.NickName = 'Daylight_Control'
ghenv.Component.Message = 'VER 2.2.1\n2020'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "3 | Regime"
import rhinoscriptsyntax as rs
import re
import scriptcontext as sc
import ghpythonlib.components as ghcomp
import Rhino as rc
import System.Guid
import Grasshopper.Kernel as gk
class DLCTRL:
    def __init__(self):
        self.Dctrl = 1
        self.Name = 'DLC'
        self.Illmode = DaylightIll
        self.Value = 0
        self.Illsetpoint1 = UpperIlluminance
        self.Illsetpoint2 = LowerIlluminance
        self.Cntrlmode = CtrlMode
        self.Minpfac = 0.2
        self.Minlfac = 0.2
        self.Geopos1 = 0
        self.Geopos2 = 0
        self.Geopos3 = 0
        self.Geopos4 = 0
        self.Sel1 = 0
        self.Sel2 = 0
        self.Sel3 = 0
        self.Sel4 = 0
        self.Grid = GridPts
        self.Schedule = AnalysisSchedule
        self.Print = PrintIlluminanceFile
        self.Gridinfo = GridInfo
        self.Frac_refarea = 1
    def __repr__(self):
        """Class representation."""
        return "{}:{}".format(self.__class__.__name__, self.Name)
#DaylightCtrl integration
DaylightCtrl = DLCTRL()
GridID = []
layername = 'DAYLIGHT_GRID'
if BakePts == True:
    sc.doc = rc.RhinoDoc.ActiveDoc
    layertable = sc.doc.Layers
    layerindex = layertable.Find('%s'%layername,True)
    if layerindex > 0:
        found_objects = rs.ObjectsByLayer('%s'%layername)
        #rs.DeleteObjects(found_objects)
    else:
        rs.AddLayer('%s'%layername)
        rs.LayerColor('%s'%layername,(234,239,46))
        layer_colour = rs.LayerColor('%s'%layername)
        layer_material = rs.AddMaterialToLayer('%s'%layername)
        rs.MaterialColor(layer_material,layer_colour)
    for ix, item in enumerate(GridPts):
        text = rs.AddTextDot(str(ix+1), item)
        rs.ObjectLayer('%s'%text,'%s'%layername)
    sc.doc = ghdoc
else:
    sc.doc = rc.RhinoDoc.ActiveDoc
    layertable = rs.LayerNames()
    if layername in layertable:
        found_objects = rs.ObjectsByLayer('%s'%layername)
        rs.DeleteObjects(found_objects)
        rs.DeleteLayer('%s'%layername)
    sc.doc = ghdoc
for ix, item in enumerate(SelectedPts):
    if ix == 0:
        DaylightCtrl.Sel1 = item
    if ix == 1:
        DaylightCtrl.Sel2 = item
    if ix == 2:
        DaylightCtrl.Sel3 = item
    if ix == 3:
        DaylightCtrl.Sel4 = item
if DaylightIll == 1:
    DaylightCtrl.Value = DaylightFactor * 100
#if DaylightIll == 2:
#    DaylightCtrl.Value = UdefLuxLevel
if DaylightIll == 3:
    DaylightCtrl.Print = PrintIlluminanceFile
if DaylightCtrl.Print != PrintIlluminanceFile:
    ghenv.Component.AddRuntimeMessage(w, "Please use SensorPts Mode and RunDaylightPreprocessing (System Component) in order to consider the illuminance file being printed!\n No file is printed right now!")
if "AirnodeAreaFraction" in locals() and AirnodeAreaFraction is not None:
    DaylightCtrl.Frac_refarea = AirnodeAreaFraction
