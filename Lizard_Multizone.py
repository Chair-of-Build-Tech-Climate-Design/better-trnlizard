import rhinoscriptsyntax as rs
import re
import scriptcontext as sc
import Grasshopper.Kernel as gh
import os
import os.path
import operator
import Rhino as rc
import copy
import math
import ghpythonlib.components as ghcomp
import copy
date = sc.sticky[sc.doc.Path]["date"]
version = '2.3.2'
ghenv.Component.Name = "Lizard_Multizone"
ghenv.Component.NickName = 'Multizone'
ghenv.Component.Category = "TRNLizard"
ghenv.Component.SubCategory = "0 | Project"
rem = gh.GH_RuntimeMessageLevel.Remark
bla = gh.GH_RuntimeMessageLevel.Blank
warn = gh.GH_RuntimeMessageLevel.Warning
errorfound = 0
#---- initial definition start
if "TrnflowNetwork" in locals():
    pass
else:
    TrnflowNetwork = []
if "AutoAdjacency" in locals():
    pass
else:
    AutoAdjacency = None
if "GapTolerance" in locals():
    pass
else:
    GapTolerance = None


class Multizone():
    def __init__(self):
        self.name = "hello"
        self.airnode = Airnode
        self.shading = Shading
        self.adddaylightgeo = AddDaylightGeometry
        self.coupling = Coupling
        self.timebase = Timebase
        self.daylightmode = DaylightMode
        self.trnflownetwork = TrnflowNetwork
        self.autoadjacency = AutoAdjacency
        self.gaptolerance = GapTolerance
        #current_class = self.__class__
    def info(self):
        print self.name
        print ""
    def __repr__(self):
        """
Class representation.
-

Args:
    Airnode (Brep): Script input Airnode.
        Access: list
        Required: True
    Shading (Brep): Script input Shading.
        Access: list
        Required: True
    AddDaylightGeometry (Brep): Script input AddDaylightGeometry.
        Access: list
        Required: True
    Coupling (object): Script input Coupling.
        Access: list
        Required: True
    Timebase (object): Script input Timebase.
        Access: item
        Required: True
    DaylightMode (object): Script input DaylightMode.
        Access: item
        Required: True
    AutoAdjacency (bool): True = surfaces with the category EXTERNAL or BOUNDARY become adjacent where another room faces them, and are split along it; what no room faces keeps its category. Not connected = only surfaces with an empty, AUTOMATIC or ADJACENT category are looked at
        Access: item
        Required: False
    GapTolerance (float): largest distance in m between two parallel surfaces of adjacent rooms, for models with net room volumes. Not connected = 0.02
        Access: item
        Required: False

Returns:
    out (object): Log Information!!!
        Access: item
    Multizone (object): Script output Multizone.
        Access: item
    MismatchedAdjacent (object): Script output MismatchedAdjacent.
        Access: item
    Brep_ (object): Script output Brep_.
        Access: item
"""
        return "{}:{}".format(self.__class__.__name__, self.name)

Multizone = Multizone()
Brep_ = copy.deepcopy(Multizone.airnode)
Brep_.extend(Multizone.shading)

